#!/usr/bin/env python3
"""
Everything Hermes Code — Unified Dashboard

Single command that shows everything at a glance:
  - Docker container health
  - Multi-repo git status
  - Service health checks
  - System resources (CPU, RAM, disk)

Usage:
    python3 ehc.py                  # full dashboard (auto-detect config)
    python3 ehc.py --config X.yaml  # use specific config
    python3 ehc.py --watch          # refresh every 30s
    python3 ehc.py --json           # JSON output
    python3 ehc.py --list           # list available configs
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Import config loader
sys.path.insert(0, str(Path(__file__).parent))
import ehc_config

# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

LINE = "─" * 66
DLINE = "═" * 66


# ============================================================
# Docker
# ============================================================

def get_docker_status() -> list[dict]:
    """Get all containers."""
    try:
        r = subprocess.run(
            ["docker", "ps", "-a", "--format",
             "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    containers = []
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        name = parts[0]
        status = parts[1] if len(parts) > 1 else "unknown"
        is_running = "up" in status.lower() or "Up" in status

        # Quick health check for known URLs
        health = ""
        health_urls = {
            "frozen-pos-api-dev": ("http://localhost:8080/api/v1/health", True),
            "frozen-pos-frontend-dev": ("http://localhost:5173", False),
            "sonarqube": ("http://localhost:9000/api/system/status", True),
        }
        if name in health_urls and is_running:
            url, quiet = health_urls[name]
            try:
                hr = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     "--max-time", "3", url],
                    capture_output=True, text=True, timeout=5
                )
                code = hr.stdout.strip()
                if code == "200":
                    health = "OK"
                elif code:
                    health = f"HTTP {code}"
                else:
                    health = "DOWN"
            except Exception:
                health = "?"

        containers.append({
            "name": name,
            "status": status,
            "running": is_running,
            "health": health,
        })

    return containers


def render_docker(containers: list[dict]) -> list[str]:
    """Render docker section."""
    lines = [f"  {BOLD}DOCKER CONTAINERS{NC}"]
    lines.append(f"  {DIM}{LINE}{NC}")

    running = [c for c in containers if c["running"]]
    stopped = [c for c in containers if not c["running"]]

    for c in running:
        icon = GREEN + "●" + NC
        health_str = ""
        if c["health"] == "OK":
            health_str = f" [{GREEN}OK{NC}]"
        elif c["health"] and c["health"] not in ("", "?"):
            health_str = f" [{YELLOW}{c['health']}{NC}]"

        # Shorten status
        status_short = c["status"].replace("Up ", "↑").replace("Exited ", "↓ ")
        lines.append(f"    {icon} {c['name']:30s} {DIM}{status_short[:25]}{NC}{health_str}")

    for c in stopped:
        icon = RED + "●" + NC
        lines.append(f"    {icon} {c['name']:30s} {RED}STOPPED{NC}")

    summary = f"{GREEN}{len(running)} up{NC}"
    if stopped:
        summary += f", {RED}{len(stopped)} down{NC}"
    lines.append(f"    {DIM}Total: {len(containers)} ({summary}{DIM}){NC}")
    return lines


# ============================================================
# Git Repos (frozen-pos focus + quick scan)
# ============================================================

def git(args: list[str], cwd: str) -> str:
    try:
        r = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, cwd=cwd, timeout=5
        )
        return (r.stdout + r.stderr).strip()
    except Exception:
        return ""


def get_repo_status(path: str, name: str) -> dict:
    """Quick status for a single repo."""
    info = {"name": name, "path": path, "branch": "", "dirty": False,
            "unpushed": 0, "last": "", "ok": True}

    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], path)
    info["branch"] = branch

    status = git(["status", "--porcelain"], path)
    info["dirty"] = bool(status.strip())

    # Unpushed
    if branch and branch != "HEAD":
        ahead = git(["rev-list", "--count",
                      f"origin/{branch}...HEAD"], path)
        if ahead.isdigit():
            info["unpushed"] = int(ahead)

    last = git(["log", "-1", "--oneline"], path)
    info["last"] = last[:50]

    return info


def render_repos(repos: list[dict]) -> list[str]:
    """Render repo section."""
    lines = [f"\n  {BOLD}FROZEN-POS REPOS{NC}"]
    lines.append(f"  {DIM}{LINE}{NC}")

    for r in repos:
        # Icon
        if r["dirty"]:
            icon = YELLOW + "●" + NC
        elif r["unpushed"] > 0:
            icon = YELLOW + "●" + NC
        else:
            icon = GREEN + "●" + NC

        # Branch
        bcolor = GREEN if r["branch"] == "main" else YELLOW
        branch_str = f"[{bcolor}{r['branch']}{NC}]"

        # Flags
        flags = []
        if r["dirty"]:
            flags.append(f"{RED}M{NC}")
        if r["unpushed"] > 0:
            flags.append(f"{YELLOW}↑{r['unpushed']}{NC}")
        flag_str = " ".join(flags) if flags else f"{GREEN}clean{NC}"

        lines.append(
            f"    {icon} {r['name']:22s} {branch_str:15s} {flag_str}"
        )
        if r["last"]:
            lines.append(f"      {DIM}{r['last']}{NC}")

    return lines


# ============================================================
# System Resources
# ============================================================

def get_system_info() -> dict:
    """Get CPU, RAM, disk usage."""
    info = {"cpu": "", "mem_total": "", "mem_used": "", "mem_pct": 0,
            "disk_total": "", "disk_used": "", "disk_pct": 0,
            "load": ""}

    # Memory (Linux /proc/meminfo)
    try:
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = int(parts[1].strip().split()[0])

        total = meminfo.get("MemTotal", 0) // 1024  # MB
        avail = meminfo.get("MemAvailable", 0) // 1024
        used = total - avail
        pct = (used / total * 100) if total else 0

        info["mem_total"] = f"{total / 1024:.1f}GB"
        info["mem_used"] = f"{used / 1024:.1f}GB"
        info["mem_pct"] = round(pct)
    except Exception:
        pass

    # Disk (root partition)
    try:
        r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                info["disk_total"] = parts[1]
                info["disk_used"] = parts[2]
                info["disk_pct"] = int(parts[4].rstrip("%"))
    except Exception:
        pass

    # Load average
    try:
        load = os.getloadavg()
        info["load"] = f"{load[0]:.1f} {load[1]:.1f} {load[2]:.1f}"
    except Exception:
        pass

    # CPU usage (quick sample)
    try:
        r = subprocess.run(
            ["grep", "-c", "^processor", "/proc/cpuinfo"],
            capture_output=True, text=True, timeout=5
        )
        info["cpu"] = f"{r.stdout.strip()} cores"
    except Exception:
        pass

    return info


def render_system(info: dict) -> list[str]:
    """Render system resources section."""
    lines = [f"\n  {BOLD}SYSTEM{NC}"]
    lines.append(f"  {DIM}{LINE}{NC}")

    # Memory
    mem_pct = info["mem_pct"]
    mem_color = GREEN if mem_pct < 70 else (YELLOW if mem_pct < 85 else RED)
    mem_bar = make_bar(mem_pct)
    lines.append(
        f"    RAM  {mem_bar} {mem_color}{info['mem_used']}/{info['mem_total']}{NC} ({mem_pct}%)"
    )

    # Disk
    disk_pct = info["disk_pct"]
    disk_color = GREEN if disk_pct < 70 else (YELLOW if disk_pct < 85 else RED)
    disk_bar = make_bar(disk_pct)
    lines.append(
        f"    Disk {disk_bar} {disk_color}{info['disk_used']}/{info['disk_total']}{NC} ({disk_pct}%)"
    )

    # Load
    if info["load"]:
        lines.append(f"    Load {info['load']}  {DIM}({info['cpu']}){NC}")

    return lines


def make_bar(pct: int, width: int = 20) -> str:
    """Make a text progress bar."""
    filled = int(pct / 100 * width)
    color = GREEN if pct < 70 else (YELLOW if pct < 85 else RED)
    bar = color + "█" * filled + DIM + "░" * (width - filled) + NC
    return bar


# ============================================================
# Deploy Status
# ============================================================

def get_service_health(services: list) -> list[str]:
    """Quick health check for configured services."""
    if not services:
        # Fallback defaults
        services = [
            {"name": "API", "url": "http://localhost:8080/api/v1/health", "type": "http"},
            {"name": "Frontend", "url": "http://localhost:5173", "type": "http"},
            {"name": "PostgreSQL", "url": "localhost:5433", "type": "tcp"},
            {"name": "Redis", "url": "localhost:6380", "type": "tcp"},
            {"name": "pgAdmin", "url": "localhost:5052", "type": "tcp"},
        ]

    lines = [f"\n  {BOLD}SERVICE HEALTH{NC}"]
    lines.append(f"  {DIM}{LINE}{NC}")

    for svc in services:
        name = svc.get("name", "?")
        endpoint = svc.get("url", "")
        stype = svc.get("type", "http")

        if stype == "http":
            try:
                r = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                     "--max-time", "3", endpoint],
                    capture_output=True, text=True, timeout=5
                )
                code = r.stdout.strip()
                if code == "200":
                    lines.append(f"    {GREEN}✓{NC} {name:15s} {DIM}{endpoint}{NC} [{GREEN}200{NC}]")
                elif code:
                    lines.append(f"    {RED}✗{NC} {name:15s} {DIM}{endpoint}{NC} [{RED}{code}{NC}]")
                else:
                    lines.append(f"    {RED}✗{NC} {name:15s} {DIM}{endpoint}{NC} [{RED}DOWN{NC}]")
            except Exception:
                lines.append(f"    {RED}?{NC} {name:15s} {DIM}{endpoint}{NC} [{RED}ERR{NC}]")
        elif stype == "tcp":
            import socket
            host, port = endpoint.split(":")
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex((host, int(port)))
                s.close()
                if result == 0:
                    lines.append(f"    {GREEN}✓{NC} {name:15s} {DIM}{endpoint}{NC} [{GREEN}OPEN{NC}]")
                else:
                    lines.append(f"    {RED}✗{NC} {name:15s} {DIM}{endpoint}{NC} [{RED}CLOSED{NC}]")
            except Exception:
                lines.append(f"    {RED}?{NC} {name:15s} {DIM}{endpoint}{NC} [{RED}ERR{NC}]")

    return lines


# ============================================================
# Dashboard
# ============================================================

def render_dashboard(config: dict):
    """Render full dashboard using config."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    project_name = config.get("project", {}).get("name", "EHC")
    project_root = ehc_config.get_project_root(config)
    services = ehc_config.get_services(config)
    repos_cfg = ehc_config.get_repos(config)

    print(f"\n{BOLD}{CYAN}{DLINE}{NC}")
    print(f"{BOLD}{CYAN}  {project_name} DASHBOARD{NC}  {DIM}{now}{NC}")
    print(f"{BOLD}{CYAN}{DLINE}{NC}")

    # Docker
    containers = get_docker_status()
    for line in render_docker(containers):
        print(line)

    # Repos from config
    repos = []
    for key, rcfg in repos_cfg.items():
        repo_path = os.path.join(project_root, os.path.basename(rcfg.get("dir", key)))
        # Try path as-is first (in case it's absolute), then relative to project root
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            repo_path = rcfg.get("dir", key)
            repo_path = os.path.expanduser(repo_path)
        if os.path.isdir(os.path.join(repo_path, ".git")):
            repos.append(get_repo_status(repo_path, rcfg.get("name", key)))

    if repos:
        for line in render_repos(repos):
            print(line)

    # Service health from config
    for line in get_service_health(services):
        print(line)

    # System
    sysinfo = get_system_info()
    for line in render_system(sysinfo):
        print(line)

    # Footer
    print(f"\n  {DIM}{LINE}{NC}")
    issues = sum(1 for c in containers if not c["running"])
    repo_issues = sum(1 for r in repos if r["dirty"] or r["unpushed"] > 0)

    if issues == 0 and repo_issues == 0:
        print(f"  {GREEN}✓ All systems operational{NC}")
    else:
        parts = []
        if issues:
            parts.append(f"{RED}{issues} container(s) down{NC}")
        if repo_issues:
            parts.append(f"{YELLOW}{repo_issues} repo(s) need attention{NC}")
        print(f"  {' | '.join(parts)}")

    print(f"  {BOLD}{CYAN}{DLINE}{NC}\n")


