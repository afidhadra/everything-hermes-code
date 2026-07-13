#!/usr/bin/env python3
"""
PR Review Bot — automated code review for GitHub pull requests.

Fetches PR diff, analyzes for regressions, security issues, and code
quality, then posts a structured review to GitHub.

Usage:
    python3 pr-review.py --pr 5                        # Review PR #5
    python3 pr-review.py --pr 5 --dry-run              # Analyze only
    python3 pr-review.py --pr 5 --json                 # JSON output
    python3 pr-review.py --all-open                    # All open PRs
    python3 pr-review.py --pr 5 --event approve        # Force approve
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Paths ──────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_DIR / "scripts"
REPORTS_DIR = REPO_DIR / "reports"


# ── GH CLI wrapper ─────────────────────────────────────────────────

def gh(*args: str, repo: Optional[str] = None) -> str:
    """Run gh CLI command and return stdout."""
    cmd = ["gh"]
    if repo:
        cmd.extend(["--repo", repo])
    cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError("gh CLI not found. Install from https://cli.github.com/")


def detect_repo() -> str:
    """Detect GitHub repo from current directory's git remote."""
    try:
        remote = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        # Parse: git@github.com:user/repo.git or https://github.com/user/repo
        m = re.search(r"(?:github\.com[:/])([\w.-]+/[\w.-]+?)(?:\.git)?$", remote)
        if m:
            return m.group(1)
    except Exception:
        pass
    raise RuntimeError("Could not detect GitHub repo from git remote")


# ── PR Data ────────────────────────────────────────────────────────

def fetch_pr_info(pr_number: int, repo: str) -> dict:
    """Fetch PR metadata as JSON."""
    raw = gh("pr", "view", str(pr_number), "--json",
             "number,title,body,author,files,additions,deletions,"
             "state,baseRefName,headRefName,createdAt,labels,merged",
             repo=repo)
    return json.loads(raw)


def fetch_pr_diff(pr_number: int, repo: str) -> str:
    """Fetch PR diff text."""
    return gh("pr", "diff", str(pr_number), repo=repo)


def fetch_pr_files(pr_number: int, repo: str) -> list[dict]:
    """Fetch list of changed files with stats."""
    info = fetch_pr_info(pr_number, repo)
    return info.get("files", [])


# ── Analysis Pipeline ──────────────────────────────────────────────

EXTENSION_MAP = {
    ".go": "go", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".vue": "vue",
    ".py": "python", ".rs": "rust", ".java": "java",
    ".sql": "sql", ".yaml": "yaml", ".yml": "yaml",
    ".json": "json", ".md": "markdown", ".css": "css",
    ".scss": "scss", ".html": "html",
}

SECURITY_PATTERNS = {
    "hardcoded_secret": {
        "pattern": r'(?i)(?:password|secret|api[_-]?key|token|credential)\s*[:]?\s*=\s*["\'](?!\$\{|<)[^"\']+["\']',
        "severity": "critical",
        "message": "Potential hardcoded credential — use environment variable or secret manager",
    },
    "sql_injection": {
        "pattern": r'(?i)(?:Exec|Query|ExecContext|QueryRow)\s*\(.*?(?:fmt\.Sprintf|fmt\.Fprintf|\+|raw)',
        "severity": "critical",
        "message": "Possible SQL injection — use parameterized queries",
    },
    "eval_usage": {
        "pattern": r'(?i)\beval\s*\(',
        "severity": "high",
        "message": "eval() can execute arbitrary code — avoid if possible",
    },
    "debug_endpoint": {
        "pattern": r'(?i)(?:/debug|/health|/metrics|pprof)',
        "severity": "medium",
        "message": "Debug/health endpoint exposed — ensure it's behind auth in production",
    },
    "todo_comment": {
        "pattern": r'(?i)(?:TODO|FIXME|HACK|XXX|BUG)\s*[:]?(?!\s*\(#\d+\))',
        "severity": "info",
        "message": "TODO/FIXME found — consider creating an issue before merge",
    },
    "console_log": {
        "pattern": r'(?i)console\.(?:log|debug|warn|error)\s*\(',
        "severity": "info",
        "message": "Console log statement — should be removed in production code",
    },
}


