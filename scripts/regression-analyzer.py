#!/usr/bin/env python3
"""
Everything Hermes Code — Regression Analyzer (Layer B)

Analyzes code changes to detect regression risks before they hit production.
Builds a dependency graph, computes blast radius, and flags mismatches.

Usage:
    python3 regression-analyzer.py                    # analyze uncommitted changes
    python3 regression-analyzer.py HEAD~1             # analyze last commit
    python3 regression-analyzer.py main..development   # compare branches
    python3 regression-analyzer.py abc123..def456      # compare commits
    python3 regression-analyzer.py --staged            # staged changes only
    python3 regression-analyzer.py --dry-run           # show plan without Hermes

Features:
    - Git diff parsing (added/modified/deleted/moved)
    - Import/dependency graph builder
    - Blast radius computation (what breaks if X changes)
    - API contract validation (FE calls vs BE endpoints)
    - Risk assessment per changed file
    - Parallel agent spawning for deep analysis (optional)
"""

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ============================================================
# Data Models
# ============================================================

class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None
    insertions: int = 0
    deletions: int = 0
    language: str = ""
    imports_added: list[str] = field(default_factory=list)
    imports_removed: list[str] = field(default_factory=list)
    exports_changed: list[str] = field(default_factory=list)
    functions_changed: list[str] = field(default_factory=list)


@dataclass
class DependencyEdge:
    source: str  # file that imports
    target: str  # file being imported
    import_type: str  # import, require, include, etc.


@dataclass
class RegressionRisk:
    file: str
    risk: RiskLevel
    reason: str
    affected_files: list[str] = field(default_factory=list)
    suggestion: str = ""


# ============================================================
# Git Operations
# ============================================================

def run_git(args: list[str], cwd: str = ".") -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=cwd, timeout=30
        )
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_diff_files(ref: str = "", staged: bool = False, cwd: str = ".") -> list[str]:
    """Get list of changed files from git diff."""
    if staged:
        args = ["diff", "--cached", "--name-status"]
    elif ".." in ref:
        args = ["diff", ref, "--name-status"]
    elif ref:
        args = ["diff", ref, "--name-status"]
    else:
        args = ["diff", "--name-status"]
    
    output = run_git(args, cwd)
    if not output:
        return []
    
    files = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        
        if status.startswith("R"):  # Renamed/Moved
            if len(parts) >= 3:
                files.append(f"R\t{parts[1]}\t{parts[2]}")
        elif status.startswith("A"):
            files.append(f"A\t{parts[-1]}")
        elif status.startswith("M"):
            files.append(f"M\t{parts[-1]}")
        elif status.startswith("D"):
            files.append(f"D\t{parts[-1]}")
        else:
            files.append(f"?\t{parts[-1]}")
    
    return files


def get_diff_stats(ref: str = "", staged: bool = False, cwd: str = ".") -> dict:
    """Get insertion/deletion stats per file."""
    if staged:
        args = ["diff", "--cached", "--numstat"]
    elif ".." in ref:
        args = ["diff", ref, "--numstat"]
    elif ref:
        args = ["diff", ref, "--numstat"]
    else:
        args = ["diff", "--numstat"]
    
    output = run_git(args, cwd)
    stats = {}
    
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            ins, dels, path = parts[0], parts[1], parts[2]
            stats[path] = {
                "insertions": int(ins) if ins.isdigit() else 0,
                "deletions": int(dels) if dels.isdigit() else 0,
            }
    
    return stats


def get_diff_content(ref: str = "", staged: bool = False, cwd: str = ".", path: str = "") -> str:
    """Get actual diff content for a specific file."""
    if staged:
        args = ["diff", "--cached"]
    elif ".." in ref:
        args = ["diff", ref]
    elif ref:
        args = ["diff", ref]
    else:
        args = ["diff"]
    
    if path:
        args.extend(["--", path])
    
    return run_git(args, cwd)


# ============================================================
# Language Detection
# ============================================================

LANG_MAP = {
    ".go": "go",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".vue": "vue",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".sql": "sql",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".sh": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
}

def detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return LANG_MAP.get(ext, "unknown")


# ============================================================
# Import / Dependency Parser
# ============================================================

