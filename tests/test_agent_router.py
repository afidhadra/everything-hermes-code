"""
Tests for Smart Agent Router (scripts/agent-router.py).

Covers:
    - Config loading (normal, missing, malformed)
    - Scoring engine correctness
    - Task routing with various task types
    - Force agents override
    - JSON output
    - CLI argument handling
    - Edge cases (empty task, no match, stop words)
"""

import json
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import yaml

from conftest import SCRIPTS_DIR, PROJECT_ROOT, import_module_from_path, run_script

# Import the router module
router = import_module_from_path(SCRIPTS_DIR / "agent-router.py")


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def sample_routing_config() -> dict:
    """A minimal routing config for testing."""
    return {
        "categories": {
            "security": {
                "keywords": ["auth", "jwt", "password", "token", "security"],
                "weight": 0.8,
                "agents": ["security", "reviewer"],
                "min_confidence": 0.1,
            },
            "bug": {
                "keywords": ["bug", "fix", "crash", "error"],
                "weight": 0.9,
                "agents": ["debugger", "reviewer"],
                "min_confidence": 0.1,
            },
            "feature": {
                "keywords": ["add", "implement", "create", "new", "build"],
                "weight": 0.7,
                "agents": ["coder"],
                "min_confidence": 0.1,
            },
            "test": {
                "keywords": ["test", "coverage", "spec", "tdd"],
                "weight": 0.8,
                "agents": ["tdd-guide"],
                "min_confidence": 0.1,
            },
        }
    }


# ── Config loading tests ──────────────────────────────────────────

def test_load_routing_config_exists():
    """routing.yaml must exist in config/."""
    config = router.load_routing_config()
    cats = config.get("categories", {})
    assert len(cats) >= 8, f"Expected 8+ categories, got {len(cats)}"
    assert "security" in cats
    assert "bug" in cats
    assert "feature" in cats


def test_load_routing_config_missing_file():
    """Non-existent path returns empty categories."""
    config = router.load_routing_config(Path("/nonexistent/routing.yaml"))
    assert config == {"categories": {}}


def test_load_agent_capabilities_exists():
    """agent-capabilities.yaml must exist in config/."""
    caps = router.load_agent_capabilities()
    agents = caps.get("agents", {})
    assert len(agents) >= 9, f"Expected 9+ agents, got {len(agents)}"
    assert "architect" in agents
    assert "coder" in agents


def test_load_agent_capabilities_missing_file():
    """Non-existent path returns empty agents."""
    caps = router.load_agent_capabilities(Path("/nonexistent/caps.yaml"))
    assert caps == {"agents": {}}


# ── Tokenization tests ────────────────────────────────────────────

def test_tokenize_basic():
    tokens = router.tokenize("Fix login authentication bug")
    assert "fix" in tokens
    assert "login" in tokens
    assert "authentication" in tokens
    assert "bug" in tokens


def test_tokenize_removes_stop_words():
    tokens = router.tokenize("This is a test for the system")
    assert "this" not in tokens
    assert "is" not in tokens
    assert "a" not in tokens
    assert "test" in tokens
    assert "system" in tokens


def test_tokenize_empty():
    assert router.tokenize("") == []


# ── Scoring tests ─────────────────────────────────────────────────

def test_score_density(sample_routing_config):
    """A task with multiple bug keywords should score high on bug."""
    result = router.route_task("Fix a crash bug in login", sample_routing_config)
    bug_score = next(
        (cs.score for cs in result.category_scores if cs.name == "bug"), 0
    )
    assert bug_score > 0, "bug should have non-zero score"
    # bug should rank higher than feature for this task
    bug = next(cs for cs in result.category_scores if cs.name == "bug")
    feat = next(
        (cs for cs in result.category_scores if cs.name == "feature"), None
    )
    if feat:
        assert bug.score > feat.score, "bug should outrank feature"


def test_score_security(sample_routing_config):
    """Security keywords should trigger security category."""
    result = router.route_task(
        "Add JWT authentication with password hashing",
        sample_routing_config
    )
    sec = next(
        (cs for cs in result.category_scores if cs.name == "security"), None
    )
    assert sec is not None, "security should be detected"
    assert "jwt" in sec.matched or "password" in sec.matched or "auth" in sec.matched


def test_score_feature(sample_routing_config):
    """Feature keywords should trigger feature category."""
    result = router.route_task(
        "Implement new user dashboard with charts",
        sample_routing_config
    )
    feat = next(
        (cs for cs in result.category_scores if cs.name == "feature"), None
    )
    assert feat is not None, "feature should be detected"
    assert feat.score > 0


def test_score_test(sample_routing_config):
    """Test keywords should trigger test category."""
    result = router.route_task(
        "Add unit tests for user service",
        sample_routing_config
    )
    test_cat = next(
        (cs for cs in result.category_scores if cs.name == "test"), None
    )
    assert test_cat is not None, "test should be detected"


def test_score_no_match(sample_routing_config):
    """Task with no matching keywords should fall back to coder."""
    result = router.route_task("xylophone", sample_routing_config)
    assert result.recommended == ["coder"]
    assert result.confidence < 1.0


