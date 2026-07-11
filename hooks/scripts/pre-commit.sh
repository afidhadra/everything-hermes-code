#!/bin/bash
set -euo pipefail

# Pre-commit hook for markdown linting
# Only fixes and re-stages markdown files that are already staged

echo "🔍 Running pre-commit checks..."

# Get list of staged markdown files only
STAGED_MD=$(git diff --cached --name-only --diff-filter=ACM -- '*.md' '*.markdown')

if [ -n "$STAGED_MD" ]; then
    # Fix only staged markdown files
    echo "$STAGED_MD" | while IFS= read -r f; do
        if [ -f "$f" ]; then
            python3 scripts/fix-markdown.py "$f" 2>/dev/null
        fi
    done

    # Re-stage only the markdown files that were fixed (not all tracked files)
    echo "$STAGED_MD" | while IFS= read -r f; do
        git add "$f" 2>/dev/null
    done
fi

echo "✅ Pre-commit checks passed"
