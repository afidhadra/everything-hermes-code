#!/usr/bin/env python3
"""
MCP Manager — Auto-Discovery, Registry, and Health Check.

Discovers MCP servers from Docker containers, running processes,
Hermes config, and existing config files — then generates configs,
validates connectivity, and provides a centralized registry.

Usage:
    python3 mcp-manager.py scan         # Discover + show all servers
    python3 mcp-manager.py list         # Show registry table
    python3 mcp-manager.py health       # Check all server health
    python3 mcp-manager.py generate     # Generate/update config files
    python3 mcp-manager.py repair <name> # Attempt to restart a server
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None

# ── Paths ──────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).resolve().parent.parent
MCP_CONFIGS_DIR = REPO_DIR / "mcp-configs"
REGISTRY_FILE = MCP_CONFIGS_DIR / "registry.yaml"
HERMES_CONFIG = Path.home() / ".hermes" / "config.yaml"


# ── Known MCP server definitions ──────────────────────────────────

# Each entry: how to detect + what config to generate
KNOWN_SERVERS: dict[str, dict] = {
    "sonarqube": {
        "friendly": "SonarQube",
        "description": "Code quality and security analysis",
        "docker": {
            "container": "sonarqube",
            "port": 9000,
            "health_url": "http://localhost:9000/api/system/status",
        },
        "binary": "sonarqube-mcp-wrapper.sh",
        "binary_path": "~/.local/bin/sonarqube-mcp-wrapper.sh",
        "hermes_config_key": "sonarqube",
        "config": {
            "type": "stdio",
            "command": "${HOME}/.local/bin/sonarqube-mcp-wrapper.sh",
            "timeout": 30000,
        },
        "tags": ["code-quality", "analysis"],
    },
    "github": {
        "friendly": "GitHub",
        "description": "GitHub API — repos, PRs, issues, code search",
        "docker": None,
        "binary": "github-mcp-server",
        "binary_path": "~/go/bin/github-mcp-server",
        "hermes_config_key": "github",
        "config": {
            "type": "stdio",
            "command": "${HOME}/go/bin/github-mcp-server",
            "args": ["stdio"],
            "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"},
            "timeout": 30000,
        },
        "tags": ["git", "github", "pr", "review"],
    },
    "context7": {
        "friendly": "Context7",
        "description": "Documentation lookup for libraries/frameworks",
        "docker": None,
        "binary": "npx",
        "npx_package": "@upstash/context7-mcp@latest",
        "hermes_config_key": "context7",
        "config": {
            "type": "remote",
            "url": "https://mcp.context7.com/mcp",
        },
        "tags": ["docs", "reference"],
    },
    "ogham": {
        "friendly": "Ogham",
        "description": "Persistent memory layer with entity graph",
        "docker": {
            "container": "ogham-postgres",
            "port": 5434,
        },
        "binary": "ogham-launcher.sh",
        "binary_path": "~/.config/opencode/scripts/ogham-launcher.sh",
        "hermes_config_key": "ogham",
        "config": {
            "type": "stdio",
            "command": "${HOME}/.config/opencode/scripts/ogham-launcher.sh",
            "timeout": 60000,
        },
        "tags": ["memory", "persistence", "graph"],
    },
}


# ── Data structures ────────────────────────────────────────────────

class MCPServer:
    """Discovered MCP server with status."""

    def __init__(self, name: str, info: dict):
        self.name = name
        self.friendly = info.get("friendly", name)
        self.description = info.get("description", "")
        self.tags = info.get("tags", [])
        self.docker_info = info.get("docker")
        self.binary = info.get("binary")
        self.binary_path = info.get("binary_path")
        self.config_key = info.get("hermes_config_key")
        self.known_config = info.get("config", {})
        self.npx_package = info.get("npx_package")

        # Probe results
        self.docker_running = False
        self.binary_found = False
        self.http_healthy = False
        self.has_config_file = False
        self.has_hermes_config = False
        self.port_open = False

    @property
    def status(self) -> str:
        if self.docker_running or self.http_healthy:
            return "up"
        if self.binary_found:
            return "available"
        if self.has_hermes_config or self.has_config_file:
            return "configured"
        return "unknown"

    @property
    def health_emoji(self) -> str:
        return {"up": "✅", "available": "🔶", "configured": "🔷", "unknown": "⬜"}.get(
            self.status, "⬜"
        )


# ── Discovery engine ──────────────────────────────────────────────

def discover_servers() -> list[MCPServer]:
    """Scan system and return list of discovered MCP servers with status."""
    servers = []
    for name, info in KNOWN_SERVERS.items():
        sv = MCPServer(name, info)
        probe_server(sv)
        servers.append(sv)
    return servers


def probe_server(sv: MCPServer):
    """Probe a single server from multiple angles."""
    # Docker check
    if sv.docker_info:
        sv.docker_running = check_docker(sv.docker_info["container"])
        sv.port_open = check_port(sv.docker_info.get("port"))

        # HTTP health
        health_url = sv.docker_info.get("health_url")
        if health_url:
            sv.http_healthy = check_http(health_url)

    # Binary check
    if sv.binary_path:
        resolved = Path(sv.binary_path).expanduser()
        sv.binary_found = resolved.exists()

    # Config file check
    config_path = MCP_CONFIGS_DIR / f"{sv.name}.json"
    sv.has_config_file = config_path.exists()

    # Hermes config check
    sv.has_hermes_config = check_hermes_config(sv.config_key)


def check_docker(container_name: str) -> bool:
    """Check if a Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        return container_name in result.stdout.splitlines()
    except Exception:
        return False


