# Architecture Guide

Understanding the structure and design of Everything Hermes Code.

## Project Structure

```text
everything-hermes-code/
├── agents/           # AI agent definitions
├── commands/         # Slash command documentation
├── examples/         # Usage examples
├── hooks/            # Git hooks system
├── mcp-configs/      # MCP server configurations
├── prompts/          # System prompts for AI models
├── rules/            # Coding rules and guidelines
├── scripts/          # Utility scripts
├── skills/           # Reusable knowledge base
├── tests/            # Unit tests
├── docs/             # Documentation
└── .github/          # GitHub configuration
```

## Core Components

### 1. Agents (`agents/`)

AI agent definitions for specific tasks:

- **architect**: System design and architecture
- **coder**: Code implementation
- **debugger**: Bug identification and fixing
- **reviewer**: Code review and quality
- **documenter**: Documentation generation
- **optimizer**: Performance optimization
- **planner**: Project planning
- **security**: Security analysis
- **tdd-guide**: Test-driven development

### 2. Commands (`commands/`)

Slash commands for quick actions:

- **analyze**: Code quality analysis
- **fix**: Auto-fix linting issues
- **review**: Comprehensive code review
- **security**: Security vulnerability scan

### 3. Skills (`skills/`)

Reusable knowledge base:

- **go-development**: Go best practices
- **vue-development**: Vue 3/TypeScript
- **docker-workflow**: Docker management
- **git-workflow**: Git best practices

### 4. Hooks (`hooks/`)

Git hook system:

- **pre-commit**: Auto-fix markdown before commit
- **post-commit**: Log commit information
- **pre-push**: Final checks before push

### 5. Scripts (`scripts/`)

Utility scripts:

- **fix-markdown.py**: Markdown auto-fixer
- **agent-runner.py**: Agent execution
- **command-runner.py**: Command execution

## Data Flow

```text
User Input → Command → Agent → Output
                ↓
            Skills (Knowledge)
                ↓
            Rules (Constraints)
```

## Design Principles

1. **Modularity**: Each component is independent
1. **Reusability**: Skills and prompts can be shared
1. **Extensibility**: Easy to add new agents/commands
1. **Automation**: Hooks reduce manual work
1. **Documentation**: Everything is documented

## Integration Points

### Hermes Agent

- Skills loaded via config
- Prompts used for context
- Rules enforced during execution

### Git Workflow

- Pre-commit hooks for quality
- Post-commit for notifications
- Pre-push for final checks

### MCP Servers

- SonarQube for code analysis
- GitHub for repository management
- Context7 for documentation

## Adding New Components

### New Agent

1. Create `agents/my-agent.md`
1. Define system prompt
1. Add to agent-runner.py
1. Test with sample task

### New Command

1. Create `commands/my-command.md`
1. Create `scripts/commands/my-command.sh`
1. Add to command-runner.py
1. Test with sample input

### New Skill

1. Create `skills/my-skill.md`
1. Document best practices
1. Add examples
1. Test with Hermes

## Performance Considerations

- Scripts are lightweight and fast
- Hooks run only when needed
- Skills are loaded on demand
- Tests run in isolation

## Security

- No sensitive data in repository
- Hooks validate inputs
- Scripts use safe operations
- MCP configs use environment variables
