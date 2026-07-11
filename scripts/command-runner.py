#!/usr/bin/env python3
"""
Command Runner - Execute slash commands.

Usage:
    python3 command-runner.py <command> [args...]
    
Example:
    python3 command-runner.py analyze src/
    python3 command-runner.py fix src/ --dry-run
"""

import sys
import subprocess
from pathlib import Path


# Command definitions
COMMANDS = {
    "analyze": {
        "name": "Analyze",
        "description": "Analyze code quality and provide detailed report",
        "usage": "/analyze [file-or-directory] [--focus security|performance|style]",
        "script": "analyze.sh"
    },
    "fix": {
        "name": "Fix",
        "description": "Automatically fix linting and formatting issues",
        "usage": "/fix [file-or-directory] [--dry-run]",
        "script": "fix.sh"
    },
    "review": {
        "name": "Review",
        "description": "Perform comprehensive code review",
        "usage": "/review [file-or-directory] [--focus security|performance|style]",
        "script": "review.sh"
    },
    "security": {
        "name": "Security",
        "description": "Perform security vulnerability scan",
        "usage": "/security [file-or-directory] [--deep]",
        "script": "security.sh"
    }
}


def get_command(command_name: str) -> dict:
    """Get command definition by name."""
    return COMMANDS.get(command_name)


def list_commands():
    """List all available commands."""
    print("Available commands:")
    print("==================")
    for name, cmd in COMMANDS.items():
        print(f"  /{name}: {cmd['description']}")
        print(f"    Usage: {cmd['usage']}")
        print()


def run_command(command_name: str, args: list):
    """Run a command with arguments."""
    cmd = get_command(command_name)
    
    if not cmd:
        print(f"❌ Command not found: /{command_name}")
        print("\nAvailable commands:")
        list_commands()
        return False
    
    print(f"🚀 Running /{command_name}...")
    print(f"📋 Arguments: {' '.join(args)}")
    print()
    
    # Get the script path
    script_dir = Path(__file__).parent / "commands"
    script_path = script_dir / cmd['script']
    
    if not script_path.exists():
        print(f"⚠️  Command script not found: {script_path}")
        print("   Using placeholder implementation...")
        print()
        
        # Placeholder implementation
        print(f"Command: /{command_name}")
        print(f"Description: {cmd['description']}")
        print(f"Arguments: {args}")
        print()
        print("This is a placeholder. In a real implementation,")
        print("this would execute the actual command logic.")
        return True
    
    # Run the actual script
    try:
        result = subprocess.run(
            ["bash", str(script_path)] + args,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 command-runner.py <command> [args...]")
        print("\nExamples:")
        print("  python3 command-runner.py list")
        print("  python3 command-runner.py analyze src/")
        print("  python3 command-runner.py fix src/ --dry-run")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_commands()
    elif command.startswith("/"):
        command_name = command[1:]  # Remove leading /
        args = sys.argv[2:]
        run_command(command_name, args)
    else:
        command_name = command
        args = sys.argv[2:]
        run_command(command_name, args)


if __name__ == "__main__":
    main()
