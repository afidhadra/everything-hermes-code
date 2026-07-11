#!/usr/bin/env python3
"""
Unit tests for fix-markdown.py script.
"""

import sys
import os
import importlib.util

# Import module with hyphen name
spec = importlib.util.spec_from_file_location(
    "fix_markdown",
    os.path.join(os.path.dirname(__file__), '..', 'scripts', 'fix-markdown.py')
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

fix_md022 = mod.fix_md022
fix_md031 = mod.fix_md031
fix_md032 = mod.fix_md032
fix_md040 = mod.fix_md040
fix_md047 = mod.fix_md047
fix_md029 = mod.fix_md029
fix_md010 = mod.fix_md010


def test_md010():
    """Test MD010: No hard tabs."""
    content = "Tab\there"
    result = fix_md010(content)
    expected = "Tab  here"
    assert result == expected, f"MD010 failed:\n{result}\nvs\n{expected}"
    print("✅ MD010 test passed")


def test_md022():
    """Test MD022: Headings should be surrounded by blank lines."""
    content = "# Heading\nSome text\n## Another heading"
    result = fix_md022(content)
    expected = "# Heading\n\nSome text\n\n## Another heading"
    assert result == expected, f"MD022 failed:\n{result}\nvs\n{expected}"
    print("✅ MD022 test passed")


def test_md031():
    """Test MD031: Fenced code blocks should be surrounded by blank lines."""
    content = "Some text\n```\ncode\n```\nMore text"
    result = fix_md031(content)
    expected = "Some text\n\n```\ncode\n```\n\nMore text"
    assert result == expected, f"MD031 failed:\n{result}\nvs\n{expected}"
    print("✅ MD031 test passed")


def test_md032():
    """Test MD032: Lists should be surrounded by blank lines."""
    content = "Some text\n- item 1\n- item 2\nMore text"
    result = fix_md032(content)
    expected = "Some text\n\n- item 1\n- item 2\n\nMore text"
    assert result == expected, f"MD032 failed:\n{result}\nvs\n{expected}"
    print("✅ MD032 test passed")


def test_md040():
    """Test MD040: Fenced code blocks should have a language specified."""
    content = "```\ncode\n```"
    result = fix_md040(content)
    expected = "```text\ncode\n```"
    assert result == expected, f"MD040 failed:\n{result}\nvs\n{expected}"
    print("✅ MD040 test passed")


def test_md047():
    """Test MD047: Files should end with a single newline character."""
    content = "Some text\n\n\n\n"
    result = fix_md047(content)
    expected = "Some text\n"
    assert result == expected, f"MD047 failed:\n{result}\nvs\n{expected}"
    print("✅ MD047 test passed")


def test_md029():
    """Test MD029: Ordered list items should use 1/1/1 prefix style."""
    content = "1. First item\n2. Second item\n3. Third item"
    result = fix_md029(content)
    expected = "1. First item\n1. Second item\n1. Third item"
    assert result == expected, f"MD029 failed:\n{result}\nvs\n{expected}"
    print("✅ MD029 test passed")


def test_combined():
    """Test combined fixes."""
    content = "# Heading\nText with\ttabs\n```\ncode\n```\n- item1\n- item2"
    result = fix_md022(content)
    result = fix_md010(result)
    result = fix_md031(result)
    result = fix_md032(result)
    result = fix_md040(result)
    assert isinstance(result, str)
    assert len(result) > 0
    print("✅ Combined test passed")


def main():
    print("Running unit tests for fix-markdown.py...")
    print()
    test_md010()
    test_md022()
    test_md031()
    test_md032()
    test_md040()
    test_md047()
    test_md029()
    test_combined()
    print()
    print("All tests passed! ✅")


if __name__ == "__main__":
    main()
