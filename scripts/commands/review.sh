#!/bin/bash
set -euo pipefail

# Review command — routes to orchestrator for AI-powered review
# For static analysis, use analyze.sh (SonarQube) instead.

TARGET="${1:-.}"

echo "📋 Code Review via AI Orchestrator..."
echo "📁 Target: $TARGET"
echo ""

if [ -f scripts/orchestrator.py ]; then
    # Use orchestrator with reviewer + security agents
    python3 scripts/orchestrator.py \
        "Review code quality and security of $TARGET" \
        --no-worktree
else
    echo "⚠️  orchestrator.py not found."
    echo "   For static analysis, use: bash scripts/commands/analyze.sh $TARGET"
    echo "   Without the orchestrator, no automated review is performed."
    exit 1
fi
