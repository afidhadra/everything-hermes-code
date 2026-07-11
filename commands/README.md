# Commands

## Overview

Slash commands for quick workflow switching. These are shortcuts to load specific agent configurations.

## Available Commands

| Command | Description | Agent |
| --------- | ------------- | ------- |
| /code | Switch to coding mode | coder |
| /debug | Switch to debug mode | debugger |
| /review | Switch to review mode | reviewer |
| /analyze | Switch to analysis mode | architect |
| /plan | Plan a feature or project | planner |
| /test | Generate and run tests | tdd-guide |
| /refactor | Refactor code with best practices | optimizer |
| /document | Generate documentation | documenter |
| /security | Run security audit | security |

## Usage

### In Terminal

```bash

# Switch to coding mode

source ~/Projects/everything-hermes-code/scripts/prompt.sh coding

# Switch to debug mode

source ~/Projects/everything-hermes-code/scripts/prompt.sh debug
```text

### In Hermes

```bash

# Set system prompt

export HERMES_EPHEMERAL_SYSTEM_PROMPT="$(cat ~/Projects/everything-hermes-code/agents/coder.md)"
```text

### In OpenCode

```markdown

## Quick Commands

- `/code` — Coding mode
- `/debug` — Debug mode
- `/review` — Review mode

```text

## Creating Custom Commands

1. Create a new `.md` file in this directory
1. Add frontmatter:

```markdown
---
name: my-command
description: Does something awesome
agent: coder
---
```text

1. Add the system prompt below

## Best Practices

- One command per task type
- Clear, specific descriptions
- Appropriate agent mapping
