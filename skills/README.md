# Skills

## Overview

Reusable knowledge base for AI agents. Skills provide specific domain expertise.

## Available Skills

| Skill | File | Description |
|-------|------|-------------|
| Coding Standards | coding-standards.md | Language-specific standards |
| Backend Patterns | backend-patterns.md | Backend architecture |
| Frontend Patterns | frontend-patterns.md | Frontend architecture |
| Database Patterns | database-patterns.md | Database design |
| DevOps Patterns | devops-patterns.md | CI/CD and deployment |
| Debugging Patterns | debugging-patterns.md | Debugging strategies |
| Security Patterns | security-patterns.md | Security implementation |

## Usage

### In Hermes

```bash

# Load skill

export HERMES_SKILL="$(cat ~/Projects/everything-hermes-code/skills/coding-standards.md)"
```text

### In OpenCode

Add to AGENTS.md:

```markdown

## Skills

- coding-standards: TypeScript best practices
- backend-patterns: REST API design
- database-patterns: PostgreSQL optimization

```text

## Creating Custom Skills

1. Create a new `.md` file in this directory
1. Add frontmatter:

```markdown
---
name: my-skill
description: Does something awesome
related:

  - other-skill

---
```text

1. Add the skill content below

## Best Practices

- One skill per domain
- Include code examples
- Reference related skills
