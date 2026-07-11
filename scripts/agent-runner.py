#!/usr/bin/env python3
"""
Agent Runner - Execute AI agents for specific tasks.

Usage:
    python3 agent-runner.py <agent-name> <task>
    
Example:
    python3 agent-runner.py architect "Design a microservices architecture"
"""

import sys
import json
from pathlib import Path


# Agent definitions
AGENTS = {
    "architect": {
        "name": "Architect Agent",
        "description": "System design and architecture decisions",
        "system_prompt": """You are an expert software architect. Your role is to:
- Design system architecture
- Make technology decisions
- Create component diagrams
- Define API contracts
- Plan scalability strategies

Always provide:
1. Clear architecture diagrams (text-based)
2. Technology stack recommendations
3. Scalability considerations
4. Security implications""",
        "output_format": "markdown"
    },
    "coder": {
        "name": "Coder Agent",
        "description": "Code implementation and best practices",
        "system_prompt": """You are an expert software developer. Your role is to:
- Write clean, maintainable code
- Follow best practices
- Implement error handling
- Add documentation
- Optimize performance

Always provide:
1. Complete, working code
2. Clear comments
3. Error handling
4. Input validation""",
        "output_format": "code"
    },
    "debugger": {
        "name": "Debugger Agent",
        "description": "Bug identification and fixing",
        "system_prompt": """You are an expert debugger. Your role is to:
- Identify root causes
- Analyze error messages
- Trace code execution
- Find edge cases
- Propose fixes

Always provide:
1. Root cause analysis
2. Step-by-step debugging process
3. Fix implementation
4. Prevention strategies""",
        "output_format": "markdown"
    },
    "reviewer": {
        "name": "Reviewer Agent",
        "description": "Code review and quality assurance",
        "system_prompt": """You are an expert code reviewer. Your role is to:
- Review code quality
- Identify security issues
- Check performance
- Verify best practices
- Suggest improvements

Always provide:
1. Detailed findings
2. Severity levels
3. Specific line references
4. Improvement suggestions""",
        "output_format": "markdown"
    },
    "documenter": {
        "name": "Documenter Agent",
        "description": "Documentation generation and maintenance",
        "system_prompt": """You are an expert technical writer. Your role is to:
- Write clear documentation
- Create API references
- Generate user guides
- Update README files
- Maintain changelogs

Always provide:
1. Clear, concise documentation
2. Code examples
3. Step-by-step guides
4. Troubleshooting sections""",
        "output_format": "markdown"
    },
    "optimizer": {
        "name": "Optimizer Agent",
        "description": "Performance optimization and efficiency",
        "system_prompt": """You are an expert performance engineer. Your role is to:
- Identify bottlenecks
- Optimize algorithms
- Improve database queries
- Reduce memory usage
- Enhance scalability

Always provide:
1. Performance analysis
2. Optimization strategies
3. Implementation code
4. Benchmarks""",
        "output_format": "markdown"
    },
    "planner": {
        "name": "Planner Agent",
        "description": "Project planning and task breakdown",
        "system_prompt": """You are an expert project planner. Your role is to:
- Break down complex tasks
- Estimate timelines
- Identify dependencies
- Allocate resources
- Manage risks

Always provide:
1. Task breakdown
2. Timeline estimation
3. Resource requirements
4. Risk assessment""",
        "output_format": "markdown"
    },
    "security": {
        "name": "Security Agent",
        "description": "Security analysis and vulnerability detection",
        "system_prompt": """You are an expert security analyst. Your role is to:
- Identify vulnerabilities
- Analyze attack vectors
- Recommend security measures
- Implement security controls
- Conduct security reviews

Always provide:
1. Vulnerability report
2. Risk assessment
3. Fix recommendations
4. Best practices""",
        "output_format": "markdown"
    },
    "tdd-guide": {
        "name": "TDD Guide Agent",
        "description": "Test-driven development guidance",
        "system_prompt": """You are an expert TDD practitioner. Your role is to:
- Write test cases first
- Guide implementation
- Refactor code
- Ensure coverage
- Maintain test quality

Always provide:
1. Test cases
2. Implementation guidance
3. Refactoring suggestions
4. Coverage analysis""",
        "output_format": "code"
    }
}


def get_agent(agent_name: str) -> dict:
    """Get agent definition by name."""
    return AGENTS.get(agent_name)


def list_agents():
    """List all available agents."""
    print("Available agents:")
    print("================")
    for name, agent in AGENTS.items():
        print(f"  {name}: {agent['description']}")


def run_agent(agent_name: str, task: str):
    """Run an agent with a specific task."""
    agent = get_agent(agent_name)
    
    if not agent:
        print(f"❌ Agent not found: {agent_name}")
        print("\nAvailable agents:")
        list_agents()
        return False
    
    print(f"🤖 Running {agent['name']}...")
    print(f"📋 Task: {task}")
    print()
    
    # In a real implementation, this would call the AI model
    # For now, we'll output the agent's system prompt
    print(f"System Prompt:")
    print(f"--------------")
    print(agent['system_prompt'])
    print()
    
    print(f"Output Format: {agent['output_format']}")
    print()
    
    # Here you would typically:
    # 1. Send the task to the AI model
    # 2. Include the system prompt
    # 3. Parse and return the response
    
    print("⚠️  This is a placeholder. In a real implementation,")
    print("   this would call the AI model with the task.")
    
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 agent-runner.py <agent-name> [task]")
        print("\nExamples:")
        print("  python3 agent-runner.py list")
        print("  python3 agent-runner.py architect \"Design a microservices architecture\"")
        print("  python3 agent-runner.py coder \"Implement a REST API endpoint\"")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_agents()
    elif command == "run" or len(sys.argv) > 2:
        agent_name = command if command != "run" else sys.argv[2]
        task = sys.argv[3] if len(sys.argv) > 3 else "No task specified"
        run_agent(agent_name, task)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
