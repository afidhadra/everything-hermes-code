#!/usr/bin/env python3
"""
Task Worker — background process for running orchestration agents.

Spawned by orchestrator.py when --background is used.
Runs agents, saves results to /tmp/ehc-tasks/<id>/, and exits.

Usage (not meant for direct use):
    python3 task-worker.py --task-id 42 --task-desc "Refactor auth" \
        --agents coder,security --mode parallel --max-parallel 3
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────

TASKS_DIR = Path("/tmp/ehc-tasks")
REPO_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_DIR / "skills"

HERMES_CMD = "hermes"
HERMES_TIMEOUT = 300


# ── Helpers ────────────────────────────────────────────────────────

def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def build_agent_prompt(agent_name: str, task: str) -> str:
    """Build a prompt for a specific agent."""
    prompts = {
        "architect": f"""You are the Architect agent. Task: {task}
Analyze the system architecture implications. Provide:
1. Impact analysis — what components are affected
2. Architecture recommendations
3. Risk assessment
4. Dependency map
Keep it concise and actionable.""",

        "coder": f"""You are the Coder agent. Task: {task}
Provide implementation plan and code:
1. Files to create/modify (with paths)
2. Implementation approach
3. Key code changes
4. Potential issues to watch for
Be specific with file paths and code snippets.""",

        "debugger": f"""You are the Debugger agent. Task: {task}
Perform root cause analysis:
1. Identify the root cause (not symptoms)
2. Trace the execution path
3. Propose a fix with code
4. Suggest prevention strategies
Be systematic and evidence-based.""",

        "reviewer": f"""You are the Reviewer agent. Task: {task}
Review the following task from a quality perspective:
1. Code quality concerns
2. Security implications
3. Performance impact
4. Testing recommendations
5. Severity: low/medium/high/critical for each concern
{task}""",

        "documenter": f"""You are the Documenter agent. Task: {task}
1. Document what changed
2. Update relevant docs (README, API docs)
3. Create or update changelog entries
Task: {task}""",

        "optimizer": f"""You are the Optimizer agent. Task: {task}
1. Identify performance bottlenecks
2. Propose optimization strategies
3. Estimate performance gains
4. Provide optimized code
Task: {task}""",

        "planner": f"""You are the Planner agent. Task: {task}
Create a project plan:
1. Break down into subtasks
2. Estimate effort (hours)
3. Identify dependencies
4. Risk assessment
5. Recommended execution order
Task: {task}""",

        "security": f"""You are the Security agent. Task: {task}
Security analysis:
1. Identify vulnerabilities (OWASP Top 10)
2. Attack surface analysis
3. Risk level: low/medium/high/critical
4. Mitigation recommendations with code
Task: {task}""",

        "tdd-guide": f"""You are the TDD Guide agent. Task: {task}
TDD approach:
1. Write test cases first (RED phase)
2. Implementation guidance (GREEN phase)
3. Refactoring suggestions (REFACTOR phase)
4. Coverage analysis
Task: {task}""",
    }
    return prompts.get(agent_name, f"Task: {task}")


def run_agent(agent_name: str, task: str, yolo: bool = False) -> dict:
    """Run a single agent as a Hermes subprocess."""
    prompt = build_agent_prompt(agent_name, task)
    start = time.time()

    cmd = [HERMES_CMD, "-z", prompt]
    if yolo:
        cmd.append("--yolo")
    cmd.append("--worktree")

    skill_path = SKILLS_DIR / f"{agent_name}.md"
    if skill_path.exists():
        cmd.extend(["--skills", str(skill_path)])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=HERMES_TIMEOUT, cwd=str(REPO_DIR),
        )
        return {
            "agent": agent_name,
            "status": "success" if result.returncode == 0 else "failed",
            "output": result.stdout.strip() or "",
            "error": result.stderr.strip() or "",
            "duration": round(time.time() - start, 1),
        }
    except subprocess.TimeoutExpired:
        return {
            "agent": agent_name, "status": "timeout",
            "output": "", "error": f"Timeout {HERMES_TIMEOUT}s",
            "duration": round(time.time() - start, 1),
        }
    except FileNotFoundError:
        return {
            "agent": agent_name, "status": "error",
            "output": "", "error": "hermes not found in PATH",
            "duration": round(time.time() - start, 1),
        }


# ── Main ───────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Task Worker (background)")
    parser.add_argument("--task-id", required=True, type=str)
    parser.add_argument("--task-desc", required=True, type=str)
    parser.add_argument("--agents", required=True, type=str,
                        help="Comma-separated agent names")
    parser.add_argument("--mode", default="parallel",
                        choices=["parallel", "sequential"])
    parser.add_argument("--max-parallel", type=int, default=3)
    parser.add_argument("--yolo", action="store_true")
    parser.add_argument("--notify", default=None, type=str)
    args = parser.parse_args()

    task_id = args.task_id
    agents = [a.strip() for a in args.agents.split(",")]
    task_dir = TASKS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # Write task metadata
    task_info = {
        "id": task_id,
        "task": args.task_desc,
        "agents": agents,
        "mode": args.mode,
        "max_parallel": args.max_parallel,
        "notify": args.notify,
        "started_at": datetime.now().isoformat(),
        "status": "running",
        "pid": os.getpid(),
    }
    write_json(task_dir / "task.json", task_info)

    # Run agents
    results = []
    total = len(agents)
    for i, agent in enumerate(agents):
        # Write progress
        task_info["progress"] = f"{i}/{total}"
        write_json(task_dir / "task.json", task_info)

        result = run_agent(agent, args.task_desc, yolo=args.yolo)
        results.append(result)

        # Write individual agent result
        write_json(task_dir / "agents.json", results)

    # Build summary report
    success_count = sum(1 for r in results if r["status"] == "success")
    report_lines = [
        "=" * 60,
        f"ORCHESTRATION REPORT — Task #{task_id}",
        f"Task: {args.task_desc}",
        f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        "",
        "AGENT RESULTS",
        "-" * 40,
    ]
    for r in results:
        report_lines.append("")
        report_lines.append(f"[{r['status'].upper()}] {r['agent']} ({r['duration']}s)")
        report_lines.append("-" * 40)
        if r["output"]:
            report_lines.append(r["output"])
        if r["error"]:
            report_lines.append(f"ERROR: {r['error']}")

    report_lines.extend([
        "",
        "-" * 60,
        f"Agents: {success_count}/{total} succeeded",
        f"Total time: {sum(r['duration'] for r in results):.1f}s",
        "=" * 60,
    ])
    report = "\n".join(report_lines)

    # Write final state
    final_info = {
        **task_info,
        "status": "done" if success_count == total else "failed",
        "completed_at": datetime.now().isoformat(),
        "success_count": success_count,
        "total_count": total,
    }
    write_json(task_dir / "task.json", final_info)
    (task_dir / "report.md").write_text(report)

    # Create done flag
    (task_dir / "done").touch()

    # Notification file
    if args.notify:
        notify_path = TASKS_DIR.parent / "ehc-notifications" / f"{task_id}.msg"
        notify_path.parent.mkdir(parents=True, exist_ok=True)
        notify_path.write_text(
            f"Task #{task_id} {final_info['status']}: "
            f"{args.task_desc} ({success_count}/{total} agents, "
            f"{sum(r['duration'] for r in results):.1f}s)"
        )

    print(f"Task #{task_id} complete: {success_count}/{total}")


if __name__ == "__main__":
    main()
