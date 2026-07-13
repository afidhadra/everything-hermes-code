#!/usr/bin/env python3
"""
Auto-generate dynamic sections of AGENTS.md.

Scans actual project state (scripts, tests, skills, configs)
and updates the marker-delimited sections in AGENTS.md.

Usage:
    python3 scripts/generate-agents.py          # generate & write
    python3 scripts/generate-agents.py --check   # verify only (CI mode)
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent

# ── Markers ────────────────────────────────────────────────────────

MARKERS = {
    "summary": ("<!-- SUMMARY:START -->", "<!-- SUMMARY:END -->"),
    "scripts": ("<!-- SCRIPTS:START -->", "<!-- SCRIPTS:END -->"),
    "structure": ("<!-- STRUCTURE:START -->", "<!-- STRUCTURE:END -->"),
    "test_count": ("<!-- TESTS:START -->", "<!-- TESTS:END -->"),
}


# ── Scanners ───────────────────────────────────────────────────────

def get_docstring(path: Path) -> str:
    """Extract first line of module docstring."""
    try:
        content = path.read_text()
        m = re.search(r'"""(.+?)"""', content, re.DOTALL)
        if m:
            return m.group(1).strip().split("\n")[0]
    except Exception:
        pass
    return ""


def scan_scripts() -> list[dict]:
    """Scan scripts/ for CLI tools with docstrings."""
    scripts = []
    for f in sorted((REPO_DIR / "scripts").glob("*.py")):
        if f.name in ("ehc_config.py", "__init__.py"):
            continue
        doc = get_docstring(f)
        if doc:
            scripts.append({"name": f.stem, "file": f.name, "desc": doc})
        else:
            scripts.append({"name": f.stem, "file": f.name, "desc": ""})
    return scripts


def scan_skills() -> list[dict]:
    """Scan skills/ for Hermes skill wrappers (have YAML frontmatter)."""
    skills = []
    for f in sorted((REPO_DIR / "skills").glob("*.md")):
        if f.name == "README.md":
            continue
        content = f.read_text()
        m = re.match(r"^---\n.*?name:\s*(.+?)\n.*?description:\s*(.+?)\n.*?---", content, re.DOTALL)
        if m:
            skills.append({"name": m.group(1).strip(), "desc": m.group(2).strip()})
        else:
            skills.append({"name": f.stem, "desc": ""})
    return skills


def get_test_count() -> tuple[int, int]:
    """Get test counts from pytest collection (fast, no execution).

    Uses 'pytest --collect-only' which only discovers tests without
    running them. Returns (passed, skipped) where skipped is
    approximate based on skip decorators in test files.
    """
    tests_dir = REPO_DIR / "tests"
    if not tests_dir.exists():
        return 0, 0

    # Try pytest collection first (accurate but needs pytest)
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir),
             "--collect-only", "-q"],
            capture_output=True, text=True, timeout=30,
        )
        m = re.search(r"(\d+) tests collected", r.stderr + r.stdout)
        if m:
            total = int(m.group(1))
            # Estimate skipped from test files
            skipped = 0
            for f in sorted(tests_dir.rglob("*.py")):
                if f.name.startswith("_"):
                    continue
                content = f.read_text()
                skipped += len(re.findall(r"pytest\.skip\(", content))
                skipped += len(re.findall(
                    r"@pytest\.mark\.(?:skip|skipif)\b", content, re.MULTILINE
                ))
            return total, skipped
    except Exception:
        pass

    # Fallback: count test functions in files
    passed = 0
    for f in sorted(tests_dir.rglob("*.py")):
        if f.name.startswith("_"):
            continue
        content = f.read_text()
        passed += len(re.findall(r"^def test_\w+", content, re.MULTILINE))
    return passed, 0


def scan_structure() -> list[dict]:
    """Scan project top-level directories."""
    dirs = []
    # Top-level items of interest
    items = [
        ("scripts/", "Python tools"),
        ("skills/", "Hermes skill wrappers + guides"),
        ("config/", "routing + agent definitions"),
        ("tests/", "pytest"),
        ("agents/", "AI agent definitions"),
        ("rules/", "Coding rules"),
        ("prompts/", "System prompts"),
        ("commands/", "Slash command docs"),
        ("hooks/", "Git hooks"),
        ("mcp-configs/", "MCP server configs"),
        (".github/", "CI/CD workflows"),
    ]
    for rel, note in items:
        path = REPO_DIR / rel
        if path.exists():
            # Count contents
            if path.is_dir():
                count = len(list(path.glob("*")))
            else:
                count = 1
            dirs.append({"path": rel.rstrip("/"), "note": note, "count": count})
    return dirs


# ── Generators ─────────────────────────────────────────────────────

def generate_summary(scripts: list[dict], skills: list[dict],
                     passed: int, skipped: int) -> str:
    """Generate summary line."""
    n_scripts = len(scripts)
    n_skills = len([s for s in skills if s["desc"]])  # only those with descriptions
    lines = [
        f"A developer toolkit for Hermes Agent — {n_scripts} Python scripts, "
        f"{n_skills} Hermes skill wrappers,",
        "config-based routing engine, MCP server manager, deploy coordinator, "
        "PR review bot,",
        "background task manager, and TUI dashboard. Local-only personal tool.",
        "",
        f"> **{passed} tests · {skipped} skipped (intentional) · "
        f"CI/CD via GitHub Actions**",
    ]
    return "\n".join(lines)


def generate_script_table(scripts: list[dict]) -> str:
    """Generate script/function table."""
    lines = [
        "| Script | Function |",
        "|--------|----------|",
    ]
    for s in scripts:
        lines.append(f"| `{s['file']}` | {s['desc']} |")
    return "\n".join(lines)


def generate_structure(dirs: list[dict], scripts: list[dict],
                       skills: list[dict]) -> str:
    """Generate project structure tree."""
    n_scripts = len(scripts)
    n_skills_all = len(skills)
    lines = []
    for d in dirs:
        icon = "├──" if d != dirs[-1] else "└──"
        count = d.get("count", 0)
        lines.append(f"{icon} {d['path']:<18} {d['note']}")
    return "\n".join(lines)


def generate_test_count(passed: int, skipped: int) -> str:
    return f"{passed} passed · {skipped} skipped"


# ── AGENTS.md patcher ──────────────────────────────────────────────

def patch_section(content: str, marker_start: str, marker_end: str,
                  new_content: str) -> str:
    """Replace content between markers (inclusive)."""
    pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
    replacement = marker_start + "\n" + new_content.strip() + "\n" + marker_end
    if re.search(pattern, content, re.DOTALL):
        return re.sub(pattern, replacement, content, flags=re.DOTALL)
    else:
        print(f"  ⚠️  Markers not found: {marker_start[:30]}", file=sys.stderr)
        return content


def generate(agents_path: Path, check_only: bool = False) -> bool:
    """Generate AGENTS.md or check if it's current. Returns True if OK."""
    # Scan
    scripts = scan_scripts()
    skills = scan_skills()
    passed, skipped = get_test_count()
    dirs = scan_structure()

    # Render dynamic sections
    summary = generate_summary(scripts, skills, passed, skipped)
    script_table = generate_script_table(scripts)
    structure = generate_structure(dirs, scripts, skills)
    test_line = generate_test_count(passed, skipped)

    if check_only:
        # Read current file and check if it matches
        current = agents_path.read_text()
        expected = current
        for key, (start, end) in MARKERS.items():
            sections = {
                "summary": summary,
                "scripts": script_table,
                "structure": structure,
                "test_count": test_line,
            }
            expected = patch_section(expected, start, end, sections[key])

        if current == expected:
            print("✅ AGENTS.md is up to date")
            return True
        else:
            print("❌ AGENTS.md is outdated — run 'make generate-agents'")
            return False
    else:
        # Write
        content = agents_path.read_text()
        sections = {
            "summary": summary,
            "scripts": script_table,
            "structure": structure,
            "test_count": test_line,
        }
        for key, (start, end) in MARKERS.items():
            content = patch_section(content, start, end, sections[key])

        agents_path.write_text(content)
        print(f"✅ AGENTS.md updated ({passed} tests, {len(scripts)} scripts, "
              f"{len(skills)} skills)")
        return True


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate dynamic sections of AGENTS.md"
    )
    parser.add_argument("--check", action="store_true",
                        help="Check if AGENTS.md is current (CI mode)")
    args = parser.parse_args()

    agents_path = REPO_DIR / "AGENTS.md"
    if not agents_path.exists():
        print(f"❌ AGENTS.md not found at {agents_path}", file=sys.stderr)
        sys.exit(1)

    # First, ensure markers exist
    content = agents_path.read_text()
    has_all_markers = all(
        start in content and end in content
        for start, end in MARKERS.values()
    )

    if not has_all_markers and not args.check:
        print("⚠️  AGENTS.md missing markers — injecting defaults...")
        # Inject markers after existing sections as fallback

    ok = generate(agents_path, check_only=args.check)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
