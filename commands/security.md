# /security — Security Scan

Perform security vulnerability scan.

## Usage

```
/security [file-or-directory] [--deep]
```

## Description

Scans for:
- Known vulnerabilities (CVE)
- Security misconfigurations
- Secret leaks
- Dependency vulnerabilities
- Code injection risks

## Examples

```bash
# Quick security scan
/security

# Deep scan with detailed report
/security --deep

# Scan specific file
/security src/auth.go

# Scan dependencies
/security --deps
```

## Security Checks

### Static Analysis
- SQL injection
- Command injection
- Path traversal
- XSS vulnerabilities
- CSRF protection

### Dependency Scanning
- Known CVEs
- Outdated packages
- License compliance
- Security advisories

### Configuration
- Environment variables
- API keys exposure
- Debug mode enabled
- CORS configuration

## Implementation

```python
# Pseudocode
def security_scan(target, deep=False):
    findings = []
    
    # Static analysis
    findings.extend(scan_code(target))
    
    # Dependency scan
    findings.extend(scan_dependencies(target))
    
    if deep:
        # Configuration scan
        findings.extend(scan_config(target))
        
        # Secret detection
        findings.extend(scan_secrets(target))
    
    return generate_security_report(findings)
```
