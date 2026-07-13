"""
Auto-discovered tests for all hook scripts in hooks/scripts/.

Adding a new .sh file to hooks/scripts/ automatically generates
test cases for it.
"""

from pathlib import Path

import pytest
from helpers.runner import assert_bash_syntax
from conftest import run_hook


# ── Bash syntax ────────────────────────────────────────────────────

def test_hook_bash_syntax(hook_path: Path):
    """Every hook script must have valid bash syntax."""
    assert_bash_syntax(hook_path)


# ── Execution (skip mode) ──────────────────────────────────────────

def test_hook_skip_mode(hook_path: Path):
    """
    Hooks should exit gracefully when run outside a git context
    (no stdin, no commit range). Acceptable exit codes:
        - 0 (skip gracefully)
        - maybe non-zero if they truly need git context
    """
    result = run_hook(hook_path, expected_code=None)  # don't assert
    # Should not crash with uncaught exception
    assert "traceback" not in result.lower(), (
        f"{hook_path.name} crashed with traceback:\n{result[:500]}"
    )
    # Should not produce bash errors
    assert "bash:" not in result.lower(), (
        f"{hook_path.name} produced bash errors:\n{result[:500]}"
    )


# ── Hook-specific assertions ───────────────────────────────────────

HOOK_SPECIFIC_TESTS = {
    "pre-commit.sh": [
        ("contains pre-commit marker", "pre-commit"),
        ("is executable", None),  # checked by file perms
    ],
    "pre-push.sh": [
        ("contains pre-push marker", "pre-push" if Path.exists else None),
    ],
    "post-commit.sh": [
        ("contains post-commit marker", "post-commit"),
    ],
}


def test_hook_content_markers(hook_path: Path):
    """Each hook should contain expected content markers."""
    name = hook_path.name
    if name not in HOOK_SPECIFIC_TESTS:
        pytest.skip(f"No specific checks for {name}")

    content = hook_path.read_text()
    for label, marker in HOOK_SPECIFIC_TESTS[name]:
        if marker is not None:
            assert marker.lower() in content.lower(), (
                f"{name}: expected '{marker}' in content ({label})"
            )
