# /review — Code Review

Perform comprehensive code review.

## Usage

```
/review [file-or-directory] [--focus security|performance|style]
```

## Description

Reviews code for:
- Code quality and best practices
- Security vulnerabilities
- Performance issues
- Maintainability concerns
- Documentation completeness

## Examples

```bash
# Review current changes
/review

# Review specific file
/review src/main.go

# Focus on security only
/review --focus security

# Review with SonarQube integration
/review --sonar
```

## Review Checklist

### Security
- [ ] Input validation
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] Authentication/authorization
- [ ] Secrets management

### Performance
- [ ] Algorithm complexity
- [ ] Memory usage
- [ ] Database queries
- [ ] Caching opportunities
- [ ] Async operations

### Style
- [ ] Naming conventions
- [ ] Code organization
- [ ] Comments/documentation
- [ ] Error handling
- [ ] Testing coverage

## Implementation

```python
# Pseudocode
def review(target, focus=None):
    results = {
        'security': security_review(target),
        'performance': performance_review(target),
        'style': style_review(target),
        'quality': quality_review(target)
    }
    
    if focus:
        return results[focus]
    return generate_review_report(results)
```
