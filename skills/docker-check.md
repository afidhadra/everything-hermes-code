---
name: docker-check
description: Docker container health monitor — detect dead/unhealthy containers, check resource usage, restart failed services
version: 1.0.0
author: afidhadra
category: devops
---

# Docker Check Skill

Monitors Docker containers, checks health endpoints, reports resource usage (CPU, RAM, disk), and can auto-restart dead containers.

## Usage

```bash

# Quick health check

python3 scripts/docker-check.py

# Restart dead containers (with confirmation)

python3 scripts/docker-check.py --restart-dead

# Auto-repair mode (restart without prompt)

python3 scripts/docker-check.py --restart-dead --yes

# Watch mode (auto-refresh every 10s)

python3 scripts/docker-check.py --watch

# Custom interval

python3 scripts/docker-check.py --watch --interval 30

# JSON output

python3 scripts/docker-check.py --json
```

## Config

Container definitions with health URLs and restart priority come from `.ehc.yaml`:

```yaml
docker:
  containers:
    api-dev:
      friendly: API
      health_url: http://localhost:8080/health
      auto_restart: true
      priority: 1
    postgres-dev:
      friendly: PostgreSQL
      auto_restart: true
      priority: 2
```

## Integration with Hermes

```text
hermes -z "check docker health" --skills skills/docker-check.md
```
