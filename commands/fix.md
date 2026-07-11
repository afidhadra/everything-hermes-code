# /fix — Auto-fix Linting Issues

Automatically fix linting and formatting issues.

## Usage

```text
/fix [file-or-directory] [--dry-run]
```text

## Description

Runs auto-fixers for:

- Code formatting (Prettier, gofmt)
- Linting errors (ESLint, golangci-lint)
- Import organization
- Unused code removal

## Examples

```bash

# Fix all issues in current directory

/fix

# Fix specific file

/fix src/main.go

# Preview changes without applying

/fix --dry-run
```text

## Supported Languages

| Language | Formatter | Linter |
| ---------- | ----------- | -------- |
| Go | gofmt | golangci-lint |
| TypeScript | Prettier | ESLint |
| Python | Black | Ruff |
| Markdown | Prettier | markdownlint |

## Implementation

```python

# Pseudocode

def fix(target, dry_run=False):
    issues = detect_issues(target)
    fixes = generate_fixes(issues)
    
    if dry_run:
        return preview_fixes(fixes)
    else:
        apply_fixes(fixes)
        return verify_fixes(target)
```text
