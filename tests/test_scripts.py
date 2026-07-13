
"""
Auto-discovered tests for all Python scripts in scripts/.

Adding a new .py file to scripts/ automatically generates test cases
for it — no edits needed in this file.

Test categories per script:
    1. Import succeeds without errors
    2. --help or --usage produces valid output (or script is known non-CLI)
    3. Bad/missing args produce non-zero exit (for scripts that require args)
    4. --dry-run works (for scripts that support it)
"""

from pathlib import Path

import pytest
from helpers.runner import assert_help, assert_usage_error, assert_imports
from conftest import SCRIPTS_DIR, run_script


# ── Script classification ──────────────────────────────────────────

# Scripts that are modules/libraries, not CLI entry points
MODULE_ONLY_SCRIPTS = {
    "ehc_config.py",
}

# Scripts with no CLI usage output (direct execution, no help)
NO_USAGE_SCRIPTS = {
    "fix-markdown.py",   # runs directly with optional path, no --help
}

# Scripts that accept zero required arguments
ZERO_ARGS_SCRIPTS = {
    "fix-markdown.py",       # optional path arg, no argparse
    "docker-check.py",       # optional --config
    "ehc.py",                # optional --config / --list / --watch
    "ehc_config.py",         # module, not CLI
    "repo-status.py",        # optional --json
    "deploy.py",             # defaults to --status when no args
    "regression-analyzer.py", # defaults to scanning HEAD~1
}

# Scripts that require at least one positional/required argument
REQUIRES_ARGS = {
    "orchestrator.py",        # requires task positional
    "agent-runner.py",        # custom parser: exits 0 with usage print
    "command-runner.py",      # custom parser: exits 0 with usage print
    "cross-repo-auditor.py",  # requires --be and --fe
}

# Scripts with non-argparse CLI (custom parsing, prints usage but exits 0)
CUSTOM_PARSER_SCRIPTS = {
    "agent-runner.py",
    "command-runner.py",
    "fix-markdown.py",
}

# Scripts that support --dry-run
DRY_RUN_SCRIPTS = {
    "orchestrator.py",
    "deploy.py",
    "regression-analyzer.py",
}


# ── Import test ────────────────────────────────────────────────────

def test_script_imports(script_path: Path):
    """Every script in scripts/ must be importable without errors."""
    assert_imports(script_path)


# ── --help test ────────────────────────────────────────────────────

def test_script_help(script_path: Path):
    """Every CLI script must produce usage output.

    Some scripts use argparse (--help), others have custom usage printing.
    Modules are skipped.
    """
    name = script_path.name
    if name in MODULE_ONLY_SCRIPTS:
        pytest.skip(f"{name} is a module, not a CLI")
    if name in NO_USAGE_SCRIPTS:
        pytest.skip(f"{name} has no --help or usage output")
    if name in CUSTOM_PARSER_SCRIPTS:
        # Custom parsers print usage to stdout, exit 0
        result = run_script(script_path, [], expected_code=None)
        assert "Usage" in result or "usage" in result, (
            f"{name}: expected 'Usage' in output, got:\n{result[:300]}"
        )
        return
    # Standard argparse scripts
    assert_help(script_path)


# ── Argument enforcement ───────────────────────────────────────────

def test_script_empty_args_fails(script_path: Path):
    """Scripts that need args should indicate usage when run with no arguments.

    Some scripts show usage and exit 0 (custom parser design).
    Those are OK as long as they show usage text.
    """
    name = script_path.name
    if name in MODULE_ONLY_SCRIPTS:
        pytest.skip(f"{name} is a module")
    if name in ZERO_ARGS_SCRIPTS:
        pytest.skip(f"{name} accepts zero required args")
    if name in CUSTOM_PARSER_SCRIPTS:
        # Custom parsers show usage and exit 0 — verify usage text is shown
        result = run_script(script_path, [], expected_code=None)
        assert "Usage" in result or "usage" in result, (
            f"{name}: expected usage output with no args, got:\n{result[:300]}"
        )
        return
    # Standard argparse scripts should fail with no args
    assert_usage_error(script_path, [])


# ── Dry-run capability ─────────────────────────────────────────────

def test_script_dry_run(script_path: Path):
    """Scripts with --dry-run should accept it without error."""
    name = script_path.name
    if name not in DRY_RUN_SCRIPTS:
        pytest.skip(f"{name} has no --dry-run")

    # Some scripts need required args even in dry-run mode
    extra_args = []
    if name == "orchestrator.py":
        extra_args = ["review"]
    elif name == "cross-repo-auditor.py":
        # Required: --be and --fe even in dry-run
        extra_args = ["--be", "/tmp/dummy-be", "--fe", "/tmp/dummy-fe"]

    run_script(script_path, ["--dry-run"] + extra_args, expected_code=0)
