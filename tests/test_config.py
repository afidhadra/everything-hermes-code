"""
Tests for .ehc.yaml config loading and schema validation.

Verifies that:
    - The existing .ehc.yaml is valid YAML
    - Config loader returns correct structure
    - Malformed configs are handled gracefully
    - Missing config falls back to defaults
"""

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import yaml

from conftest import PROJECT_ROOT, SCRIPTS_DIR, import_module_from_path

# Import ehc_config
ehc_config = import_module_from_path(SCRIPTS_DIR / "ehc_config.py")


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def temp_config() -> Generator[Path, None, None]:
    """Create a temporary directory with a .ehc.yaml for testing."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def valid_config_dict() -> dict:
    """A minimal valid config dict."""
    return {
        "project": {"name": "test", "root": "~/test"},
        "repos": {
            "be": {"name": "Backend", "dir": "be", "lang": "go"},
            "fe": {"name": "Frontend", "dir": "fe", "lang": "vue"},
        },
        "deploy": {
            "dir": "deploy",
            "compose_dev": "docker-compose.dev.yml",
            "compose_prod": "docker-compose.prod.yml",
            "health_timeout": 30,
            "health_interval": 2,
        },
        "docker": {
            "containers": {
                "test-api": {"friendly": "Test API"},
            }
        },
        "services": [
            {"name": "API", "url": "http://localhost:8080", "type": "http"},
        ],
    }


# ── Existing config validation ─────────────────────────────────────

def test_ehc_yaml_exists():
    """The project must have a .ehc.yaml config file."""
    config_path = PROJECT_ROOT / ".ehc.yaml"
    assert config_path.exists(), f"Missing .ehc.yaml at {config_path}"


def test_ehc_yaml_valid():
    """.ehc.yaml must be valid YAML."""
    config_path = PROJECT_ROOT / ".ehc.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), ".ehc.yaml must be a dict"
    assert "project" in data, ".ehc.yaml missing 'project' key"
    assert "repos" in data, ".ehc.yaml missing 'repos' key"


def test_config_loader_finds_default():
    """load_config() must find and load .ehc.yaml from project root."""
    old_cwd = Path.cwd()
    os.chdir(str(PROJECT_ROOT))
    try:
        cfg = ehc_config.load_config()
        assert isinstance(cfg, dict)
        assert cfg.get("project", {}).get("name") == "FROZEN-POS"
    finally:
        os.chdir(str(old_cwd))


# ── Schema compliance ──────────────────────────────────────────────

SCHEMA_KEYS = {"project", "repos", "deploy", "docker", "services"}
REPO_KEYS = {"name", "dir", "lang"}
DEPLOY_KEYS = {"dir", "compose_dev", "compose_prod", "health_timeout", "health_interval"}


def test_config_schema_structure():
    """Config must have all top-level schema keys."""
    old_cwd = Path.cwd()
    os.chdir(str(PROJECT_ROOT))
    try:
        cfg = ehc_config.load_config()
        for key in SCHEMA_KEYS:
            assert key in cfg, f"Config missing required key: {key}"
    finally:
        os.chdir(str(old_cwd))


def test_repos_schema():
    """Each repo must have required fields."""
    old_cwd = Path.cwd()
    os.chdir(str(PROJECT_ROOT))
    try:
        cfg = ehc_config.load_config()
        for name, repo in cfg.get("repos", {}).items():
            for key in REPO_KEYS:
                assert key in repo, f"Repo '{name}' missing required key: {key}"
    finally:
        os.chdir(str(old_cwd))


# ── Helper function tests ──────────────────────────────────────────

def test_find_config_nonexistent():
    """find_config should return None for non-existent path."""
    result = ehc_config.find_config("/nonexistent/path/.ehc.yaml")
    assert result is None


def test_find_config_explicit(temp_config):
    """find_config with explicit path should return that path."""
    cfg_path = temp_config / ".ehc.yaml"
    cfg_path.write_text("project:\n  name: explicit\n")
    result = ehc_config.find_config(str(cfg_path))
    assert result is not None
    assert str(result) == str(cfg_path)


def test_load_config_missing_yaml_module(monkeypatch):
    """If yaml is not installed, load_config should return empty dict."""
    monkeypatch.setattr(ehc_config, "yaml", None)
    result = ehc_config.load_config()
    assert result == {}


def test_expand_path():
    """expand_path should expand ~ and env vars."""
    result = ehc_config.expand_path("~/test")
    assert result.startswith("/")
    assert result.endswith("/test")
    assert not result.startswith("~")


def test_get_repos_defaults():
    """get_repos with empty config should return frozen-pos defaults."""
    repos = ehc_config.get_repos({})
    assert "be" in repos
    assert "fe" in repos
    assert repos["be"]["lang"] == "go"
    assert repos["fe"]["lang"] == "vue"


def test_get_repos_custom():
    """get_repos with custom config should return custom values."""
    config = {
        "repos": {
            "custom": {"name": "Custom", "dir": "custom-dir", "lang": "rust"},
        }
    }
    repos = ehc_config.get_repos(config)
    assert "custom" in repos
    assert repos["custom"]["lang"] == "rust"


def test_get_project_root():
    """get_project_root should expand the configured root."""
    config = {"project": {"root": "~/custom-root"}}
    root = ehc_config.get_project_root(config)
    assert root.startswith("/")
    assert root.endswith("custom-root")


def test_get_deploy_config_defaults():
    """get_deploy_config should return sensible defaults."""
    deploy = ehc_config.get_deploy_config({})
    assert deploy["dir"] == "inventory-deploy"
    assert deploy["health_timeout"] == 60
    assert deploy["health_interval"] == 2


def test_get_docker_containers():
    """get_docker_containers should return containers dict."""
    config = {"docker": {"containers": {"a": {"friendly": "A"}}}}
    containers = ehc_config.get_docker_containers(config)
    assert "a" in containers
    assert containers["a"]["friendly"] == "A"


def test_get_services():
    """get_services should return services list."""
    config = {"services": [{"name": "API"}]}
    services = ehc_config.get_services(config)
    assert len(services) == 1
    assert services[0]["name"] == "API"


def test_list_available_configs():
    """list_available_configs should find .ehc.yaml files."""
    configs = ehc_config.list_available_configs()
    assert isinstance(configs, list)
    # At minimum, should find the one in this project
    assert any(PROJECT_ROOT / ".ehc.yaml" == p for p in configs)
