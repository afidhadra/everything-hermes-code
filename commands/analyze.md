# /analyze — Analyze Code Quality

Analyze code quality and provide detailed report.

## Usage

```text
/analyze [file-or-directory]
```

## Description

Runs comprehensive code analysis including:

- Code complexity metrics
- Duplicate code detection
- Technical debt assessment
- Code smell identification
- Maintainability index

## Examples

```bash

# Analyze current directory

/analyze

# Analyze specific file

/analyze src/main.go

# Analyze with SonarQube

/analyze --sonar
```

## Implementation

```python

# Pseudocode

def analyze(target):
    metrics = {
        'complexity': calculate_complexity(target),
        'duplicates': find_duplicates(target),
        'debt': assess_technical_debt(target),
        'smells': detect_code_smells(target)
    }
    return generate_report(metrics)
```
