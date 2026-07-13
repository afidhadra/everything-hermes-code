# AGENTS.md — everything-hermes-code

> Project context file for AI coding agents (Hermes, OpenCode, Claude Code, Codex).

## What is this project?

A developer toolkit for Hermes Agent — 15 Python scripts, 6 Hermes skill wrappers,
config-based routing engine, MCP server manager, deploy coordinator, PR review bot,
background task manager, and TUI dashboard. Local-only personal tool.

**188 tests · 28 skipped (intentional) · CI/CD via GitHub Actions**

## Tech Stack

- **Scripts:** Python 3.11+, Bash (git hooks), Node.js (hooks)
- **Config:** YAML (`.ehc.yaml`, `config/routing.yaml`)
- **Testing:** pytest, coverage
- **TUI:** Rich (terminal tables, panels, live display)
- **CI/CD:** GitHub Actions (3 Python versions)
- **AI Agents:** Hermes Agent (primary), OpenCode, Claude Code, Codex

## Project Structure

```
├── scripts/          15 Python tools (orchestrator, agent-router, pr-review, ...)
├── skills/           6 Hermes skill wrappers + 5 tech guides
├── config/           routing.yaml (scoring) + agent-capabilities.yaml
├── tests/            188 tests (pytest, auto-discovery)
├── agents/           AI agent definitions (architect, coder, debugger, ...)
├── rules/            Coding rules (security, testing, git-workflow)
├── prompts/          System prompts (coding, debug, review)
├── commands/         Slash command docs (analyze, fix, review, security)
├── hooks/            Git hooks (pre-commit, pre-push, post-commit)
├── mcp-configs/      MCP server configs (SonarQube, GitHub, Context7, Ogham)
├── .github/          CI/CD workflows
├── .ehc.yaml         Project config (edit for your project)
├── .ehc.yaml.example Generic template
└── AGENTS.md         This file
```

## Available Tools

| Script | Function |
|--------|----------|
| `orchestrator.py` | Plan-first multi-agent pipeline (analyze → plan → review → execute → report) |
| `agent-router.py` | Weighted scoring agent recommendation engine |
| `pr-review.py` | Automated GitHub PR review (security, quality, deps) |
| `mcp-manager.py` | MCP server auto-discovery + registry + health check |
| `deploy.py` | Multi-repo deploy coordinator with health verification |
| `docker-check.py` | Docker container health monitor |
| `task-worker.py` | Background agent execution worker |
| `tui.py` | Rich-based TUI dashboard + history |
| `ehc.py` | Unified status dashboard (docker, git, system) |
| `repo-status.py` | Git repo status |

## Quick Commands

```bash
make help              # show all targets
make test              # run 188 tests
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
2. Run `make test` before every commit (pre-commit hook auto-fixes markdown)
3. Pre-push hook runs regression analysis
4. CI/CD runs 188 tests on push (3 Python versions)
5. Commit format: `type(scope): subject` (feat, fix, refactor, chore, docs, test)
