---
applyTo: "**/*"
---

Guidelines for using SonarQube MCP Server in this project.

# SonarQube MCP Server Setup

## Quick Start

- SonarQube Server: `http://localhost:9000` (Community Edition, self-hosted)
- MCP Server: Docker container `sonarsource/sonarqube-mcp`
- Token: Stored in `~/.sonarqube_token`

## Important Tool Guidelines

### Basic usage

- After generating or modifying code, call `analyze_file_list` to analyze files
- When starting a new task, disable automatic analysis with `toggle_automatic_analysis`
- When done, re-enable automatic analysis with `toggle_automatic_analysis`

### Project Keys

- Always use `search_my_sonarqube_projects` to find exact project keys
- Don't guess project keys

### Code Language Detection

- Detect programming language from code syntax
- If unclear, ask the user

### Branch and Pull Request Context

- Include branch parameter when working on feature branches

### Code Issues and Violations

- After fixing issues, don't verify using `search_sonar_issues_in_projects`
- Server needs time to reflect updates

# Common Troubleshooting

## Authentication Issues

- SonarQube requires USER tokens (not project tokens)
- When "Not authorized" error occurs, verify token type

## Project Not Found

- Use `search_my_sonarqube_projects` to find available projects
- Verify project key spelling

## Code Analysis Issues

- Ensure programming language is correctly specified
- Snippet analysis doesn't replace full project scans
- Provide full file content for better analysis
