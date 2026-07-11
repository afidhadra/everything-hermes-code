#!/usr/bin/env python3
"""
Everything Hermes Code — Orchestration Engine

Analyzes task complexity, spawns parallel AI agents via Hermes CLI,
and aggregates results.

Usage:
    python3 orchestrator.py <task-description>
    python3 orchestrator.py "Refactor authentication module"
    python3 orchestrator.py --dry-run "Fix login bug"

Features:
    - Task complexity analysis (simple/medium/complex)
    - Parallel agent spawning via subprocess
    - Agent selection based on task type
    - Result aggregation and summary
    - Dry-run mode for planning without execution

Requirements:
    - Hermes CLI (hermes) in PATH
    - Active model configured (hermes config)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# ============================================================
# Configuration
# ============================================================

REPO_DIR = Path(__file__).parent.parent
AGENTS_DIR = REPO_DIR / "agents"
RULES_DIR = REPO_DIR / "rules"
SKILLS_DIR = REPO_DIR / "skills"

MAX_PARALLEL = 3  # Max concurrent agents
HERMES_CMD = "hermes"
HERMES_TIMEOUT = 300  # 5 minutes per agent

# ============================================================
# Task Complexity Classification
# ============================================================

class Complexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


# Keywords that indicate task type
TASK_KEYWORDS = {
    "security": ["security", "vulnerability", "auth", "inject", "xss",
                 "csrf", "encrypt", "password", "token", "secret"],
    "bug": ["bug", "fix", "error", "crash", "broken", "fail", "exception",
            "traceback", "regression"],
    "feature": ["add", "implement", "create", "new", "feature", "build",
                "develop"],
    "refactor": ["refactor", "cleanup", "clean up", "restructure",
                 "simplify", "optimize", "performance"],
    "test": ["test", "coverage", "unit test", "integration test"],
    "docs": ["document", "readme", "docs", "explain", "describe"],
    "architecture": ["architecture", "design", "plan", "structure",
                     "database", "schema", "api", "endpoint"],
}

# Keywords that increase complexity
COMPLEXITY_MARKERS = {
    "high": ["microservice", "migration", "database schema", "refactor",
             "entire", "all", "every", "full", "complete overhaul",
             "architecture", "redesign", "rewrite"],
    "medium": ["module", "feature", "endpoint", "component", "service",
               "multiple files", "integration"],
}


class TaskAnalysis:
    """Result of analyzing a task."""

    def __init__(self, task: str):
        self.task = task
        self.task_lower = task.lower()
        self.complexity = Complexity.SIMPLE
        self.task_types: list[str] = []
        self.agents: list[str] = []
        self.reasoning: list[str] = []
        self.confidence = 0.0
        self._analyze()

    def _analyze(self):
        # --- Detect task types ---
        detected = set()
        for ttype, keywords in TASK_KEYWORDS.items():
            if any(kw in self.task_lower for kw in keywords):
                detected.add(ttype)

        # Default to feature if nothing detected
        if not detected:
            detected.add("feature")

        self.task_types = sorted(detected)

        # --- Assess complexity ---
        score = 0

        # Word count
        word_count = len(self.task.split())
        if word_count <= 5:
            score += 1
        elif word_count <= 15:
            score += 2
        else:
            score += 3

        # Complexity markers
        for marker in COMPLEXITY_MARKERS["high"]:
            if marker in self.task_lower:
                score += 3
                self.reasoning.append(f"High-complexity marker: '{marker}'")

        for marker in COMPLEXITY_MARKERS["medium"]:
            if marker in self.task_lower:
                score += 2
                self.reasoning.append(f"Medium-complexity marker: '{marker}'")

        # Multiple task types = more complex
        if len(self.task_types) >= 2:
            score += 1
            self.reasoning.append(
                f"Multiple task types: {', '.join(self.task_types)}"
            )

        # Multiple conjunctions suggest multiple sub-tasks
        conjunctions = self.task_lower.count(" and ") + \
                        self.task_lower.count(" or ") + \
                        self.task_lower.count(" then ")
        if conjunctions >= 2:
            score += 2
            self.reasoning.append(
                f"Multiple conjunctions ({conjunctions})"
            )

        # Set complexity
        if score <= 3:
            self.complexity = Complexity.SIMPLE
        elif score <= 6:
            self.complexity = Complexity.MEDIUM
        else:
            self.complexity = Complexity.COMPLEX

        self.confidence = min(1.0, score / 10.0)

        # --- Select agents ---
        self.agents = self._select_agents()

    def _select_agents(self) -> list[str]:
        """Map task types to agents."""
        mapping = {
            "security": ["security", "reviewer"],
            "bug": ["debugger", "reviewer"],
            "feature": ["coder"],
            "refactor": ["coder", "optimizer"],
            "test": ["tdd-guide"],
            "docs": ["documenter"],
            "architecture": ["architect", "planner"],
        }

        agents = []
        for ttype in self.task_types:
            for agent in mapping.get(ttype, []):
                if agent not in agents:
                    agents.append(agent)

        # Always add reviewer for complex tasks
        if self.complexity == Complexity.COMPLEX and \
                "reviewer" not in agents:
            agents.append("reviewer")

        return agents if agents else ["coder"]

    def summary(self) -> str:
        lines = [
            f"Task: {self.task}",
            f"Complexity: {self.complexity.value}",
            f"Task Types: {', '.join(self.task_types)}",
            f"Agents: {', '.join(self.agents)}",
            f"Confidence: {self.confidence:.0%}",
        ]
        if self.reasoning:
            lines.append(f"Reasoning: {'; '.join(self.reasoning)}")
        return "\n".join(lines)


# ============================================================
# Agent Execution
# ============================================================

def build_agent_prompt(agent_name: str, task: str, analysis: TaskAnalysis) -> str:
    """Build a prompt for a specific agent."""
    prompts = {
        "architect": f"""You are the Architect agent. Task: {task}