# Regex patterns for different languages
IMPORT_PATTERNS = {
    "go": [
        re.compile(r'^\s*"([^"]+)"', re.MULTILINE),  # import "pkg"
        re.compile(r'^\s*(\w+)\s+"([^"]+)"', re.MULTILINE),  # alias "pkg"
    ],
    "python": [
        re.compile(r'^\s*import\s+(\S+)', re.MULTILINE),
        re.compile(r'^\s*from\s+(\S+)\s+import', re.MULTILINE),
    ],
    "javascript": [
        re.compile(r'import\s+.*\s+from\s+["\']([^"\']+)["\']'),
        re.compile(r'require\(\s*["\']([^"\']+)["\']\s*\)'),
    ],
    "typescript": [
        re.compile(r'import\s+.*\s+from\s+["\']([^"\']+)["\']'),
        re.compile(r'require\(\s*["\']([^"\']+)["\']\s*\)'),
    ],
    "vue": [
        re.compile(r'import\s+.*\s+from\s+["\']([^"\']+)["\']'),
        re.compile(r'require\(\s*["\']([^"\']+)["\']\s*\)'),
    ],
}

# Export patterns
EXPORT_PATTERNS = {
    "go": [
        re.compile(r'^func\s+([A-Z]\w*)', re.MULTILINE),  # Exported functions
        re.compile(r'^type\s+([A-Z]\w*)', re.MULTILINE),
        re.compile(r'^var\s+([A-Z]\w*)', re.MULTILINE),
    ],
    "python": [
        re.compile(r'^def\s+(\w+)', re.MULTILINE),
        re.compile(r'^class\s+(\w+)', re.MULTILINE),
    ],
    "javascript": [
        re.compile(r'export\s+(?:default\s+)?(?:function|const|let|var|class)\s+(\w+)'),
        re.compile(r'export\s+\{([^}]+)\}'),
    ],
    "typescript": [
        re.compile(r'export\s+(?:default\s+)?(?:function|const|let|var|class|interface|type)\s+(\w+)'),
        re.compile(r'export\s+\{([^}]+)\}'),
    ],
    "vue": [
        re.compile(r'export\s+(?:default\s+)?(?:function|const|let|var|class)\s+(\w+)'),
    ],
}


def extract_imports(content: str, language: str) -> list[str]:
    """Extract import/dependency paths from file content."""
    imports = []
    patterns = IMPORT_PATTERNS.get(language, [])
    for pattern in patterns:
        matches = pattern.findall(content)
        for match in matches:
            if isinstance(match, tuple):
                imports.append(match[-1])  # Last group = path
            else:
                imports.append(match)
    return list(set(imports))


def extract_exports(content: str, language: str) -> list[str]:
    """Extract exported symbols from file content."""
    exports = []
    patterns = EXPORT_PATTERNS.get(language, [])
    for pattern in patterns:
        matches = pattern.findall(content)
        for match in matches:
            if "," in str(match):
                # Handle export { a, b, c }
                exports.extend(s.strip() for s in match.split(","))
            else:
                exports.append(match)
    return list(set(exports))


def extract_functions_from_diff(diff_content: str) -> list[str]:
    """Extract function names from added/removed lines in diff."""
    funcs = []
    func_patterns = [
        r'^\+.*func\s+(\w+)',       # Go
        r'^\+.*def\s+(\w+)',        # Python
        r'^\+.*function\s+(\w+)',   # JS/TS
        r'^\+.*const\s+(\w+)\s*=',  # JS/TS const
    ]
    for pattern in func_patterns:
        matches = re.findall(pattern, diff_content, re.MULTILINE)
        funcs.extend(matches)
    return list(set(funcs))


# ============================================================
# Dependency Graph Builder
# ============================================================

