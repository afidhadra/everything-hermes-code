# AGENTS.md — everything-hermes-code

> Project context file for AI coding agents (Hermes, OpenCode, Claude Code, Codex).

## What is this project?

<!-- SUMMARY:START -->
A developer toolkit for Hermes Agent — 16 Python scripts, 6 Hermes skill wrappers,
config-based routing engine, MCP server manager, deploy coordinator, PR review bot,
background task manager, and TUI dashboard. Local-only personal tool.

> **222 tests · 7 skipped (intentional) · CI/CD via GitHub Actions**
<!-- SUMMARY:END -->

## Tech Stack

- **Scripts:** Python 3.11+, Bash (git hooks), Node.js (hooks)
- **Config:** YAML (`.ehc.yaml`, `config/routing.yaml`)
- **Testing:** pytest, coverage
- **TUI:** Rich (terminal tables, panels, live display)
- **CI/CD:** GitHub Actions (3 Python versions)
- **AI Agents:** Hermes Agent (primary), OpenCode, Claude Code, Codex

## Project Structure

<!-- STRUCTURE:START -->
├── scripts            Python tools
├── skills             Hermes skill wrappers + guides
├── config             routing + agent definitions
├── tests              pytest
├── agents             AI agent definitions
├── rules              Coding rules
├── prompts            System prompts
├── commands           Slash command docs
├── hooks              Git hooks
├── mcp-configs        MCP server configs
└── .github            CI/CD workflows
<!-- STRUCTURE:END -->

## Available Tools

<!-- SCRIPTS:START -->
| Script | Function |
| -------- | ---------- |
| `agent-router.py` | Smart Agent Router — intelligent agent recommendation engine. |
| `agent-runner.py` | Agent Runner - Execute AI agents for specific tasks. |
| `command-runner.py` | Command Runner - Execute slash commands. |
| `cross-repo-auditor.py` | Everything Hermes Code — Cross-Repo Auditor (Layer C) |
| `deploy.py` | Everything Hermes Code — Deploy Coordinator |
| `docker-check.py` | Everything Hermes Code — Docker Health Check |
| `ehc.py` | Everything Hermes Code — Unified Dashboard |
| `fix-markdown.py` | Enhanced markdownlint auto-fixer. |
| `generate-agents.py` | Auto-generate dynamic sections of AGENTS.md. |
| `mcp-manager.py` | MCP Manager — Auto-Discovery, Registry, and Health Check. |
| `orchestrator.py` | Everything Hermes Code — Orchestration Engine with Plan-First Workflow. |
| `pr-review.py` | PR Review Bot — automated code review for GitHub pull requests. |
| `regression-analyzer.py` | Everything Hermes Code — Regression Analyzer (Layer B) |
| `repo-status.py` | Everything Hermes Code — Multi-Repo Status |
| `task-worker.py` | Task Worker — background process for running orchestration agents. |
| `tui.py` | TUI — Terminal UI for EHC Task Manager. |
<!-- SCRIPTS:END -->

## Quick Commands

```bash
make help              # show all targets
make test              # run <!-- TESTS:START -->
222 passed · 7 skipped
<!-- TESTS:END -->
make lint              # fix markdown formatting
make check             # check dependencies
make install-skills    # install tools as Hermes skills
python3 ehc.py         # unified dashboard
python3 docker-check.py # container health
```

## Hermes Skills (installed via `make install-skills`)

All tools have Hermes skill wrappers. Install permanently:

```bash
make install-skills

# → ~/.hermes/skills/ehc-*/

# → Load: hermes -z "orchestrate: refactor auth" --skills ehc-orchestrator

```

## Config

Edit `.ehc.yaml` for project-specific settings (repos, containers, services).
Template at `.ehc.yaml.example`.

Routing config at `config/routing.yaml` — edit scoring rules without touching code.

## Environment

- **OS:** Fedora 44, Hyprland (Wayland), fish shell
- **SELinux:** Enforcing — Docker volumes need `:Z` flag
- **Hardware:** Dell Precision 5530 (i9-8950HK, 30GB RAM)
- **AI Model:** GLM-5.2 via Z.AI (primary)

## Git Workflow

1. Feature branches → conventional commits → PR → squash-merge to `development`
1. Run `make test` before every commit (pre-commit hook auto-fixes markdown)
1. Pre-push hook runs regression analysis
1. CI/CD runs <!-- TESTS:START -->

222 passed · 7 skipped
<!-- TESTS:END --> on push (3 Python versions)

1. Commit format: `type(scope): subject` (feat, fix, refactor, chore, docs, test)
