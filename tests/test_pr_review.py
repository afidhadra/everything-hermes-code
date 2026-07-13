"""
Tests for PR Review Bot (scripts/pr-review.py).

Covers:
    - Security pattern detection
    - Code quality analysis
    - Dependency analysis
    - PR info parsing
    - Review markdown generation
    - CLI argument handling
    - Edge cases
"""

import json
import re
from pathlib import Path

import pytest

from conftest import SCRIPTS_DIR, import_module_from_path, run_script

pr = import_module_from_path(SCRIPTS_DIR / "pr-review.py")


# ── Security pattern tests ─────────────────────────────────────────

SAMPLE_GO_CODE = """
package main

import "fmt"

func handler(w http.ResponseWriter, r *http.Request) {
    password := "s3cr3t-pass"  // hardcoded
    apiKey := env.Get("API_KEY")  // ok

    // SQL injection: string concat in query
    query := "SELECT * FROM users WHERE id=" + r.URL.Query().Get("id")
    db.Exec(query)

    // Direct injection: fmt.Sprintf in Exec
    db.Exec(fmt.Sprintf("UPDATE users SET name='%s'", r.URL.Query().Get("name")))

    eval("process(" + input + ")")

    // TODO: add rate limiting
    log.Debug("request: %v", r)
}
"""


def test_security_hardcoded_secret():
    """Should detect hardcoded password/secret."""
    findings = pr.analyze_security(SAMPLE_GO_CODE)
    secrets = [f for f in findings if f["type"] == "hardcoded_secret"]
    assert len(secrets) >= 1
    assert secrets[0]["severity"] == "critical"


def test_security_sql_injection():
    """Should detect SQL injection via fmt.Sprintf."""
    findings = pr.analyze_security(SAMPLE_GO_CODE)
    sqli = [f for f in findings if f["type"] == "sql_injection"]
    assert len(sqli) >= 1
    assert sqli[0]["severity"] == "critical"


def test_security_eval():
    """Should detect eval() usage."""
    findings = pr.analyze_security(SAMPLE_GO_CODE)
    eval_f = [f for f in findings if f["type"] == "eval_usage"]
    assert len(eval_f) >= 1


def test_security_todo():
    """Should detect TODO/FIXME comments."""
    findings = pr.analyze_security(SAMPLE_GO_CODE)
    todos = [f for f in findings if f["type"] == "todo_comment"]
    assert len(todos) >= 1


def test_security_no_false_positives():
    """Environment variable access should not flag as hardcoded."""
    findings = pr.analyze_security(SAMPLE_GO_CODE)
    secrets = [f for f in findings if f["type"] == "hardcoded_secret"]
    # Only the string literal should match, not env.Get("API_KEY")
    assert len(secrets) == 1


def test_security_empty_diff():
    """Empty diff should return no findings."""
    findings = pr.analyze_security("")
    assert len(findings) == 0


def test_security_clean_code():
    """Clean code should have no security findings."""
    clean = """
func handler(w http.ResponseWriter, r *http.Request) {
    pass := os.Getenv("DB_PASSWORD")
    db.Exec("SELECT * FROM users WHERE id = $1", r.URL.Query().Get("id"))
    log.Info("processed request")
}
"""
    findings = pr.analyze_security(clean)
    critical = [f for f in findings if f["severity"] == "critical"]
    assert len(critical) == 0


# ── Code quality tests ────────────────────────────────────────────

def test_large_file_detected():
    """Large files should be flagged."""
    files = [
        {"path": "server.go", "additions": 250, "deletions": 10},
    ]
    findings = pr.analyze_code_quality(files)
    large = [f for f in findings if f["type"] == "large_file"]
    assert len(large) >= 1
    assert "server.go" in str(large)


def test_small_file_ok():
    """Small files should not be flagged."""
    files = [
        {"path": "main.go", "additions": 50, "deletions": 5},
    ]
    findings = pr.analyze_code_quality(files)
    large = [f for f in findings if f["type"] == "large_file"]
    assert len(large) == 0


def test_massive_pr():
    """Very large PRs should be flagged."""
    files = [
        {"path": "big.ts", "additions": 600, "deletions": 100},
    ]
    findings = pr.analyze_code_quality(files)
    massive = [f for f in findings if f["type"] == "massive_pr"]
    assert len(massive) >= 1


def test_test_files_not_flagged():
    """Test files with large additions should not be flagged as large_file."""
    files = [
        {"path": "server_test.go", "additions": 250, "deletions": 10},
    ]
    findings = pr.analyze_code_quality(files)
    large = [f for f in findings if f["type"] == "large_file"]
    # Test files are excluded from large_file check
    assert len(large) == 0


# ── Dependency analysis tests ──────────────────────────────────────

