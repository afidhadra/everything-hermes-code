# Basic Workflow Example

Complete workflow example for using Hermes with Everything Claude Code.

## Step 1: Setup

```bash

# Clone the repository

git clone https://github.com/afidhadra/everything-hermes-code.git
cd everything-hermes-code

# Install dependencies (if any)

./scripts/setup.sh
```

## Step 2: Configure Hermes

```bash

# Add to ~/.hermes/config.yaml

cat >> ~/.hermes/config.yaml << 'EOF'
skills:

  - /path/to/everything-hermes-code/skills

EOF
```

## Step 3: Use Commands

```bash

# Analyze code quality

/analyze src/

# Fix linting issues

/fix src/

# Review code changes

/review src/

# Security scan

/security src/
```

## Step 4: Use Agents

```bash

# Use architect agent for design

"Act as architect agent: design the database schema"

# Use coder agent for implementation

"Act as coder agent: implement the API endpoint"

# Use debugger agent for issues

"Act as debugger agent: fix the failing test"
```

## Complete Example

```bash

# 1. Analyze current state

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
