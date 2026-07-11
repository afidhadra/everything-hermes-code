# AGENTS.md — everything-hermes-code

> Project context file for AI coding agents (Hermes, OpenCode, Claude Code, Codex).

## What is this project?

A Claude Code-style toolkit for Hermes Agent — agents, commands, rules, skills,
hooks, prompts, and MCP configurations. Local-only personal tool, no deployment.

## Tech Stack

- **Scripts:** Python 3, Bash, Node.js (hooks)
- **Docs:** Markdown (markdownlint + Prettier enforced)
- **Code Quality:** SonarQube Community Edition v26.7 (Docker, localhost:9000)
- **AI Models:** GLM-5.2 via Z.AI (primary), Big Pickle via OpenCode Zen (free tier)

## Project Structure

```text
agents/          AI agent definitions (architect, coder, debugger, ...)
commands/        Slash command docs (analyze, fix, review, security)
rules/           Coding rules (security, coding-style, testing, git-workflow)
skills/          Tech skill guides (Go, Vue, Docker, Git)
hooks/           Git hooks (pre-commit, post-commit, pre-push)
prompts/         System prompts (coding, debug, review, analysis)
scripts/         Utility scripts (fix-markdown.py, agent-runner.py)
mcp-configs/     MCP server configs (SonarQube, GitHub)
tests/           Unit tests
docs/            Documentation (quick-start, architecture, contributing)
examples/        Usage examples
```

## Conventions

- **Commit messages:** Conventional Commits — `type(scope): subject`
- **Markdown:** markdownlint enforced via pre-commit hook. Config in `.markdownlint.json`
- **Python:** PEP 8, type hints, docstrings on public functions
- **Shell:** `set -euo pipefail`, no bashisms in portable scripts
- **File naming:** lowercase-with-hyphens for all files

## Quick Commands

```bash
make help      # show all targets
make setup     # first-run: check deps + permissions + hooks
make lint      # fix markdown formatting
make test      # run unit tests
make analyze   # run SonarQube scan
make clean     # remove cache files
```

## Rules (auto-loaded)

1. **Security:** No hardcoded secrets, validate all inputs, least privilege
1. **Coding Style:** PEP 8 for Python, shellcheck for Bash, consistent naming
1. **Testing:** Write tests for new Python functions, run `make test` before commit
1. **Git Workflow:** Feature branches, conventional commits, squash-merge to development

## MCP Servers

- **SonarQube:** localhost:9000, token at `~/.sonarqube_token`, Community Edition
- **GitHub:** `~/go/bin/github-mcp-server`, token from env `GITHUB_TOKEN`

## Environment

- **OS:** Fedora 44, Hyprland (Wayland), fish shell
- **SELinux:** Enforcing — Docker volumes need `:Z` flag
- **Hardware:** Dell Precision 5530 (i9-8950HK, 30GB RAM)

## Agent Workflow

1. Read rules from `rules/*.md` before making changes
1. Check relevant skill in `skills/*.md` for tech-specific guidance
1. Use prompts from `prompts/*.md` for task-appropriate system context
1. Run `make test` before committing
1. Pre-commit hook auto-fixes markdown

## Files NOT to edit

- `.git/hooks/*` — these are symlinks to `hooks/scripts/`, edit the source
- `node_modules/` — doesn't exist but reserved
- `scripts/__pycache__/` — generated, gitignored
