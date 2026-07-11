# Scripts

## Overview

Automation and setup scripts for quick configuration.

## Available Scripts

| Script | Description |
|--------|-------------|
| prompt.sh | Switch prompt mode (bash) |
| prompt.fish | Switch prompt mode (fish) |
| setup.sh | Setup project for Hermes |
| install.sh | Install everything-hermes-code |

## Usage

### Switch Mode

```bash
# Bash
source ~/Projects/everything-hermes-code/scripts/prompt.sh coding

# Fish
source ~/Projects/everything-hermes-code/scripts/prompt.fish coding
```

### Setup Project

```bash
~/Projects/everything-hermes-code/scripts/setup.sh ~/Projects/my-project
```

### Install

```bash
~/Projects/everything-hermes-code/scripts/install.sh
```

## Creating Custom Scripts

1. Create a new `.sh` or `.py` file in this directory
2. Add frontmatter:

```markdown
---
name: my-script
description: Does something awesome
---
```

3. Add the script below

## Best Practices

- Keep scripts simple
- Add error handling
- Document usage
- Make scripts executable (`chmod +x`)