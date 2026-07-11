# Rules

## Overview

AI rules and constraints that ensure consistent, high-quality output.

## Available Rules

| Rule | File | Description |
| ------ | ------ | ------------- |
| Security | security.md | Security best practices |
| Coding Style | coding-style.md | Coding standards |
| Testing | testing.md | Testing guidelines |
| Git Workflow | git-workflow.md | Git conventions |

## Usage

### In Hermes

```bash

# Load rules

export HERMES_RULES="$(cat ~/Projects/everything-hermes-code/rules/*.md)"
```

### In OpenCode

Add to AGENTS.md:

```markdown

## Rules

- security: No hardcoded secrets, validate all inputs
- coding-style: Follow ESLint/Prettier config
- testing: Write tests before implementation

```

## Creating Custom Rules

1. Create a new `.md` file in this directory
1. Add frontmatter:

```markdown
---
name: my-rule\ndescription: Does something important\npriority: high
---
```

1. Add the rule content below

## Rule Priorities

| Priority | Description |
| ---------- | ------------- |
| critical | Must follow, blocks deployment |
| high | Should follow, requires justification to skip |
| medium | Recommended, can be relaxed if needed |
| low | Optional, style preference |
