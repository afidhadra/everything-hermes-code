#!/bin/bash
set -euo pipefail

# Pre-push hook — regression gate
# Runs regression-analyzer.py ONLY if code files changed in commits being pushed.
# Blocks push on CRITICAL findings, warns on HIGH.

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

REPO_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ANALYZER="$REPO_DIR/scripts/regression-analyzer.py"
CODE_PATTERN='\.(go|ts|tsx|js|jsx|vue|sql|py|rs|java|rb|php|c|cpp|h)$'
ALL_CHANGED=""
DIFF_REF=""

while read -r local_ref local_sha remote_ref remote_sha; do
    [ "$local_sha" = "0000000000000000000000000000000000000000" ] && continue
    if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
        CHANGED=$(git rev-list --name-only "$local_sha" 2>/dev/null | grep -E "$CODE_PATTERN" || true)
        DIFF_REF="HEAD~1"
    else
        CHANGED=$(git diff --name-only "$remote_sha" "$local_sha" 2>/dev/null | grep -E "$CODE_PATTERN" || true)
        DIFF_REF="${remote_sha}..${local_sha}"
    fi
    [ -n "$CHANGED" ] && ALL_CHANGED="${ALL_CHANGED}${CHANGED}\n"
done

if [ -z "$(echo -e "$ALL_CHANGED" | tr -d '[:space:]')" ]; then
    exit 0
fi

CODE_COUNT=$(echo -e "$ALL_CHANGED" | grep -c . || true)
echo -e "\xf0\x9f\x94\x8d ${CODE_COUNT} code file(s) in push \xe2\x80\x94 running regression check..."

if [ ! -f "$ANALYZER" ]; then
    echo -e "  ${YELLOW}regression-analyzer.py not found \xe2\x80\x94 skipping${NC}"
    exit 0
fi

OUTPUT=$(python3 "$ANALYZER" "$DIFF_REF" 2>&1 || true)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo -e "  ${RED}PUSH BLOCKED \xe2\x80\x94 CRITICAL REGRESSION${NC}"
    echo ""
    echo "$OUTPUT" | grep -A 100 "RISK SUMMARY" | head -30
    echo ""
    echo -e "  ${RED}Fix CRITICAL issues before pushing.${NC}"
    echo -e "  ${YELLOW}To override: git push --no-verify${NC}"
    exit 1
elif [ $EXIT_CODE -eq 1 ]; then
    echo -e "  ${YELLOW}HIGH regression risk detected (push allowed)${NC}"
    echo "$OUTPUT" | grep -E "^\s+(CRITICAL|HIGH)" | head -10
else
    echo -e "  ${GREEN}Regression check passed${NC}"
fi
