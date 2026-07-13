#!/usr/bin/env python3
"""
Smart Agent Router — intelligent agent recommendation engine.

Analyzes task descriptions using weighted scoring against a YAML routing
config to recommend the best agents for the job.

Usage:
    python3 agent-router.py "Fix authentication token bug"
    python3 agent-router.py "Add user login feature" --json
    python3 agent-router.py "Refactor code" --force-agents coder,reviewer
    python3 agent-router.py "Write tests" --interactive

Features:
    - Weighted density scoring (not simple keyword match)
    - YAML config — add categories without code changes
    - JSON output for orchestrator integration
    - Force override specific agents
    - Interactive mode with manual override
    - Task type classification with confidence score
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


# ── Paths ──────────────────────────────────────────────────────────

REPO_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_DIR / "config"
ROUTING_FILE = CONFIG_DIR / "routing.yaml"
CAPABILITIES_FILE = CONFIG_DIR / "agent-capabilities.yaml"


# ── Data structures ────────────────────────────────────────────────

class CategoryScore:
    """Score for a single routing category."""

    def __init__(self, name: str, score: float, matched: list[str],
                 density: float, agents: list[str]):
        self.name = name
        self.score = round(score, 4)
        self.matched = matched
        self.density = round(density, 4)
        self.agents = agents

    def __repr__(self):
        return (f"CategoryScore(name={self.name}, score={self.score:.2f}, "
                f"matched={self.matched})")


class RoutingResult:
    """Result of routing a task through the agent router."""

    def __init__(self, task: str):
        self.task = task
        self.category_scores: list[CategoryScore] = []
        self.recommended: list[str] = []
        self.confidence: float = 0.0
        self.reasoning: list[str] = []
        self.force_agents: list[str] | None = None

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "scores": {cs.name: cs.score for cs in self.category_scores},
            "details": [
                {
                    "category": cs.name,
                    "score": cs.score,
                    "matched": cs.matched,
                    "density": cs.density,
                    "agents": cs.agents,
                }
                for cs in self.category_scores
            ],
            "recommended": self.recommended,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
            "force_agents": self.force_agents,
        }

    def summary(self) -> str:
        lines = [
            f"Task: {self.task}",
            "",
            f"  {'Category':<18} {'Score':>6}  {'Agents':<30}",
            f"  {'─'*18} {'─'*6}  {'─'*30}",
        ]
        for cs in self.category_scores:
            agent_str = ", ".join(cs.agents)
            bar = self._score_bar(cs.score)
            lines.append(
                f"  {cs.name:<18} {cs.score:.2f}  {agent_str:<30} {bar}"
            )

        lines.extend([
            "",
            f"  Recommended: {', '.join(self.recommended)}",
            f"  Confidence:  {self.confidence:.0%}",
        ])
        if self.reasoning:
            lines.append("")
            lines.append("  Reasoning:")
            for r in self.reasoning:
                lines.append(f"    • {r}")
        return "\n".join(lines)

    @staticmethod
    def _score_bar(score: float, width: int = 12) -> str:
        filled = max(0, min(width, int(score * width)))
        bar = "█" * filled + "░" * (width - filled)
        return bar


# ── Config Loader ──────────────────────────────────────────────────

def load_routing_config(path: Path = ROUTING_FILE) -> dict:
    """Load routing rules from YAML file.

    Returns dict with 'categories' key, or empty dict on failure.
    """
    if yaml is None:
        return {"categories": {}}
    if not path.exists():
        return {"categories": {}}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {"categories": {}}
    except Exception:
        return {"categories": {}}


def load_agent_capabilities(path: Path = CAPABILITIES_FILE) -> dict:
    """Load agent capabilities from YAML file.

    Returns dict with 'agents' key, or empty dict on failure.
    """
    if yaml is None:
        return {"agents": {}}
    if not path.exists():
        return {"agents": {}}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {"agents": {}}
    except Exception:
        return {"agents": {}}


# ── Scoring Engine ─────────────────────────────────────────────────

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "be", "this",
    "that", "it", "its", "we", "they", "you", "i", "my", "me",
}


def tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, removing stop words."""
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]*", text.lower())
    return [t for t in tokens if t not in STOP_WORDS]


