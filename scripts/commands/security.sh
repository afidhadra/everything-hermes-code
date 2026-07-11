#!/bin/bash
set -euo pipefail

# Security command — delegates to SonarQube via analyze.sh
# This is NOT a real security scanner. It routes to SonarQube which has
# actual vulnerability detection (SAST, dependency check, etc.)

TARGET="${1:-.}"

echo "🔒 Security Scan via SonarQube..."
echo "📁 Target: $TARGET"
echo ""

if [ -f scripts/commands/analyze.sh ]; then
    # Route to SonarQube which has real security analysis
    bash scripts/commands/analyze.sh "$TARGET" "$TARGET-security"
else
    echo "⚠️  SonarQube analyze.sh not found."
    echo "   This command requires analyze.sh to function."
    echo "   Without SonarQube, no real security scanning is performed."
    exit 1
fi
