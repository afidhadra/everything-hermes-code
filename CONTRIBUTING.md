# Everything Hermes Code

## Overview

This is a Claude Code-style toolkit for Hermes Agent. It provides a complete AI development workflow with agents, commands, skills, rules, hooks, prompts, and MCP configs.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development

### Prerequisites

- Node.js 18+
- Git
- Hermes Agent or OpenCode

### Setup

```bash
# Clone the repo
git clone https://github.com/afidhadra/everything-hermes-code.git

# Install dependencies
npm install

# Run tests
npm test
```

### Project Structure

```
everything-hermes-code/
├── agents/           # Specialized AI agents
├── commands/         # Slash commands
├── rules/            # AI rules & constraints
├── skills/           # Reusable knowledge
├── hooks/            # Pre/Post execution hooks
├── prompts/          # System prompts
├── scripts/          # Automation scripts
├── config/           # Config templates
├── mcp-configs/      # MCP server configs
├── examples/         # Example setups
└── tests/            # Tests
```

### Adding New Components

1. Follow the existing structure
2. Add frontmatter with name, description, and metadata
3. Include examples where appropriate
4. Update README.md
5. Add tests if applicable

## License

MIT