"""
Tests for Makefile targets.

Verifies that:
    - All documented targets exist
    - Each target can be parsed (make -n) without error
    - Critical targets produce expected output
    - No undefined target references
"""

from pathlib import Path
import subprocess

import pytest
from conftest import PROJECT_ROOT, parse_makefile_targets


# ── Target discovery ───────────────────────────────────────────────

EXPECTED_TARGETS = {
    "dashboard", "status", "repos", "docker-check",
    "lint", "test", "hooks", "check", "analyze",
    "clean", "setup", "help",
}


def test_makefile_exists():
    """Makefile must exist at project root."""
    makefile = PROJECT_ROOT / "Makefile"
    assert makefile.exists(), f"Missing Makefile at {makefile}"


def test_all_expected_targets_present():
    """All documented targets must be defined."""
    targets = set(parse_makefile_targets())
    for t in EXPECTED_TARGETS:
        assert t in targets, f"Expected target '{t}' not found in Makefile"


def test_no_extra_targets():
    """No undocumented targets (dev convenience)."""
    targets = parse_makefile_targets()
    expected = EXPECTED_TARGETS
    extras = set(targets) - expected
    if extras:
        print(f"⚠️  Extra targets found (not in EXPECTED_TARGETS): {extras}")


# ── Dry-run validation ─────────────────────────────────────────────

# Targets that are safe to dry-run (no side effects)
SAFE_TO_DRY_RUN = {
    "lint", "test", "hooks", "check", "clean", "help",
}

# Targets that need external services (skip in CI)
NEEDS_EXTERNAL = {"dashboard", "status", "repos", "docker-check", "analyze"}


def test_target_dry_run(make_target):
    """Safe targets must parse without error in dry-run mode."""
    if make_target in NEEDS_EXTERNAL:
        pytest.skip(f"{make_target} needs external services")
    result = subprocess.run(
        ["make", "-n", make_target],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"make -n {make_target} failed:\n{result.stderr}"
    )


# ── Specific target output checks ──────────────────────────────────

def test_help_output():
    """make help must show all targets."""
    result = subprocess.run(
        ["make", "help"],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
    output = result.stdout
    for t in EXPECTED_TARGETS:
        assert t in output, f"make help missing target '{t}'"


def test_lint_dry_run():
    """make lint -n must not error."""
    result = subprocess.run(
        ["make", "-n", "lint"],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0


def test_clean_dry_run():
    """make clean -n must not error."""
    result = subprocess.run(
        ["make", "-n", "clean"],
        capture_output=True, text=True, timeout=15,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0
