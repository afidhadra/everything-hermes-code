# Git Workflow Rules

## Branches

- `main` — Production-ready code
- `development` — Integration branch
- `feature/*` — New features
- `fix/*` — Bug fixes
- `hotfix/*` — Production fixes

## Commits

- Use Conventional Commits
- One logical change per commit
- Write clear commit messages
- Reference issues when applicable

## Pull Requests

- Keep PRs small (<500 lines)
- Write clear descriptions
- Link related issues
- Request review from appropriate people

## Merging

- Squash merge feature branches
- Never force push to main/development
- Delete branches after merge
- Update changelog for releases

## Tags

- Use semantic versioning
- Tag releases on main
- Annotate tags with release notes