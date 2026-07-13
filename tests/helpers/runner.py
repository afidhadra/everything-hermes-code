"""
Helper utilities for testing EHC scripts and hooks.

Provides structured assertion helpers on top of conftest's run_script/run_hook.
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional


def assert_help(script_path: Path, expected_prefix: str = "usage:") -> str:
    """Verify --help works and returns usage text."""
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, (
        f"{script_path.name} --help exited {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    output = (result.stdout or "") + (result.stderr or "")
    assert expected_prefix in output.lower(), (
        f"{script_path.name} --help missing '{expected_prefix}'\n"
        f"Got: {output[:300]}"
    )
    return output


def assert_imports(script_path: Path) -> None:
    """Verify that a Python script can be imported without errors."""
    import importlib.util
    modname = script_path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(modname, str(script_path))
    assert spec is not None, f"Could not create spec for {script_path.name}"
    assert spec.loader is not None, f"No loader for {script_path.name}"
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        pytest.fail(f"Import of {script_path.name} failed: {e}")


def assert_usage_error(script_path: Path, bad_args: list[str]) -> None:
    """Verify the script exits non-zero with bad/missing arguments."""
    result = subprocess.run(
        [sys.executable, str(script_path)] + bad_args,
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode != 0, (
        f"{script_path.name} {' '.join(bad_args)} should have failed "
        f"but exited 0.\nstdout: {result.stdout[:300]}"
    )


def assert_bash_syntax(hook_path: Path) -> None:
    """Verify a shell script has valid bash syntax."""
    result = subprocess.run(
        ["bash", "-n", str(hook_path)],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, (
        f"{hook_path.name} has bash syntax errors:\n{result.stderr}"
    )


def assert_make_target(project_root: Path, target: str) -> str:
    """Verify a make target runs without error (dry-run mode for dangerous ones)."""
    result = subprocess.run(
        ["make", "-n", target],
        capture_output=True, text=True, timeout=15,
        cwd=str(project_root),
    )
    assert result.returncode == 0, (
        f"make {target} -n exited {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    return result.stdout


# Import pytest only at module level for the assert_imports helper
import pytest
