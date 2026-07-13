# Fish shell completion for ehc — everything-hermes-code
# Install: cp this file to ~/.config/fish/completions/ehc.fish
# Or run: make install-completion

# Subcommands
complete -c ehc -f -n "__fish_use_subcommand" -a "orchestrate" -d "Plan-first multi-agent pipeline"
complete -c ehc -f -n "__fish_use_subcommand" -a "route"       -d "Smart agent recommendation"
complete -c ehc -f -n "__fish_use_subcommand" -a "deploy"      -d "Multi-repo deploy coordinator"
complete -c ehc -f -n "__fish_use_subcommand" -a "docker"      -d "Docker container health monitor"
complete -c ehc -f -n "__fish_use_subcommand" -a "review"      -d "Automated GitHub PR review"
complete -c ehc -f -n "__fish_use_subcommand" -a "mcp"         -d "MCP server discovery + registry"
complete -c ehc -f -n "__fish_use_subcommand" -a "dashboard"   -d "Unified status dashboard"
complete -c ehc -f -n "__fish_use_subcommand" -a "status"      -d "Multi-repo git status"
complete -c ehc -f -n "__fish_use_subcommand" -a "generate"    -d "Auto-generate AGENTS.md"
complete -c ehc -f -n "__fish_use_subcommand" -a "lint"        -d "Fix markdown formatting"
complete -c ehc -f -n "__fish_use_subcommand" -a "hooks"       -d "Git hooks management"
complete -c ehc -f -n "__fish_use_subcommand" -a "test"        -d "Run unit tests"
complete -c ehc -f -n "__fish_use_subcommand" -a "check"       -d "Check dependencies"
complete -c ehc -f -n "__fish_use_subcommand" -a "clean"       -d "Remove cache files"
complete -c ehc -f -n "__fish_use_subcommand" -a "install-skills" -d "Install Hermes skills"
complete -c ehc -f -n "__fish_use_subcommand" -a "help"        -d "Show help"

# Don't suggest subcommands after one is given
complete -c ehc -f -n "__fish_seen_subcommand_from orchestrate route deploy docker review mcp dashboard status generate lint hooks test check clean install-skills help"

# ── Subcommand-specific flags ──

# orchestrate
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l dry-run      -d "Preview only"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l plan-only    -d "Generate plan and exit"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l auto-approve  -d "Skip plan review"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l background    -d "Run as background task"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -s s -l status   -d "Live task dashboard"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -s r -l result   -d "View task detail" -a "(ls /tmp/ehc-tasks/ 2>/dev/null)"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -s H -l history  -d "Task history"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l cancel        -d "Cancel running task"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l force-agents  -d "Override agent selection"
complete -c ehc -n "__fish_seen_subcommand_from orchestrate" -l sequential    -d "Run agents one by one"

# route
complete -c ehc -n "__fish_seen_subcommand_from route" -l json          -d "JSON output"
complete -c ehc -n "__fish_seen_subcommand_from route" -l force-agents   -d "Force specific agents"
complete -c ehc -n "__fish_seen_subcommand_from route" -l interactive    -d "Interactive mode"
complete -c ehc -n "__fish_seen_subcommand_from route" -l list-agents    -d "List all agents"
complete -c ehc -n "__fish_seen_subcommand_from route" -l list-categories -d "List routing categories"

# deploy
complete -c ehc -n "__fish_seen_subcommand_from deploy" -l status    -d "Check deploy status"
complete -c ehc -n "__fish_seen_subcommand_from deploy" -l check     -d "Pre-deploy checks only"
complete -c ehc -n "__fish_seen_subcommand_from deploy" -l deploy    -d "Deploy repos" -a "all be fe"
complete -c ehc -n "__fish_seen_subcommand_from deploy" -l env       -d "Environment" -a "dev prod"
complete -c ehc -n "__fish_seen_subcommand_from deploy" -l dry-run   -d "Preview only"
complete -c ehc -n "__fish_seen_subcommand_from deploy" -l force     -d "Force deploy"

# docker
complete -c ehc -n "__fish_seen_subcommand_from docker" -l restart-dead -d "Restart dead containers"
complete -c ehc -n "__fish_seen_subcommand_from docker" -l watch       -d "Auto-refresh mode"
complete -c ehc -n "__fish_seen_subcommand_from docker" -l json        -d "JSON output"
complete -c ehc -n "__fish_seen_subcommand_from docker" -l interval    -d "Watch interval"
complete -c ehc -n "__fish_seen_subcommand_from docker" -l yes         -d "Skip confirmations"

# review
complete -c ehc -n "__fish_seen_subcommand_from review" -l pr        -d "PR number to review"
complete -c ehc -n "__fish_seen_subcommand_from review" -l repo      -d "GitHub repo (owner/repo)"
complete -c ehc -n "__fish_seen_subcommand_from review" -l all-open  -d "Review all open PRs"
complete -c ehc -n "__fish_seen_subcommand_from review" -l dry-run   -d "Analyze only, don't post"
complete -c ehc -n "__fish_seen_subcommand_from review" -l json      -d "JSON output"
complete -c ehc -n "__fish_seen_subcommand_from review" -l event     -d "Override review event" -a "APPROVE COMMENT REQUEST_CHANGES"

# mcp
complete -c ehc -n "__fish_seen_subcommand_from mcp" -a "scan list health generate repair" -d "MCP action"

# dashboard
complete -c ehc -n "__fish_seen_subcommand_from dashboard" -l json   -d "JSON output"
complete -c ehc -n "__fish_seen_subcommand_from dashboard" -l watch  -d "Auto-refresh"
complete -c ehc -n "__fish_seen_subcommand_from dashboard" -l list   -d "List available configs"

# generate
complete -c ehc -n "__fish_seen_subcommand_from generate" -l check   -d "Verify AGENTS.md is current"
