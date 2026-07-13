#!/usr/bin/env python3
"""
Everything Hermes Code — Deploy Coordinator

Coordinates multi-repo deployment with pre-deploy checks, docker compose
management, and post-deploy verification. Solves "lupa deploy FE" problem.

Usage:
    # Check what needs deploying
    python3 deploy.py --status

    # Full deploy (BE + FE + checks)
    python3 deploy.py --deploy all

    # Deploy specific repo
    python3 deploy.py --deploy be
    python3 deploy.py --deploy fe

    # Pre-deploy checks only (no deploy)
    python3 deploy.py --check

    # Dry run (show what would happen)
    python3 deploy.py --deploy all --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


# ============================================================
# Configuration — loaded from .ehc.yaml
# ============================================================

# Import config loader
import importlib.util
_ehc_config_path = Path(__file__).parent / "ehc_config.py"
_ehc_config_spec = importlib.util.spec_from_file_location("ehc_config", str(_ehc_config_path))
ehc_config = importlib.util.module_from_spec(_ehc_config_spec)
_ehc_config_spec.loader.exec_module(ehc_config)

def _load_config() -> dict:
    """Load project config from .ehc.yaml."""
    config = ehc_config.load_config()
    if not config:
        print("⚠️  No .ehc.yaml found. Create one from .ehc.yaml.example")
        print("   Using built-in defaults for demo.\n")
    return config

_CONFIG = _load_config()

# Resolve root from config or fallback
PROJECT_ROOT = Path(ehc_config.get_project_root(_CONFIG))

# Build repo list from config
REPOS: dict[str, dict] = {}
_rcfg = ehc_config.get_repos(_CONFIG)
for key, r in _rcfg.items():
    dir_path = r.get("dir", key)
    # Resolve relative to project root if not absolute
    if not Path(dir_path).is_absolute():
        dir_path = str(PROJECT_ROOT / dir_path)
    REPOS[key] = {
        "name": r.get("name", key),
        "dir": dir_path,
        "lang": r.get("lang", "unknown"),
        "health_url": r.get("health_url", ""),
        "container": r.get("container", ""),
        "compose_service": r.get("compose_service", ""),
    }

# Deploy config
_DEPLOY = ehc_config.get_deploy_config(_CONFIG)
DEPLOY_DIR = _DEPLOY.get("dir", "deploy")
COMPOSE_FILES = {
    "dev": _DEPLOY.get("compose_dev", "docker-compose.dev.yml"),
    "prod": _DEPLOY.get("compose_prod", "docker-compose.prod.yml"),
}

HEALTH_TIMEOUT = 60  # seconds to wait for health check
HEALTH_INTERVAL = 2  # seconds between retries


# ============================================================
# Colors
# ============================================================

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def ok(msg):    return f"  {GREEN}✓{NC} {msg}"
def fail(msg):  return f"  {RED}✗{NC} {msg}"
def warn(msg):  return f"  {YELLOW}!{NC} {msg}"
def info(msg):  return f"  {CYAN}→{NC} {msg}"
def head(msg):  return f"\n{BOLD}{CYAN}{'='*60}{NC}\n  {msg}\n{BOLD}{CYAN}{'='*60}{NC}"


# ============================================================
# Data Models
# ============================================================

class DeployStatus(Enum):
    UP_TO_DATE = "up_to date"
    NEEDS_DEPLOY = "needs deploy"
    UNKNOWN = "unknown"


@dataclass
class RepoState:
    key: str
    name: str
    path: Path
    branch: str = ""
    main_branch: str = "main"
    last_commit_main: str = ""
    last_commit_short: str = ""
    uncommitted: bool = False
    unpushed: int = 0
    ahead_of_main: int = 0
    deploy_status: DeployStatus = DeployStatus.UNKNOWN
    container_running: bool = False
    container_status: str = ""
    health_ok: bool = False
    health_detail: str = ""
    issues: list[str] = field(default_factory=list)


# ============================================================
# Git Operations
# ============================================================

def git(args: list[str], cwd: Path) -> tuple[int, str]:
    """Run git command, return (exit_code, output)."""
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=str(cwd), timeout=30
        )
        return r.returncode, r.stdout.strip() + r.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1, ""


def get_repo_state(key: str, config: dict, project_root: Path) -> RepoState:
    """Gather full state of a repo."""
    repo_path = project_root / config["dir"]
    state = RepoState(
        key=key,
        name=config["name"],
        path=repo_path,
    )

    if not repo_path.is_dir():
        state.issues.append("Repository directory not found")
        return state

    # Branch
    rc, branch = git(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)
    state.branch = branch

    # Uncommitted changes
    rc, status = git(["status", "--porcelain"], repo_path)
    state.uncommitted = bool(status.strip())

    # Unpushed commits
    rc, unpushed = git(["log", "@{u}..HEAD", "--oneline"], repo_path)
    state.unpushed = len([l for l in unpushed.split("\n") if l.strip()])

    # Last commit on main
    rc, main_hash = git(["rev-parse", f"refs/heads/{state.main_branch}"], repo_path)
    state.last_commit_main = main_hash[:12]

    rc, short = git(["log", "-1", "--oneline", f"refs/heads/{state.main_branch}"], repo_path)
    state.last_commit_short = short

    # Check if current branch is ahead of main
    rc, ahead = git(
        ["rev-list", "--count", f"refs/heads/{state.main_branch}..HEAD"], repo_path
    )
    try:
        state.ahead_of_main = int(ahead)
    except ValueError:
        state.ahead_of_main = 0

    # Docker container status
    state.container_running = check_container(config.get("container", ""))

    # Health check
    health_url = config.get("health_url", "")
    if health_url and state.container_running:
        state.health_ok, state.health_detail = check_health(health_url)

    return state


def check_container(container_name: str) -> bool:
    """Check if a Docker container is running."""
    if not container_name:
        return False
    try:
        r = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}",
             container_name],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip() == "true"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_health(url: str) -> tuple[bool, str]:
    """Check if a URL responds with 200."""
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "5", url],
            capture_output=True, text=True, timeout=10
        )
        code = r.stdout.strip()
        if code == "200":
            return True, "HTTP 200"
        elif code:
            return False, f"HTTP {code}"
        else:
            return False, "No response"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Curl failed"


def get_container_image_version(container_name: str) -> str:
    """Get the image hash/tag of a running container."""
    try:
        r = subprocess.run(
            ["docker", "inspect", "--format", "{{.Image}}", container_name],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()[:19]
    except Exception:
        return ""


# ============================================================
# Deploy Operations
# ============================================================

def docker_compose_cmd(
    compose_file: Path, service: str, action: str, dry_run: bool = False
) -> tuple[bool, str]:
    """Run docker compose command."""
    cmd = ["docker", "compose", "-f", str(compose_file), action, service]

    if dry_run:
        return True, " ".join(cmd)

    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(compose_file.parent)
        )
        success = r.returncode == 0
        output = (r.stdout + r.stderr).strip()
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Docker compose timed out (120s)"


def deploy_repo(
    key: str,
    config: dict,
    project_root: Path,
    compose_file: str = "dev",
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Rebuild and restart a single repo via docker compose."""
    deploy_path = project_root / DEPLOY_DIR
    compose_path = deploy_path / COMPOSE_FILES.get(compose_file, COMPOSE_FILES["dev"])

    if not compose_path.exists():
        return False, f"Compose file not found: {compose_path}"

    service = config.get("compose_service", key)
    container = config.get("container", "")

    steps = []

    # Step 1: Pull latest code
    if not dry_run:
        repo_path = project_root / config["dir"]
        git(["checkout", "main"], repo_path)
        rc, pull_output = git(["pull", "origin", "main"], repo_path)
        steps.append(f"git pull: {'OK' if rc == 0 else 'FAIL'}")
        if rc != 0:
            return False, "\n".join(steps) + f"\n{pull_output}"

    # Step 2: Rebuild container
    if not dry_run:
        success, build_output = docker_compose_cmd(
            compose_path, service, "build", dry_run
        )
        steps.append(f"docker build: {'OK' if success else 'FAIL'}")
        if not success:
            return False, "\n".join(steps) + f"\n{build_output}"
    else:
        steps.append(f"docker build: [DRY RUN]")

    # Step 3: Restart container
    if not dry_run:
        # Up with --force-recreate
        cmd = ["docker", "compose", "-f", str(compose_path),
               "up", "-d", "--force-recreate", service]
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                cwd=str(compose_path.parent)
            )
            success = r.returncode == 0
            steps.append(f"docker up: {'OK' if success else 'FAIL'}")
            if not success:
                return False, "\n".join(steps) + f"\n{r.stderr}"
        except subprocess.TimeoutExpired:
            steps.append("docker up: TIMEOUT")
            return False, "\n".join(steps)
    else:
        steps.append(f"docker up: [DRY RUN]")

    # Step 4: Health check
    health_url = config.get("health_url", "")
    if health_url and not dry_run:
        steps.append("Waiting for health check...")
        healthy = wait_for_health(health_url, HEALTH_TIMEOUT)
        if healthy:
            steps.append(f"health: {GREEN}OK{NC}")
        else:
            steps.append(f"health: {RED}TIMEOUT{NC}")
            return False, "\n".join(steps)
    elif dry_run:
        steps.append("health: [DRY RUN]")

    return True, "\n".join(steps)