Analyze the system architecture implications. Provide:
1. Impact analysis — what components are affected
2. Architecture recommendations
3. Risk assessment
4. Dependency map (what depends on what)
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


def run_agent_subprocess(
    agent_name: str,
    task: str,
    analysis: TaskAnalysis,
    use_worktree: bool = True,
    yolo: bool = False,
) -> dict:
    """
    Run a single agent as a Hermes subprocess.
    Returns dict with agent_name, status, output, duration.
    """
    prompt = build_agent_prompt(agent_name, task, analysis)
    start = time.time()

    cmd = [
        HERMES_CMD,
        "-z", prompt,
    ]

    # Only use --yolo when explicitly requested (auto-approve all tool calls)
    if yolo:
        cmd.append("--yolo")

    if use_worktree:
        cmd.append("--worktree")

    # Add agent-specific skill if available
    skill_path = SKILLS_DIR / f"{agent_name}.md"
    if skill_path.exists():
        cmd.extend(["--skills", str(skill_path)])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=HERMES_TIMEOUT,
            cwd=str(REPO_DIR),
        )

        duration = time.time() - start

        return {
            "agent": agent_name,
            "status": "success" if result.returncode == 0 else "failed",
            "output": result.stdout.strip() if result.stdout else "",
            "error": result.stderr.strip() if result.stderr else "",
            "returncode": result.returncode,
            "duration": round(duration, 1),
        }

    except subprocess.TimeoutExpired:
        return {
            "agent": agent_name,
            "status": "timeout",
            "output": "",
            "error": f"Agent timed out after {HERMES_TIMEOUT}s",
            "returncode": -1,
            "duration": round(time.time() - start, 1),
        }
    except FileNotFoundError:
        return {
            "agent": agent_name,
            "status": "error",
            "error": "hermes command not found in PATH",
            "returncode": -1,
            "duration": round(time.time() - start, 1),
        }


def run_agents_parallel(
    agents: list[str],
    task: str,
    analysis: TaskAnalysis,
    max_parallel: int = MAX_PARALLEL,
    yolo: bool = False,
) -> list[dict]:
    """Run multiple agents in parallel and return results."""
    results = []

    if yolo:
        print(f"\n🚀 Spawning {len(agents)} agent(s) "
              f"(max {max_parallel} parallel, --yolo)... \n")
    else:
        print(f"\n🚀 Spawning {len(agents)} agent(s) "
              f"(max {max_parallel} parallel)... \n")

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        future_map = {
            executor.submit(
                run_agent_subprocess, agent, task, analysis,
                True, yolo
            ): agent
            for agent in agents
        }

        for future in as_completed(future_map):
            agent = future_map[future]
            try:
                result = future.result()
                results.append(result)
                status_icon = {
                    "success": "✅",
                    "failed": "❌",
                    "timeout": "⏱️",
                    "error": "💥",
                }.get(result["status"], "❓")
                print(f"  {status_icon} {agent} "
                      f"({result['duration']}s)")
            except Exception as e:
                print(f"  💥 {agent} crashed: {e}")
                results.append({
                    "agent": agent,
                    "status": "error",
                    "output": "",
                    "error": str(e),
                    "returncode": -1,
                    "duration": 0,
                })

    # Sort by original agent order
    agent_order = {a: i for i, a in enumerate(agents)}
    results.sort(key=lambda r: agent_order.get(r["agent"], 999))
    return results


