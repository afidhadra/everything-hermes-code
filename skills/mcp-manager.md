---
name: mcp-manager
description: MCP server auto-discovery and registry — scan Docker, binaries, and Hermes config to detect, configure, and health-check MCP servers
version: 1.0.0
author: afidhadra
category: devops
---

# MCP Manager Skill

Discovers MCP servers from multiple sources (Docker containers, system binaries, Hermes config), generates config files, validates connectivity, and maintains a centralized registry.

Auto-discovers: SonarQube, GitHub MCP, Context7, Ogham, and any Docker service with known ports.

## Usage

```bash

# Scan and discover all MCP servers

python3 scripts/mcp-manager.py scan

# Compact list view

python3 scripts/mcp-manager.py list

# Health check all servers

python3 scripts/mcp-manager.py health

# Auto-generate config files

python3 scripts/mcp-manager.py generate

# Restart a failed Docker-based server

python3 scripts/mcp-manager.py repair sonarqube

# JSON output

python3 scripts/mcp-manager.py scan --json
python3 scripts/mcp-manager.py health --json
```

## Output

Scan result shows status per server:

```text
  Server         Status  Docker  Binary  HTTP  Config  Hermes
  ──────────────  ────  ──────  ──────  ────  ──────  ──────
  sonarqube         ✅    🐳      📄      ─      📁      ⚙️
  github            🔶    ─      📄      ─      📁      ⚙️
  context7          🔷    ─      ─      ─      ─      ⚙️
  ogham             ✅    🐳      📄      ─      ─      ⚙️
```

Registry saved to `mcp-configs/registry.yaml`.

## Integration with Hermes

```text
hermes -z "scan for MCP servers" --skills skills/mcp-manager.md
```
