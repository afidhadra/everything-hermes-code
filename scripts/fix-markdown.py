#!/usr/bin/env python3
"""Fix all markdownlint warnings in a directory."""

import re
import sys
from pathlib import Path


def fix_md022(content: str) -> str:
    """Headings should be surrounded by blank lines."""
    lines = content.split("\n")
    result = []
    for i, line in enumerate(lines):
        is_heading = re.match(r"^#{1,6}\s", line)
        if is_heading:
            # Add blank line above if prev line is not blank and not start
            if result and result[-1].strip() != "":
                result.append("")
        result.append(line)
        if is_heading:
            # Add blank line below if next line exists and is not blank
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                result.append("")
    return "\n".join(result)


def fix_md031(content: str) -> str:
    """Fenced code blocks should be surrounded by blank lines."""
    lines = content.split("\n")
    result = []
    in_fence = False
    for i, line in enumerate(lines):
        if re.match(r"^```", line):
            if not in_fence:
                # Opening fence: blank line above
                if result and result[-1].strip() != "":
                    result.append("")
                in_fence = True
            else:
                # Closing fence: blank line below
                result.append(line)
                if i + 1 < len(lines) and lines[i + 1].strip() != "":
                    result.append("")
                in_fence = False
                continue
        result.append(line)
    return "\n".join(result)


def fix_md032(content: str) -> str:
    """Lists should be surrounded by blank lines."""
    lines = content.split("\n")
    result = []
    for i, line in enumerate(lines):
        is_list = re.match(r"^(\s*[-*+]|\s*\d+\.)\s", line)
        prev_is_list = bool(result) and re.match(
            r"^(\s*[-*+]|\s*\d+\.)\s", result[-1]
        )
        if is_list and not prev_is_list:
            if result and result[-1].strip() != "":
                result.append("")
        result.append(line)
        # Check if next line is not a list item
        next_is_list = False
        if i + 1 < len(lines):
            next_is_list = bool(
                re.match(r"^(\s*[-*+]|\s*\d+\.)\s", lines[i + 1])
            )
        if is_list and not next_is_list:
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                result.append("")
    return "\n".join(result)


def fix_md040(content: str) -> str:
    """Fenced code blocks should have a language specified."""
    lines = content.split("\n")
    result = []
    for line in lines:
        if re.match(r"^```\s*$", line):
            result.append("```text")
        else:
            result.append(line)
    return "\n".join(result)


def fix_md047(content: str) -> str:
    """Files should end with a single newline character."""
    content = content.rstrip("\n") + "\n"
    return content


def fix_md060(content: str) -> str:
    """Table column style — add spaces around pipes in tables."""
    lines = content.split("\n")
    result = []
    for line in lines:
        if re.match(r"^\|.*\|.*\|$", line.strip()):
            # Fix table rows: ensure space after | and before |
            line = re.sub(r"\|(\S)", r"| \1", line)
            line = re.sub(r"(\S)\|", r"\1 |", line)
            # But keep leading | clean
            line = re.sub(r"^(\|) (\s)", r"\1\2", line)
        result.append(line)
    return "\n".join(result)


def fix_md029(content: str) -> str:
    """Ordered list items should use 1/1/1 prefix style."""
    lines = content.split("\n")
    result = []
    for line in lines:
        m = re.match(r"^(\s*)(\d+)\.\s", line)
        if m:
            indent = m.group(1)
            rest = line[m.end(0) :]
            result.append(f"{indent}1. {rest}")
        else:
            result.append(line)
    return "\n".join(result)


def fix_file(filepath: Path) -> int:
    """Apply all fixes to a single file. Returns number of changes."""
    original = filepath.read_text(encoding="utf-8")
    content = original

    content = fix_md022(content)
    content = fix_md031(content)
    content = fix_md032(content)
    content = fix_md040(content)
    content = fix_md047(content)
    content = fix_md029(content)

    if content != original:
        filepath.write_text(content, encoding="utf-8")
        return 1
    return 0


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = sorted(target.rglob("*.md"))
    fixed = 0
    for f in files:
        if ".git" in str(f):
            continue
        if fix_file(f):
            print(f"  ✅ {f}")
            fixed += 1
    print(f"\nFixed {fixed}/{len(files)} files")


if __name__ == "__main__":
    main()
