# Coding Style Rules

## General

- Use consistent naming conventions
- Write self-documenting code
- Keep functions small (<50 lines)
- Keep files small (<500 lines)
- Avoid premature optimization

## Naming

- Variables: camelCase (JS/TS), snake_case (Python/Go)
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Functions: camelCase (JS/TS), snake_case (Python/Go)
- Files: kebab-case (JS/TS), snake_case (Python)

## Formatting

- Use Prettier/ESLint for JS/TS
- Use Black for Python
- Use gofmt for Go
- Max line length: 100 characters
- Use consistent indentation (2 or 4 spaces)

## Comments

- Don't comment obvious code
- Document why, not what
- Use JSDoc/TSDoc for functions
- Update comments when code changes

## Imports

- Group imports: external, internal, relative
- Sort imports alphabetically
- Avoid unused imports
- Use barrel exports for modules