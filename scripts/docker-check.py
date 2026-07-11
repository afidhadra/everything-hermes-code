#!/usr/bin/env python3
"""
Everything Hermes Code — Docker Health Check

Monitor all running Docker containers, detect dead/unhealthy ones,
check resource usage, and optionally restart dead containers.

Usage:
    python3 docker-check.py
    python3 docker-check.py --restart-dead
    python3 docker-check.py --watch
    python3 docker-check.py --json
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

# Known containers (for friendly names + auto-restart priority)
KNOWN_CONTAINERS = {
    "frozen-pos-api-dev": {
        "friendly": "Frozen POS API",
        "health_url": "http://localhost:8080/api/v1/health",
        "auto_restart": True,
        "priority": 1,
    },
    "frozen-pos-frontend-dev": {
        "friendly": "Frozen POS Frontend",
        "health_url": "http://localhost:5173",
        "auto_restart": True,
        "priority": 1,
    },
    "frozen-pos-postgres-dev": {
        "friendly": "Frozen POS PostgreSQL",
        "auto_restart": True,
        "priority": 2,
    },
    "frozen-pos-redis-dev": {
        "friendly": "Frozen POS Redis",
        "auto_restart": True,
        "priority": 2,
    },
    "sonarqube": {
        "friendly": "SonarQube",
        "health_url": "http://localhost:9000/api/system/status",
        "auto_restart": False,
        "priority": 3,
    },
    "9router": {
        "friendly": "9Router Proxy",
        "auto_restart": False,
        "priority": 3,
    },
    "ogham-postgres": {
        "friendly": "Ogham PostgreSQL",
        "auto_restart": False,
        "priority": 3,
    },
}


@dataclass
class ContainerInfo:
    name: str
    image: str
    status: str  # "running", "exited", "restarting", etc
    health: str = ""  # "healthy", "unhealthy", "starting", ""
    cpu: str = ""
    memory: str = ""
    net_io: str = ""
    ports: str = ""
    uptime: str = ""
    friendly: str = ""
    priority: int = 99
    needs_attention: bool = False
    issue: str = ""

    @property
    def is_running(self) -> bool:
        return "running" in self.status.lower() or "up" in self.status.lower()

    @property
    def status_icon(self) -> str:
        if not self.is_running:
            return f"{RED}●{NC}"
        if self.health == "unhealthy":
            return f"{RED}●{NC}"
        if self.health == "starting":
            return f"{YELLOW}●{NC}"
        if self.needs_attention:
            return f"{YELLOW}●{NC}"
        return f"{GREEN}●{NC}"


def run_docker(args: list[str], timeout: int = 15) -> tuple[int, str]:
    """Run docker command."""
    try:
        r = subprocess.run(
            ["docker"] + args,
            capture_output=True, text=True, timeout=timeout
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1, "Docker not available"


def get_all_containers() -> list[ContainerInfo]:
    """Get all containers (running and stopped)."""
    rc, output = run_docker([
        "ps", "-a",
        "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}",
    ])

    if rc != 0 or not output:
        return []

    containers = []
    for line in output.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue

        name = parts[0]
        image = parts[1]
        status = parts[2]
        ports = parts[3] if len(parts) > 3 else ""

        known = KNOWN_CONTAINERS.get(name, {})
        info = ContainerInfo(
            name=name,
            image=image,
            status=status,
            ports=ports,
            friendly=known.get("friendly", name),
            priority=known.get("priority", 99),
        )

        # Parse health from status
        if "(healthy)" in status:
            info.health = "healthy"
        elif "(unhealthy)" in status:
            info.health = "unhealthy"
            info.needs_attention = True
            info.issue = "Container unhealthy"
        elif "(starting)" in status:
            info.health = "starting"
            info.needs_attention = True
            info.issue = "Container starting"

        if not info.is_running:
            info.needs_attention = True
            if not info.issue:
                info.issue = "Container stopped"

        containers.append(info)

    return containers


def get_container_stats(name: str) -> dict:
    """Get CPU/memory stats for a container."""
    rc, output = run_docker([
        "stats", "--no-stream",
        "--format",
        "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}",
        name
    ], timeout=10)

    if rc != 0 or not output.strip():
        return {}

    parts = output.strip().split("\t")
    if len(parts) >= 3:
        return {
            "cpu": parts[0].strip(),
            "memory": parts[1].strip(),
            "net_io": parts[2].strip(),
        }
    return {}


def check_http_health(url: str) -> tuple[bool, str]:
    """Check HTTP health endpoint."""
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
        return False, "No response"
    except Exception:
        return False, "Curl failed"


def restart_container(name: str) -> bool:
    """Restart a container."""
    rc, output = run_docker(["restart", name], timeout=60)
    return rc == 0


def print_report(containers: list[ContainerInfo], show_stats: bool = False):
    """Print container health dashboard."""
    # Sort by priority then name
    containers.sort(key=lambda c: (c.priority, c.name))

    print(f"\n{BOLD}{CYAN}{'═' * 70}{NC}")
    print(f"{BOLD}{CYAN}  DOCKER HEALTH CHECK{NC}")
    print(f"{BOLD}{CYAN}{'═' * 70}{NC}")

    running = [c for c in containers if c.is_running]
    stopped = [c for c in containers if not c.is_running]
    unhealthy = [c for c in containers if c.health == "unhealthy"]

    print(f"  Total: {len(containers)} | "
          f"{GREEN}Running: {len(running)}{NC} | "
          f"{RED}Stopped: {len(stopped)}{NC} | "
          f"{RED}Unhealthy: {len(unhealthy)}{NC}")
    print()

    # Running containers
    if running:
        print(f"  {BOLD}RUNNING{NC}")
        print(f"  {DIM}{'─' * 66}{NC}")

        for c in running:
            line = f"    {c.status_icon} {BOLD}{c.friendly:25s}{NC}"
            line += f" {DIM}{c.name}{NC}"

            if c.health:
                hc = GREEN if c.health == "healthy" else YELLOW
                line += f" [{hc}{c.health}{NC}]"
            else:
                line += f" {DIM}[no healthcheck]{NC}"

            # Uptime from status
            line += f" {DIM}{c.status.split(' ')[1:3][0] if ' ' in c.status else ''}{NC}"

            print(line)

            if show_stats and c.is_running:
                stats = get_container_stats(c.name)
                if stats:
                    print(f"       {DIM}CPU: {stats.get('cpu', '?')}  "
                          f"Mem: {stats.get('memory', '?')}  "
                          f"Net: {stats.get('net_io', '?')}{NC}")

            # HTTP health for known containers
            known = KNOWN_CONTAINERS.get(c.name, {})
            if known.get("health_url"):
                healthy, detail = check_http_health(known["health_url"])
                if healthy:
                    print(f"       {GREEN}✓ {known['health_url']}{NC}")
                else:
                    print(f"       {YELLOW}! {known['health_url']} → "
                          f"{detail}{NC}")
                    if not c.needs_attention:
                        c.needs_attention = True
                        c.issue = f"HTTP health: {detail}"

        print()

    # Stopped containers
    if stopped:
        print(f"  {BOLD}STOPPED{NC}")
        print(f"  {DIM}{'─' * 66}{NC}")
        for c in stopped:
            line = f"    {c.status_icon} {BOLD}{c.friendly:25s}{NC}"
            line += f" {DIM}{c.name}{NC} [{RED}{c.status}{NC}]"

            known = KNOWN_CONTAINERS.get(c.name, {})
            if known.get("auto_restart"):
                line += f" {YELLOW}(auto-restartable){NC}"

            print(line)
        print()

    # Summary
    issues = [c for c in containers if c.needs_attention]
    print(f"  {BOLD}{'─' * 66}{NC}")
    if issues:
        print(f"  {YELLOW}⚠️  {len(issues)} container(s) need attention:{NC}")
        for c in issues:
            print(f"    {YELLOW}●{NC} {c.name}: {c.issue or c.status}")
        print()
        auto_restart = [c for c in issues
                        if KNOWN_CONTAINERS.get(c.name, {}).get("auto_restart")]
        if auto_restart:
            print(f"  {DIM}Auto-restartable: "
                  f"{', '.join(c.name for c in auto_restart)}{NC}")
            print(f"  {DIM}Run: python3 docker-check.py --restart-dead{NC}")
    else:
        print(f"  {GREEN}✓ All containers healthy{NC}")

    print(f"\n  {BOLD}{CYAN}{'═' * 70}{NC}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Docker Health Check — monitor and manage containers"
    )
    parser.add_argument(
        "--stats", "-s", action="store_true",
        help="Show CPU/memory stats"
    )
    parser.add_argument(
        "--restart-dead", action="store_true",
        help="Restart stopped auto-restartable containers"
    )
    parser.add_argument(
        "--watch", "-w", action="store_true",
        help="Continuously monitor (refresh every 10s)"
    )
    parser.add_argument(
        "--interval", type=int, default=10,
        help="Watch interval in seconds (default: 10)"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON"
    )

    args = parser.parse_args()

    # Check docker available
    rc, _ = run_docker(["info"])
    if rc != 0:
        print(f"\n  {RED}✗ Docker daemon not available{NC}")
        sys.exit(1)

    def run_once():
        containers = get_all_containers()

        if args.restart_dead:
            stopped = [c for c in containers if not c.is_running]
            restartable = [c for c in stopped
                           if KNOWN_CONTAINERS.get(c.name, {}).get("auto_restart")]
            if restartable:
                print(f"\n  {YELLOW}Restarting {len(restartable)} container(s)...{NC}")
                for c in restartable:
                    success = restart_container(c.name)
                    icon = f"{GREEN}✓{NC}" if success else f"{RED}✗{NC}"
                    print(f"    {icon} {c.name}")
            else:
                print(f"\n  {GREEN}No stopped containers to restart.{NC}")

        if args.json:
            data = []
            for c in get_all_containers():
                data.append({
                    "name": c.name,
                    "friendly": c.friendly,
                    "status": c.status,
                    "health": c.health,
                    "is_running": c.is_running,
                    "needs_attention": c.needs_attention,
                    "issue": c.issue,
                })
            print(json.dumps(data, indent=2))
        else:
            print_report(containers, show_stats=args.stats)

        return any(c.needs_attention for c in containers)

    if args.watch:
        try:
            while True:
                subprocess.run(["clear"])
                run_once()
                print(f"\n  {DIM}Refreshing in {args.interval}s... "
                      f"(Ctrl+C to stop){NC}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n  {GREEN}Stopped.{NC}")
    else:
        has_issues = run_once()
        sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
