# Everything Hermes Code

**Claude Code-style toolkit for Hermes Agent**

Complete AI development workflow for Hermes + Big Pickle (GLM-4.6) — agents, commands, skills, rules, hooks, prompts, and MCP configs.

Inspired by [Everything Claude Code](https://github.com/WorldFlowAI/everything-claude-code).

## Features

| Component | Count | Description |
| ----------- | ------- | ------------- |
| Agents | 9 | Specialized AI agents for different tasks |
| Commands | 4 | Slash commands for quick workflows |
| Rules | 5 | AI rules and constraints |
| Skills | 4 | Reusable knowledge base |
| Hooks | 1 | Pre/Post execution automation |
| Prompts | 4 | System prompts for different modes |
| MCP Configs | 1 | Server configurations (SonarQube) |
| Scripts | 1 | Automation scripts |

## Directory Structure

```text
everything-hermes-code/
├── agents/           # Specialized AI agents
├── commands/         # Slash commands
├── rules/            # AI rules & constraints
├── skills/           # Reusable knowledge
├── hooks/            # Pre/Post execution hooks
├── prompts/          # System prompts (coding, debug, review, analysis)
├── scripts/          # Automation scripts
├── mcp-configs/      # MCP server configs
├── examples/         # Example setups
├── .github/          # GitHub Copilot instructions
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
| ------- | --------- |
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
| --------- | ------------- |
| /analyze | Analyze code quality and metrics |
| /fix | Auto-fix linting and formatting issues |
| /review | Comprehensive code review |
| /security | Security vulnerability scan |

### Skills

| Skill | Description |
| ------- | ------------- |
| go-development | Go best practices and patterns |
| vue-development | Vue 3/TypeScript best practices |
| docker-workflow | Docker development workflow |
| git-workflow | Git best practices and conventions |

### Rules

- security.md — Security best practices
- coding-style.md — Coding standards
- testing.md — Testing guidelines
- git-workflow.md — Git conventions

### Prompts

- coding.md — Production-ready code generation
- debug.md — Root cause analysis
- review.md — Code review and security
- analysis.md — Systems analysis

## Model

**Big Pickle** (GLM-4.6 via OpenCode Zen)

- Context: 200K tokens
- Max output: 128K tokens
- Price: Free

## MCP Servers

### SonarQube (Configured)

```yaml
sonarqube:
  type: stdio
  command: /home/afidhadra/.local/bin/sonarqube-mcp-wrapper.sh
  timeout: 30000
```

- Server: http://localhost:9000
- Version: 26.7.0 (Community Edition)
- Token: ~/.sonarqube_token

## Compatibility

- Hermes Agent ✓
- OpenCode ✓
- Claude Code (partial) ✓
- GitHub Copilot ✓

## License

MIT — Use freely, modify as needed.

## Credits

- [Everything Claude Code](https://github.com/WorldFlowAI/everything-claude-code) — Inspiration
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — Platform
- [OpenCode Zen](https://opencode.ai) — Model provider
- [SonarQube](https://www.sonarsource.com) — Code quality
