---
name: pr-review
description: Automated code review for GitHub pull requests — security scanning, code quality, dependency analysis, and regression detection
version: 1.0.0
author: afidhadra
category: development
---

# PR Review Skill

Automated GitHub PR review. Fetches diff, analyzes for hardcoded secrets, SQL injection, eval, TODO markers, large changes, dependency modifications, and regression risks. Posts structured review as COMMENT, APPROVE, or REQUEST_CHANGES.

Requires `gh` CLI authenticated.

## Detection Rules

| Pattern | Severity |
| --------- | ---------- |
| Hardcoded password/secret/API key | 🔴 Critical |
| SQL injection (string concat in query) | 🔴 Critical |
| eval() usage | 🟡 High |
| Debug endpoints exposed | 🟠 Medium |
| Large file changes | 🟠 Medium |
| TODO/FIXME markers | 🟢 Info |
| Console.log statements | 🟢 Info |
| Dependency changes | 🟢 Info |

## Usage

```bash

# Review a specific PR (auto-detect repo from git remote)

python3 scripts/pr-review.py --pr 5

# Review PR in specific repo

python3 scripts/pr-review.py --repo owner/repo --pr 42

# Review all open PRs

python3 scripts/pr-review.py --all-open

# Analyze only (don't post)

python3 scripts/pr-review.py --pr 5 --dry-run

# Force review event

python3 scripts/pr-review.py --pr 5 --event approve
python3 scripts/pr-review.py --pr 5 --event request-changes

# JSON output (CI integration)

python3 scripts/pr-review.py --pr 5 --json
```

## Examples

```bash

# Quick review

python3 scripts/pr-review.py --pr 5

# → Verdict: COMMENT | 0 critical · 1 high · 2 medium · 3 info

# CI pipeline: auto-fail on critical

python3 scripts/pr-review.py --pr $CI_PR_NUMBER --dry-run --json | \
  python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(1) if d['summary']['critical']>0 else sys.exit(0)"
```

## Integration with Hermes

```text
hermes -z "review PR #5" --skills skills/pr-review.md
```