def analyze_security(diff_text: str) -> list[dict]:
    """Scan diff for security patterns."""
    findings = []
    for name, rule in SECURITY_PATTERNS.items():
        for m in re.finditer(rule["pattern"], diff_text):
            # Find which file
            line_num = diff_text[:m.start()].count("\n") + 1
            findings.append({
                "type": name,
                "severity": rule["severity"],
                "line": line_num,
                "message": rule["message"],
                "snippet": m.group()[:80],
            })
    return findings


def analyze_code_quality(files: list[dict]) -> list[dict]:
    """Analyze changed files for code quality issues."""
    findings = []
    for f in files:
        path = f.get("path", "")
        ext = Path(path).suffix.lower()
        lang = EXTENSION_MAP.get(ext)

        if not lang:
            continue

        # Go-specific
        if lang == "go":
            if f.get("additions", 0) > 200 and "test" not in path:
                findings.append({
                    "type": "large_file",
                    "severity": "medium",
                    "file": path,
                    "message": f"Large file ({f['additions']} additions). Consider splitting.",
                })

        # General
        if f.get("additions", 0) > 500:
            findings.append({
                "type": "massive_pr",
                "severity": "medium",
                "file": path,
                "message": f"Massive change ({f['additions']} lines). Consider smaller PRs.",
            })

    return findings


def analyze_dependencies(files: list[dict], diff_text: str) -> list[dict]:
    """Analyze dependency changes (go.mod, package.json, etc.)."""
    findings = []
    dep_files = [f for f in files if f.get("path", "").endswith(
        ("go.mod", "go.sum", "package.json", "pnpm-lock.yaml", "requirements.txt")
    )]
    for f in dep_files:
        path = f.get("path", "")
        if f.get("additions", 0) > 0:
            findings.append({
                "type": "dependency_change",
                "severity": "info",
                "file": path,
                "message": f"Dependencies modified ({f['additions']} added, {f['deletions']} removed). Verify compatibility.",
            })
    return findings


def run_regression_analysis(diff_text: str, repo_path: str) -> list[dict]:
    """Run regression-analyzer logic if available."""
    findings = []
    analyzer = SCRIPTS_DIR / "regression-analyzer.py"
    if not analyzer.exists():
        return findings

    # Count files changed
    file_count = len(set(
        re.findall(r'^\+\+\+\s+(?:b/)?(.+)$', diff_text, re.MULTILINE)
    ))

    if file_count > 10:
        findings.append({
            "type": "regression_risk",
            "severity": "medium",
            "message": f"Large diff ({file_count} files) — high regression risk. "
                       f"Ensure thorough testing.",
        })

    # Check for risky keywords
    risky_patterns = [
        (r'\bpanic\b', "info", "panic() call found — ensure it's intentional"),
        (r'\bdangerous\b', "high", "DANGEROUS marker in diff — investigate"),
        (r'\bFIXME\b', "info", "FIXME marker — should be resolved before merge"),
    ]
    for pattern, severity, msg in risky_patterns:
        if re.search(pattern, diff_text):
            findings.append({
                "type": "code_smell",
                "severity": severity,
                "message": msg,
            })

    return findings


def analyze_pr(pr_number: int, repo: str, repo_path: Optional[str] = None) -> dict:
    """Run full analysis pipeline on a PR."""
    info = fetch_pr_info(pr_number, repo)
    diff = fetch_pr_diff(pr_number, repo)
    files = info.get("files", [])

    findings = []
    findings.extend(analyze_security(diff))
    findings.extend(analyze_code_quality(files))
    findings.extend(analyze_dependencies(files, diff))
    findings.extend(run_regression_analysis(diff, repo_path or str(REPO_DIR)))

    # Categorize
    critical = [f for f in findings if f["severity"] == "critical"]
    high = [f for f in findings if f["severity"] == "high"]
    medium = [f for f in findings if f["severity"] == "medium"]
    info_findings = [f for f in findings if f["severity"] == "info"]

    # Determine event
    if critical:
        event = "REQUEST_CHANGES"
    elif high:
        event = "REQUEST_CHANGES"
    elif medium:
        event = "COMMENT"
    else:
        event = "APPROVE"

    return {
        "pr": info,
        "diff_preview": diff[:2000],  # First 2000 chars for context
        "findings": findings,
        "summary": {
            "critical": len(critical),
            "high": len(high),
            "medium": len(medium),
            "info": len(info_findings),
            "total_changed_files": len(files),
            "total_additions": info.get("additions", 0),
            "total_deletions": info.get("deletions", 0),
        },
        "recommended_event": event,
        "analyzed_at": datetime.now().isoformat(),
    }


