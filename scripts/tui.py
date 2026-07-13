#!/usr/bin/env python3
"""
TUI — Terminal UI for EHC Task Manager.

Rich-based terminal user interface for viewing background task status,
details, and history.

Usage (called by orchestrator.py, not directly):
    python3 -c "from tui import dashboard; dashboard()"
"""

import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

# ── Config ─────────────────────────────────────────────────────────

TASKS_DIR = Path("/tmp/ehc-tasks")
NOTIFY_DIR = TASKS_DIR.parent / "ehc-notifications"

console = Console()


# ── Data helpers ───────────────────────────────────────────────────

def load_task(task_id: str) -> Optional[dict]:
    """Load task.json for a given task ID."""
    path = TASKS_DIR / task_id / "task.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, Exception):
        return None


def load_agents(task_id: str) -> list[dict]:
    """Load agents.json for a given task ID."""
    path = TASKS_DIR / task_id / "agents.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, Exception):
        return []


def load_report(task_id: str) -> str:
    """Load report.md for a given task ID."""
    path = TASKS_DIR / task_id / "report.md"
    if not path.exists():
        return "(no report)"
    return path.read_text()


def list_tasks() -> list[dict]:
    """List all tasks sorted by ID (descending)."""
    if not TASKS_DIR.exists():
        return []
    tasks = []
    for d in sorted(TASKS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            info = load_task(d.name)
            if info:
                tasks.append(info)
    return tasks


def get_next_id() -> str:
    """Generate the next task ID."""
    if not TASKS_DIR.exists():
        return "1"
    ids = []
    for d in TASKS_DIR.iterdir():
        if d.is_dir() and d.name.isdigit():
            ids.append(int(d.name))
    return str(max(ids) + 1) if ids else "1"


def status_emoji(status: str) -> str:
    return {
        "running": "🔄", "done": "✅", "failed": "❌",
        "queued": "⏳", "cancelled": "🚫", "timeout": "⏱️",
    }.get(status, "❓")


def status_style(status: str) -> str:
    return {
        "running": "bold yellow", "done": "bold green",
        "failed": "bold red", "queued": "blue",
        "cancelled": "dim", "timeout": "yellow",
    }.get(status, "dim")


def format_duration(secs: Optional[float]) -> str:
    if secs is None:
        return "─"
    if secs < 60:
        return f"{secs:.0f}s"
    return f"{int(secs // 60)}m {int(secs % 60)}s"


def short_task(task: str, max_w: int = 26) -> str:
    return task if len(task) <= max_w else task[:max_w - 3] + "..."


def format_notify(notify: Optional[str], task_id: str) -> str:
    if not notify or notify == "none":
        return "[dim]─[/]"
    # Check if notification was delivered
    msg_path = NOTIFY_DIR / f"{task_id}.msg"
    if msg_path.exists():
        return f"[green]{notify} ✅[/]"
    return notify


# ── TUI Screens ────────────────────────────────────────────────────

def build_task_table(tasks: list[dict]) -> Table:
    """Build a Rich Table from task list."""
    table = Table(box=box.ROUNDED, header_style="bold cyan",
                  title="Tasks", title_style="bold")
    table.add_column("ID", width=5, no_wrap=True)
    table.add_column("Task", width=28)
    table.add_column("Agents", width=6, justify="right")
    table.add_column("Status", width=22)
    table.add_column("Time", width=8, no_wrap=True)
    table.add_column("Notify", width=12, no_wrap=True)

    if not tasks:
        table.add_row("", "[dim]No tasks yet[/]", "", "", "", "")
        return table

    for t in tasks[:12]:  # max 12 rows for terminal
        tid = t.get("id", "?")
        task_str = short_task(t.get("task", ""), 26)
        agents = t.get("agents", [])
        n_agents = t.get("total_count", len(agents) if isinstance(agents, list) else 0)
        agent_str = str(n_agents) if n_agents else str(len(agents)) if isinstance(agents, list) else "0"
        status = t.get("status", "unknown")
        emoji = status_emoji(status)

        # Status column with optional progress bar
        if status == "running":
            prog = t.get("progress", "0/0")
            status_text = f"{emoji} [yellow]RUN[/] [dim]{prog}[/]"
        elif status == "queued":
            status_text = f"{emoji} [blue]QUEUE[/]"
        elif status == "done":
            sc = t.get("success_count", "?")
            tc = t.get("total_count", "?")
            status_text = f"{emoji} [green]DONE[/] [dim]({sc}/{tc})[/]"
        elif status == "failed":
            sc = t.get("success_count", 0)
            tc = t.get("total_count", 0)
            status_text = f"{emoji} [red]FAIL[/] [dim]({sc}/{tc})[/]"
        else:
            status_text = f"{emoji} [dim]{status.upper()}[/]"

        # Duration
        started = t.get("started_at")
        completed = t.get("completed_at")
        duration = None
        if started and completed:
            try:
                s = datetime.fromisoformat(started)
                c = datetime.fromisoformat(completed)
                duration = format_duration((c - s).total_seconds())
            except Exception:
                duration = "─"
        elif started and status == "running":
            try:
                s = datetime.fromisoformat(started)
                duration = format_duration(
                    (datetime.now() - s).total_seconds()
                )
            except Exception:
                duration = "─"
        else:
            duration = "─"

        notify = format_notify(t.get("notify"), tid)

        table.add_row(tid, task_str, agent_str, status_text, duration, notify)

    return table


def build_summary(tasks: list[dict], width: int = 60) -> Panel:
    """Build summary panel."""
    total = len(tasks)
    running = sum(1 for t in tasks if t.get("status") == "running")
    done = sum(1 for t in tasks if t.get("status") == "done")
    failed = sum(1 for t in tasks if t.get("status") == "failed")
    queued = sum(1 for t in tasks if t.get("status") == "queued")
    cancelled = sum(1 for t in tasks if t.get("status") == "cancelled")

    parts = [f"[bold]Summary:[/] {total} total"]
    if running:
        parts.append(f"[yellow]{running} running[/]")
    if done:
        parts.append(f"[green]{done} done[/]")
    if failed:
        parts.append(f"[red]{failed} failed[/]")
    if queued:
        parts.append(f"[blue]{queued} queued[/]")
    if cancelled:
        parts.append(f"[dim]{cancelled} cancelled[/]")

    return Panel(
        "  │  ".join(parts),
        style="dim",
        box=box.HORIZONTALS,
    )


def build_header(title: str, subtitle: str = "") -> Panel:
    """Build header panel."""
    ts = datetime.now().strftime("%H:%M:%S")
    sub = f"  {subtitle}" if subtitle else ""
    return Panel(
        f"{title}{sub}",
        style="bold cyan",
        box=box.HEAVY,
        subtitle=ts,
    )


def dashboard(interval: float = 3.0):
    """Live-updating task dashboard."""
    try:
        with Live(console=console, refresh_per_second=1 / interval,
                  screen=True) as live:
            while True:
                tasks = list_tasks()

                layout = Layout()
                layout.split_column(
                    Layout(build_header(
                        "EHC TASK MANAGER",
                        "— Live dashboard"
                    ), size=3),
                    Layout(build_task_table(tasks)),
                    Layout(build_summary(tasks), size=3),
                )

                live.update(layout)
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        console.print("[dim]Dashboard closed[/]")


def task_detail(task_id: str):
    """Show detailed view of a single task."""
    info = load_task(task_id)
    if not info:
        console.print(f"[red]Task #{task_id} not found[/]")
        return

    agents = load_agents(task_id) or []
    report = load_report(task_id)

    console.print()
    console.print()
    console.print(build_header(f"TASK #{task_id} DETAIL"))

    # Metadata grid
    from rich.table import Column
    meta = Table.grid(padding=(0, 2))
    meta.add_column(style="bold")
    meta.add_column()
    meta.add_row("Task:", info.get("task", "?"))
    meta.add_row("Created:", info.get("started_at", "?")[:19])
    if info.get("completed_at"):
        meta.add_row("Completed:", f"{info['completed_at'][:19]} "
                     f"{status_emoji(info['status'])}")
    meta.add_row("Status:", f"{status_emoji(info['status'])} "
                 f"[{status_style(info['status'])}]{info.get('status', '?').upper()}[/]")
    if info.get("notify") and info["notify"] != "none":
        meta.add_row("Notify:", format_notify(info["notify"], task_id))
    console.print(meta)
    console.print()

    # Agent results table
    if agents:
        agent_table = Table(box=box.ROUNDED, header_style="bold",
                            title="Agent Results")
        agent_table.add_column("Agent", width=12)
        agent_table.add_column("Status", width=8)
        agent_table.add_column("Time", width=8)
        agent_table.add_column("Output Preview", width=48)

        for a in agents:
            st = a.get("status", "?")
            em = {"success": "✅", "failed": "❌", "timeout": "⏱️",
                  "error": "💥"}.get(st, "❓")
            preview = (a.get("output", "") or "")[:46].replace("\n", " ")
            agent_table.add_row(
                a.get("agent", "?"),
                f"{em}",
                format_duration(a.get("duration")),
                preview or "[dim]─[/]",
            )
        console.print(agent_table)
        console.print()

    # Report
    report_lines = report.split("\n")
    max_lines = 20  # Don't flood terminal
    if len(report_lines) > max_lines:
        report_preview = "\n".join(report_lines[:max_lines])
        console.print(Panel(
            report_preview + f"\n[dim]... ({len(report_lines) - max_lines} more lines)[/]",
            title="Report (preview)",
            box=box.HORIZONTALS,
        ))
    else:
        console.print(Panel(
            report, title="Report", box=box.HORIZONTALS
        ))

    console.print(f"\n[dim]Path:[/] {TASKS_DIR / task_id}")
    console.print()


def history(limit: int = 20):
    """Show all task history."""
    tasks = list_tasks()
    if not tasks:
        console.print("[yellow]No tasks in history.[/]")
        return

    # Sort oldest first for history (handle None values)
    def _sort_key(t):
        v = t.get("started_at")
        return v or ""
    tasks.sort(key=_sort_key)
    tasks = tasks[-limit:]

    console.print()
    console.print(build_header("TASK HISTORY"))

    table = Table(box=box.ROUNDED, header_style="bold")
    table.add_column("ID", width=5, no_wrap=True)
    table.add_column("Task", width=28)
    table.add_column("Date", width=14)
    table.add_column("Status", width=8)
    table.add_column("Duration", width=10)

    for t in tasks[-limit:]:
        tid = t.get("id", "?")
        task_str = short_task(t.get("task", ""), 26)
        started_raw = t.get("started_at")
        started = started_raw[:10] if started_raw else "─"
        status = t.get("status", "?")
        emoji = status_emoji(status)

        dur = "─"
        s_started = t.get("started_at")
        s_completed = t.get("completed_at")
        if s_started and s_completed:
            try:
                s = datetime.fromisoformat(t["started_at"])
                c = datetime.fromisoformat(t["completed_at"])
                dur = format_duration((c - s).total_seconds())
            except Exception:
                pass

        table.add_row(
            tid, task_str, started,
            f"{emoji} [{status_style(status)}]{status.upper()}[/]",
            dur,
        )

    console.print(table)
    console.print(f"\n[dim]Showing last {len(tasks)} of "
                  f"{len(list_tasks())} total tasks[/]")
    console.print()


def cancel_task(task_id: str) -> bool:
    """Cancel a running task by killing its PID."""
    info = load_task(task_id)
    if not info:
        console.print(f"[red]Task #{task_id} not found[/]")
        return False

    pid = info.get("pid")
    if not pid or info.get("status") != "running":
        console.print(f"[yellow]Task #{task_id} is not running (status: "
                      f"{info.get('status', '?')})[/]")
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        # Update task status
        info["status"] = "cancelled"
        info["completed_at"] = datetime.now().isoformat()
        (TASKS_DIR / task_id / "task.json").write_text(
            json.dumps(info, indent=2, default=str)
        )
        console.print(f"[green]Task #{task_id} cancelled[/]")
        return True
    except ProcessLookupError:
        console.print(f"[yellow]Task #{task_id} process already exited[/]")
        return False
    except Exception as e:
        console.print(f"[red]Error cancelling task #{task_id}: {e}[/]")
        return False


def cleanup(days: int = 7):
    """Remove tasks older than N days."""
    now = datetime.now()
    removed = 0
    for t in list_tasks():
        started = t.get("started_at")
        if started:
            try:
                s = datetime.fromisoformat(started)
                if (now - s).days >= days:
                    import shutil
                    shutil.rmtree(TASKS_DIR / t["id"], ignore_errors=True)
                    removed += 1
            except Exception:
                pass
    console.print(f"[green]Cleaned up {removed} old task(s)[/]")


# ── CLI entry point ────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="EHC Task Manager TUI")
    parser.add_argument("action", nargs="?", default="dashboard",
                        choices=["dashboard", "detail", "history",
                                 "cancel", "cleanup"])
    parser.add_argument("--id", type=str, default=None)
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    if args.action == "dashboard":
        dashboard()
    elif args.action == "detail":
        task_detail(args.id or "0")
    elif args.action == "history":
        history()
    elif args.action == "cancel":
        cancel_task(args.id or "0")
    elif args.action == "cleanup":
        cleanup(args.days)


if __name__ == "__main__":
    main()
