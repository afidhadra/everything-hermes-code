# Everything Hermes Code

CLI toolkit + Hermes Agent skills untuk development workflow — orchestrator, agent router, MCP manager, deploy coordinator, PR review, dan container monitoring.

```
╭──────────────────────────────────────────────╮
│  188 tests · 15 scripts · 6 Hermes skills    │
│  CI/CD: GitHub Actions (3 Python versions)   │
╰──────────────────────────────────────────────╯
```

## Quick Start

```bash
# 1. Install dependencies
pip install pyyaml pytest rich

# 2. Copy config template
cp .ehc.yaml.example .ehc.yaml
# lalu edit isinya sesuai project lo

# 3. Coba tools
python3 scripts/docker-check.py    # docker health
python3 scripts/ehc.py             # unified dashboard
python3 scripts/orchestrator.py --help  # orchestration

# 4. Install Hermes skills (optional, recommended)
make install-skills
```

## Tools

### Orchestrator — Plan-First AI Agent Execution
`scripts/orchestrator.py`

Multi-agent pipeline: Analyze task → Generate plan → Human review → Execute agents → Aggregate report.

```bash
python3 orchestrator.py "Refactor auth module"
python3 orchestrator.py --plan-only "Add login feature"
python3 orchestrator.py --dry-run "Fix login bug"
```

### Agent Router — Smart Agent Recommendation
`scripts/agent-router.py`

Weighted scoring engine berbasis YAML config. Stemming-aware keyword matching.

```bash
python3 agent-router.py "Fix authentication bug"
python3 agent-router.py "Add login page" --json
python3 agent-router.py --list-agents
```

### PR Review Bot — Automated Code Review
`scripts/pr-review.py`

Scan PR diff untuk hardcoded secrets, SQL injection, code quality, dependency changes.

```bash
python3 pr-review.py --pr 5                    # review PR #5
python3 pr-review.py --all-open                # semua open PR
python3 pr-review.py --pr 5 --dry-run --json   # preview
```

### MCP Manager — Server Discovery & Registry
`scripts/mcp-manager.py`

Auto-detect MCP servers dari Docker, binaries, dan Hermes config.

```bash
python3 mcp-manager.py scan     # discover
python3 mcp-manager.py health   # check connectivity
python3 mcp-manager.py generate # generate configs
```

### Deploy Coordinator — Multi-Repo Deploy
`scripts/deploy.py`

Deploy BE + FE dengan pre-deploy checks dan health verification.

```bash
python3 deploy.py --status          # apa yang perlu dideploy
python3 deploy.py --deploy all      # full deploy
python3 deploy.py --deploy be        # backend only
```

### Docker Check — Container Health Monitor
`scripts/docker-check.py`

Monitor containers, health endpoints, auto-restart.

```bash
python3 docker-check.py              # quick check
python3 docker-check.py --restart-dead
python3 docker-check.py --watch
```

### Task Manager — Background Jobs + TUI
`scripts/task-worker.py` + `scripts/tui.py`

Background agent execution dengan live dashboard.

```bash
python3 orchestrator.py "task" --background  # spawn
python3 orchestrator.py --status             # live TUI
python3 orchestrator.py --history            # all tasks
```

### Unified Dashboard — All Status in One Screen
`scripts/ehc.py`

```bash
python3 ehc.py            # full dashboard
python3 ehc.py --json     # JSON output
python3 ehc.py --watch    # auto-refresh
```

## Hermes Skills

Semua tools punya Hermes skill wrapper di `skills/`. Load via:

```bash
hermes -z "orchestrate: refactor auth" --skills skills/orchestrator.md
hermes -z "check docker health" --skills skills/docker-check.md
hermes -z "deploy backend" --skills skills/deploy.md
hermes -z "review PR #5" --skills skills/pr-review.md
```

Atau install permanent:

```bash
make install-skills
# lalu panggil tanpa --skills path:
hermes -z "orchestrate: refactor auth" --skills orchestrator
```

## Config

Semua konfigurasi via `.ehc.yaml` — lihat `.ehc.yaml.example` untuk template.

```yaml
project:
  name: MY-PROJECT
  root: ~/Projects/my-project
repos:
  be:
    name: Backend
    dir: backend
    lang: go
docker:
  containers:
    api-dev:
      friendly: API
      health_url: http://localhost:8080/health
```

## Testing

```bash
make test       # pytest — 188 tests
make lint       # markdown fix
make check      # dependency check
```

Atau langsung:

```bash
python3 -m pytest tests/ -v
```

## CI/CD

GitHub Actions otomatis jalan di setiap push ke `development` / `main`:

- Python 3.11, 3.12, 3.13 matrix
- 188 tests
- Coverage report
- Script import check
- Makefile validation

## Project Structure

```
├── scripts/              # 15 Python tools
├── skills/               # 6 Hermes skill wrappers
├── config/               # routing.yaml
├── tests/                # 188 tests
├── hooks/                # git hooks
├── agents/               # agent definitions
├── commands/             # slash command docs
├── rules/                # coding rules
├── prompts/              # system prompts
├── mcp-configs/          # MCP server configs
├── .ehc.yaml             # project config
└── .ehc.yaml.example     # template
```

## Requirements

| Dependency | Untuk |
|-----------|-------|
| Python 3.11+ | Semua tools |
| PyYAML | Config parsing, routing YAML |
| Rich | TUI dashboard (optional) |
| `gh` CLI | PR Review Bot (optional) |
| Docker | Container management (optional) |

## License

MIT
