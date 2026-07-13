# everything-hermes-code Makefile
# Single entry point for all project operations.
#
# Usage:
#   make [target]
#
# Targets:
#   lint      — fix markdown formatting across all .md files
#   test      — run Python unit tests
#   hooks     — install git hooks via install.sh
#   check     — run dependency check
#   analyze   — run SonarQube code analysis
#   clean     — remove generated/cache files
#   setup     — full first-run setup (check + permissions + hooks)
#   help      — show this help

.PHONY: lint test hooks check analyze clean setup help \
        dashboard status repos docker-check install-skills generate-agents

PYTHON  := python3
FIX_MD  := scripts/fix-markdown.py

help:
	@echo "everything-hermes-code"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "  dashboard       Show unified status (docker + repos + health)"
	@echo "  status          Deploy status (BE + FE)"
	@echo "  repos           Multi-repo git status"
	@echo "  docker-check    Docker health check"
	@echo "  lint            Fix markdown formatting"
	@echo "  test            Run unit tests"
	@echo "  hooks           Install git hooks"
	@echo "  check           Check dependencies"
	@echo "  analyze         Run SonarQube analysis"
	@echo "  clean           Remove cache files"
	@echo "  setup           Full setup (check + permissions + hooks)"
	@echo "  install-skills  Install Hermes skill wrappers to ~/.hermes/skills/"
	@echo "  help            Show this help"
	@echo ""

dashboard:
	@python3 scripts/ehc.py

lint:
	@echo ">>> Linting markdown..."
	@$(PYTHON) $(FIX_MD) .
	@echo ">>> Done"

test:
	@echo ">>> Running tests..."
	@$(PYTHON) -m pytest tests/ -v --tb=short 2>&1 | tail -50
	@echo ">>> Done (exit code: $$?)"

hooks:
	@echo ">>> Installing git hooks..."
	@./install.sh --hooks
	@echo ">>> Done"

check:
	@echo ">>> Checking dependencies..."
	@./install.sh --check
	@echo ">>> Done"

analyze:
	@echo ">>> Running SonarQube analysis..."
	@bash scripts/commands/analyze.sh .
	@echo ">>> Done"

status:
	@echo ">>> Deploy status..."
	@python3 scripts/deploy.py --status
	@echo ">>> Done"

repos:
	@echo ">>> Multi-repo status..."
	@python3 scripts/repo-status.py
	@echo ">>> Done"

docker-check:
	@echo ">>> Docker health..."
	@python3 scripts/docker-check.py
	@echo ">>> Done"

clean:
	@echo ">>> Cleaning..."
	@find . -name "__pycache__" -not -path "./.git/*" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true
	@find . -name "*.log" -not -path "./.git/*" -delete 2>/dev/null || true
	@find . -name "*.tmp" -not -path "./.git/*" -delete 2>/dev/null || true
	@echo ">>> Done"

setup:
	@echo ">>> Running full setup..."
	@./install.sh --all
	@echo ">>> Done"

install-skills:
	@echo ">>> Installing Hermes skills..."
	@mkdir -p ~/.hermes/skills
	@for f in skills/*.md; do \
	    name=$$(basename "$$f" .md); \
	    dir=~/.hermes/skills/ehc-$$name; \
	    mkdir -p "$$dir"; \
	    cp "$$f" "$$dir/SKILL.md"; \
	    echo "  ✅ Installed: ehc-$$name"; \
	done
	@echo ">>> Done. Load via: hermes --skills ehc-<name>"

generate-agents:
	@echo ">>> Generating AGENTS.md..."
	@$(PYTHON) scripts/generate-agents.py
	@echo ">>> Done"
