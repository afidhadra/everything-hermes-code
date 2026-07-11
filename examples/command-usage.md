# Command Usage Examples

Examples for using slash commands in the toolkit.

## /analyze — Code Quality Analysis

**Basic Usage:**

```bash
/analyze src/
```

**With Options:**

```bash
/analyze src/ --focus security
/analyze src/ --focus performance
/analyze src/ --focus style
```

**Example Output:**

```text
Code Quality Report
==================

Files analyzed: 15
Issues found: 3

Critical: 0
Warning: 2
Info: 1

Recommendations:

1. Add input validation to API endpoints
1. Implement error handling in database layer
1. Update documentation for public methods

```

## /fix — Auto-fix Linting Issues

**Basic Usage:**

```bash
/fix src/
```

**Dry Run:**

```bash
/fix src/ --dry-run
```

**Example Output:**

```text
Auto-fix Report
===============

Files processed: 10
Issues fixed: 5

Fixed:

- MD022: Added blank lines around headings
- MD031: Added blank lines around code blocks
- MD032: Added blank lines around lists
- MD040: Added language to code blocks
- MD047: Fixed trailing newline

```

## /review — Code Review

**Basic Usage:**

```bash
/review src/
```

**Focus Areas:**

```bash
/review src/ --focus security
/review src/ --focus performance
/review src/ --focus style
```

**Example Output:**

```text
Code Review Report
==================

Files reviewed: 8
Issues found: 4

Security: 1
Performance: 2
Style: 1

Detailed Findings:

1. [SECURITY] Missing input validation in user.go:45
   - SQL injection vulnerability
   - Fix: Add parameterized queries

1. [PERFORMANCE] N+1 query in user_service.go:78
   - Multiple database calls
   - Fix: Use batch query

1. [PERFORMANCE] Missing cache in auth.go:23
   - Repeated expensive operations
   - Fix: Implement Redis cache

1. [STYLE] Inconsistent error handling in api.go:56
   - Mixed error patterns
   - Fix: Use consistent error types

```

## /security — Security Scan

**Basic Usage:**

```bash
/security src/
```

**Deep Scan:**

```bash
/security src/ --deep
```

**Example Output:**

```text
Security Scan Report
====================

Files scanned: 20
Vulnerabilities found: 2

Critical: 0
High: 1
Medium: 1
Low: 0

Details:

1. [HIGH] SQL Injection in user.go:45
   - Vulnerable code: db.Query("SELECT * FROM users WHERE id=" + id)
   - Fix: Use parameterized queries

1. [MEDIUM] Missing CSRF protection in api.go:23
   - No CSRF token validation
   - Fix: Implement CSRF middleware

```

## Combining Commands

**Complete Workflow:**

```bash

# 1. Analyze code quality

/analyze .

# 2. Review recent changes

/review HEAD~3

# 3. Fix any issues found

/fix .

# 4. Security check

/security .

# 5. Commit changes

git add .
git commit -m "feat: implement new feature"
```

**Quick Fix Workflow:**

```bash

# Fix all issues in current directory

/fix .

# Verify fixes

/analyze .

# Commit

git add .
git commit -m "fix: resolve linting issues"
```