def count_keyword_matches(tokens: list[str], keywords: list[str]) -> int:
    """Count how many unique keywords appear in the token list.

    Handles multi-word keywords (e.g. 'sql injection') by checking
    n-grams of the matching length. Also handles stemming:
    keyword 'auth' matches 'authentication', 'auth', 'auths', etc.
    """
    text = " ".join(tokens)
    matched = set()
    for kw in keywords:
        kw_lower = kw.lower()
        if " " in kw_lower:
            # Multi-word keyword — check contiguous bigram match
            if kw_lower in text:
                matched.add(kw_lower)
        else:
            # Direct match
            if kw_lower in tokens:
                matched.add(kw_lower)
                continue
            # Stemming: check if any token starts with the keyword
            # e.g. 'auth' matches 'auth', 'authentication', 'authorize'
            if any(t.startswith(kw_lower) for t in tokens):
                matched.add(kw_lower)
    return len(matched)


def compute_specificity(keyword: str, all_keywords: list[str]) -> float:
    """Compute TF-IDF-like specificity: rare keywords score higher.

    A keyword that appears in fewer categories is more specific.
    Returns a multiplier between 0.5 and 2.0.
    """
    # Rough approximation: shorter keywords are more common
    length = len(keyword)
    if length <= 2:
        return 0.5
    elif length <= 4:
        return 0.8
    elif length <= 6:
        return 1.0
    elif length <= 10:
        return 1.3
    else:
        return 1.6


def route_task(
    task: str,
    routing_config: Optional[dict] = None,
    force_agents: Optional[list[str]] = None,
) -> RoutingResult:
    """Route a task to the best agents.

    Args:
        task: The task description to analyze.
        routing_config: Routing config dict. Auto-loaded if None.
        force_agents: If set, skip scoring and return these agents.

    Returns:
        RoutingResult with scores and recommendations.
    """
    result = RoutingResult(task)

    if force_agents:
        result.force_agents = force_agents
        result.recommended = force_agents
        result.confidence = 1.0
        result.reasoning = [f"Agents forced by user: {', '.join(force_agents)}"]
        return result

    if routing_config is None:
        routing_config = load_routing_config()

    categories = routing_config.get("categories", {})
    if not categories:
        # Fallback: default to coder
        result.recommended = ["coder"]
        result.confidence = 0.5
        result.reasoning = [
            "No routing config found — defaulting to coder"
        ]
        return result

    tokens = tokenize(task)
    text = " ".join(tokens)
    all_scores: list[CategoryScore] = []

    for cat_name, cat_config in categories.items():
        keywords = cat_config.get("keywords", [])
        weight = cat_config.get("weight", 0.5)
        min_conf = cat_config.get("min_confidence", 0.0)
        agents = cat_config.get("agents", ["coder"])

        # Count matched keywords (using count_keyword_matches for stemming)
        matched_count = count_keyword_matches(tokens, keywords)

        if matched_count == 0:
            continue

        # Extract actual matched keywords for reporting
        matched = []
        for kw in keywords:
            kw_lower = kw.lower()
            if " " in kw_lower:
                if kw_lower in text:
                    matched.append(kw)
            else:
                if kw_lower in tokens or any(t.startswith(kw_lower) for t in tokens):
                    matched.append(kw)

        # Compute density: matched / total_task_tokens (not category keywords)
        # This ensures short tasks with good matches score higher
        total_tokens = max(len(tokens), 1)
        density = matched_count / total_tokens

        # Compute specificity bonus
        specificity_bonus = 1.0
        if matched:
            avg_specificity = sum(
                compute_specificity(m, keywords) for m in matched
            ) / len(matched)
            specificity_bonus = avg_specificity

        # Final score: density × weight × specificity
        score = density * weight * specificity_bonus

        if score >= min_conf:
            all_scores.append(
                CategoryScore(cat_name, score, matched, density, agents)
            )

    # Sort by score descending
    all_scores.sort(key=lambda cs: cs.score, reverse=True)
    result.category_scores = all_scores

    # Build recommended agent list (preserving order, deduped)
    seen_agents: set[str] = set()
    recommended: list[str] = []

    # Top 3 categories contribute agents
    for cs in all_scores[:3]:
        for agent in cs.agents:
            if agent not in seen_agents:
                seen_agents.add(agent)
                recommended.append(agent)
                result.reasoning.append(
                    f"{cs.name} (score={cs.score:.2f}): "
                    f"'{', '.join(cs.matched)}' → {agent}"
                )

    if not recommended:
        recommended = ["coder"]
        result.reasoning.append("No matching categories — defaulting to coder")

    result.recommended = recommended

    # Confidence = weighted average of top scores
    if all_scores:
        top_scores = [cs.score for cs in all_scores[:3]]
        result.confidence = min(1.0, sum(top_scores) / len(top_scores))

    return result


