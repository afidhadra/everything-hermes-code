#!/bin/bash
#
# analyze.sh — Code quality analysis via SonarQube API
#
# Usage:
#   analyze.sh [target-dir] [project-key]
#
# Defaults:
#   target-dir  — current directory (.)
#   project-key — everything-hermes-code
#
# Requirements:
#   - SonarQube running at localhost:9000
#   - Token at ~/.sonarqube_token
#   - sonar-scanner or docker for scan
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

TARGET="${1:-.}"
PROJECT_KEY="${2:-everything-hermes-code}"
SONAR_URL="http://localhost:9000"
TOKEN_FILE="$HOME/.sonarqube_token"

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
info() { echo -e "  ${CYAN}→${NC} $1"; }
head() { echo -e "\n${BOLD}${CYAN}=== $1 ===${NC}"; }

# --- Pre-checks ---

head "Pre-checks"

if [ ! -f "$TOKEN_FILE" ]; then
    fail "SonarQube token not found at $TOKEN_FILE"
    fail "Run: hermes config show mcp_servers.sonarqube for setup info"
    exit 1
fi

TOKEN=$(cat "$TOKEN_FILE")

# Test SonarQube connectivity
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -u "$TOKEN:" "$SONAR_URL/api/system/status" 2>/dev/null || echo "000")
if [ "$STATUS" != "200" ]; then
    fail "SonarQube not reachable at $SONAR_URL (HTTP $STATUS)"
    warn "Start with: docker start sonarqube"
    exit 1
fi
ok "SonarQube reachable"

# --- File stats ---

head "Target: $TARGET"

FILE_COUNT=$(find "$TARGET" -not -path "*/.git/*" -not -path "*/node_modules/*" -type f \
    \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.vue" -o -name "*.md" \) \
    | wc -l | tr -d ' ')

LOC=$(find "$TARGET" -not -path "*/.git/*" -not -path "*/node_modules/*" -type f \
    \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.vue" \) \
    -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')

info "Files: $FILE_COUNT"
info "Lines of code: $LOC"

# --- Markdown linting ---

head "Markdown Linting"

MD_COUNT=$(find "$TARGET" -not -path "*/.git/*" -name "*.md" | wc -l | tr -d ' ')

if [ "$MD_COUNT" -gt 0 ] && [ -f "scripts/fix-markdown.py" ]; then
    python3 scripts/fix-markdown.py "$TARGET" 2>/dev/null
    ok "$MD_COUNT markdown files checked"
else
    info "No markdown files found"
fi

# --- SonarQube scan ---

head "SonarQube Scan"

# Create project if not exists
PROJECT_EXISTS=$(curl -s -u "$TOKEN:" \
    "$SONAR_URL/api/components/show?component=$PROJECT_KEY" \
    2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('component',{}).get('key',''))" 2>/dev/null)

if [ -z "$PROJECT_EXISTS" ]; then
    info "Creating project: $PROJECT_KEY"
    curl -s -u "$TOKEN:" -X POST \
        "$SONAR_URL/api/projects/create" \
        -d "name=$PROJECT_KEY&project=$PROJECT_KEY" >/dev/null 2>&1
    ok "Project created"
else
    ok "Project exists: $PROJECT_KEY"
fi

# Run scan via sonar-scanner or docker
if command -v sonar-scanner &>/dev/null; then
    info "Using sonar-scanner CLI"
    sonar-scanner \
        -Dsonar.host.url="$SONAR_URL" \
        -Dsonar.login="$TOKEN" \
        -Dsonar.projectKey="$PROJECT_KEY" \
        -Dsonar.projectName="$PROJECT_KEY" \
        -Dsonar.sources="$TARGET" \
        -Dsonar.exclusions="**/.git/**,**/node_modules/**,**/__pycache__/**" \
        2>&1 | tail -5
    ok "Scan submitted"
elif command -v docker &>/dev/null; then
    info "Using Docker sonar-scanner"
    docker run --rm \
        --network host \
        -v "$(pwd)/$TARGET:/usr/src:Z" \
        sonarsource/sonar-scanner-cli \
        -Dsonar.host.url="$SONAR_URL" \
        -Dsonar.login="$TOKEN" \
        -Dsonar.projectKey="$PROJECT_KEY" \
        -Dsonar.projectName="$PROJECT_KEY" \
        -Dsonar.sources=. \
        -Dsonar.exclusions="**/.git/**,**/node_modules/**,**/__pycache__/**" \
        2>&1 | tail -5
    ok "Scan submitted"
else
    warn "sonar-scanner not found — skipping scan step"
    warn "Install: https://docs.sonarsource.com/sonarqube/latest/analyzing-source-code/scanners/sonarscanner/"
fi

# --- Fetch metrics ---

head "Quality Metrics"

sleep 2  # Wait for processing

METRICS="bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc,sqale_rating,reliability_rating,security_rating"

RAW=$(curl -s -u "$TOKEN:" \
    "$SONAR_URL/api/measures/component?component=$PROJECT_KEY&metricKeys=$METRICS" \
    2>/dev/null)

if [ -z "$RAW" ]; then
    warn "No metrics yet — scan may still be processing"
    exit 0
fi

# Parse and display
echo "$RAW" | python3 -c "
import sys, json

data = json.load(sys.stdin)
measures = data.get('component', {}).get('measures', [])

if not measures:
    print('  ! No metrics available yet — scan may still be processing')
    print('  → Check http://localhost:9000/dashboard?id=$PROJECT_KEY')
    sys.exit(0)

ratings = {'1.0': 'A', '2.0': 'B', '3.0': 'C', '4.0': 'D', '5.0': 'E'}
labels = {
    'bugs': 'Bugs',
    'vulnerabilities': 'Vulnerabilities',
    'code_smells': 'Code Smells',
    'coverage': 'Coverage',
    'duplicated_lines_density': 'Duplicated Code %',
    'ncloc': 'Lines of Code',
    'sqale_rating': 'Maintainability',
    'reliability_rating': 'Reliability',
    'security_rating': 'Security',
}

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

for m in measures:
    metric = m['metric']
    value = m.get('value', 'N/A')
    label = labels.get(metric, metric)

    if metric.endswith('_rating') and value in ratings:
        grade = ratings[value]
        color = GREEN if grade in ('A', 'B') else (YELLOW if grade == 'C' else RED)
        print(f'  {color}{grade}{NC}  {label}')
    elif metric == 'coverage':
        color = GREEN if float(value) >= 80 else (YELLOW if float(value) >= 50 else RED)
        print(f'  {color}{value}%{NC}  {label}')
    elif metric in ('bugs', 'vulnerabilities'):
        color = GREEN if value == '0' else RED
        print(f'  {color}{value}{NC}  {label}')
    elif metric == 'duplicated_lines_density':
        color = GREEN if float(value) < 3 else (YELLOW if float(value) < 5 else RED)
        print(f'  {color}{value}%{NC}  {label}')
    else:
        print(f'  {value}  {label}')
" 2>/dev/null

# --- Summary ---

head "Summary"

info "Dashboard: $SONAR_URL/dashboard?id=$PROJECT_KEY"
info "Markdown:  $MD_COUNT files checked"
info "Files:     $FILE_COUNT total scanned"
echo ""
ok "Analysis complete"
