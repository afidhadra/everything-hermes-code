# Security Rules

## Input Validation

- Validate ALL input at the boundary
- Use allowlists over denylists
- Validate type, length, range, and format
- Reject invalid input, don't try to fix it

## Authentication & Authorization

- Hash passwords with bcrypt/scrypt (min 12 rounds)
- Implement rate limiting on auth endpoints
- Use RBAC for authorization
- Log all authentication attempts

## Secrets Management

- Never commit secrets to version control
- Use environment variables for configuration
- Rotate secrets regularly
- Use a secrets manager for production

## SQL Injection Prevention

- Use parameterized queries
- Never concatenate user input into SQL
- Use ORM/query builder when possible
- Apply principle of least privilege to DB user

## XSS Prevention

- Escape output by default
- Use Content Security Policy (CSP)
- Sanitize HTML input if allowed
- Use HTTPOnly cookies for sensitive data

## Dependencies

- Lock dependency versions
- Regularly scan for vulnerabilities
- Remove unused dependencies
- Use npm audit / pip check / go mod verify
