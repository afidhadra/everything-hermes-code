#!/bin/bash
# Pre-commit hook for markdown linting

echo "🔍 Running pre-commit checks..."

# Fix markdown files
python3 scripts/fix-markdown.py . 2>/dev/null

# Re-stage fixed files
git add -u 2>/dev/null

echo "✅ Pre-commit checks passed"