class DependencyGraph:
    """Builds and queries a dependency graph from project files."""
    
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.edges: list[DependencyEdge] = []
        self.reverse_deps: dict[str, list[str]] = defaultdict(list)
        self.forward_deps: dict[str, list[str]] = defaultdict(list)
        self.file_exports: dict[str, list[str]] = defaultdict(list)
        self._scanned = False
    
    def scan(self, max_files: int = 500):
        """Scan project files and build dependency graph."""
        if self._scanned:
            return
        
        count = 0
        skip_dirs = {".git", "node_modules", "vendor", "dist", "build",
                     "__pycache__", ".venv", "venv", "target", "bin", "obj"}
        
        for path in self.project_dir.rglob("*"):
            if count >= max_files:
                break
            if not path.is_file():
                continue
            if any(part in skip_dirs for part in path.parts):
                continue
            
            lang = detect_language(str(path))
            if lang not in IMPORT_PATTERNS:
                continue
            
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            
            rel_path = str(path.relative_to(self.project_dir))
            
            # Extract exports
            exports = extract_exports(content, lang)
            if exports:
                self.file_exports[rel_path] = exports
            
            # Extract imports
            imports = extract_imports(content, lang)
            for imp in imports:
                target = self._resolve_import(imp, rel_path, lang)
                if target:
                    edge = DependencyEdge(
                        source=rel_path,
                        target=target,
                        import_type="import"
                    )
                    self.edges.append(edge)
                    self.forward_deps[rel_path].append(target)
                    self.reverse_deps[target].append(rel_path)
            
            count += 1
        
        self._scanned = True
    
    def _resolve_import(self, import_path: str, source_file: str, lang: str) -> str:
        """Resolve an import path to a relative file path."""
        # Go imports are package paths, skip for now
        if lang == "go":
            return import_path  # Keep as package path
        
        # JS/TS/Vue: resolve relative imports
        if import_path.startswith("."):
            source_dir = Path(source_file).parent
            resolved = source_dir / import_path
            
            # Try common extensions
            for ext in ["", ".ts", ".js", ".tsx", ".jsx", ".vue",
                        "/index.ts", "/index.js", "/index.vue"]:
                candidate = str(resolved) + ext
                candidate_path = self.project_dir / candidate
                if candidate_path.exists():
                    return candidate
        
        # Python: resolve module paths
        if lang == "python":
            parts = import_path.replace(".", "/")
            for ext in [".py", "/__init__.py"]:
                candidate = parts + ext
                if (self.project_dir / candidate).exists():
                    return candidate
        
        return import_path  # Unresolved, keep raw
    
    def get_blast_radius(self, changed_file: str) -> list[str]:
        """Get all files that depend on a changed file (transitive)."""
        affected = set()
        queue = [changed_file]
        visited = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            dependents = self.reverse_deps.get(current, [])
            for dep in dependents:
                if dep not in affected:
                    affected.add(dep)
                    queue.append(dep)
        
        return sorted(affected)
    
    def get_direct_dependents(self, file_path: str) -> list[str]:
        """Get files that directly import/depend on this file."""
        return sorted(set(self.reverse_deps.get(file_path, [])))


# ============================================================
# API Contract Validator (FE/BE sync)
# ============================================================

# Go HTTP route patterns
GO_ROUTE_PATTERNS = [
    re.compile(r'(?:r\.(?:HandleFunc|Get|Post|Put|Delete|Patch|Handle))\s*\(\s*"([^"]+)"'),
    re.compile(r'(?:router|mux|r|api)\.(?:GET|POST|PUT|DELETE|PATCH|HandleFunc)\s*\(\s*"([^"]+)"'),
    re.compile(r'Group\s*\(\s*"([^"]+)"'),
    re.compile(r'(?:e\.(?:GET|POST|PUT|DELETE))\s*\(\s*"([^"]+)"'),
]

# JS/TS/Vue API call patterns
JS_API_PATTERNS = [
    # axios.get("/api/v1/..."), apiClient.get(...)
    re.compile(r'(?:axios|fetch|http|api|apiClient)\.(?:get|post|put|delete|patch)\s*\(\s*[`"\']([^`"\']+)[`"\']'),
    # Helper wrappers: get("/api/v1/..."), post("/api/v1/..."), etc. (from api-client.ts)
    re.compile(r'(?:^|\s)(?:get|post|put|delete|patch)<[^>]*>\s*\(\s*[`"\'](/api/[^`"\']+)[`"\']', re.MULTILINE),
    # Template literal URLs: `/api/v1/distributions/${id}/return`
    re.compile(r'[`"\'](/api/v1/[^`"\']+?)(?:\$\{|[`"\'])'),
    # $http.get("...")
    re.compile(r'\$http\.(?:get|post|put|delete)\s*\(\s*[`"\']([^`"\']+)[`"\']'),
    # request({ url: "..." })
    re.compile(r'request\s*\(\s*\{[^}]*url:\s*[`"\']([^`"\']+)[`"\']'),
    # api("...")
    re.compile(r'api\s*\(\s*[`"\']([^`"\']+)[`"\']'),
    # BASE_URL = '/api/v1/...' constant definitions
    re.compile(r'(?:BASE_URL|BASE|ENDPOINT)\s*=\s*[`"\'](/api/[^`"\']+)[`"\']'),
]