# ── Review Generation ──────────────────────────────────────────────

def generate_review_markdown(analysis: dict) -> str:
    """Generate formatted review markdown."""
    s = analysis["summary"]
    findings = analysis["findings"]
    pr = analysis["pr"]
    event = analysis["recommended_event"]

    event_icon = {"APPROVE": "✅", "COMMENT": "💬", "REQUEST_CHANGES": "❌"}
    risk_level = {
        "APPROVE": "LOW",
        "COMMENT": "MEDIUM",
        "REQUEST_CHANGES": "HIGH",
    }

    lines = [
        f"## 🔍 Automated PR Review — #{pr['number']}",
        "",
        f"**{pr['title']}**",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Files changed | {s['total_changed_files']} |",
        f"| Lines added | {s['total_additions']} |",
        f"| Lines removed | {s['total_deletions']} |",
        f"| Risk level | **{risk_level.get(event, 'UNKNOWN')}** {event_icon.get(event, '')} |",
        f"| Findings | 🔴 {s['critical']} critical · 🟡 {s['high']} high · 🟠 {s['medium']} medium · 🟢 {s['info']} info |",
        f"| Verdict | **{event}** |",
        "",
    ]

    if event == "REQUEST_CHANGES":
        lines.append("> ❌ **This PR has critical/high issues that should be addressed before merging.**")
        lines.append("")

    # Group findings by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    severity_labels = {
        "critical": ("🔴 Critical", "### 🔴 Critical"),
        "high": ("🟡 High", "### 🟡 High"),
        "medium": ("🟠 Medium", "### 🟠 Medium"),
        "info": ("🟢 Info", "### 🟢 Info"),
    }

    findings.sort(key=lambda f: severity_order.get(f["severity"], 99))

    current_sev = None
    for f in findings:
        if f["severity"] != current_sev:
            current_sev = f["severity"]
            label, heading = severity_labels.get(current_sev, ("Unknown", "### Unknown"))
            lines.append("")
            lines.append(heading)
            lines.append("")
            lines.append(f"| Severity | Location | Finding |")
            lines.append(f"|----------|----------|---------|")

        # Location: file or diff line
        loc = f.get("file", f.get("line", "?"))
        if isinstance(loc, int):
            loc = f":{loc}"

        # Snippet preview
        snippet = f.get("snippet", "")
        msg = f["message"]
        if snippet:
            msg += f" (`{snippet}`)"

        lines.append(f"| {label} | {loc} | {msg} |")

    if not findings:
        lines.append("")
        lines.append("No issues found. ✅")
        lines.append("")

    lines.extend([
        "",
        "---",
        "",
        f"_Auto-reviewed by PR Review Bot · {analysis['analyzed_at'][:19]}_",
        "",
    ])

    return "\n".join(lines)


# ── Post Review ────────────────────────────────────────────────────

def post_review(pr_number: int, repo: str, body: str,
                event: str = "COMMENT") -> bool:
    """Post review to GitHub PR using gh CLI."""
    try:
        # Write body to temp file (avoid shell escaping issues)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                         delete=False) as f:
            f.write(body)
            tmp_path = f.name

        cmd = [
            "gh", "pr", "review", str(pr_number),
            "--repo", repo,
            "--body", f"@{tmp_path}",
            "--event", event,
        ]
        # gh doesn't support @file, so use stdin instead
        result = subprocess.run(
            ["gh", "pr", "review", str(pr_number),
             "--repo", repo, "--body", body, "--event", event],
            capture_output=True, text=True, timeout=30,
        )
        os.unlink(tmp_path)

        if result.returncode != 0:
            print(f"  ❌ Failed to post review: {result.stderr.strip()}",
                  file=sys.stderr)
            return False
        print(f"  ✅ Review posted: {event}")
        return True
    except Exception as e:
        print(f"  ❌ Error posting review: {e}", file=sys.stderr)
        return False


# ── Output ─────────────────────────────────────────────────────────