def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is open."""
    if port is None:
        return False
    try:
        import socket
        with socket.create_connection((host, port), timeout=3):
            return True
    except Exception:
        return False


def check_http(url: str, timeout: int = 5) -> bool:
    """Check if an HTTP endpoint responds (2xx or 3xx)."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except Exception:
        try:
            # Fallback to GET if HEAD not supported
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return 200 <= resp.status < 400
        except Exception:
            return False


def check_hermes_config(config_key: str) -> bool:
    """Check if a server is configured in Hermes config."""
    if config_key is None or not HERMES_CONFIG.exists():
        return False
    try:
        content = HERMES_CONFIG.read_text()
        return f"{config_key}:" in content
    except Exception:
        return False


# ── Registry file (YAML) ──────────────────────────────────────────

def generate_registry(servers: list[MCPServer]) -> str:
    """Generate a YAML registry of all discovered MCP servers."""
    reg = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_by": "mcp-manager.py",
        "servers": {},
    }

    for sv in servers:
        entry = {
            "friendly": sv.friendly,
            "description": sv.description,
            "status": sv.status,
            "tags": sv.tags,
            "probe": {
                "docker_running": sv.docker_running,
                "binary_found": sv.binary_found,
                "http_healthy": sv.http_healthy,
                "port_open": sv.port_open,
                "has_config_file": sv.has_config_file,
                "has_hermes_config": sv.has_hermes_config,
            },
        }

        if sv.docker_info:
            entry["docker"] = {
                "container": sv.docker_info["container"],
                "port": sv.docker_info.get("port"),
                "health_url": sv.docker_info.get("health_url"),
            }
        if sv.binary_path:
            entry["binary"] = str(Path(sv.binary_path).expanduser())

        reg["servers"][sv.name] = entry

    return yaml.dump(reg, default_flow_style=False, sort_keys=False) \
        if yaml else json.dumps(reg, indent=2)


