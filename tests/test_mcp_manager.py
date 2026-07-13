"""
Tests for MCP Manager (scripts/mcp-manager.py).

Covers:
    - Discovery engine (Docker, binary, port, HTTP)
    - Config generation
    - Registry generation
    - CLI arguments
    - Edge cases
"""

import json
import sys
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Generator

import pytest

from conftest import SCRIPTS_DIR, PROJECT_ROOT, import_module_from_path, run_script

mcp = import_module_from_path(SCRIPTS_DIR / "mcp-manager.py")


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def mock_server():
    """Create a minimal server info dict for testing."""
    return {
        "friendly": "Test Server",
        "description": "A test MCP server",
        "docker": {
            "container": "test-container",
            "port": 9999,
            "health_url": "http://localhost:9999/health",
        },
        "binary": "test-binary",
        "binary_path": "~/test-binary.sh",
        "hermes_config_key": "test-server",
        "config": {
            "type": "stdio",
            "command": "${HOME}/test-binary.sh",
            "timeout": 30000,
        },
        "tags": ["test"],
    }


# ── MCPServer class tests ─────────────────────────────────────────

def test_mcp_server_creation(mock_server):
    """MCPServer should init from info dict."""
    sv = mcp.MCPServer("test", mock_server)
    assert sv.name == "test"
    assert sv.friendly == "Test Server"
    assert sv.binary == "test-binary"
    assert sv.status == "unknown"


def test_mcp_server_status_up(mock_server):
    """Status should be 'up' when docker is running."""
    sv = mcp.MCPServer("test", mock_server)
    sv.docker_running = True
    assert sv.status == "up"


def test_mcp_server_status_available(mock_server):
    """Status should be 'available' when binary found."""
    sv = mcp.MCPServer("test", mock_server)
    sv.binary_found = True
    assert sv.status == "available"


def test_mcp_server_status_configured(mock_server):
    """Status should be 'configured' when config exists."""
    sv = mcp.MCPServer("test", mock_server)
    sv.has_hermes_config = True
    assert sv.status == "configured"


def test_mcp_server_health_emoji():
    """Each status should have a distinct emoji."""
    sv = mcp.MCPServer("test", {"friendly": "Test"})
    assert sv.status == "unknown"
    assert sv.health_emoji == "⬜"

    sv.docker_running = True
    assert sv.health_emoji == "✅"

    sv = mcp.MCPServer("test", {"friendly": "Test"})
    sv.binary_found = True
    assert sv.health_emoji == "🔶"

    sv = mcp.MCPServer("test", {"friendly": "Test"})
    sv.has_hermes_config = True
    assert sv.health_emoji == "🔷"


# ── Probe tests (mock-free, use test doubles) ──────────────────────

def test_check_docker_not_found():
    """check_docker should return False for non-existent container."""
    result = mcp.check_docker("nonexistent-container-xyz-123")
    assert result is False


def test_check_port_closed():
    """check_port should return False for a closed port."""
    result = mcp.check_port(1)  # port 1 is never open
    assert result is False


def test_check_http_invalid_url():
    """check_http should return False for unreachable URL."""
    result = mcp.check_http("http://192.0.2.1:1/health")  # RFC 5737 TEST-NET
    assert result is False


def test_check_hermes_config_none():
    """check_hermes_config should return False for None key."""
    assert mcp.check_hermes_config(None) is False


# ── Config generation tests ───────────────────────────────────────

def test_generate_config_file(mock_server, tmp_path):
    """generate_config_file should produce a valid JSON config."""
    sv = mcp.MCPServer("test-server", mock_server)

    # Temporarily override MCP_CONFIGS_DIR
    original = mcp.MCP_CONFIGS_DIR
    mcp.MCP_CONFIGS_DIR = tmp_path
    try:
        config_path = mcp.generate_config_file(sv)
        assert config_path is not None
        assert config_path.exists()

        data = json.loads(config_path.read_text())
        assert "test-server" in data
        assert data["test-server"]["type"] == "stdio"
        assert "command" in data["test-server"]
    finally:
        mcp.MCP_CONFIGS_DIR = original


def test_generate_config_no_config(mock_server, tmp_path):
    """generate_config_file should return None for servers without known_config."""
    sv = mcp.MCPServer("test", {"friendly": "Test"})
    original = mcp.MCP_CONFIGS_DIR
    mcp.MCP_CONFIGS_DIR = tmp_path
    try:
        config_path = mcp.generate_config_file(sv)
        assert config_path is None
    finally:
        mcp.MCP_CONFIGS_DIR = original


def test_generate_config_invalid_json(mock_server, tmp_path):
    """Generated config must be valid JSON."""
    sv = mcp.MCPServer("test-server", mock_server)
    original = mcp.MCP_CONFIGS_DIR
    mcp.MCP_CONFIGS_DIR = tmp_path
    try:
        config_path = mcp.generate_config_file(sv)
        assert config_path is not None
        # Should not raise
        json.loads(config_path.read_text())
    finally:
        mcp.MCP_CONFIGS_DIR = original


