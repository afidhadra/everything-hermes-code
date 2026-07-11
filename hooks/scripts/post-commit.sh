#!/bin/bash
# Post-commit hook for notifications

COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --pretty=%s)

echo "📝 Committed: $COMMIT_HASH - $COMMIT_MSG"
