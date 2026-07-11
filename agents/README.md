# Agents

## Overview

Specialized AI agents for different development tasks. Each agent has a specific role, permissions, and system prompt.

## Available Agents

| Agent | File | Purpose |
|-------|------|---------|
| coder | coder.md | Write production-ready code |
| debugger | debugger.md | Find and fix bugs |
| reviewer | reviewer.md | Code review and security |
| architect | architect.md | System design and architecture |
| planner | planner.md | Project planning and breakdown |
| tdd-guide | tdd-guide.md | Test-driven development |
| documenter | documenter.md | Documentation generation |
| optimizer | optimizer.md | Performance optimization |
| security | security.md | Security audit and hardening |

## Usage

### In Hermes

Load agent via system prompt:

```bash
export HERMES_EPHEMERAL_SYSTEM_PROMPT="$(cat ~/Projects/everything-hermes-code/agents/coder.md)"
```text

### In OpenCode

Add to AGENTS.md:

```markdown

## Agents

- coder: Write production-ready code
- debugger: Find and fix bugs
- reviewer: Code review and security

```text

## Creating Custom Agents

1. Create a new `.md` file in this directory
1. Add frontmatter:

```markdown
---
name: my-agent
role: Write awesome code
permissions:

  - edit
  - bash
  - read

---
```text

1. Add system prompt below

## Agent Permissions

| Permission | Description |
|------------|-------------|
| edit | Can modify files |
| bash | Can run shell commands |
| read | Can read files |
| write | Can create files |
| delete | Can delete files |

## Best Practices

- One agent per task type
- Clear, specific system prompts
- Appropriate permissions (least privilege)
- Reusable across projects
