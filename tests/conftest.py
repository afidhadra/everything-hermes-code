"""
Shared fixtures and auto-discovery engine for EHC tests.

Auto-discovery:
    - scripts/*.py  → parametrized via `script_path`
    - hooks/scripts/*.sh → parametrized via `hook_path`
    - Makefile targets → parsed via `make_targets`

Adding a new file to scripts/ or hooks/scripts/ automatically
generates test cases — no test file edits needed.
"""

import sys
import os
import subprocess
import importlib.util
from pathlib import Path
from typing import Generator

import pytest

# ── Project paths ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
HOOKS_DIR = PROJECT_ROOT / "hooks" / "scripts"
TESTS_DIR = PROJECT_ROOT / "tests"
HELPERS_DIR = TESTS_DIR / "helpers"

sys.path.insert(0, str(SCRIPTS_DIR))


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def scripts_dir() -> Path:
    return SCRIPTS_DIR


@pytest.fixture(scope="session")
def hooks_dir() -> Path:
    return HOOKS_DIR


@pytest.fixture(scope="session")
def helpers_dir() -> Path:
    return HELPERS_DIR


# ── Auto-discovery helpers ─────────────────────────────────────────

def discover_scripts() -> list[Path]:
    """Return all .py files in scripts/ (excluding __pycache__)."""
    return sorted(SCRIPTS_DIR.glob("*.py"))


def discover_hooks() -> list[Path]:
    """Return all .sh files in hooks/scripts/."""
    return sorted(HOOKS_DIR.glob("*.sh"))


def parse_makefile_targets() -> list[str]:
    """Extract .PHONY target names from Makefile.

    Only matches real targets (indented with a tab, not variable assignments).
    """
    makefile = PROJECT_ROOT / "Makefile"
    if not makefile.exists():
        return []
    targets = []
    with open(makefile) as f:
        for line in f:
            # Real Makefile targets are at column 0, end with ":"
            # Variable assignments have "=" without leading ":" or start with "."
            # ECHO lines are body, not targets.
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#") or stripped.startswith("."):
                continue
            if stripped.startswith("\t"):
                continue  # recipe line
            if ":" not in stripped:
                continue  # variable assignment like "PYTHON := python3"
            if ":=" in stripped:
                continue  # simple assignment
            # It's a target line
            target = stripped.split(":")[0].strip()
            if target and not target.startswith("$") and not target.startswith("\\") and not target.startswith("@"):
                targets.append(target)
    return sorted(set(targets))


SKIP_SCRIPTS = {"__init__", "__pycache__"}


def import_module_from_path(filepath: Path, modname: str = None):
    """Dynamically import a Python file by path."""
    if modname is None:
        modname = filepath.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(modname, str(filepath))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {filepath}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Pytest parametrization hooks (auto-discovery) ──────────────────

def pytest_generate_tests(metafunc):
    """Auto-parametrize tests based on discovered files."""
    if "script_path" in metafunc.fixturenames:
        scripts = discover_scripts()
        ids = [s.name for s in scripts]
        metafunc.parametrize("script_path", scripts, ids=ids)

    if "hook_path" in metafunc.fixturenames:
        hooks = discover_hooks()
        ids = [h.name for h in hooks]
        metafunc.parametrize("hook_path", hooks, ids=ids)

    if "make_target" in metafunc.fixturenames:
        targets = parse_makefile_targets()
        metafunc.parametrize("make_target", targets, ids=targets)


# ── Subprocess runner convenience ──────────────────────────────────

def run_script(script_path: Path, args: list[str] = None, expected_code: int = 0) -> str:
    """Run a script as a subprocess and return stdout."""
    if args is None:
        args = []
    result = subprocess.run(
        [sys.executable, str(script_path)] + args,
        capture_output=True, text=True, timeout=30,
    )
    if expected_code is not None:
        assert result.returncode == expected_code, (
            f"{script_path.name} {' '.join(args)} "
            f"returned {result.returncode}, expected {expected_code}.\n"
            f"stdout: {result.stdout[:500]}\n"
            f"stderr: {result.stderr[:500]}"
        )
    return result.stdout


def run_hook(hook_path: Path, args: list[str] = None, expected_code: int = 0) -> str:
    """Run a hook script as a subprocess."""
    if args is None:
        args = []
    result = subprocess.run(
        ["bash", str(hook_path)] + args,
        capture_output=True, text=True, timeout=30,
    )
    if expected_code is not None:
        assert result.returncode == expected_code, (
            f"{hook_path.name} returned {result.returncode}, expected {expected_code}.\n"
            f"stdout: {result.stdout[:500]}\n"
            f"stderr: {result.stderr[:500]}"
        )
    return result.stdout
