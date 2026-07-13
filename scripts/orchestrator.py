#!/usr/bin/env python3
"""
Everything Hermes Code — Orchestration Engine with Plan-First Workflow.

Analyzes task complexity, generates a detailed plan for review,
then spawns parallel AI agents via Hermes CLI upon approval.

Usage:
    python3 orchestrator.py "Refactor authentication module"
    python3 orchestrator.py --plan-only "Add login feature"
    python3 orchestrator.py --plan plan.md --auto-approve
    python3 orchestrator.py --dry-run "Fix login bug"

Workflow:
    1. Analyze  — classify task complexity, detect types, select agents
    2. Plan     — generate structured markdown plan
    3. Review   — show plan, wait for user approval (unless --auto-approve)
    4. Execute  — spawn agents (parallel or sequential)
    5. Report   — aggregate results into a summary

Features:
    - Plan-first workflow with human-in-the-loop approval
    - Plan file save/load for async review and editing
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

# Import Smart Agent Router (sibling in scripts/)
import importlib.util
_router_path = Path(__file__).parent / "agent-router.py"
_router_spec = importlib.util.spec_from_file_location("agent_router", str(_router_path))
agent_router = importlib.util.module_from_spec(_router_spec)
_router_spec.loader.exec_module(agent_router)

# ============================================================
# Configuration
# ============================================================

REPO_DIR = Path(__file__).parent.parent
AGENTS_DIR = REPO_DIR / "agents"
RULES_DIR = REPO_DIR / "rules"
SKILLS_DIR = REPO_DIR / "skills"
REPORTS_DIR = REPO_DIR / "reports"

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


# ============================================================
# Task Analysis
# ============================================================

class TaskAnalysis:
    """Result of analyzing a task."""

    def __init__(self, task: str, force_agents: Optional[list[str]] = None):
        self.task = task
        self.task_lower = task.lower()
        self.complexity = Complexity.SIMPLE
        self.task_types: list[str] = []
        self.agents: list[str] = []
        self.reasoning: list[str] = []
        self.confidence = 0.0
        self.estimated_minutes = 0
        self.force_agents = force_agents
        self.routing_scores: list[dict] = []
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

        # Estimate time
        if self.complexity == Complexity.SIMPLE:
            self.estimated_minutes = 5
        elif self.complexity == Complexity.MEDIUM:
            self.estimated_minutes = 15
        else:
            self.estimated_minutes = 30

        # --- Select agents via Smart Agent Router ---
        self._route_agents()

    def _route_agents(self):
        """Use Smart Agent Router to select agents based on task."""
        global agent_router
        if agent_router is not None:
            try:
                routing_config = agent_router.load_routing_config()
                result = agent_router.route_task(
                    self.task, routing_config,
                    force_agents=self.force_agents,
                )
                self.agents = result.recommended
                self.confidence = result.confidence
                self.routing_scores = [
                    {"category": cs.name, "score": cs.score,
                     "matched": cs.matched, "agents": cs.agents}
                    for cs in result.category_scores
                ]
                if result.reasoning:
                    self.reasoning.extend(result.reasoning)
                return
            except Exception:
                pass  # Fall through to keyword-based

        # Fallback: keyword-based agent selection
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
        if self.routing_scores:
            scores_str = ", ".join(
                f"{s['category']}={s['score']:.2f}"
                for s in self.routing_scores[:3]
            )
            lines.append(f"Routing: {scores_str}")
        if self.reasoning:
            lines.append(f"Reasoning: {'; '.join(self.reasoning[:3])}")
        return "\n".join(lines)


# ============================================================
# Plan Generation  (NEW — Plan-First Workflow)
# ============================================================

def generate_plan(analysis: TaskAnalysis) -> str:
    """Generate a structured markdown plan for the task analysis.

    This plan is shown to the user for review before execution.
    """
    agent_descriptions = {
        "architect": "Design system architecture and component interactions",
        "coder": "Implement code changes with best practices",
        "debugger": "Root cause analysis and fix implementation",
        "reviewer": "Code quality, security, and performance review",
        "documenter": "Documentation updates and changelog entries",
        "optimizer": "Performance optimization and efficiency improvements",
        "planner": "Task breakdown, timeline, and dependency analysis",
        "security": "Vulnerability assessment and security hardening",
        "tdd-guide": "Test-driven development with RED-GREEN-REFACTOR",
    }

    lines = [
        "# Orchestration Plan",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Task",
        "",
        f"> {analysis.task}",
        "",
        "## Analysis",
        "",
        f"| Property | Value |",
        "|----------|-------|",
        f"| Complexity | **{analysis.complexity.value.upper()}** |",
        f"| Confidence | {analysis.confidence:.0%} |",
        f"| Task Types | {', '.join(analysis.task_types)} |",
        f"| Est. Time | ~{analysis.estimated_minutes} min |",
        "",
    ]

    if analysis.reasoning:
        lines.extend([
            "### Reasoning",
            "",
        ])
        for r in analysis.reasoning:
            lines.append(f"- {r}")
        lines.append("")

    # Routing scores (from Smart Agent Router)
    if analysis.routing_scores:
        lines.extend([
            "### Routing Scores",
            "",
            "| Category | Score | Matched | Agents |",
            "|----------|-------|---------|--------|",
        ])
        for s in analysis.routing_scores:
            matched_str = ", ".join(s.get("matched", []) or [])
            agents_str = ", ".join(s.get("agents", []))
            lines.append(
                f"| {s['category']} | {s['score']:.2f} "
                f"| {matched_str} | {agents_str} |"
            )
        lines.append("")

    # Agent plan
    lines.extend([
        "## Execution Plan",
        "",
        f"**Mode:** parallel (max {MAX_PARALLEL} agents)",
        "**Worktree:** enabled",
        "",
        "| # | Agent | Role |",
        "|---|-------|------|",
    ])
    for i, agent in enumerate(analysis.agents, 1):
        desc = agent_descriptions.get(agent, agent)
        lines.append(f"| {i} | `{agent}` | {desc} |")

    lines.extend([
        "",
        "## Order & Dependencies",
        "",
    ])

    if len(analysis.agents) <= 1:
        lines.append("Single agent — no dependencies.")
    elif analysis.complexity == Complexity.SIMPLE:
        lines.append("All agents can run independently in parallel.")
    else:
        # For complex tasks, suggest a dependency order
        lines.append("Suggested execution order:")
        has_architect = "architect" in analysis.agents
        has_planner = "planner" in analysis.agents
        has_coder = "coder" in analysis.agents
        has_reviewer = "reviewer" in analysis.agents
        has_security = "security" in analysis.agents
        has_documenter = "documenter" in analysis.agents

        step = 1
        if has_architect or has_planner:
            lines.append(f"  {step}. **Design phase:** "
                         f"architect + planner (parallel)")
            step += 1
        if has_coder:
            lines.append(f"  {step}. **Implementation:** coder, "
                         f"optimizer, tdd-guide (parallel)")
            step += 1
        if has_reviewer or has_security:
            lines.append(f"  {step}. **Review phase:** "
                         f"reviewer + security (parallel)")
            step += 1
        if has_documenter:
            lines.append(f"  {step}. **Documentation:** documenter")
            step += 1
        if step == 1:
            lines.append("  All agents run in parallel (no strict deps).")

    lines.extend([
        "",
        "---",
        "",
        "## Risk Assessment",
        "",
    ])

    if analysis.complexity == Complexity.SIMPLE:
        lines.append("✅ **Low risk** — well-defined task, single agent.")
    elif analysis.complexity == Complexity.MEDIUM:
        lines.append("⚠️ **Medium risk** — multiple agents involved, "
                      "coordination needed.")
    else:
        lines.append("🔴 **High risk** — complex multi-agent orchestration. "
                      "Review each agent output carefully.")

    if "security" in analysis.agents:
        lines.append("- Security implications need review")
    if "database" in analysis.task_lower or "schema" in analysis.task_lower:
        lines.append("- Database changes may require migration")
    if "refactor" in analysis.task_types:
        lines.append("- Refactoring may introduce regressions")

    lines.extend([
        "",
        "---",
        "",
        "## Status",
        "",
        "**PENDING REVIEW**",
        "",
    ])

    return "\n".join(lines)


def load_plan(plan_path: Path) -> tuple[bool, str]:
    """Load an existing plan file.

    Returns (exists, content).
    """
    if plan_path and plan_path.exists():
        return True, plan_path.read_text(encoding="utf-8")
    return False, ""


def save_plan(plan: str, path: Optional[Path] = None) -> Path:
    """Save plan to a markdown file.

    If no path given, saves to reports/plan_<timestamp>.md.
    Returns the path.
    """
    if path is None:
        REPORTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"plan_{timestamp}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan, encoding="utf-8")
    return path


def review_plan(plan: str, auto_approve: bool = False) -> bool:
    """Show the plan and prompt the user for approval.

    Returns True if approved, False if rejected.
    If auto_approve is True, skip prompt.
    """
    print()
    print("=" * 60)
    print("  ORCHESTRATION PLAN")
    print("=" * 60)
    print()
    print(plan)
    print()

    if auto_approve:
        print("✅ Auto-approve enabled — executing plan...")
        return True

    # Interactive approval
    try:
        response = input(
            "Approve and execute this plan?\n"
            "  [Y] Yes, execute now\n"
            "  [n] No, abort\n"
            "  [e] Edit plan file first\n"
            "Choice [Y/n/e]: "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\n⚠️  Plan review aborted.")
        return False

    if response == "e":
        # Tell user how to edit and re-run
        plan_path = save_plan(plan)
        print(f"\n📝 Plan saved to: {plan_path}")
        print(f"   Edit the file, then re-run with: --plan {plan_path}")
        return False
    elif response == "n" or response == "no":
        print("\n❌ Plan rejected. Aborting.")
        return False
    else:
        # Y, yes, Enter, or anything else = approve
        print("\n✅ Plan approved. Executing...")
        return True


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
# Background Task Spawning
# ============================================================

def _spawn_background_worker(
    task_id: str,
    task_desc: str,
    agents: list[str],
    mode: str = "parallel",
    max_parallel: int = 3,
    yolo: bool = False,
    notify: str = "hermes",
):
    """Spawn a background task-worker subprocess.

    The worker runs agents independently and saves results to
    /tmp/ehc-tasks/<task_id>/.
    """
    worker_script = Path(__file__).parent / "task-worker.py"
    if not worker_script.exists():
        print("❌ task-worker.py not found — cannot run in background")
        sys.exit(1)

    cmd = [
        sys.executable, str(worker_script),
        "--task-id", task_id,
        "--task-desc", task_desc,
        "--agents", ",".join(agents),
        "--mode", mode,
        "--max-parallel", str(max_parallel),
    ]
    if yolo:
        cmd.append("--yolo")
    if notify:
        cmd.extend(["--notify", notify])

    # Create tasks directory
    tasks_dir = Path("/tmp/ehc-tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print()
        print("=" * 60)
        print("  BACKGROUND TASK SPAWNED")
        print("=" * 60)
        print()
        print(f"  🆔 Task ID:   #{task_id}")
        print(f"  📋 Task:      {task_desc}")
        print(f"  🤖 Agents:    {', '.join(agents)}")
        print(f"  💻 PID:       {process.pid}")
        print(f"  📁 Logs:      {tasks_dir / task_id}")
        print(f"  🔔 Notify:    {notify}")
        print()
        print(f"  ─────────────────────────────────────────────")
        print(f"  Usage:")
        print(f"    orchestrator.py --status     Live dashboard")
        print(f"    orchestrator.py --result {task_id}  View result")
        print(f"    orchestrator.py --history   All tasks")
        print(f"  ─────────────────────────────────────────────")
        print()
    except Exception as e:
        print(f"❌ Failed to spawn background worker: {e}")
        sys.exit(1)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Orchestration Engine — parallel AI agent execution "
                    "with plan-first workflow"
    )
    parser.add_argument(
        "task",
        nargs="*",
        help="Task description to orchestrate (not needed with --plan)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze task and show plan without executing agents"
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Generate plan and save to file, then exit (no execution)"
    )
    parser.add_argument(
        "--plan",
        type=str,
        default=None,
        metavar="FILE",
        help="Path to existing plan file (skips analysis, loads from file)"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip plan review prompt — auto-approve and execute"
    )
    parser.add_argument(
        "--force-agents",
        type=str,
        default=None,
        metavar="AGENTS",
        help="Override agent selection (comma-separated: coder,security)"
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
    # ── Background + TUI flags ──────────────────────────────────
    parser.add_argument(
        "--background", "-b",
        action="store_true",
        help="Run task in background (async)"
    )
    parser.add_argument(
        "--notify",
        type=str,
        default=None,
        metavar="CHANNEL",
        help="Notification channel on completion: terminal, hermes, slack (default: hermes when --background)"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show live task dashboard"
    )
    parser.add_argument(
        "--result", "-r",
        type=str,
        default=None,
        metavar="ID",
        help="Show detail for a specific task"
    )
    parser.add_argument(
        "--history", "-H",
        action="store_true",
        help="Show all task history"
    )
    parser.add_argument(
        "--cancel",
        type=str,
        default=None,
        metavar="ID",
        help="Cancel a running task"
    )
    parser.add_argument(
        "--cleanup",
        type=int,
        nargs="?",
        const=7,
        default=None,
        metavar="DAYS",
        help="Remove tasks older than N days (default: 7)"
    )
    args = parser.parse_args()

    # Parse force-agents if provided
    _force_agents = None
    if args.force_agents:
        _force_agents = [a.strip() for a in args.force_agents.split(",")]

    # ── TUI / Management commands ──────────────────────────────────
    # Import TUI module
    _tui_path = Path(__file__).parent / "tui.py"
    _tui_spec = importlib.util.spec_from_file_location("tui", str(_tui_path))
    _tui_mod = importlib.util.module_from_spec(_tui_spec)
    _tui_spec.loader.exec_module(_tui_mod)

    if args.status:
        _tui_mod.dashboard()
        return
    if args.result:
        _tui_mod.task_detail(args.result)
        return
    if args.history:
        _tui_mod.history()
        return
    if args.cancel:
        _tui_mod.cancel_task(args.cancel)
        return
    if args.cleanup:
        _tui_mod.cleanup(args.cleanup)
        return

    # ================================================================
    # PHASE 0: Load existing plan (if --plan provided)
    # ================================================================

    if args.plan:
        plan_path = Path(args.plan)
        exists, plan_content = load_plan(plan_path)

        if exists:
            print()
            print("=" * 60)
            print("  PLAN-FIRST ORCHESTRATION")
            print("=" * 60)
            print(f"\n📄 Loaded plan from: {plan_path}")
            print()

            if args.dry_run:
                print(plan_content)
                print("\n--- End of dry run (loaded from plan file) ---")
                return

            if args.plan_only:
                print(plan_content)
                print(f"\n📄 Plan file: {plan_path}")
                return

            # Review the loaded plan
            if not review_plan(plan_content, auto_approve=args.auto_approve):
                sys.exit(1)

            # Extract just the task description from the plan
            task = ""
            for line in plan_content.split("\n"):
                if line.startswith("> "):
                    task = line[2:].strip()
                    break
            if not task:
                task = f"Task from plan: {plan_path.name}"

            # Parse agent names from plan table
            agents = []
            for line in plan_content.split("\n"):
                m = re.match(r"^\| \d+ \| `(\w[\w-]*)` \|", line)
                if m:
                    agents.append(m.group(1))
            if not agents:
                agents = ["coder"]

            analysis = TaskAnalysis(task, force_agents=_force_agents)
            if not _force_agents:
                analysis.agents = agents

            print(f"\n📋 Using {len(agents)} agent(s) from plan: "
                  f"{', '.join(agents)}")

        else:
            # Plan file doesn't exist — generate and save
            if not args.task:
                print("❌ No task provided and no existing plan file found.")
                print("   Provide a task or point --plan to an existing file.")
                sys.exit(1)

            task = " ".join(args.task)
            print(f"\n📋 Analyzing task...")
            analysis = TaskAnalysis(task, force_agents=_force_agents)
            plan_content = generate_plan(analysis)
            saved = save_plan(plan_content, plan_path)
            print(f"\n📄 New plan saved to: {saved}")

            if args.dry_run:
                print(plan_content)
                print("\n--- End of dry run ---")
                return

            if args.plan_only:
                print(plan_content)
                print(f"\n📄 Plan file: {saved}")
                print("   Edit the plan, then re-run with the same --plan flag.")
                return

            if not review_plan(plan_content, auto_approve=False):
                sys.exit(1)

            task = " ".join(args.task)
            analysis = TaskAnalysis(task, force_agents=_force_agents)
            agents = analysis.agents

        # --- Execute from plan ---
        yolo_flag = args.yes

        if args.background:
            # Spawn background worker
            _spawn_background_worker(
                task_id=_tui_mod.get_next_id(),
                task_desc=task,
                agents=agents,
                mode="sequential" if args.sequential else "parallel",
                max_parallel=args.max_parallel,
                yolo=yolo_flag,
                notify=args.notify or "hermes",
            )
            return

        if args.sequential:
            results = run_agents_sequential(
                agents, task, analysis, yolo=yolo_flag
            )
        else:
            results = run_agents_parallel(
                agents, task, analysis, args.max_parallel,
                yolo=yolo_flag
            )

        report = aggregate_results(results, analysis)
        print(f"\n{report}")

        save_path = args.save
        if not save_path:
            REPORTS_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = REPORTS_DIR / f"orchestration_{timestamp}.md"

        Path(save_path).write_text(report, encoding="utf-8")
        print(f"\n📄 Report saved to: {save_path}")
        return

    # ================================================================
    # PHASE 1: Task is required for non-plan-file mode
    # ================================================================

    if not args.task:
        parser.print_usage()
        print("orchestrator.py: error: the following arguments are required: task")
        print("  (or use --plan to load an existing plan file)")
        sys.exit(2)

    task = " ".join(args.task)

    # Banner
    print()
    print("=" * 60)
    print("  PLAN-FIRST ORCHESTRATION")
    print("=" * 60)

    # ================================================================
    # PHASE 2: Analyze
    # ================================================================
    print(f"\n📋 Analyzing task...")
    analysis = TaskAnalysis(task, force_agents=_force_agents)

    print(f"\n{analysis.summary()}")

    # ================================================================
    # PHASE 3: Plan
    # ================================================================
    plan_content = generate_plan(analysis)

    # Save plan to a temp path for potential editing
    plan_save_path = save_plan(plan_content)

    # ================================================================
    # PHASE 4: Review (unless --dry-run or --plan-only)
    # ================================================================

    if args.dry_run:
        print()
        print("─" * 60)
        print("DRY RUN — no agents will be spawned")
        print("─" * 60)
        print(f"\n{plan_content}")
        print("\n--- End of dry run ---")
        return

    if args.plan_only:
        print()
        print(f"\n{plan_content}")
        print(f"\n📄 Plan saved to: {plan_save_path}")
        print("   Edit the plan file if needed, then execute with:")
        print(f"     python3 orchestrator.py --plan {plan_save_path}")
        return

    approved = review_plan(plan_content, auto_approve=args.auto_approve)
    if not approved:
        sys.exit(1)

    # ================================================================
    # PHASE 5: Execute
    # ================================================================
    yolo_flag = args.yes

    if args.background:
        _spawn_background_worker(
            task_id=_tui_mod.get_next_id(),
            task_desc=task,
            agents=analysis.agents,
            mode="sequential" if args.sequential else "parallel",
            max_parallel=args.max_parallel,
            yolo=yolo_flag,
            notify=args.notify or "hermes",
        )
        return

    if args.sequential:
        results = run_agents_sequential(
            analysis.agents, task, analysis, yolo=yolo_flag
        )
    else:
        results = run_agents_parallel(
            analysis.agents, task, analysis, args.max_parallel,
            yolo=yolo_flag
        )

    # ================================================================
    # PHASE 6: Report
    # ================================================================
    report = aggregate_results(results, analysis)
    print(f"\n{report}")

    # ================================================================
    # PHASE 7: Save
    # ================================================================
    save_path = args.save
    if not save_path:
        REPORTS_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = REPORTS_DIR / f"orchestration_{timestamp}.md"

    Path(save_path).write_text(report, encoding="utf-8")
    print(f"\n📄 Report saved to: {save_path}")


if __name__ == "__main__":
    main()
