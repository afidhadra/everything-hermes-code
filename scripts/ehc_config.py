#!/usr/bin/env python3
"""
Config loader for EHC tools.
Reads .ehc.yaml from project root or --config path.
"""

import os
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None


DEFAULT_CONFIG_PATHS = [
    Path.cwd() / ".ehc.yaml",
    Path.cwd() / ".ehc.yml",
    Path.home() / ".ehc.yaml",
]


def find_config(explicit: Optional[str] = None) -> Optional[Path]:
    """Find config file from explicit path, CWD, or home."""
    if explicit:
        p = Path(explicit).expanduser()
        if p.exists():
            return p
        return None

    for p in DEFAULT_CONFIG_PATHS:
        if p.exists():
            return p

    return None


def load_config(explicit: Optional[str] = None) -> dict:
    """Load and parse .ehc.yaml config file.
    
    Returns dict with keys:
        project: {name, root}
        repos: {be: {...}, fe: {...}}
        deploy: {dir, compose_dev, compose_prod, ...}
        docker: {containers: {...}}
        services: [...]
    
    Returns empty dict if no config found (tools use built-in defaults).
    """
    if yaml is None:
        return {}

    path = find_config(explicit)
    if path is None:
        return {}

    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception as e:
        print(f"Warning: could not parse {path}: {e}", file=sys.stderr)
        return {}


def expand_path(path_str: str) -> str:
    """Expand ~ and env vars in path."""
    return os.path.expanduser(os.path.expandvars(path_str))


def get_repos(config: dict) -> dict:
    """Get repo configs. Falls back to frozen-pos defaults."""
    repos = config.get("repos", {})
    if not repos:
        # Built-in defaults for frozen-pos
        root = expand_path("~/Projects/Freelance/FROZEN-POS")
        return {
            "be": {
                "name": "Backend",
                "dir": "frozen-pos-api",
                "lang": "go",
                "container": "frozen-pos-api-dev",
                "health_url": "http://localhost:8080/api/v1/health",
                "compose_service": "api",
            },
            "fe": {
                "name": "Frontend",
                "dir": "frozen-pos-frontend",
                "lang": "vue",
                "container": "frozen-pos-frontend-dev",
                "health_url": "http://localhost:5173",
                "compose_service": "frontend",
            },
        }
    
    # Expand paths
    for key, repo in repos.items():
        if "dir" in repo:
            repo["dir"] = expand_path(repo["dir"])
    return repos


def get_project_root(config: dict) -> str:
    """Get project root path."""
    root = config.get("project", {}).get("root", "~/Projects/Freelance/FROZEN-POS")
    return expand_path(root)


def get_deploy_config(config: dict) -> dict:
    """Get deploy configuration."""
    deploy = config.get("deploy", {})
    return {
        "dir": deploy.get("dir", "inventory-deploy"),
        "compose_dev": deploy.get("compose_dev", "docker-compose.dev.yml"),
        "compose_prod": deploy.get("compose_prod", "docker-compose.prod.yml"),
        "health_timeout": deploy.get("health_timeout", 60),
        "health_interval": deploy.get("health_interval", 2),
    }


def get_docker_containers(config: dict) -> dict:
    """Get docker container configs."""
    return config.get("docker", {}).get("containers", {})


def get_services(config: dict) -> list:
    """Get service health check configs."""
    return config.get("services", [])


def list_available_configs() -> list[Path]:
    """Find all .ehc.yaml files under ~/Projects."""
    results = []
    projects = Path.home() / "Projects"
    if not projects.is_dir():
        return results

    for p in projects.rglob(".ehc.yaml"):
        results.append(p)
    return results
