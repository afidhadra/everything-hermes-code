# Prompts

## Overview

System prompts for different modes. These define how the AI should behave.

## Available Prompts

| Prompt | File | Description |
| -------- | ------ | ------------- |
| Coding | coding.md | Write production-ready code |
| Debug | debug.md | Find and fix bugs |
| Review | review.md | Code review and security |
| Analysis | analysis.md | Deep thinking and analysis |

## Usage

### In Terminal

```bash

# Switch to coding mode

source ~/Projects/everything-hermes-code/scripts/prompt.sh coding

# Switch to debug mode

source ~/Projects/everything-hermes-code/scripts/prompt.sh debug
```

### In Hermes

```bash

# Set system prompt

export HERMES_EPHEMERAL_SYSTEM_PROMPT="$(cat ~/Projects/everything-hermes-code/prompts/coding.md)"
```

### In OpenCode

Add to AGENTS.md:

```markdown

## Prompts

- coding: Write production-ready code
- debug: Find and fix bugs
- review: Code review and security

```

## Creating Custom Prompts

1. Create a new `.md` file in this directory
1. Add frontmatter:

```markdown
---
name: my-prompt
mode: custom
---
```

1. Add the system prompt below

## Best Practices

- One prompt per mode
- Clear, specific instructions
- Include format examples
- Define rules and constraints
