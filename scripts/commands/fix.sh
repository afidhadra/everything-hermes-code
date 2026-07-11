#!/bin/bash
set -euo pipefail

# Fix command - Auto-fix linting issues

TARGET="${1:-.}"
DRY_RUN="${2:-}"

echo "🔧 Fixing linting issues..."
echo "📁 Target: $TARGET"
echo ""

if [ "$DRY_RUN" = "--dry-run" ]; then
    echo "🔍 Dry run mode (no changes will be made)"
    python3 scripts/fix-markdown.py "$TARGET" 2>/dev/null
else
    echo "📝 Applying fixes..."
    python3 scripts/fix-markdown.py "$TARGET" 2>/dev/null
    echo ""
    echo "✅ Fixes applied"
fi
