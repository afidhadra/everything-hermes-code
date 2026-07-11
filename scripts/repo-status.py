#!/usr/bin/env python3
"""
Everything Hermes Code — Multi-Repo Status

Scan all project directories for git status at a glance.
Shows: branch, uncommitted, unpushed, ahead/behind across all repos.

Usage:
    python3 repo-status.py
    python3 repo-status.py --root ~/Projects
    python3 repo-status.py --json
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ============================================================
# Config
# ============================================================

DEFAULT_ROOTS = [
    Path.home() / "Projects" / "Freelance",
    Path.home() / "Projects" / "Pemerintah",
    Path.home() / "Projects" / "Coding-Gabut",
    Path.home() / "Projects" / "Personal",
    Path.home() / "Projects",  # direct children too
]

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "__pycache__",
    ".venv", "venv", "target", "bin", "obj", ".idea", ".vscode",
    "test-results", "tmp", "coverage",
}

# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


# ============================================================
# Data Model
# ============================================================

@dataclass
class RepoInfo:
    name: str
    path: str
    branch: str = ""
    dirty: bool = False
    staged: bool = False
    untracked: int = 0
    unpushed: int = 0
    unpulled: int = 0
    ahead: int = 0
    behind: int = 0
    last_commit: str = ""
    last_commit_time: str = ""
    has_remote: bool = False
    issues: list[str] = field(default_factory=list)

    @property
    def needs_attention(self) -> bool:
        return (
            self.dirty or self.staged or self.unpushed > 0
            or self.untracked > 0 or bool(self.issues)
        )

    @property
    def attention_icon(self) -> str:
        if self.issues:
            return f"{RED}●{NC}"
        if self.dirty or self.staged or self.unpushed > 0:
            return f"{YELLOW}●{NC}"
        return f"{GREEN}●{NC}"


# ============================================================
# Git
# ============================================================

def git(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=str(cwd), timeout=10
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1, ""


def scan_repo(path: Path) -> Optional[RepoInfo]:
    """Scan a single git repo."""
    if not (path / ".git").is_dir():
        return None

    info = RepoInfo(
        name=path.name,
        path=str(path),
    )

    # Branch
    rc, branch = git(["rev-parse", "--abbrev-ref", "HEAD"], path)
    if rc != 0:
        info.issues.append("Not a valid git repo")
        return info
    info.branch = branch

    # Status porcelain
    rc, status = git(["status", "--porcelain"], path)
    if rc == 0 and status:
        for line in status.split("\n"):
            if not line.strip():
                continue
            code = line[:2]
            if code == "??":
                info.untracked += 1
            elif code.strip() in ("M", "A", "D", "R", "C"):
                info.staged = True
            elif "?" not in code:
                info.dirty = True

    # Remote
    rc, remote = git(["remote"], path)
    info.has_remote = bool(remote.strip())

    # Ahead/behind
    if info.has_remote and info.branch != "HEAD":
        rc, ab = git(
            ["rev-list", "--left-right", "--count",
             f"origin/{info.branch}...HEAD"],
            path
        )
        if rc == 0 and ab:
            parts = ab.split()
            if len(parts) == 2:
                info.behind = int(parts[0]) if parts[0].isdigit() else 0
                info.ahead = int(parts[1]) if parts[1].isdigit() else 0
                info.unpushed = info.ahead
                info.unpulled = info.behind

    # Last commit
    rc, last = git(["log", "-1", "--oneline"], path)
    if rc == 0:
        info.last_commit = last[:60]

    rc, last_time = git(
        ["log", "-1", "--format=%cr"], path
    )
    if rc == 0:
        info.last_commit_time = last_time

    return info


def find_repos(roots: list[Path], max_depth: int = 3) -> list[Path]:
    """Find all git repos under root directories."""
    repos = []
    seen = set()

    for root in roots:
        if not root.is_dir():
            continue

        # Check root itself
        if (root / ".git").is_dir():
            real = root.resolve()
            if real not in seen:
                repos.append(root)
                seen.add(real)
            continue

        # Scan children
        try:
            for path in root.rglob(".git"):
                if path.is_dir():
                    repo = path.parent
                    real = repo.resolve()

                    # Check depth
                    try:
                        rel = repo.relative_to(root)
                        depth = len(rel.parts)
                    except ValueError:
                        depth = 0
                    if depth > max_depth:
                        continue

                    # Skip dirs
                    if any(part in SKIP_DIRS for part in repo.parts):
                        continue

                    if real not in seen:
                        repos.append(repo)
                        seen.add(real)
        except (PermissionError, OSError):
            continue

    return sorted(repos, key=lambda p: str(p))


# ============================================================
# Report
# ============================================================

def print_report(repos: list[RepoInfo], detailed: bool = False):
    """Print multi-repo status dashboard."""
    if not repos:
        print(f"\n  {YELLOW}No git repositories found.{NC}")
        return

    # Group by parent directory
    groups: dict[str, list[RepoInfo]] = {}
    for repo in repos:
        parent = str(Path(repo.path).parent)
        groups.setdefault(parent, []).append(repo)

    print(f"\n{BOLD}{CYAN}{'═' * 70}{NC}")
    print(f"{BOLD}{CYAN}  MULTI-REPO STATUS{NC}")
    print(f"{BOLD}{CYAN}{'═' * 70}{NC}")
    print(f"  Repos: {len(repos)} | "
          f"Needs attention: {sum(1 for r in repos if r.needs_attention)} | "
          f"Clean: {sum(1 for r in repos if not r.needs_attention)}")
    print()

    for group_path in sorted(groups):
        group_repos = groups[group_path]
        group_name = Path(group_path).name or group_path

        print(f"  {BOLD}{DIM}━ {group_name}{NC}")

        for repo in sorted(group_repos, key=lambda r: r.name):
            line = f"    {repo.attention_icon} {BOLD}{repo.name:30s}{NC}"

            # Branch
            if repo.branch:
                branch_color = GREEN if repo.branch == "main" else YELLOW
                line += f" [{branch_color}{repo.branch}{NC}]"
            else:
                line += f" {DIM}[detached]{NC}"

            # Status indicators
            flags = []
            if repo.dirty:
                flags.append(f"{RED}M{NC}")
            if repo.staged:
                flags.append(f"{YELLOW}S{NC}")
            if repo.untracked > 0:
                flags.append(f"{DIM}?{repo.untracked}{NC}")
            if repo.unpushed > 0:
                flags.append(f"{YELLOW}↑{repo.unpushed}{NC}")
            if repo.unpulled > 0:
                flags.append(f"{CYAN}↓{repo.unpulled}{NC}")

            if flags:
                line += f" {' '.join(flags):15s}"
            else:
                line += f" {GREEN}clean{NC}        "

            # Last commit
            if repo.last_commit_time:
                line += f" {DIM}{repo.last_commit_time}{NC}"

            print(line)

            if detailed and repo.needs_attention:
                if repo.last_commit:
                    print(f"       {DIM}last: {repo.last_commit}{NC}")
                if repo.issues:
                    for issue in repo.issues:
                        print(f"       {RED}{issue}{NC}")

        print()

    # Summary
    needs = [r for r in repos if r.needs_attention]
    clean = [r for r in repos if not r.needs_attention]

    print(f"  {BOLD}{'─' * 66}{NC}")
    if needs:
        print(f"  {YELLOW}NEEDS ATTENTION ({len(needs)}):{NC}")
        for r in needs:
            reasons = []
            if r.dirty:
                reasons.append("modified")
            if r.staged:
                reasons.append("staged")
            if r.unpushed > 0:
                reasons.append(f"{r.unpushed} unpushed")
            if r.untracked > 0:
                reasons.append(f"{r.untracked} untracked")
            if r.issues:
                reasons.append(", ".join(r.issues))
            print(f"    {YELLOW}●{NC} {r.name}: {', '.join(reasons)}")
    else:
        print(f"  {GREEN}✓ All repos clean{NC}")

    if clean:
        print(f"\n  {DIM}Clean: {', '.join(r.name for r in clean)}{NC}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Multi-Repo Status — scan all projects at a glance"
    )
    parser.add_argument(
        "--root", type=str, action="append",
        help="Root directory to scan (can repeat). Defaults to ~/Projects/*"
    )
    parser.add_argument(
        "--detailed", "-v", action="store_true",
        help="Show last commit for repos needing attention"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--max-depth", type=int, default=3,
        help="Max directory depth to scan (default: 3)"
    )

    args = parser.parse_args()

    roots = [Path(r) for r in args.root] if args.root else DEFAULT_ROOTS

    # Find repos
    repo_paths = find_repos(roots, args.max_depth)

    # Scan each
    repos = []
    for path in repo_paths:
        info = scan_repo(path)
        if info:
            repos.append(info)

    if args.json:
        # JSON output
        data = []
        for r in repos:
            data.append({
                "name": r.name,
                "path": r.path,
                "branch": r.branch,
                "dirty": r.dirty,
                "staged": r.staged,
                "untracked": r.untracked,
                "unpushed": r.unpushed,
                "unpulled": r.unpulled,
                "last_commit": r.last_commit,
                "needs_attention": r.needs_attention,
            })
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_report(repos, detailed=args.detailed)

    # Exit code: 1 if any repo needs attention
    sys.exit(1 if any(r.needs_attention for r in repos) else 0)


if __name__ == "__main__":
    main()