def extract_go_endpoints(content: str) -> list[str]:
    """Extract API endpoint paths from Go source code (Gin framework aware)."""
    endpoints = set()
    
    # Parse Gin route files: find Group() prefixes and route registrations
    # Pattern: varname := v1.Group("/path")
    groups = {}
    for m in re.finditer(
        r'(\w+)\s*:?=\s*(?:v1|r|\w+)\.Group\s*\(\s*"([^"]*)"', content
    ):
        groups[m.group(1)] = m.group(2)
    
    # Pattern: varname.METHOD("path", handler)
    for m in re.finditer(
        r'(\w+)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*"([^"]*)"', content
    ):
        var, path = m.group(1), m.group(3)
        base = "/api/v1"
        if var in groups:
            gpath = groups[var]
            full = f"{base}{gpath}{path}" if gpath else f"{base}{path}"
        elif var == "v1":
            full = f"{base}{path}"
        elif var in ("r", "router"):
            full = path if path.startswith("/") else f"/{path}"
        else:
            # Unknown var — try prefix from first group
            if groups:
                first_group = list(groups.values())[0]
                full = f"{base}{first_group}{path}"
            else:
                full = f"{base}/{path}"
        full = re.sub(r'/+', '/', full)
        endpoints.add(full)
    
    # Fallback: generic Go HTTP patterns (non-Gin frameworks)
    if not endpoints:
        for pattern in GO_ROUTE_PATTERNS:
            endpoints.update(pattern.findall(content))
    
    return sorted(endpoints)


def extract_fe_api_calls(content: str) -> list[str]:
    """Extract API call URLs from JS/TS/Vue source code."""
    calls = set()
    for pattern in JS_API_PATTERNS:
        calls.update(pattern.findall(content))
    return sorted(calls)


def validate_api_contracts(project_dir: str) -> dict:
    """
    Compare FE API calls against BE endpoints.
    Returns dict with: matched, fe_only (potential 404), be_only (unused).
    """
    project_path = Path(project_dir)
    
    be_endpoints: set[str] = set()
    fe_calls: set[str] = set()
    
    skip_dirs = {".git", "node_modules", "vendor", "dist", "build",
                 "__pycache__", ".venv", "venv", "target"}
    
    for path in project_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        
        ext = path.suffix.lower()
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        if ext == ".go":
            be_endpoints.update(extract_go_endpoints(content))
        elif ext in (".js", ".ts", ".vue", ".jsx", ".tsx"):
            fe_calls.update(extract_fe_api_calls(content))
    
    # Normalize paths for comparison (strip params, lowercasse)
    def normalize(path: str) -> str:
        path = path.split("?")[0].split("#")[0]
        path = re.sub(r'/\d+', '/:id', path)  # /123 → /:id
        path = re.sub(r'/[a-f0-9-]{36}', '/:uuid', path)  # UUIDs
        return path.rstrip("/") or "/"
    
    be_normalized = {normalize(e) for e in be_endpoints}
    fe_normalized = {normalize(c) for c in fe_calls}
    
    matched = be_normalized & fe_normalized
    fe_only = fe_normalized - be_normalized  # FE calls that BE doesn't have
    be_only = be_normalized - fe_normalized  # BE endpoints FE doesn't call
    
    return {
        "be_endpoints": sorted(be_endpoints),
        "fe_calls": sorted(fe_calls),
        "matched": sorted(matched),
        "fe_only": sorted(fe_only),  # potential 404s
        "be_only": sorted(be_only),  # potentially dead code
        "be_count": len(be_endpoints),
        "fe_count": len(fe_calls),
        "match_count": len(matched),
    }


# ============================================================
# DB Schema Validator
# ============================================================

