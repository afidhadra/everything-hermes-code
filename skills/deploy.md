---
name: deploy
description: Multi-repo deployment coordinator with pre-deploy checks, Docker compose management, and health verification
version: 1.0.0
author: afidhadra
category: devops
---

# Deploy Skill

Coordinates deployment across multiple repositories. Config via `.ehc.yaml`.

## Usage

```bash

# Check status (what needs deploying)

python3 scripts/deploy.py --status

# Pre-deploy checks only (no deploy)

python3 scripts/deploy.py --check

# Deploy specific repo

python3 scripts/deploy.py --deploy be        # backend only
python3 scripts/deploy.py --deploy fe        # frontend only
python3 scripts/deploy.py --deploy all       # both + restart

# Dry run (show what would happen)

python3 scripts/deploy.py --deploy all --dry-run

# Custom project root

python3 scripts/deploy.py --status --project-root ~/Projects/my-project
```

## Config

Edit `.ehc.yaml`:

```yaml
project:
  name: MY-PROJECT
  root: ~/Projects/my-project
repos:
  be:
    name: backend
    dir: backend
    lang: go
    container: api-dev
    health_url: http://localhost:8080/health
deploy:
  dir: deploy
  compose_dev: docker-compose.dev.yml
```

## Integration with Hermes

```text
hermes -z "deploy backend to staging" --skills skills/deploy.md
```