# ── CLI ────────────────────────────────────────────────────────────

def print_table(result: RoutingResult):
    """Print a formatted routing result table."""
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║              SMART AGENT ROUTER                     ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    print(result.summary())
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Smart Agent Router — recommend agents for a task"
    )
    parser.add_argument(
        "task",
        nargs="*",
        help="Task description to route"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (for orchestrator integration)"
    )
    parser.add_argument(
        "--force-agents",
        type=str,
        default=None,
        metavar="AGENTS",
        help="Skip routing and force specific agents (comma-separated)"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Show scores and allow manual agent override"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List all available agents with capabilities"
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List all routing categories with keywords"
    )

    args = parser.parse_args()

    # Handle list modes
    if args.list_agents:
        caps = load_agent_capabilities()
        agents = caps.get("agents", {})
        if not agents:
            print("No agent capabilities found. Check agent-capabilities.yaml")
            return
        print(f"\nAvailable Agents ({len(agents)}):")
        print("=" * 60)
        for name, info in agents.items():
            strengths = ", ".join(info.get("strengths", []))
            print(f"  {name:<14} — {info.get('description', '')}")
            print(f"  {'':14}   strengths: {strengths}")
            print()
        return

    if args.list_categories:
        config = load_routing_config()
        cats = config.get("categories", {})
        if not cats:
            print("No routing categories found. Check routing.yaml")
            return
        print(f"\nRouting Categories ({len(cats)}):")
        print("=" * 60)
        for name, info in cats.items():
            kw = ", ".join(info.get("keywords", [])[:8])
            agents = ", ".join(info.get("agents", []))
            extra = f"+{len(info.get('keywords', [])) - 8} more" \
                if len(info.get("keywords", [])) > 8 else ""
            print(f"  {name:<14} weight={info.get('weight', 0.5):.2f} "
                  f"→ [{agents}]")
            print(f"  {'':14}   keywords: {kw}{extra}")
            print()
        return

    # Task is required for routing
    if not args.task:
        parser.print_usage()
        print("agent-router.py: error: task description is required")
        sys.exit(2)

    task = " ".join(args.task)

    # Parse force agents
    force = None
    if args.force_agents:
        force = [a.strip() for a in args.force_agents.split(",")]

    # Route
    config = load_routing_config()
    result = route_task(task, config, force_agents=force)

    # Interactive mode
    if args.interactive and not force:
        print()
        print("=" * 60)
        print("  SMART AGENT ROUTER — Interactive")
        print("=" * 60)
        print()
        print(result.summary())
        print()
        try:
            response = input(
                "Choose agents to use (comma-separated), or press Enter\n"
                f"  Recommended: {', '.join(result.recommended)}\n"
                "  Agents > "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)

        if response:
            custom = [a.strip() for a in response.split(",")]
            result.recommended = custom
            result.confidence = 1.0
            result.reasoning.append(
                f"User override: {', '.join(custom)}"
            )

        print(f"\n✅ Using agents: {', '.join(result.recommended)}")

    # Output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print_table(result)


if __name__ == "__main__":
    main()
