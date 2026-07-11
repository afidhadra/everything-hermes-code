# Everything Hermes Code

**Claude Code-style toolkit for Hermes Agent**

Complete AI development workflow for Hermes + Big Pickle (GLM-4.6) — agents, commands, skills, rules, hooks, prompts, and MCP configs.

Inspired by [Everything Claude Code](https://github.com/WorldFlowAI/everything-claude-code).

## Features

| Component | Count | Description |
|-----------|-------|-------------|
| Agents | 9+ | Specialized AI agents for different tasks |
| Commands | 9+ | Slash commands for quick workflows |
| Rules | 8+ | AI rules and constraints |
| Skills | 7+ | Reusable knowledge base |
| Hooks | 5+ | Pre/Post execution automation |
| Prompts | 4 | System prompts for different modes |
| MCP Configs | 10+ | Server configurations |
| Scripts | 5+ | Automation and setup scripts |

## Directory Structure

```
everything-hermes-code/
├── agents/           # Specialized AI agents
├── commands/         # Slash commands
├── rules/            # AI rules & constraints
├── skills/           # Reusable knowledge
├── hooks/            # Pre/Post execution hooks
├── prompts/          # System prompts (coding, debug, review, analysis)
├── scripts/          # Automation scripts
├── config/           # Config templates
├── mcp-configs/      # MCP server configs
├── examples/         # Example setups
└── README.md
```

## Quick Start

### 1. Install

```bash
git clone https://github.com/afidhadra/everything-hermes-code.git ~/Projects/everything-hermes-code
```

### 2. Setup

```bash
# Copy prompts to Hermes
cp -r prompts/* ~/.hermes/prompts/

# Or set system prompt
export HERMES_EPHEMERAL_SYSTEM_PROMPT="$(cat ~/Projects/everything-hermes-code/prompts/coding.md)"
```

### 3. Use

```bash
# Switch mode
source ~/Projects/everything-hermes-code/scripts/prompt.sh coding

# Or in fish
source ~/Projects/everything-hermes-code/scripts/prompt.fish coding
```

## Components

### Agents

| Agent | Purpose |
|-------|---------|
| coder | Write production-ready code |
| debugger | Find and fix bugs |
| reviewer | Code review and security |
| architect | System design and architecture |
| planner | Project planning and breakdown |
| tdd-guide | Test-driven development |
| documenter | Documentation generation |
| optimizer | Performance optimization |
| security | Security audit and hardening |

### Commands

| Command | Description |
|---------|-------------|
| /code | Switch to coding mode |
| /debug | Switch to debug mode |
| /review | Switch to review mode |
| /analyze | Switch to analysis mode |
| /plan | Plan a feature or project |
| /test | Generate and run tests |
| /refactor | Refactor code with best practices |
| /document | Generate documentation |
| /security | Run security audit |

### Rules

- security.md — Security best practices
- coding-style.md — Coding standards
- testing.md — Testing guidelines
- git-workflow.md — Git conventions
- performance.md — Performance optimization
- documentation.md — Documentation standards
- error-handling.md — Error handling patterns
- api-design.md — API design principles

### Skills

- coding-standards — Language-specific standards
- backend-patterns — Backend architecture
- frontend-patterns — Frontend architecture
- database-patterns — Database design
- devops-patterns — CI/CD and deployment
- debugging-patterns — Debugging strategies
- security-patterns — Security implementation

## Model

**Big Pickle** (GLM-4.6 via OpenCode Zen)
- Context: 200K tokens
- Max output: 128K tokens
- Price: Free

## Compatibility

- Hermes Agent ✓
- OpenCode ✓
- Claude Code (partial) ✓

## License

MIT — Use freely, modify as needed.

## Credits

- [Everything Claude Code](https://github.com/WorldFlowAI/everything-claude-code) — Inspiration
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Platform
- [OpenCode Zen](https://opencode.ai) — Model provider