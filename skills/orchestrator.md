---
name: orchestrator
description: Plan-first orchestration engine — analyzes tasks, generates plans, coordinates multi-agent execution with human approval
version: 1.0.0
author: afidhadra
category: development
---

# Orchestrator Skill

Plan-first workflow for task execution. Uses `orchestrator.py` to analyze tasks, generate plans, get human approval, then coordinate parallel/sequential agent execution.

## Workflow

1. **Analyze** — detect task types, complexity, select agents via router
1. **Plan** — generate structured markdown plan with agent roles + dependencies + risk
1. **Review** — human approves or edits the plan
1. **Execute** — spawn agents (parallel or sequential)
1. **Report** — aggregate results into summary

## Usage

```bash

# Basic: plan + review + execute

python3 scripts/orchestrator.py "Refactor authentication module"

# Generate plan only, save to file

python3 scripts/orchestrator.py --plan-only "Add login feature"

# Load existing plan (after editing)

python3 scripts/orchestrator.py --plan plan.md

# Background execution (non-blocking)

python3 scripts/orchestrator.py "Deploy to staging" --background

# Live task dashboard

python3 scripts/orchestrator.py --status

# View task result

python3 scripts/orchestrator.py --result 42

# Override agents

python3 scripts/orchestrator.py "Fix bug" --force-agents coder,security

# Skip plan review (CI mode)

python3 scripts/orchestrator.py "Run migration" --auto-approve

# Dry run

python3 scripts/orchestrator.py "Refactor auth" --dry-run
```

## Flags

| Flag | Description |
| ------ | ------------- |
| `--plan-only` | Generate plan and exit (no execution) |
| `--plan FILE` | Load existing plan file |
| `--auto-approve` | Skip plan review prompt |
| `--force-agents` | Override agent selection |
| `--background` / `-b` | Run as background task |
| `--status` / `-s` | Live task dashboard |
| `--result` / `-r` | View task detail |
| `--history` / `-H` | All task history |
| `--cancel` | Kill a running task |
| `--sequential` | Run agents one by one |
| `--yes` | Auto-approve tool calls |
| `--dry-run` | Preview only |

## Integration with Hermes

Load this skill and ask:

```text
hermes -z "use orchestrator to refactor auth module" --skills skills/orchestrator.md
```
