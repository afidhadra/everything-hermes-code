# Hooks

## Overview

Pre/Post execution hooks for automation. Hooks run before or after AI actions.

## Available Hooks

| Hook | Type | Description |
| ------ | ------ | ------------- |
| PreToolUse | Pre | Validate before tool execution |
| PostToolUse | Post | Process after tool execution |
| Stop | Post | Cleanup when AI stops |
| FileWrite | Pre | Validate file writes |
| BashExec | Pre | Validate shell commands |

## Usage

### In Hermes

```yaml

# ~/.hermes/config.yaml

hooks:
  pre_tool_use:

    - validate_input

  post_tool_use:

    - log_action

```

### In OpenCode

```yaml

# .opencode/hooks.yaml

pre_tool_use:

  - validate_input

post_tool_use:

  - log_action

```

## Creating Custom Hooks

1. Create a new `.sh` or `.js` file in this directory
1. Add frontmatter:

```markdown
---
name: my-hook
type: pre
tool: bash
---
```

1. Add the hook script below

## Hook Types

| Type | Description |
| ------ | ------------- |
| pre | Runs before action |
| post | Runs after action |

## Best Practices

- Keep hooks fast (<1 second)
- Don't modify tool output
- Log actions for debugging
- Handle errors gracefully