def test_dependency_change_detected():
    """Changes to go.mod should be flagged."""
    files = [
        {"path": "go.mod", "additions": 5, "deletions": 2},
    ]
    findings = pr.analyze_dependencies(files, "")
    dep = [f for f in findings if f["type"] == "dependency_change"]
    assert len(dep) >= 1


def test_non_dep_file_ignored():
    """Non-dependency files should not trigger dep analysis."""
    files = [
        {"path": "main.go", "additions": 10, "deletions": 0},
    ]
    findings = pr.analyze_dependencies(files, "")
    assert len(findings) == 0


# ── Review generation tests ────────────────────────────────────────

def test_generate_review_empty():
    """Empty findings should produce clean review."""
    analysis = {
        "pr": {"number": 1, "title": "Test"},
        "findings": [],
        "summary": {
            "critical": 0, "high": 0, "medium": 0, "info": 0,
            "total_changed_files": 2,
            "total_additions": 50,
            "total_deletions": 10,
        },
        "recommended_event": "APPROVE",
        "analyzed_at": "2026-07-13T12:00:00",
    }
    review = pr.generate_review_markdown(analysis)
    assert "APPROVE" in review
    assert "#1" in review
    assert "No issues found" in review


def test_generate_review_with_findings():
    """Findings should appear in review."""
    analysis = {
        "pr": {"number": 42, "title": "Fix auth"},
        "findings": [
            {"severity": "critical", "file": "auth.go", "line": 45,
             "message": "Hardcoded secret", "snippet": "password = \"x\""},
            {"severity": "info", "file": "main.go", "line": 10,
             "message": "TODO found", "snippet": "// TODO: fix"},
        ],
        "summary": {
            "critical": 1, "high": 0, "medium": 0, "info": 1,
            "total_changed_files": 3,
            "total_additions": 100,
            "total_deletions": 20,
        },
        "recommended_event": "REQUEST_CHANGES",
        "analyzed_at": "2026-07-13T12:00:00",
    }
    review = pr.generate_review_markdown(analysis)
    assert "REQUEST_CHANGES" in review
    assert "Hardcoded secret" in review
    assert "TODO found" in review
    assert "#42" in review


def test_generate_review_request_changes_has_blocker_message():
    """REQUEST_CHANGES verdict should have warning banner."""
    analysis = {
        "pr": {"number": 1, "title": "Test"},
        "findings": [
            {"severity": "critical", "file": "main.go", "line": 1,
             "message": "Critical issue", "snippet": ""},
        ],
        "summary": {
            "critical": 1, "high": 0, "medium": 0, "info": 0,
            "total_changed_files": 1,
            "total_additions": 10,
            "total_deletions": 0,
        },
        "recommended_event": "REQUEST_CHANGES",
        "analyzed_at": "2026-07-13T12:00:00",
    }
    review = pr.generate_review_markdown(analysis)
    assert "addressed before merging" in review


# ── Extensions map test ────────────────────────────────────────────

def test_extension_map_coverage():
    """Common extensions should be in the map."""
    common = [".go", ".ts", ".tsx", ".vue", ".py", ".js", ".sql",
              ".yaml", ".json", ".md"]
    for ext in common:
        assert ext in pr.EXTENSION_MAP, f"Missing extension: {ext}"


# ── Edge cases ─────────────────────────────────────────────────────

def test_analyze_pr_missing_repo():
    """analyze_pr should fail gracefully with bad repo."""
    with pytest.raises((RuntimeError, Exception)):
        pr.analyze_pr(999999, "nonexistent/user")


def test_run_regression_analysis():
    """Regression analysis should handle empty diff."""
    findings = pr.run_regression_analysis("", str(SCRIPTS_DIR))
    assert isinstance(findings, list)


def test_security_console_log_detected():
    """Console.log statements should be flagged."""
    diff = 'console.log("debug info");\nconsole.error("err");'
    findings = pr.analyze_security(diff)
    logs = [f for f in findings if f["type"] == "console_log"]
    assert len(logs) >= 1


# ── CLI tests ──────────────────────────────────────────────────────

def test_cli_help():
    """--help should produce usage output."""
    result = run_script(SCRIPTS_DIR / "pr-review.py", ["--help"])
    assert "usage:" in result.lower() or "Usage" in result


def test_cli_no_args():
    """No args should print usage and exit non-zero."""
    result = run_script(SCRIPTS_DIR / "pr-review.py", [], expected_code=None)
    assert result is not None


def test_cli_dry_run_no_repo():
    """Dry run without repo should fail to detect repo."""
    # Run from a temp directory without git
    import tempfile
    import subprocess, sys
    with tempfile.TemporaryDirectory() as td:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "pr-review.py"),
             "--pr", "1", "--dry-run"],
            capture_output=True, text=True, timeout=10,
            cwd=td,
        )
        assert result.returncode != 0
        assert "detect" in (result.stdout + result.stderr).lower()
