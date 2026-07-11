# MCP Configs

## Overview

MCP server configurations for Hermes and OpenCode.

## Available Configs

| Config | File | Description |
| -------- | ------ | ------------- |
| GitHub | github.yaml | GitHub integration |
| Ogham | ogham.yaml | Persistent memory |
| Context7 | context7.yaml | Documentation lookup |
| Puppeteer | puppeteer.yaml | Browser automation |
| SQLite | sqlite.yaml | Local database |

## Usage

### In Hermes

Add to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  github:
    type: stdio
    command: /path/to/github-mcp-server
    args: [stdio]
```text

### In OpenCode

Add to `.opencode/mcp.yaml`:

```yaml
mcp_servers:
  github:
    type: stdio
    command: /path/to/github-mcp-server
    args: [stdio]
```text

## Creating Custom Configs

1. Create a new `.yaml` file in this directory
1. Add frontmatter:

```markdown
---
name: my-mcp
type: stdio
---
```text

1. Add the MCP config below

## MCP Server Types

| Type | Description |
| ------ | ------------- |
| stdio | Standard input/output |
| http | HTTP server |
| sse | Server-sent events |
