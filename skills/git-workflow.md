# Git Workflow Skill

Best practices for Git version control.

## Branch Strategy

### Git Flow
```
main (production)
├── develop (integration)
│   ├── feature/user-auth
│   ├── feature/payment
│   └── feature/dashboard
├── release/v1.2.0
└── hotfix/critical-bug
```

### GitHub Flow
```
main (production)
├── feature/user-auth
├── feature/payment
└── fix/login-bug
```

## Commit Messages

### Conventional Commits
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Examples
```bash
# Good
git commit -m "feat(auth): add JWT token refresh"

# Good with body
git commit -m "fix(payment): handle currency conversion

- Added currency conversion logic
- Updated tests for edge cases
- Fixed rounding errors

Closes #123"

# Bad
git commit -m "update code"
git commit -m "fix stuff"
```

## Common Commands

### Status & History
```bash
# Check status
git status

# View history
git log --oneline --graph --all

# View changes
git diff

# View staged changes
git diff --staged
```

### Branching
```bash
# Create branch
git checkout -b feature/user-auth

# List branches
git branch -a

# Switch branch
git checkout develop

# Delete branch
git branch -d feature/user-auth

# Force delete
git branch -D feature/user-auth
```

### Staging & Committing
```bash
# Stage specific file
git add src/main.go

# Stage all changes
git add .

# Unstage file
git reset HEAD src/main.go

# Commit
git commit -m "feat: add user authentication"

# Amend last commit
git commit --amend

# Interactive rebase
git rebase -i HEAD~3
```

### Remote Operations
```bash
# Fetch changes
git fetch origin

# Pull changes
git pull origin develop

# Push changes
git push origin feature/user-auth

# Push new branch
git push -u origin feature/user-auth

# Force push (dangerous!)
git push --force-with-lease
```

## Workflows

### Feature Development
```bash
# 1. Create feature branch
git checkout develop
git pull origin develop
git checkout -b feature/user-auth

# 2. Make changes
# ... code ...

# 3. Commit changes
git add .
git commit -m "feat(auth): implement user authentication"

# 4. Push to remote
git push -u origin feature/user-auth

# 5. Create Pull Request
# ... on GitHub ...

# 6. Merge to develop
git checkout develop
git pull origin develop
git merge feature/user-auth

# 7. Delete feature branch
git branch -d feature/user-auth
git push origin --delete feature/user-auth
```

### Hotfix
```bash
# 1. Create hotfix from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 2. Fix the bug
# ... code ...

# 3. Commit fix
git commit -m "fix: resolve critical security vulnerability"

# 4. Merge to main AND develop
git checkout main
git merge hotfix/critical-bug
git checkout develop
git merge hotfix/critical-bug

# 5. Tag release
git tag -a v1.0.1 -m "Hotfix: security vulnerability"
git push origin --tags

# 6. Delete hotfix branch
git branch -d hotfix/critical-bug
```

## Undoing Changes

### Working Directory
```bash
# Discard changes
git checkout -- file.go

# Or using restore (newer)
git restore file.go

# Discard all changes
git checkout -- .
```

### Staged Changes
```bash
# Unstage file
git reset HEAD file.go

# Or using restore
git restore --staged file.go
```

### Last Commit
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Amend last commit
git commit --amend -m "new message"
```

### Remote Changes
```bash
# Revert commit (creates new commit)
git revert <commit-hash>

# Reset remote (dangerous!)
git push --force-with-lease
```

## Stashing

### Basic Usage
```bash
# Stash changes
git stash

# Stash with message
git stash push -m "work in progress"

# List stashes
git stash list

# Apply stash
git stash apply

# Apply and remove stash
git stash pop

# Drop stash
git stash drop stash@{0}

# Clear all stashes
git stash clear
```

## Tags

### Creating Tags
```bash
# Lightweight tag
git tag v1.0.0

# Annotated tag
git tag -a v1.0.0 -m "Release version 1.0.0"

# Tag specific commit
git tag -a v1.0.0 <commit-hash>
```

### Managing Tags
```bash
# List tags
git tag

# Push tags
git push origin v1.0.0

# Push all tags
git push origin --tags

# Delete tag locally
git tag -d v1.0.0

# Delete tag remotely
git push origin --delete v1.0.0
```

## Best Practices

### Commit Often
```bash
# Small, focused commits
git commit -m "feat: add user model"
git commit -m "feat: add user repository"
git commit -m "feat: add user service"
git commit -m "feat: add user controller"
```

### Write Clear Messages
```bash
# Good
git commit -m "fix: resolve null pointer in user validation"

# Bad
git commit -m "fix bug"
```

### Keep History Clean
```bash
# Squash commits before merge
git rebase -i develop

# Interactive rebase
git rebase -i HEAD~5
```

## Tools

### Essential
- `git` — Version control
- `gh` — GitHub CLI
- `tig` — Terminal UI

### GUIs
- VS Code Git integration
- GitKraken
- SourceTree

### Hooks
- pre-commit
- commit-msg
- pre-push
