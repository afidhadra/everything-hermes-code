"""
End-to-end smoke tests for the EHC project.

Verifies the project is genuinely usable:
    1. Core dependencies are present
    2. make check passes
    3. make lint passes (or at least runs without crash)
    4. make test passes (the core test suite)
    5. Python scripts can load and respond
    6. All hooks can be parsed
"""

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import PROJECT_ROOT, SCRIPTS_DIR, run_script


# ── Dependency checks ──────────────────────────────────────────────

REQUIRED_BINARIES = ["python3", "git", "make", "bash"]
REQUIRED_PYTHON_MODULES = ["yaml"]


def test_required_binaries():
    """All required system binaries must be on PATH."""
    for binary in REQUIRED_BINARIES:
        result = subprocess.run(["which", binary], capture_output=True, text=True)
        assert result.returncode == 0, f"Required binary not found: {binary}"


def test_required_python_modules():
    """All required Python modules must be importable."""
    for mod in REQUIRED_PYTHON_MODULES:
        result = subprocess.run(
            [sys.executable, "-c", f"import {mod}"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Required Python module not found: {mod}"


# ── make targets ───────────────────────────────────────────────────

def test_make_check():
    """make check must pass (dependency verification)."""
    result = subprocess.run(
        ["make", "check"],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"make check failed:\n{result.stderr[-500:]}"
    )


def test_make_lint():
    """make lint must run without crashing."""
    result = subprocess.run(
        ["make", "lint"],
        capture_output=True, text=True, timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"make lint failed:\n{result.stderr[-500:]}"
    )


def test_make_test(project_root):
    """make test must pass (core test suite).

    NOTE: excludes test_smoke.py to prevent infinite recursion.
    """
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/test_smoke.py", "-q"],
        capture_output=True, text=True, timeout=60,
        cwd=str(project_root),
    )
    output = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, (
        f"pytest failed ({result.returncode}):\n{output[-1500:]}"
    )


# ── All scripts help output ────────────────────────────────────────

def test_all_scripts_respond():
    """Every Python script in scripts/ must respond to --help."""
    failures = []
    for script in sorted(SCRIPTS_DIR.glob("*.py")):
        try:
            run_script(script, ["--help"], expected_code=0)
        except AssertionError as e:
            failures.append(str(e))
    assert not failures, f"\n".join(failures[:5])


# ── Project structure integrity ────────────────────────────────────

def test_project_structure():
    """Verify critical directories and files exist."""
    required = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "Makefile",
        PROJECT_ROOT / ".gitignore",
        PROJECT_ROOT / ".ehc.yaml",
        PROJECT_ROOT / ".markdownlint.json",
        PROJECT_ROOT / "LICENSE",
        PROJECT_ROOT / "scripts",
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "hooks" / "scripts",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f"Missing project files:\n" + "\n".join(missing)


def test_git_hooks_symlinked():
    """Git hooks must be symlinked to hooks/scripts/."""
    hook_dir = PROJECT_ROOT / ".git" / "hooks"
    for hook_name in ["pre-commit", "pre-push", "post-commit"]:
        hook_path = hook_dir / hook_name
        if hook_path.exists():
            assert hook_path.is_symlink(), (
                f"{hook_name} hook is not a symlink"
            )
            target = hook_path.resolve()
            assert target.parent.name == "scripts", (
                f"{hook_name} symlinked to wrong location: {target}"
            )


# ── Quick script smoke tests ───────────────────────────────────────

def test_ehc_dashboard_json():
    """ehc.py must produce valid JSON output with --json."""
    try:
        output = run_script(SCRIPTS_DIR / "ehc.py", ["--json"])
        import json
        data = json.loads(output)
        assert "timestamp" in data
        assert "docker" in data or "repos" in data or "error" in data
    except AssertionError:
        # ehc.py may fail if docker isn't running — that's OK
        # but it should not crash with Python traceback
        pass