def print_review_table(analysis: dict):
    """Print a formatted summary table to terminal."""
    s = analysis["summary"]
    event = analysis["recommended_event"]
    pr = analysis["pr"]

    event_colors = {
        "APPROVE": "\033[32m",       # green
        "COMMENT": "\033[33m",       # yellow
        "REQUEST_CHANGES": "\033[31m",  # red
    }
    color = event_colors.get(event, "\033[0m")
    reset = "\033[0m"

    print()
    print(f"  🔍 PR #{pr['number']}: {pr['title']}")
    print(f"  {'─' * 50}")
    print(f"  Files:     {s['total_changed_files']} changed "
          f"(+{s['total_additions']}/-{s['total_deletions']})")
    print(f"  Findings:  "
          f"\033[31m{s['critical']} critical\033[0m · "
          f"\033[33m{s['high']} high\033[0m · "
          f"\033[35m{s['medium']} medium\033[0m · "
          f"\033[36m{s['info']} info\033[0m")
    print(f"  Verdict:   {color}{event}\033[0m")
    print(f"  {'─' * 50}")

    # List findings
    if analysis["findings"]:
        for f in analysis["findings"][:10]:  # top 10
            icon = {"critical": "🔴", "high": "🟡", "medium": "🟠", "info": "🟢"}
            loc = f.get("file", f.get("line", ""))
            print(f"  {icon.get(f['severity'], '•')} [{f['severity']}] "
                  f"{loc} — {f['message'][:60]}")
        if len(analysis["findings"]) > 10:
            print(f"  ... and {len(analysis['findings']) - 10} more findings")
    else:
        print(f"  ✅ No issues found")

    print()


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PR Review Bot — automated code review for GitHub PRs"
    )
    parser.add_argument("--pr", type=int, default=None,
                        help="PR number to review")
    parser.add_argument("--repo", type=str, default=None,
                        help="GitHub repo (user/repo). Auto-detected from git remote")
    parser.add_argument("--all-open", action="store_true",
                        help="Review all open PRs in the repo")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze only — don't post review")
    parser.add_argument("--json", action="store_true",
                        help="Output analysis as JSON")
    parser.add_argument("--event", type=str, default=None,
                        choices=["APPROVE", "COMMENT", "REQUEST_CHANGES"],
                        help="Override review event decision")
    args = parser.parse_args()

    # Detect repo if not specified
    repo = args.repo or detect_repo()

    # Collect PR numbers
    pr_numbers = []
    if args.pr:
        pr_numbers = [args.pr]
    elif args.all_open:
        raw = gh("pr", "list", "--state", "open", "--json", "number",
                 repo=repo)
        prs = json.loads(raw)
        pr_numbers = [p["number"] for p in prs]
        if not pr_numbers:
            print(f"  ℹ️  No open PRs in {repo}")
            return
    else:
        parser.print_help()
        print("\nError: specify --pr <number> or --all-open")
        sys.exit(1)

    # Analyze each PR
    all_results = []
    for num in pr_numbers:
        print(f"\n📋 Analyzing PR #{num} in {repo}...")

        try:
            analysis = analyze_pr(num, repo)
            all_results.append(analysis)

            if args.json:
                # Print individual PR JSON
                print(json.dumps(analysis, indent=2, default=str))
                continue

            # Print table
            print_review_table(analysis)

            # Post review
            if not args.dry_run and not args.json:
                event = args.event or analysis["recommended_event"]
                review_body = generate_review_markdown(analysis)

                print(f"  📝 Posting review as '{event}'...")
                ok = post_review(num, repo, review_body, event)

                # Save report
                if ok:
                    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
                    report_path = REPORTS_DIR / f"pr-review-{num}.md"
                    report_path.write_text(review_body)
                    print(f"  📄 Report saved to: {report_path}")

                print()

        except Exception as e:
            print(f"  ❌ Error analyzing PR #{num}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()

    # Summary for multiple PRs
    if len(all_results) > 1 and not args.json:
        print()
        print("=" * 50)
        print("  SUMMARY")
        print("=" * 50)
        for r in all_results:
            p = r["pr"]
            print(f"  #{p['number']}: {r['recommended_event']} "
                  f"({r['summary']['critical']}C/{r['summary']['high']}H)")
        print()

    # JSON array for multiple
    if args.json and len(all_results) > 1:
        print(json.dumps(all_results, indent=2, default=str))


if __name__ == "__main__":
    main()