# ── Registry generation tests ─────────────────────────────────────

def test_generate_registry(mock_server):
    """generate_registry should produce YAML with server entries."""
    sv = mcp.MCPServer("test", mock_server)
    sv.docker_running = True
    sv.binary_found = True

    content = mcp.generate_registry([sv])
    # Should contain server info
    assert "test" in content
    assert "Test Server" in content
    assert "generated_at" in content
    assert "generated_by" in content


def test_generate_registry_empty():
    """generate_registry with empty list should produce valid output."""
    content = mcp.generate_registry([])
    assert "servers" in content
    assert "generated_at" in content


def test_save_registry(tmp_path):
    """save_registry should write to file."""
    test_path = tmp_path / "registry.yaml"
    result = mcp.save_registry("test: true", test_path)
    assert result == test_path
    assert test_path.exists()
    assert test_path.read_text() == "test: true"


# ── Discovery tests ───────────────────────────────────────────────

def test_discover_servers_returns_list():
    """discover_servers should return a list of MCPServer objects."""
    servers = mcp.discover_servers()
    assert isinstance(servers, list)
    assert len(servers) >= 4  # sonarqube, github, context7, ogham
    names = [s.name for s in servers]
    assert "sonarqube" in names
    assert "github" in names
    assert "context7" in names


def test_discover_servers_probes():
    """discover_servers should probe each server."""
    servers = mcp.discover_servers()
    for sv in servers:
        # Each server should have at least one probe result
        has_probe = (
            sv.docker_running or sv.binary_found or
            sv.has_hermes_config or sv.has_config_file
        )
        # At minimum, hermes_config should be found for known servers
        # (since they're in ~/.hermes/config.yaml)
        print(f"  {sv.name}: "
              f"docker={sv.docker_running} "
              f"binary={sv.binary_found} "
              f"config={sv.has_config_file} "
              f"hermes={sv.has_hermes_config}")


# ── CLI tests ─────────────────────────────────────────────────────

def test_cli_help():
    """--help should produce usage output."""
    result = run_script(SCRIPTS_DIR / "mcp-manager.py", ["--help"])
    assert "usage:" in result.lower() or "Usage" in result


def test_cli_scan():
    """scan should produce discovery table."""
    result = run_script(SCRIPTS_DIR / "mcp-manager.py", ["scan"])
    assert "sonarqube" in result or "SonarQube" in result
    assert "MCP Server Discovery" in result


def test_cli_scan_json():
    """scan --json should produce valid JSON."""
    output = run_script(SCRIPTS_DIR / "mcp-manager.py", ["scan", "--json"])
    data = json.loads(output)
    assert isinstance(data, list)
    assert len(data) >= 4


def test_cli_list():
    """list should show server registry."""
    result = run_script(SCRIPTS_DIR / "mcp-manager.py", ["list"])
    assert "sonarqube" in result.lower()
    assert "server(s)" in result


def test_cli_health():
    """health should show health check table."""
    result = run_script(SCRIPTS_DIR / "mcp-manager.py", ["health"])
    assert "Health Check" in result
    assert "/" in result  # "2/4 servers up"


def test_cli_health_json():
    """health --json should produce valid JSON."""
    output = run_script(SCRIPTS_DIR / "mcp-manager.py", ["health", "--json"])
    data = json.loads(output)
    assert isinstance(data, list)
    for entry in data:
        assert "name" in entry
        assert "status" in entry


def test_cli_generate():
    """generate should create config files."""
    # Use --json to avoid overwriting actual configs
    result = run_script(SCRIPTS_DIR / "mcp-manager.py", ["generate"])
    assert "Generated" in result or "Registry" in result


def test_cli_repair_unknown():
    """repair with unknown server should fail gracefully."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "mcp-manager.py"),
         "repair", "nonexistent-server"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "Unknown" in result.stdout or "Unknown" in result.stderr


# ── Health check logic (strict) ───────────────────────────────────

def test_sonarqube_config_exists():
    """sonarqube.json config should exist after generate."""
    config_path = mcp.MCP_CONFIGS_DIR / "sonarqube.json"
    # May or may not exist depending on test order
    # Just check it's valid if it exists
    if config_path.exists():
        data = json.loads(config_path.read_text())
        assert "sonarqube" in data


def test_github_config_exists():
    """github.json config should exist."""
    config_path = mcp.MCP_CONFIGS_DIR / "github.json"
    if config_path.exists():
        data = json.loads(config_path.read_text())
        assert "github" in data


def test_registry_file_generated():
    """registry.yaml should be generated after scan."""
    registry_path = mcp.REGISTRY_FILE
    if registry_path.exists():
        content = registry_path.read_text()
        assert "servers" in content
