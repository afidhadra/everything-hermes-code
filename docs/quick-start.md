# Quick Start Guide

Get started with Everything Hermes Code in minutes.

## Prerequisites

- Python 3.x
- Git
- Hermes Agent installed

## Installation

```bash

# Clone the repository

git clone https://github.com/afidhadra/everything-hermes-code.git
cd everything-hermes-code

# Make scripts executable

chmod +x scripts/*.py
chmod +x scripts/commands/*.sh
chmod +x hooks/scripts/*.sh
```

## Basic Usage

### 1. Analyze Code Quality

```bash

# Analyze current directory

python3 scripts/commands/analyze.sh .

# Analyze specific directory

python3 scripts/commands/analyze.sh src/
```

### 2. Fix Linting Issues

```bash

# Fix all markdown files

python3 scripts/fix-markdown.py .

# Fix specific directory

python3 scripts/fix-markdown.py src/
```

### 3. Run Tests

```bash

# Run unit tests

python3 tests/test_fix_markdown.py
```

### 4. Use Agent Runner

```bash

# List available agents

python3 scripts/agent-runner.py list

# Run an agent

python3 scripts/agent-runner.py architect "Design a microservices architecture"
```

## Configuration

### Hermes Integration

Add to your `~/.hermes/config.yaml`:

```yaml
skills:

  - /path/to/everything-hermes-code/skills

```

### Git Hooks

```bash

# Install git hooks

node hooks/index.js install
```

## Commands

| Command | Description |
| --------- | ------------- |
| `/analyze` | Analyze code quality |
| `/fix` | Auto-fix linting issues |
| `/review` | Code review |
| `/security` | Security scan |

## Agents

| Agent | Description |
| ------- | ------------- |
| `architect` | System design |
| `coder` | Code implementation |
| `debugger` | Bug fixing |
| `reviewer` | Code review |
| `documenter` | Documentation |
| `optimizer` | Performance |
| `planner` | Project planning |
| `security` | Security analysis |
| `tdd-guide` | Test-driven development |

## Next Steps

- Read the [Architecture Guide](architecture.md)
- Check out [Examples](examples/)
- Read [Contributing Guidelines](contributing.md)