def render_json(config: dict):
    """Output JSON."""
    project_root = ehc_config.get_project_root(config)
    repos_cfg = ehc_config.get_repos(config)

    data = {
        "timestamp": datetime.now().isoformat(),
        "docker": get_docker_status(),
        "repos": [],
        "system": get_system_info(),
    }
    for key, rcfg in repos_cfg.items():
        repo_path = os.path.join(project_root, os.path.basename(rcfg.get("dir", key)))
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            repo_path = os.path.expanduser(rcfg.get("dir", key))
        if os.path.isdir(os.path.join(repo_path, ".git")):
            data["repos"].append(get_repo_status(repo_path, rcfg.get("name", key)))
    print(json.dumps(data, indent=2))


# ============================================================
# Main
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="EHC Dashboard — unified status at a glance"
    )
    parser.add_argument(
        "--config", "-c", type=str, default=None,
        help="Path to .ehc.yaml config file (auto-detected by default)"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List available .ehc.yaml configs under ~/Projects"
    )
    parser.add_argument(
        "--watch", "-w", action="store_true",
        help="Auto-refresh every 30 seconds"
    )
    parser.add_argument(
        "--interval", type=int, default=30,
        help="Watch interval (default: 30s)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        configs = ehc_config.list_available_configs()
        if configs:
            print(f"\n  {BOLD}Available .ehc.yaml configs:{NC}")
            for c in configs:
                print(f"    {GREEN}→{NC} {c}")
        else:
            print(f"\n  {YELLOW}No .ehc.yaml files found under ~/Projects{NC}")
            print(f"  Copy .ehc.yaml template to your project root.")
        return

    # Load config
    config = ehc_config.load_config(args.config)

    if args.json:
        render_json(config)
        return

    if args.watch:
        try:
            while True:
                subprocess.run(["clear"])
                render_dashboard(config)
                print(f"  {DIM}Refreshing in {args.interval}s... (Ctrl+C to stop){NC}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n  {GREEN}Stopped.{NC}")
    else:
        render_dashboard(config)

        # Exit code
        containers = get_docker_status()
        down = sum(1 for c in containers if not c["running"])
        sys.exit(1 if down > 0 else 0)


if __name__ == "__main__":
    main()
