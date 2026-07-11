# Contributing Guidelines

How to contribute to Everything Hermes Code.

## Getting Started

1. Fork the repository
1. Clone your fork
1. Create a feature branch
1. Make your changes
1. Submit a pull request

## Development Setup

```bash

# Clone your fork

git clone https://github.com/YOUR_USERNAME/everything-hermes-code.git
cd everything-hermes-code

# Install dependencies

chmod +x scripts/*.py
chmod +x scripts/commands/*.sh
chmod +x hooks/scripts/*.sh

# Run tests

python3 tests/test_fix_markdown.py
```

## Coding Standards

### Python

- Follow PEP 8
- Use type hints
- Write docstrings
- Add unit tests

### Markdown

- Use proper formatting
- Follow markdownlint rules
- Add language to code blocks
- Surround headings with blank lines

### Git

- Use conventional commits
- Keep commits atomic
- Write clear commit messages
- Reference issues when applicable

## Commit Message Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation
- **style**: Formatting
- **refactor**: Code restructuring
- **test**: Adding tests
- **chore**: Maintenance

### Examples

```text
feat(agents): add new security agent

- Add security agent definition
- Include vulnerability scanning
- Add examples to documentation

Closes #123
```

```text
fix(scripts): fix markdown linting issue

- Fix MD040 not handling closing fences
- Add unit test for edge case
- Update documentation

Fixes #456
```

## Pull Request Process

1. Update documentation if needed
1. Add tests for new features
1. Ensure all tests pass
1. Request review from maintainers
1. Address feedback promptly

## Code Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included
- [ ] Documentation is updated
- [ ] No breaking changes
- [ ] Commit messages are clear

## Reporting Issues

- Use GitHub Issues
- Include reproduction steps
- Provide environment details
- Attach relevant logs

## Feature Requests

- Describe the use case
- Explain the benefit
- Provide examples if possible
- Consider implementation complexity

## Documentation

- Update README if needed
- Add examples for new features
- Keep documentation current
- Use clear, concise language

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