def wait_for_health(url: str, timeout: int) -> bool:
    """Wait for a URL to return 200."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        healthy, _ = check_health(url)
        if healthy:
            return True
        time.sleep(HEALTH_INTERVAL)
    return False


# ============================================================
# Pre-Deploy Checks
# ============================================================

def run_pre_deploy_checks(
    states: dict[str, RepoState], project_root: Path
) -> tuple[bool, list[str]]:
    """Run pre-deploy validation. Returns (can_proceed, messages)."""
    messages = []
    can_proceed = True

    # Check 1: Uncommitted changes
    for key, state in states.items():
        if state.uncommitted:
            messages.append(
                fail(f"{state.name}: uncommitted changes on {state.branch}")
            )
            can_proceed = False

    # Check 2: Unpushed commits
    for key, state in states.items():
        if state.unpushed > 0:
            messages.append(
                warn(f"{state.name}: {state.unpushed} unpushed commit(s)")
            )

    # Check 3: Not on main branch
    for key, state in states.items():
        if state.branch and state.branch != "main":
            messages.append(
                warn(f"{state.name}: on '{state.branch}', not 'main'")
            )

    # Check 4: Docker available
    try:
        subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10
        )
        messages.append(ok("Docker daemon available"))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        messages.append(fail("Docker daemon not available"))
        can_proceed = False

    # Check 5: Compose file exists
    for env_name, compose_file in COMPOSE_FILES.items():
        compose_path = project_root / DEPLOY_DIR / compose_file
        if compose_path.exists():
            messages.append(ok(f"Compose file: {compose_file}"))
        else:
            messages.append(
                warn(f"Compose file missing: {compose_file}")
            )

    return can_proceed, messages


# ============================================================
# Report
# ============================================================

def print_status(states: dict[str, RepoState], project_root: Path):
    """Print deployment status dashboard."""
    print(head("DEPLOY STATUS DASHBOARD"))
    print(f"\n  Project: {project_root}")
    print(f"  Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    for key, state in states.items():
        cfg = REPOS[key]
        print(f"  {BOLD}{state.name}{NC}")
        print(f"  {'─' * 50}")

        if state.issues:
            for issue in state.issues:
                print(f"    {fail(issue)}")
            print()
            continue

        # Branch
        branch_icon = ok if state.branch == "main" else warn
        print(f"    {branch_icon(f'Branch: {state.branch}')}")

        # Uncommitted
        if state.uncommitted:
            print(f"    {warn('Uncommitted changes: YES')}")
        else:
            print(f"    {ok('Uncommitted changes: none')}")

        # Unpushed
        if state.unpushed > 0:
            print(f"    {warn(f'Unpushed: {state.unpushed} commit(s)')}")
        else:
            print(f"    {ok('All commits pushed')}")

        # Main status
        if state.last_commit_short:
            print(f"    {ok(f'main: {state.last_commit_short}')}")

        # Docker
        container_name = cfg.get("container", "?")
        if state.container_running:
            print(f"    {ok(f'Container: {container_name} running')}")
        else:
            print(f"    {fail(f'Container: {container_name} STOPPED')}")

        # Health
        if state.health_ok:
            print(f"    {ok(f'Health: {state.health_detail}')}")
        elif state.container_running:
            print(f"    {warn(f'Health: {state.health_detail}')}")
        else:
            print(f"    {DIM}Health: skipped (container not running){NC}")

        print()

    # Summary
    all_healthy = all(s.health_ok for s in states.values())
    all_pushed = all(s.unpushed == 0 for s in states.values())
    all_clean = all(not s.uncommitted for s in states.values())
    all_main = all(s.branch == "main" for s in states.values())

    print(f"  {BOLD}SUMMARY{NC}")
    print(f"  {'─' * 50}")

    if all_healthy:
        print(f"    {ok('All services healthy')}")
    else:
        print(f"    {fail('Some services unhealthy')}")

    if all_pushed and all_clean and all_main:
        print(f"    {ok('All repos clean and pushed to main')}")
    else:
        if not all_pushed:
            print(f"    {warn('Some repos have unpushed commits')}")
        if not all_clean:
            print(f"    {warn('Some repos have uncommitted changes')}")
        if not all_main:
            print(f"    {warn('Some repos not on main branch')}")

    # Deploy recommendation
    print()
    needs_deploy = False
    for key, state in states.items():
        if state.unpushed > 0 or state.ahead_of_main > 0:
            needs_deploy = True
            break

    if needs_deploy:
        print(f"    {YELLOW}⚠️  Repos have unpushed changes — "
              f"push before deploying{NC}")
    elif not all_healthy:
        print(f"    {YELLOW}⚠️  Some services down — "
              f"consider: python3 deploy.py --deploy all{NC}")
    else:
        print(f"    {GREEN}✓ Everything up to date and healthy{NC}")


def print_deploy_result(
    key: str, success: bool, detail: str, dry_run: bool = False
):
    """Print deploy result for a single repo."""
    cfg = REPOS[key]
    mode = "[DRY RUN] " if dry_run else ""
    icon = f"{GREEN}✓{NC}" if success else f"{RED}✗{NC}"
    status = "SUCCESS" if success else "FAILED"

    print(f"\n  {icon} {mode}{cfg['name']}: {status}")
    if detail:
        for line in detail.split("\n"):
            print(f"    {line}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Coordinator — multi-repo deploy with checks"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show deployment status dashboard"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Run pre-deploy checks without deploying"
    )
    parser.add_argument(
        "--deploy",
        choices=["all", "be", "fe"],
        help="Deploy specific repo or all"
    )
    parser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="dev",
        help="Deployment environment (default: dev)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=str(PROJECT_ROOT),
        help=f"Project root (default: {PROJECT_ROOT})"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip pre-deploy checks and deploy anyway"
    )

    args = parser.parse_args()
    project_root = Path(args.project_root)

    # Default action: status
    if not any([args.status, args.check, args.deploy]):
        args.status = True

    # Gather repo states
    if args.status or args.check or args.deploy:
        states = {}
        for key, config in REPOS.items():
            states[key] = get_repo_state(key, config, project_root)

    # --- Status ---
    if args.status:
        print_status(states, project_root)
        return

    # --- Pre-deploy checks ---
    if args.check or args.deploy:
        print(head("PRE-DEPLOY CHECKS"))
        can_proceed, messages = run_pre_deploy_checks(states, project_root)
        for msg in messages:
            print(msg)

        if args.check:
            print()
            if can_proceed:
                print(f"  {GREEN}✓ Pre-deploy checks passed{NC}")
            else:
                print(f"  {RED}✗ Pre-deploy checks FAILED{NC}")
            return

        if args.deploy:
            if not can_proceed and not args.force:
                print(f"\n  {RED}✗ Pre-deploy checks failed.{NC}")
                print(f"  {YELLOW}  Use --force to deploy anyway.{NC}")
                return
            elif not can_proceed and args.force:
                print(f"\n  {YELLOW}! --force: deploying despite check failures{NC}")

    # --- Deploy ---
    if args.deploy:
        repos_to_deploy = (
            list(REPOS.keys()) if args.deploy == "all" else [args.deploy]
        )

        print(head(f"DEPLOY: {', '.join(repos_to_deploy).upper()}"))

        all_success = True
        for key in repos_to_deploy:
            config = REPOS[key]
            print(f"\n  {BOLD}Deploying {config['name']}...{NC}")

            success, detail = deploy_repo(
                key, config, project_root,
                compose_file=args.env, dry_run=args.dry_run
            )
            print_deploy_result(key, success, detail, args.dry_run)

            if not success:
                all_success = False
                print(f"\n  {RED}Stopping deployment — "
                      f"{config['name']} failed.{NC}")
                break

        # Summary
        print(head("DEPLOY SUMMARY"))
        if all_success:
            if args.dry_run:
                print(f"\n  {CYAN}Dry run complete — no changes made.{NC}")
            else:
                print(f"\n  {GREEN}✓ All repos deployed successfully.{NC}")
                print(f"  Verify: python3 deploy.py --status")
        else:
            print(f"\n  {RED}✗ Deployment failed.{NC}")
            print(f"  Check logs: docker logs <container-name>")

        # Exit code
        sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