SQL_PATTERNS = {
    "create_table": re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)',
        re.IGNORECASE | re.DOTALL
    ),
    "alter_add_column": re.compile(
        r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?\s+ADD\s+(?:COLUMN\s+)?[`"]?(\w+)[`"]?',
        re.IGNORECASE
    ),
    "drop_column": re.compile(
        r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?\s+DROP\s+(?:COLUMN\s+)?[`"]?(\w+)[`"]?',
        re.IGNORECASE
    ),
}


def extract_db_schema(project_dir: str) -> dict:
    """Extract DB schema from migration files."""
    project_path = Path(project_dir)
    skip_dirs = {".git", "node_modules", "vendor", "dist", "build", "__pycache__"}
    
    tables: dict[str, list[str]] = defaultdict(list)
    migrations: list[str] = []
    
    for path in project_path.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        
        ext = path.suffix.lower()
        if ext not in (".sql",):
            # Also check Go migration files
            if ext == ".go" and "migrat" in path.name.lower():
                pass
            else:
                continue
        
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        
        migrations.append(str(path.relative_to(project_path)))
        
        # CREATE TABLE
        for match in SQL_PATTERNS["create_table"].finditer(content):
            table_name = match.group(1).lower()
            columns_text = match.group(2)
            # Extract column names
            for line in columns_text.split("\n"):
                line = line.strip().rstrip(",")
                if not line or line.upper().startswith(("PRIMARY", "FOREIGN", "UNIQUE", "CONSTRAINT", "CHECK", "INDEX", "KEY")):
                    continue
                col_name = re.match(r'[`"]?(\w+)[`"]?', line)
                if col_name:
                    tables[table_name].append(col_name.group(1).lower())
        
        # ALTER TABLE ADD COLUMN
        for match in SQL_PATTERNS["alter_add_column"].finditer(content):
            table_name = match.group(1).lower()
            col_name = match.group(2).lower()
            if col_name not in tables[table_name]:
                tables[table_name].append(col_name)
        
        # ALTER TABLE DROP COLUMN
        for match in SQL_PATTERNS["drop_column"].finditer(content):
            table_name = match.group(1).lower()
            col_name = match.group(2).lower()
            if col_name in tables.get(table_name, []):
                tables[table_name].remove(col_name)
    
    return {
        "tables": dict(tables),
        "migration_files": migrations,
        "table_count": len(tables),
        "total_columns": sum(len(cols) for cols in tables.values()),
    }


# ============================================================
# Risk Assessment
# ============================================================

CRITICAL_PATTERNS = [
    "migration", "schema", "config", "auth", "middleware",
    "database", "model", "entity", "docker-compose",
]

HIGH_RISK_PATTERNS = [
    "service", "handler", "controller", "route", "router",
    "store", "repository", "api", "endpoint",
]


def assess_risk(change: FileChange, blast_radius: list[str]) -> RegressionRisk:
    """Assess regression risk for a single file change."""
    path_lower = change.path.lower()
    filename = Path(change.path).name.lower()
    
    reasons = []
    suggestions = []
    risk = RiskLevel.LOW
    
    # Critical files
    if any(p in path_lower for p in CRITICAL_PATTERNS):
        risk = RiskLevel.CRITICAL
        reasons.append(f"Critical file pattern matched: {filename}")
        suggestions.append("Review carefully — changes to this file affect core system behavior")
    
    # High-risk files
    elif any(p in path_lower for p in HIGH_RISK_PATTERNS):
        risk = RiskLevel.HIGH
        reasons.append(f"High-risk file pattern: {filename}")
        suggestions.append("Run integration tests for affected endpoints")
    
    # Large changes
    total_lines = change.insertions + change.deletions
    if total_lines > 100:
        if risk.value == "LOW":
            risk = RiskLevel.MEDIUM
        reasons.append(f"Large change: +{change.insertions}/-{change.deletions} lines")
    
    # Deleted files
    if change.change_type == ChangeType.DELETED:
        risk = RiskLevel.HIGH if risk == RiskLevel.LOW else risk
        reasons.append("File deleted — check for broken imports")
        suggestions.append(f"Search for references to {filename} across the codebase")
    
    # Blast radius
    if len(blast_radius) > 5:
        if risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
            risk = RiskLevel.HIGH
        reasons.append(f"High blast radius: {len(blast_radius)} files depend on this")
        suggestions.append(f"Review all {len(blast_radius)} dependent files")
    elif len(blast_radius) > 0:
        reasons.append(f"Blast radius: {len(blast_radius)} dependent files")
    
    # Default reason
    if not reasons:
        reasons.append("Low-risk change")
        suggestions.append("Standard review sufficient")
    
    return RegressionRisk(
        file=change.path,
        risk=risk,
        reason="; ".join(reasons),
        affected_files=blast_radius,
        suggestion="; ".join(suggestions),
    )


# ============================================================
# Report Generator
# ============================================================

RISK_COLORS = {
    RiskLevel.CRITICAL: "\033[0;31m",  # Red
    RiskLevel.HIGH: "\033[1;31m",      # Bold red
    RiskLevel.MEDIUM: "\033[1;33m",    # Yellow
    RiskLevel.LOW: "\033[0;32m",       # Green
    RiskLevel.INFO: "\033[0;36m",      # Cyan
}
NC = "\033[0m"


def generate_report(
    changes: list[FileChange],
    risks: list[RegressionRisk],
    api_contracts: dict,
    db_schema: dict,
    ref: str,
) -> str:
    """Generate full regression analysis report."""
    lines = [
        "=" * 70,
        "REGRESSION ANALYSIS REPORT",
        "=" * 70,
        "",
        f"Scope: {ref or 'uncommitted changes'}",
        f"Files changed: {len(changes)}",
        f"Files analyzed: {sum(len(r.affected_files) for r in risks)}",
        "",
    ]
    
    # --- Risk Summary ---
    risk_counts = defaultdict(int)
    for r in risks:
        risk_counts[r.risk] += 1
    
    lines.extend([
        "-" * 70,
        "RISK SUMMARY",
        "-" * 70,
    ])
    
    for level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
        count = risk_counts.get(level, 0)
        if count > 0:
            color = RISK_COLORS[level]
            lines.append(f"  {color}{level.value:8s}{NC}  {count} file(s)")
    
    lines.append("")
    
    # --- Changed Files ---
    lines.extend([
        "-" * 70,
        "CHANGED FILES",
        "-" * 70,
    ])
    
    type_icons = {
        ChangeType.ADDED: "🟢",
        ChangeType.MODIFIED: "🟡",
        ChangeType.DELETED: "🔴",
        ChangeType.MOVED: "🔵",
        ChangeType.UNKNOWN: "❓",
    }
    
    for change in changes:
        icon = type_icons.get(change.change_type, "❓")
        lines.append(
            f"  {icon} {change.path}"
        )
        if change.insertions or change.deletions:
            lines.append(
                f"     +{change.insertions}/-{change.deletions} "
                f"({change.language})"
            )
    
    lines.append("")
    
    # --- Risk Details ---
    lines.extend([
        "-" * 70,
        "RISK DETAILS",
        "-" * 70,
    ])
    
    for risk in sorted(risks, key=lambda r: list(RiskLevel).index(r.risk)):
        color = RISK_COLORS[risk.risk]
        lines.append(f"\n  {color}[{risk.risk.value}]{NC} {risk.file}")
        lines.append(f"     Reason: {risk.reason}")
        if risk.affected_files:
            lines.append(f"     Affected ({len(risk.affected_files)}):")
            for f in risk.affected_files[:10]:
                lines.append(f"       → {f}")
            if len(risk.affected_files) > 10:
                lines.append(f"       ... and {len(risk.affected_files) - 10} more")
        if risk.suggestion:
            lines.append(f"     Action: {risk.suggestion}")
    
    lines.append("")
    
    # --- API Contract Validation ---
    if api_contracts.get("be_count", 0) > 0 or api_contracts.get("fe_count", 0) > 0:
        lines.extend([
            "-" * 70,
            "API CONTRACT VALIDATION",
            "-" * 70,
            f"  BE endpoints:  {api_contracts['be_count']}",
            f"  FE API calls:  {api_contracts['fe_count']}",
            f"  Matched:       {api_contracts['match_count']}",
            "",
        ])
        
        if api_contracts["fe_only"]:
            lines.append(f"  ⚠️  FE calls with NO BE endpoint ({len(api_contracts['fe_only'])}):")
            for ep in api_contracts["fe_only"][:15]:
                lines.append(f"     → {ep}")
            if len(api_contracts["fe_only"]) > 15:
                lines.append(f"     ... and {len(api_contracts['fe_only']) - 15} more")
            lines.append("")
        
        if api_contracts["be_only"]:
            lines.append(f"  ℹ️  BE endpoints NOT called by FE ({len(api_contracts['be_only'])}):")
            for ep in api_contracts["be_only"][:15]:
                lines.append(f"     → {ep}")
            if len(api_contracts["be_only"]) > 15:
                lines.append(f"     ... and {len(api_contracts['be_only']) - 15} more")
            lines.append("")
    
    # --- DB Schema ---
    if db_schema.get("table_count", 0) > 0:
        lines.extend([
            "-" * 70,
            "DATABASE SCHEMA",
            "-" * 70,
            f"  Tables:        {db_schema['table_count']}",
            f"  Total columns: {db_schema['total_columns']}",
            f"  Migrations:    {len(db_schema['migration_files'])}",
            "",
        ])
        
        for table, columns in sorted(db_schema["tables"].items()):
            lines.append(f"  📦 {table} ({len(columns)} columns)")
            for col in columns[:8]:
                lines.append(f"     • {col}")
            if len(columns) > 8:
                lines.append(f"     ... +{len(columns) - 8} more")
            lines.append("")
    
    # --- Final Verdict ---
    lines.extend([
        "-" * 70,
        "VERDICT",
        "-" * 70,
    ])
    
    critical = risk_counts.get(RiskLevel.CRITICAL, 0)
    high = risk_counts.get(RiskLevel.HIGH, 0)
    
    if critical > 0:
        lines.append(f"  🔴 {critical} CRITICAL risk(s) — DO NOT merge without review")
    elif high > 0:
        lines.append(f"  🟡 {high} HIGH risk(s) — Review carefully before merge")
    else:
        lines.append("  🟢 Low regression risk — Standard review sufficient")
    
    fe_404s = len(api_contracts.get("fe_only", []))
    if fe_404s > 0:
        lines.append(f"  ⚠️  {fe_404s} FE API call(s) may 404 — verify endpoints exist")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Regression Analyzer — detect regression risks before merge"
    )
    parser.add_argument(
        "ref",
        nargs="?",
        default="",
        help="Git ref to analyze (e.g. HEAD~1, main..development, commit hash)"
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Analyze staged changes only"
    )
    parser.add_argument(
        "--project",
        type=str,
        default=".",
        help="Project directory to analyze (default: current directory)"
    )
    parser.add_argument(
        "--api-check",
        action="store_true",
        help="Validate FE/BE API contracts"
    )
    parser.add_argument(
        "--db-check",
        action="store_true",
        help="Extract and validate DB schema"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all checks (API + DB + dependency graph)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show analysis plan without deep inspection"
    )
    parser.add_argument(
        "--cross-repo",
        nargs=2,
        metavar=("BE_DIR", "FE_DIR"),
        help="Cross-repo audit: compare BE endpoints vs FE API calls"
    )
    
    args = parser.parse_args()
    
    project_dir = args.project
    ref = args.ref
    
    # Banner
    print()
    print("=" * 70)
    print("  REGRESSION ANALYZER")
    print("=" * 70)
    
    # --- Cross-repo mode ---
    if args.cross_repo:
        be_dir, fe_dir = args.cross_repo
        print(f"\n🔌 Cross-repo audit: BE={be_dir} vs FE={fe_dir}")
        
        be_data = validate_api_contracts(be_dir)
        fe_data = validate_api_contracts(fe_dir)
        
        def normalize(path):
            path = path.split("?")[0].split("#")[0]
            path = re.sub(r'/\d+', '/:id', path)
            path = re.sub(r'/[a-f0-9-]{36}', '/:uuid', path)
            path = re.sub(r'/\$\{[^}]+\}', '/:id', path)
            return path.rstrip("/") or "/"
        
        be_norm = {normalize(e) for e in be_data['be_endpoints']}
        fe_norm = {normalize(c) for c in fe_data['fe_calls']}
        # Remove noise
        fe_norm.discard("/DELETE")
        fe_norm.discard("/GET")
        fe_norm.discard("/POST")
        fe_norm.discard("/PUT")
        
        matched = be_norm & fe_norm
        fe_only = fe_norm - be_norm
        be_only = be_norm - fe_norm
        
        print(f"\n  BE endpoints:     {len(be_data['be_endpoints'])}")
        print(f"  FE API calls:     {len(fe_data['fe_calls'])}")
        print(f"  Matched:          {len(matched)}")
        print(f"  FE-only (404?):   {len(fe_only)}")
        print(f"  BE-only (unused): {len(be_only)}")
        
        if fe_only:
            print(f"\n  ⚠️  FE calls WITHOUT BE endpoint (potential 404s):")
            for ep in sorted(fe_only):
                print(f"     → {ep}")
        
        if be_only:
            print(f"\n  ℹ️  BE endpoints NOT called by FE:")
            for ep in sorted(be_only)[:30]:
                print(f"     → {ep}")
            if len(be_only) > 30:
                print(f"     ... +{len(be_only) - 30} more")
        
        # Also check DB schema if BE has migrations
        db_data = extract_db_schema(be_dir)
        if db_data['table_count'] > 0:
            print(f"\n  🗄️  DB: {db_data['table_count']} tables, "
                  f"{db_data['total_columns']} columns, "
                  f"{len(db_data['migration_files'])} migrations")
        
        print(f"\n{'=' * 70}")
        return
    
    # --- Get changed files ---
    print(f"\n📋 Scanning git diff...")
    
    raw_files = get_diff_files(ref, args.staged, project_dir)
    stats = get_diff_stats(ref, args.staged, project_dir)
    
    if not raw_files:
        print("  ℹ️  No changes detected. Use --staged or provide a git ref.")
        print(f"  Example: python3 {sys.argv[0]} HEAD~1")
        print(f"           python3 {sys.argv[0]} main..feature-branch")
        return
    
    # Parse changes
    changes: list[FileChange] = []
    for raw in raw_files:
        parts = raw.split("\t")
        status_code = parts[0]
        
        if status_code == "A":
            change_type = ChangeType.ADDED
            path = parts[1]
        elif status_code == "M":
            change_type = ChangeType.MODIFIED
            path = parts[1]
        elif status_code == "D":
            change_type = ChangeType.DELETED
            path = parts[1]
        elif status_code == "R":
            change_type = ChangeType.MOVED
            path = parts[2]
            old_path = parts[1]
        else:
            change_type = ChangeType.UNKNOWN
            path = parts[-1]
        
        file_stats = stats.get(path, {"insertions": 0, "deletions": 0})
        
        change = FileChange(
            path=path,
            change_type=change_type,
            insertions=file_stats["insertions"],
            deletions=file_stats["deletions"],
            language=detect_language(path),
        )
        changes.append(change)
    
    print(f"  Found {len(changes)} changed file(s)")
    
    # --- Build dependency graph ---
    print(f"\n🔗 Building dependency graph...")
    
    graph = DependencyGraph(project_dir)
    graph.scan()
    
    print(f"  Scanned {len(graph.forward_deps)} files")
    print(f"  Found {len(graph.edges)} dependency edges")
    
    # --- Assess risks ---
    print(f"\n⚡ Assessing regression risks...")
    
    risks: list[RegressionRisk] = []
    for change in changes:
        blast = graph.get_blast_radius(change.path)
        risk = assess_risk(change, blast)
        risks.append(risk)
    
    critical_count = sum(1 for r in risks if r.risk == RiskLevel.CRITICAL)
    high_count = sum(1 for r in risks if r.risk == RiskLevel.HIGH)
    print(f"  {critical_count} critical, {high_count} high risk(s)")
    
    # --- API contract validation ---
    api_contracts = {}
    if args.api_check or args.full:
        print(f"\n🔌 Validating API contracts (FE vs BE)...")
        api_contracts = validate_api_contracts(project_dir)
        print(f"  BE: {api_contracts['be_count']} endpoints, "
              f"FE: {api_contracts['fe_count']} calls, "
              f"Matched: {api_contracts['match_count']}")
        if api_contracts["fe_only"]:
            print(f"  ⚠️  {len(api_contracts['fe_only'])} FE calls without BE endpoint")
    
    # --- DB schema ---
    db_schema = {}
    if args.db_check or args.full:
        print(f"\n🗄️  Extracting DB schema...")
        db_schema = extract_db_schema(project_dir)
        if db_schema["table_count"]:
            print(f"  {db_schema['table_count']} tables, "
                  f"{db_schema['total_columns']} columns")
        else:
            print(f"  No SQL migration files found")
    
    # --- Generate report ---
    report = generate_report(changes, risks, api_contracts, db_schema,
                             (ref or "staged") if args.staged else "uncommitted")
    print(f"\n{report}")
    
    # --- Exit code ---
    if critical_count > 0:
        sys.exit(2)  # Critical = blocking
    elif high_count > 0:
        sys.exit(1)  # High = warning
    else:
        sys.exit(0)  # Clean


if __name__ == "__main__":
    main()
