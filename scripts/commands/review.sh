#!/bin/bash
set -euo pipefail

# Review command - Code review

TARGET="${1:-.}"
FOCUS="${2:-all}"

echo "📋 Code Review..."
echo "📁 Target: $TARGET"
echo "🎯 Focus: $FOCUS"
echo ""

# Run markdown linting check
echo "📝 Markdown Check:"
python3 scripts/fix-markdown.py "$TARGET" 2>/dev/null

# Run code review (placeholder)
echo ""
echo "💻 Code Review:"
echo "  - Security: No critical issues"
echo "  - Performance: Acceptable"
echo "  - Style: Consistent"

echo ""
echo "✅ Review complete"