def run_agents_sequential(
    agents: list[str],
    task: str,
    analysis: TaskAnalysis,
    yolo: bool = False,
) -> list[dict]:
    """Run agents one by one."""
    results = []
    print(f"\n🚀 Running {len(agents)} agent(s) sequentially...\n")

    for agent in agents:
        result = run_agent_subprocess(
            agent, task, analysis, use_worktree=False, yolo=yolo
        )
        results.append(result)
        status_icon = {
            "success": "✅",
            "failed": "❌",
            "timeout": "⏱️",
            "error": "💥",
        }.get(result["status"], "❓")
        print(f"  {status_icon} {agent} ({result['duration']}s)")

    return results


# ============================================================
# Result Aggregation
# ============================================================

def aggregate_results(results: list[dict], analysis: TaskAnalysis) -> str:
    """Aggregate agent outputs into a summary report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "=" * 60,
        "ORCHESTRATION REPORT",
        f"Timestamp: {timestamp}",
        "=" * 60,
        "",
        analysis.summary(),
        "",
        "-" * 60,
        "AGENT RESULTS",
        "-" * 60,
    ]

    success_count = sum(1 for r in results if r["status"] == "success")
    total_count = len(results)
    total_time = sum(r["duration"] for r in results)

    for r in results:
        status = r["status"].upper()
        lines.append("")
        lines.append(f"[{status}] {r['agent'].upper()} "
                     f"({r['duration']}s)")
        lines.append("-" * 40)

        if r["output"]:
            lines.append(r["output"])
        if r["error"]:
            lines.append(f"ERROR: {r['error']}")

    lines.extend([
        "",
        "-" * 60,
        "SUMMARY",
        "-" * 60,
        f"Agents spawned:   {total_count}",
        f"Agents succeeded: {success_count}/{total_count}",
        f"Total time:       {total_time:.1f}s",
        f"Complexity:       {analysis.complexity.value}",
        "",
    ])

    if success_count == total_count:
        lines.append("✅ All agents completed successfully.")
    elif success_count > 0:
        lines.append("⚠️  Partial completion — some agents failed.")
    else:
        lines.append("❌ All agents failed.")

    lines.append("=" * 60)
    return "\n".join(lines)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Orchestration Engine — parallel AI agent execution"
    )
    parser.add_argument(
        "task",
        nargs="+",
        help="Task description to orchestrate"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze task and show plan without executing agents"
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run agents sequentially instead of parallel"
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=MAX_PARALLEL,
        help=f"Max concurrent agents (default: {MAX_PARALLEL})"
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Save report to file (default: reports/ directory)"
    )
    parser.add_argument(
        "--no-worktree",
        action="store_true",
        help="Disable git worktree isolation"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Allow --yolo on spawned agents (auto-approve all tool calls)"
    )
    args = parser.parse_args()

    task = " ".join(args.task)

    # Banner
    print()
    print("=" * 60)
    print("  ORCHESTRATION ENGINE")
    print("=" * 60)

    # --- Analyze ---
    print(f"\n📋 Analyzing task...")
    analysis = TaskAnalysis(task)

    print(f"\n{analysis.summary()}")

    # --- Dry run ---
    if args.dry_run:
        print(f"\n{'─' * 60}")
        print("DRY RUN — no agents will be spawned")
        print(f"{'─' * 60}")
        print(f"\nWould spawn {len(analysis.agents)} agents: "
              f"{', '.join(analysis.agents)}")
        print(f"Execution: "
              f"{'sequential' if args.sequential else 'parallel'}")
        if not args.sequential:
            print(f"Max parallel: {args.max_parallel}")
        print(f"\nAgent prompts:")
        for agent in analysis.agents:
            preview = build_agent_prompt(agent, task, analysis)
            preview_short = preview[:200].replace("\n", " ")
            print(f"  [{agent}]: {preview_short}...")
        print("\n--- End of dry run ---")
        return

    # --- Execute ---
    if args.sequential:
        results = run_agents_sequential(
            analysis.agents, task, analysis, yolo=args.yes
        )
    else:
        results = run_agents_parallel(
            analysis.agents, task, analysis, args.max_parallel,
            yolo=args.yes
        )

    # --- Aggregate ---
    report = aggregate_results(results, analysis)
    print(f"\n{report}")

    # --- Save ---
    save_path = args.save
    if not save_path:
        reports_dir = REPO_DIR / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = reports_dir / f"orchestration_{timestamp}.md"

    Path(save_path).write_text(report, encoding="utf-8")
    print(f"\n📄 Report saved to: {save_path}")


if __name__ == "__main__":
    main()
