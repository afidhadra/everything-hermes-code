#!/bin/bash
#
# everything-hermes-code setup script
# Usage: ./install.sh [--check | --hooks | --all]
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

print_ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
print_fail()  { echo -e "  ${RED}✗${NC} $1"; }
print_warn()  { echo -e "  ${YELLOW}!${NC} $1"; }
print_info()  { echo -e "  ${CYAN}→${NC} $1"; }
print_head()  { echo -e "\n${CYAN}=== $1 ===${NC}"; }

check_command() {
    if command -v "$1" &>/dev/null; then
        print_ok "$1 found: $(command -v "$1")"
        return 0
    else
        print_fail "$1 not found"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        print_ok "$1"
    else
        print_fail "$1 missing"
    fi
}

# --- Mode handlers ---

do_check() {
    print_head "Dependency Check"

    local missing=0

    # Core
    check_command python3 || missing=1
    check_command git || missing=1
    check_command node || missing=1

    # Optional
    print_head "Optional Tools"
    check_command docker || print_warn "docker not found (SonarQube needs it)"
    check_command go || print_warn "go not found (github-mcp-server needs it)"

    # Python scripts
    print_head "Project Scripts"
    for f in scripts/fix-markdown.py scripts/agent-runner.py scripts/command-runner.py; do
        check_file "$REPO_DIR/$f"
    done

    # MCP configs
    print_head "MCP Configs"
    check_file "$REPO_DIR/mcp-configs/sonarqube.json"
    check_file "$REPO_DIR/mcp-configs/github.json"

    # Markdown tooling
    print_head "Markdown Tooling"
    check_file "$REPO_DIR/.markdownlint.json"
    check_file "$REPO_DIR/.prettierrc"
    check_file "$REPO_DIR/.vscode/settings.json"

    # Summary
    print_head "Summary"
    if [ $missing -eq 0 ]; then
        print_ok "All core dependencies present"
    else
        print_fail "Missing core dependencies — install before continuing"
    fi
}

do_hooks() {
    print_head "Installing Git Hooks"

    local hooks_dir="$REPO_DIR/.git/hooks"
    local scripts_dir="$REPO_DIR/hooks/scripts"

    if [ ! -d "$hooks_dir" ]; then
        print_fail "Not a git repo (.git/hooks not found)"
        return 1
    fi

    for hook in pre-commit post-commit pre-push; do
        local target="$scripts_dir/${hook}.sh"
        local link="$hooks_dir/${hook}"

        if [ ! -f "$target" ]; then
            print_warn "$hook.sh missing in hooks/scripts/"
            continue
        fi

        # Remove existing
        rm -f "$link"

        # Create symlink (relative path for portability)
        ln -s "../../hooks/scripts/${hook}.sh" "$link"
        print_ok "${hook} → hooks/scripts/${hook}.sh"
    done

    print_head "Hook Status"
    ls -la "$hooks_dir"/{pre-commit,post-commit,pre-push} 2>/dev/null
}

do_permissions() {
    print_head "Fixing Script Permissions"

    for f in scripts/*.py scripts/commands/*.sh hooks/scripts/*.sh tests/*.py; do
        local full="$REPO_DIR/$f"
        if [ -f "$full" ]; then
            chmod +x "$full"
            print_ok "chmod +x $f"
        fi
    done
}

do_all() {
    print_head "everything-hermes-code setup"
    echo ""

    do_check
    echo ""
    do_permissions
    echo ""
    do_hooks

    print_head "Done"
    print_ok "Setup complete."
    echo ""
    print_info "Next steps:"
    echo "    make test     # run unit tests"
    echo "    make lint     # lint all markdown"
    echo "    make analyze  # scan code quality (SonarQube)"
}

# --- Main ---

case "${1:---all}" in
    --check)       do_check ;;
    --hooks)       do_hooks ;;
    --permissions) do_permissions ;;
    --all|-a)      do_all ;;
    *)
        echo "Usage: $0 [--check | --hooks | --permissions | --all]"
        echo ""
        echo "  --check       Check dependencies and files"
        echo "  --hooks       Install git hooks (symlink)"
        echo "  --permissions Fix script permissions"
        echo "  --all         Run everything (default)"
        exit 1
        ;;
esac
