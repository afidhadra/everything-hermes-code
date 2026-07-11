#!/usr/bin/env python3
"""
Unit tests for agent-runner.py and command-runner.py.

Run: python3 tests/test_runners.py
"""

import sys
import os
from pathlib import Path

# Add scripts dir to path
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)


def import_module(filepath: str, modulename: str):
    """Import a module from filepath (handles hyphenated names)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(modulename, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Import our modules
agent_runner = import_module(
    os.path.join(SCRIPTS_DIR, "agent-runner.py"), "agent_runner"
)
command_runner = import_module(
    os.path.join(SCRIPTS_DIR, "command-runner.py"), "command_runner"
)

PASS = 0
FAIL = 0


def assert_eq(actual, expected, label: str):
    global PASS, FAIL
    if actual == expected:
        print(f"  ✅ {label}")
        PASS += 1
    else:
        print(f"  ❌ {label}")
        print(f"     Expected: {expected}")
        print(f"     Got:      {actual}")
        FAIL += 1


def assert_true(value, label: str):
    assert_eq(bool(value), True, label)


def assert_false(value, label: str):
    assert_eq(bool(value), False, label)


# ============================================================
# Agent Runner Tests
# ============================================================

def test_agent_count():
    """Should have 9 agents defined."""
    assert_eq(len(agent_runner.AGENTS), 9, "9 agents defined")


def test_agent_keys():
    """Agent keys should match expected names."""
    expected = {
        "architect", "coder", "debugger", "reviewer",
        "documenter", "optimizer", "planner", "security", "tdd-guide"
    }
    assert_eq(set(agent_runner.AGENTS.keys()), expected, "Agent keys match")


def test_agent_structure():
    """Each agent should have name, description, system_prompt, output_format."""
    for name, agent in agent_runner.AGENTS.items():
        assert_true("name" in agent, f"{name}: has 'name'")
        assert_true("description" in agent, f"{name}: has 'description'")
        assert_true("system_prompt" in agent, f"{name}: has 'system_prompt'")
        assert_true("output_format" in agent, f"{name}: has 'output_format'")


def test_get_agent_valid():
    """get_agent should return agent dict for valid name."""
    agent = agent_runner.get_agent("coder")
    assert_true(agent is not None, "get_agent('coder') returns dict")
    assert_eq(agent["name"], "Coder Agent", "coder agent name correct")


def test_get_agent_invalid():
    """get_agent should return None for invalid name."""
    agent = agent_runner.get_agent("nonexistent")
    assert_true(agent is None, "get_agent('nonexistent') returns None")


def test_agent_prompt_not_empty():
    """Each agent system_prompt should not be empty."""
    for name, agent in agent_runner.AGENTS.items():
        assert_true(
            len(agent["system_prompt"].strip()) > 10,
            f"{name}: system_prompt not empty"
        )


def test_agent_output_format():
    """output_format should be 'markdown' or 'code'."""
    valid_formats = {"markdown", "code"}
    for name, agent in agent_runner.AGENTS.items():
        assert_true(
            agent["output_format"] in valid_formats,
            f"{name}: output_format is valid"
        )


# ============================================================
# Command Runner Tests
# ============================================================

def test_command_count():
    """Should have 4 commands defined."""
    assert_eq(len(command_runner.COMMANDS), 4, "4 commands defined")


def test_command_keys():
    """Command keys should match expected names."""
    expected = {"analyze", "fix", "review", "security"}
    assert_eq(
        set(command_runner.COMMANDS.keys()), expected, "Command keys match"
    )


def test_command_structure():
    """Each command should have name, description, usage, script."""
    for name, cmd in command_runner.COMMANDS.items():
        assert_true("name" in cmd, f"{name}: has 'name'")
        assert_true("description" in cmd, f"{name}: has 'description'")
        assert_true("usage" in cmd, f"{name}: has 'usage'")
        assert_true("script" in cmd, f"{name}: has 'script'")


def test_get_command_valid():
    """get_command should return dict for valid name."""
    cmd = command_runner.get_command("analyze")
    assert_true(cmd is not None, "get_command('analyze') returns dict")
    assert_eq(cmd["name"], "Analyze", "analyze command name correct")


def test_get_command_invalid():
    """get_command should return None for invalid name."""
    cmd = command_runner.get_command("nonexistent")
    assert_true(cmd is None, "get_command('nonexistent') returns None")


def test_command_scripts_exist():
    """Each command's script should exist on disk."""
    scripts_dir = Path(SCRIPTS_DIR) / "commands"
    for name, cmd in command_runner.COMMANDS.items():
        script_path = scripts_dir / cmd["script"]
        assert_true(
            script_path.exists(),
            f"{name}: script '{cmd['script']}' exists on disk"
        )


def test_command_usage_format():
    """Usage strings should start with /."""
    for name, cmd in command_runner.COMMANDS.items():
        assert_true(
            cmd["usage"].startswith("/"),
            f"{name}: usage starts with /"
        )


# ============================================================
# Run All Tests
# ============================================================

def main():
    print("Running unit tests for agent-runner.py and command-runner.py...\n")

    # Agent runner tests
    print("--- Agent Runner ---")
    test_agent_count()
    test_agent_keys()
    test_agent_structure()
    test_get_agent_valid()
    test_get_agent_invalid()
    test_agent_prompt_not_empty()
    test_agent_output_format()

    # Command runner tests
    print("\n--- Command Runner ---")
    test_command_count()
    test_command_keys()
    test_command_structure()
    test_get_command_valid()
    test_get_command_invalid()
    test_command_scripts_exist()
    test_command_usage_format()

    # Summary
    print(f"\n{'=' * 50}")
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("All tests passed! ✅")
        sys.exit(0)
    else:
        print("Some tests FAILED! ❌")
        sys.exit(1)


if __name__ == "__main__":
    main()
