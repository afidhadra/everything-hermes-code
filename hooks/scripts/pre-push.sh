#!/bin/bash
set -euo pipefail

# Pre-push hook for final checks

echo "🔍 Running pre-push checks..."

# Run markdown lint check
python3 scripts/fix-markdown.py . 2>/dev/null

# Check if there are unstaged changes
if ! git diff --quiet 2>/dev/null; then
    echo "⚠️  Unstaged changes detected. Please commit or stash them."
    exit 1
fi

echo "✅ Pre-push checks passed"
