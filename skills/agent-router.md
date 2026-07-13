---
name: agent-router
description: Smart agent recommendation engine — analyzes task descriptions using weighted scoring to select the best AI agents
version: 1.0.0
author: afidhadra
category: development
---

# Agent Router Skill

Intelligent agent routing using `agent-router.py`. Analyzes task descriptions with a weighted scoring engine (density × specificity × weight) against YAML routing rules to recommend the best agents.

## Scoring

```text
score = (matched_tokens / total_task_tokens) × weight × specificity
```

- **Density** — proportion of task tokens that match category keywords
- **Stemming** — `auth` matches `authentication`, `authorize`, `auths`
- **Specificity** — rare/long keywords weighted higher (TF-IDF style)
- **Confidence** — normalized 0–100%

## Usage

```bash

# Basic routing

python3 scripts/agent-router.py "Fix authentication token bug"

# → security (0.36), bug (0.36) → [security, reviewer, debugger]

# JSON output (for programmatic use)

python3 scripts/agent-router.py "Add login page" --json

# Force override agents

python3 scripts/agent-router.py "Refactor code" --force-agents coder,reviewer

# Interactive mode

python3 scripts/agent-router.py "Write tests" --interactive

# List agents or categories

python3 scripts/agent-router.py --list-agents
python3 scripts/agent-router.py --list-categories
```

## Config

Edit `config/routing.yaml` to add/modify categories, keywords, weights:

```yaml
categories:
  security:
    keywords: [auth, jwt, oauth, password, ...]
    weight: 0.80
    agents: [security, reviewer]
    min_confidence: 0.05
```

## Integration with Hermes

```text
hermes -z "route: fix login authentication bug" --skills skills/agent-router.md
```