def save_registry(content: str, path: Path = REGISTRY_FILE):
    """Save registry to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ── Config generation ──────────────────────────────────────────────

def generate_config_file(sv: MCPServer) -> Optional[Path]:
    """Generate an MCP config JSON file for a server.

    Returns the path if generated, None if skipped.
    """
    if not sv.known_config:
        return None

    config_path = MCP_CONFIGS_DIR / f"{sv.name}.json"

    # Build config in Hermes format: { server_name: { ... } }
    hermes_config = {sv.name: dict(sv.known_config)}

    config_path.write_text(json.dumps(hermes_config, indent=2) + "\n")
    return config_path


# ── Display ────────────────────────────────────────────────────────

def print_discovery_table(servers: list[MCPServer]):
    """Print a formatted discovery results table."""
    print()
    print("MCP Server Discovery Results")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Header
    name_w = 14
    print(f"  {'Server':<{name_w}} {'Status':>4}  Docker  Binary  HTTP  Config  Hermes")
    print(f"  {'─'*name_w}  {'─'*4}  ──────  ──────  ────  ──────  ──────")

    for sv in sorted(servers, key=lambda s: s.status, reverse=True):
        d = "🐳" if sv.docker_running else "─"
        b = "📄" if sv.binary_found else "─"
        h = "✅" if sv.http_healthy else "─"
        cf = "📁" if sv.has_config_file else "─"
        hm = "⚙️" if sv.has_hermes_config else "─"
        print(
            f"  {sv.name:<{name_w}} {sv.health_emoji:>4}  {d:^6} {b:^6} {h:^5} {cf:^7} {hm:^7}"
        )

    print()
    print(f"  {len(servers)} server(s) discovered")
    print()


def print_health_table(servers: list[MCPServer]):
    """Print health check results."""
    print()
    print("MCP Server Health Check")
    print()

    up = sum(1 for s in servers if s.status == "up")
    total = len(servers)
    name_w = 14

    print(f"  {'Server':<{name_w}} {'Status':>8}  Detail")
    print(f"  {'─'*name_w}  {'─'*8}  ──────")

    for sv in sorted(servers, key=lambda s: s.status):
        detail = []
        if sv.docker_running:
            detail.append(f"Docker:{sv.docker_info['container']}")
        if sv.http_healthy:
            detail.append("HTTP:OK")
        if sv.port_open:
            detail.append(f"Port:{sv.docker_info.get('port', '?')}")
        if sv.binary_found:
            detail.append(f"Binary:{Path(sv.binary_path).expanduser().name}")

        status_str = sv.status.upper()
        detail_str = ", ".join(detail) if detail else "not found"
        print(f"  {sv.name:<{name_w}} {sv.health_emoji:>8}  {detail_str}")

    print()
    print(f"  {up}/{total} servers up")
    print()


def print_list_table(servers: list[MCPServer]):
    """Print a compact list of all servers."""
    print()
    name_w = 14
    print(f"  {'Server':<{name_w}} {'Status':>4}  {'Config':>6}  {'Description'}")
    print(f"  {'─'*name_w}  {'─'*4}  {'─'*6}  ─────────────────────────────────")

    for sv in sorted(servers, key=lambda s: s.name):
        cfg = "✅" if sv.has_config_file else "❌" if sv.has_hermes_config else "─"
        desc = sv.description[:50] if sv.description else ""
        print(
            f"  {sv.name:<{name_w}} {sv.health_emoji:>4}  {cfg:^6}  {desc}"
        )

    print(f"  {len(servers)} server(s)")
    print()


# ── Repair ─────────────────────────────────────────────────────────

def repair_server(name: str) -> bool:
    """Attempt to restart a failed MCP server.

    Currently supports: Docker container restart.
    """
    if name not in KNOWN_SERVERS:
        print(f"❌ Unknown server: {name}")
        return False

    info = KNOWN_SERVERS[name]
    docker_info = info.get("docker")

    if docker_info:
        container = docker_info["container"]
        print(f"  🔄 Restarting Docker container: {container}...")
        try:
            result = subprocess.run(
                ["docker", "restart", container],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                print(f"  ✅ {container} restarted successfully")
                return True
            else:
                print(f"  ❌ Failed: {result.stderr.strip()}")
                return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False

    print(f"  ⚠️  No repair strategy for {name} (not a Docker container)")
    return False


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MCP Manager — Auto-discovery, registry, and health check"
    )
    parser.add_argument(
        "action",
        nargs="?",
        choices=["scan", "list", "health", "generate", "repair"],
        default="scan",
        help="Action to perform (default: scan)"
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Server name for repair action"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format (scan/health)"
    )
    args = parser.parse_args()

    if args.action == "repair":
        if not args.name:
            print("❌ Usage: mcp-manager.py repair <server-name>")
            sys.exit(1)
        success = repair_server(args.name)
        sys.exit(0 if success else 1)

    # Discover servers
    servers = discover_servers()

    if args.action == "scan":
        if args.json:
            output = []
            for sv in servers:
                output.append({
                    "name": sv.name,
                    "friendly": sv.friendly,
                    "status": sv.status,
                    "docker_running": sv.docker_running,
                    "binary_found": sv.binary_found,
                    "http_healthy": sv.http_healthy,
                    "has_config_file": sv.has_config_file,
                    "has_hermes_config": sv.has_hermes_config,
                })
            print(json.dumps(output, indent=2))
        else:
            print_discovery_table(servers)

        # Also save registry
        registry_content = generate_registry(servers)
        saved_path = save_registry(registry_content)
        if not args.json:
            print(f"  📄 Registry saved to: {saved_path}")
            print()

    elif args.action == "list":
        print_list_table(servers)

    elif args.action == "health":
        if args.json:
            output = []
            for sv in servers:
                output.append({
                    "name": sv.name,
                    "status": sv.status,
                    "docker_running": sv.docker_running,
                    "http_healthy": sv.http_healthy,
                    "port_open": sv.port_open,
                })
            print(json.dumps(output, indent=2))
        else:
            print_health_table(servers)

        # Also save registry on health check
        registry_content = generate_registry(servers)
        save_registry(registry_content)

    elif args.action == "generate":
        generated = []
        for sv in servers:
            config_path = generate_config_file(sv)
            if config_path:
                generated.append(config_path)
                print(f"  ✅ Generated: {config_path}")

        if not generated:
            print("  ⚠️  No configs generated (all already exist or no template)")

        # Also save registry
        registry_content = generate_registry(servers)
        save_registry(registry_content)
        print(f"  📄 Registry saved to: {REGISTRY_FILE}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
