#!/usr/bin/env python3
"""
Enhanced markdownlint auto-fixer.
Fixes: MD010, MD022, MD031, MD032, MD040, MD047, MD060
Usage: python3 fix-markdown.py [directory]
"""

import re
import sys
from pathlib import Path


def fix_md010(content: str) -> str:
    """No hard tabs — replace tabs with spaces."""
    return content.replace("\t", "  ")


def fix_md022(content: str) -> str:
    """Headings should be surrounded by blank lines."""
    lines = content.split("\n")
    result = []
    for i, line in enumerate(lines):
        is_heading = re.match(r"^#{1,6}\s", line)
        if is_heading:
            if result and result[-1].strip() != "":
                result.append("")
        result.append(line)
        if is_heading:
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
                if result and result[-1].strip() != "":
                    result.append("")
                in_fence = True
            else:
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
        is_list = bool(re.match(r"^(\s*[-*+]|\s*\d+\.)\s", line))
        prev_is_list = bool(result) and bool(
            re.match(r"^(\s*[-*+]|\s*\d+\.)\s", result[-1])
        )
        if is_list and not prev_is_list:
            if result and result[-1].strip() != "":
                result.append("")
        result.append(line)
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
    """Fenced code blocks should have a language specified.
    
    Also fixes corrupted closing fences (```text → ```).
    """
    lines = content.split("\n")
    result = []
    in_fence = False
    for line in lines:
        if re.match(r"^```", line):
            if not in_fence:
                # Opening fence: add language if missing
                if re.match(r"^```\s*$", line):
                    result.append("```text")
                else:
                    result.append(line)
                in_fence = True
            else:
                # Closing fence: strip language if present
                # A closing fence should be just ``` (possibly with trailing spaces)
                stripped = line.strip()
                if stripped != "```":
                    result.append("```")
                else:
                    result.append(line)
                in_fence = False
        else:
            result.append(line)
    return "\n".join(result)


def fix_md047(content: str) -> str:
    """Files should end with a single newline character."""
    return content.rstrip("\n") + "\n"


def fix_md060(content: str) -> str:
    """Table column style — add spaces around pipes in tables."""
    lines = content.split("\n")
    result = []
    for line in lines:
        if re.match(r"^\|.*\|.*\|$", line.strip()):
            line = re.sub(r"\|(\S)", r"| \1", line)
            line = re.sub(r"(\S)\|", r"\1 |", line)
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
            rest = line[m.end(0):]
            result.append(f"{indent}1. {rest}")
        else:
            result.append(line)
    return "\n".join(result)


def fix_file(filepath: Path) -> int:
    """Apply all fixes to a single file. Returns number of changes."""
    original = filepath.read_text(encoding="utf-8")
    content = original

    content = fix_md010(content)
    content = fix_md040(content)   # Fix fences first (before md031/032)
    content = fix_md031(content)
    content = fix_md022(content)
    content = fix_md032(content)
    content = fix_md047(content)
    content = fix_md029(content)
    content = fix_md060(content)

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