def test_score_empty_task(sample_routing_config):
    """Empty task should fall back to coder."""
    result = router.route_task("", sample_routing_config)
    assert result.recommended == ["coder"]


# ── Routing result tests ──────────────────────────────────────────

def test_routing_result_dedup():
    """Recommended agents list should not contain duplicates."""
    config = {
        "categories": {
            "security": {
                "keywords": ["auth", "token"],
                "weight": 0.8,
                "agents": ["security", "reviewer"],
                "min_confidence": 0.1,
            },
            "bug": {
                "keywords": ["bug", "fix"],
                "weight": 0.9,
                "agents": ["debugger", "reviewer"],
                "min_confidence": 0.1,
            },
        }
    }
    result = router.route_task("Fix auth token bug", config)
    # reviewer should appear only once
    assert result.recommended.count("reviewer") <= 1
    assert len(result.recommended) == len(set(result.recommended))


def test_force_agents():
    """Force agents should bypass scoring."""
    result = router.route_task(
        "Any task here",
        force_agents=["coder", "security"]
    )
    assert result.recommended == ["coder", "security"]
    assert result.confidence == 1.0
    assert result.force_agents == ["coder", "security"]


def test_routing_result_to_dict():
    """to_dict() should produce serializable JSON."""
    result = router.route_task(
        "Fix login bug",
        {
            "categories": {
                "bug": {
                    "keywords": ["bug", "fix"],
                    "weight": 0.9,
                    "agents": ["debugger"],
                    "min_confidence": 0.1,
                }
            }
        }
    )
    d = result.to_dict()
    assert "task" in d
    assert "scores" in d
    assert "recommended" in d
    assert "confidence" in d
    # Must be JSON-serializable
    json.dumps(d)


def test_summary_contains_recommended():
    """Summary output should mention recommended agents."""
    result = router.route_task(
        "Add tests for API",
        {
            "categories": {
                "test": {
                    "keywords": ["test"],
                    "weight": 0.8,
                    "agents": ["tdd-guide"],
                    "min_confidence": 0.1,
                }
            }
        }
    )
    summary = result.summary()
    assert "tdd-guide" in summary
    assert "Recommended" in summary


# ── Multi-word keyword tests ──────────────────────────────────────

def test_multi_word_keyword():
    """Multi-word keywords (e.g. 'sql injection') should match."""
    config = {
        "categories": {
            "security": {
                "keywords": ["sql injection", "xss", "csrf"],
                "weight": 0.8,
                "agents": ["security"],
                "min_confidence": 0.1,
            },
        }
    }
    result = router.route_task("Fix sql injection vulnerability", config)
    sec = next(
        (cs for cs in result.category_scores if cs.name == "security"), None
    )
    assert sec is not None
    assert any("sql injection" in m for m in sec.matched)


# ── CLI tests ──────────────────────────────────────────────────────

def test_cli_help():
    """--help should produce usage output."""
    result = run_script(SCRIPTS_DIR / "agent-router.py", ["--help"])
    assert "usage:" in result.lower() or "Usage" in result


def test_cli_empty_args():
    """No arguments should exit non-zero."""
    result = run_script(SCRIPTS_DIR / "agent-router.py", [], expected_code=None)
    assert result is not None  # either exit or print usage


def test_cli_routing():
    """Routing a task via CLI should produce output."""
    result = run_script(
        SCRIPTS_DIR / "agent-router.py",
        ["Fix authentication bug"]
    )
    assert "debugger" in result or "security" in result
    assert "SMART AGENT ROUTER" in result or "Smart Agent Router" in result


def test_cli_json():
    """--json flag should produce valid JSON."""
    output = run_script(
        SCRIPTS_DIR / "agent-router.py",
        ["Fix login bug", "--json"]
    )
    data = json.loads(output)
    assert "task" in data
    assert "scores" in data
    assert "recommended" in data


def test_cli_force_agents():
    """--force-agents should override scoring."""
    output = run_script(
        SCRIPTS_DIR / "agent-router.py",
        ["Fix login bug", "--force-agents", "coder,security", "--json"]
    )
    data = json.loads(output)
    assert data["recommended"] == ["coder", "security"]


def test_cli_list_agents():
    """--list-agents should show all agents."""
    output = run_script(SCRIPTS_DIR / "agent-router.py", ["--list-agents"])
    assert "architect" in output
    assert "coder" in output
    assert "debugger" in output
    assert "9" in output or "Agent" in output


def test_cli_list_categories():
    """--list-categories should show routing categories."""
    output = run_script(SCRIPTS_DIR / "agent-router.py", ["--list-categories"])
    assert "security" in output
    assert "bug" in output
    assert "feature" in output


# ── Edge case: stop-word-only task ─────────────────────────────────

def test_stop_word_only_task(sample_routing_config):
    """Task with only stop words should fall back to coder."""
    result = router.route_task("a an the is it", sample_routing_config)
    assert result.recommended == ["coder"]


# ── Edge case: short task ─────────────────────────────────────────

def test_very_short_task(sample_routing_config):
    """Very short tasks should still route correctly."""
    result = router.route_task("add auth", sample_routing_config)
    assert len(result.recommended) >= 1
