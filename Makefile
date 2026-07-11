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

.PHONY: lint test hooks check analyze clean setup help

PYTHON  := python3
FIX_MD  := scripts/fix-markdown.py
TESTS   := tests/test_fix_markdown.py
TESTS2  := tests/test_runners.py

help:
	@echo "everything-hermes-code"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "  lint      Fix markdown formatting"
	@echo "  test      Run unit tests"
	@echo "  hooks     Install git hooks"
	@echo "  check     Check dependencies"
	@echo "  analyze   Run SonarQube analysis"
	@echo "  clean     Remove cache files"
	@echo "  setup     Full setup (check + permissions + hooks)"
	@echo "  help      Show this help"
	@echo ""

lint:
	@echo ">>> Linting markdown..."
	@$(PYTHON) $(FIX_MD) .
	@echo ">>> Done"

test:
	@echo ">>> Running tests..."
	@$(PYTHON) $(TESTS)
	@$(PYTHON) $(TESTS2)
	@echo ">>> Done"

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
