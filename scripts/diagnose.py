#!/usr/bin/env python3
"""Tank World environment health check.

Run this when something is broken and you are not sure where. It prints a
green/red checklist covering the Python toolchain, core modules, the algorithm
registry, a live (short) simulation, and the frontend toolchain — turning
"it's broken somewhere" into a precise pointer.

Usage:
    python scripts/diagnose.py
    python scripts/diagnose.py --no-color

Exit code is 0 when every required check passes, 1 otherwise. Warnings (for
optional tooling like Node or pre-commit) never fail the run.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import os
import shutil
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_ALGORITHM_COUNT = 58


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
class Style:
    """ANSI styling that disables itself when output is not a TTY."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def green(self, t: str) -> str:
        return self._wrap("32", t)

    def red(self, t: str) -> str:
        return self._wrap("31", t)

    def yellow(self, t: str) -> str:
        return self._wrap("33", t)

    def bold(self, t: str) -> str:
        return self._wrap("1", t)

    def dim(self, t: str) -> str:
        return self._wrap("2", t)


# Check outcomes
OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass
class Result:
    status: str
    title: str
    detail: str = ""
    hint: str = ""


def _icon(style: Style, status: str) -> str:
    if status == OK:
        return style.green("PASS")
    if status == WARN:
        return style.yellow("WARN")
    return style.red("FAIL")


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def check_python_version() -> Result:
    major, minor = sys.version_info[:2]
    version = f"{major}.{minor}.{sys.version_info.micro}"
    if (major, minor) >= (3, 10):
        return Result(OK, "Python version", f"{version} (>= 3.10)")
    return Result(
        FAIL,
        "Python version",
        f"{version} is too old",
        hint="Tank World requires Python 3.10+ (see pyproject.toml).",
    )


def check_dependencies() -> Result:
    required = ["numpy", "fastapi", "uvicorn", "pydantic", "orjson", "websockets"]
    missing = []
    for mod in required:
        if importlib.util.find_spec(mod) is None:
            missing.append(mod)
    if not missing:
        return Result(OK, "Python dependencies", f"{len(required)} core packages present")
    return Result(
        FAIL,
        "Python dependencies",
        f"missing: {', '.join(missing)}",
        hint="Install the project: pip install -e .[dev]",
    )


def check_core_imports() -> Result:
    modules = [
        "core.simulation.engine",
        "core.algorithms.registry",
        "core.worlds",
        "backend.main",
    ]
    failures = []
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as exc:
            failures.append(f"{mod} ({type(exc).__name__}: {exc})")
    if not failures:
        return Result(OK, "Core modules", f"{len(modules)} modules import cleanly")
    return Result(
        FAIL,
        "Core modules",
        "; ".join(failures),
        hint="A broken import usually means an editable install is stale: pip install -e .",
    )


def check_algorithm_registry() -> Result:
    try:
        from core.algorithms.registry import ALL_ALGORITHMS
    except Exception as exc:
        return Result(
            FAIL,
            "Algorithm registry",
            f"could not import ALL_ALGORITHMS ({type(exc).__name__}: {exc})",
            hint="Check core/algorithms/registry.py imports.",
        )

    count = len(ALL_ALGORITHMS)
    if count == 0:
        return Result(FAIL, "Algorithm registry", "registry is empty")
    if count != EXPECTED_ALGORITHM_COUNT:
        return Result(
            WARN,
            "Algorithm registry",
            f"{count} algorithms registered (docs reference {EXPECTED_ALGORITHM_COUNT})",
            hint="If this is intentional, update the count in docs/BEHAVIOR_DEVELOPMENT_GUIDE.md.",
        )
    return Result(OK, "Algorithm registry", f"{count} behavior algorithms registered")


def check_simulation_smoke(frames: int = 50) -> Result:
    try:
        from core.worlds import WorldRegistry

        world = WorldRegistry.create_world("tank", seed=42, headless=True)
        world.reset(seed=42)
        advance = getattr(world, "update", None) or world.step
        start = time.perf_counter()
        for _ in range(frames):
            advance()
        elapsed = time.perf_counter() - start
        metrics = world.get_current_metrics(include_distributions=False)
    except Exception as exc:
        return Result(
            FAIL,
            "Simulation smoke test",
            f"{type(exc).__name__}: {exc}",
            hint="Run with TANK_LOG_LEVEL=DEBUG for a fuller trace.",
        )

    fish = metrics.get("fish_count")
    if not fish:
        return Result(
            WARN,
            "Simulation smoke test",
            f"ran {frames} frames but fish_count is {fish!r}",
            hint="Population collapsed immediately — check spawn/energy config.",
        )
    rate = frames / elapsed if elapsed else float("inf")
    return Result(
        OK,
        "Simulation smoke test",
        f"{frames} frames OK, {fish} fish alive ({rate:.0f} fps headless)",
    )


def check_frontend_deps() -> Result:
    node_modules = REPO_ROOT / "frontend" / "node_modules"
    if node_modules.is_dir():
        return Result(OK, "Frontend dependencies", "frontend/node_modules present")
    return Result(
        WARN,
        "Frontend dependencies",
        "frontend/node_modules missing",
        hint="The web UI needs them: cd frontend && npm install",
    )


def check_node_toolchain() -> Result:
    npm = shutil.which("npm")
    node = shutil.which("node")
    if npm and node:
        return Result(OK, "Node toolchain", "node and npm on PATH")
    missing = [name for name, found in (("node", node), ("npm", npm)) if not found]
    return Result(
        WARN,
        "Node toolchain",
        f"missing from PATH: {', '.join(missing)}",
        hint="Node 20+ is needed only for the web UI; headless mode does not require it.",
    )


def check_precommit() -> Result:
    hook = REPO_ROOT / ".git" / "hooks" / "pre-commit"
    if hook.exists():
        return Result(OK, "Pre-commit hook", "installed")
    return Result(
        WARN,
        "Pre-commit hook",
        "not installed",
        hint="Enable auto-formatting/linting on commit: pre-commit install",
    )


CHECKS = [
    check_python_version,
    check_dependencies,
    check_core_imports,
    check_algorithm_registry,
    check_simulation_smoke,
    check_frontend_deps,
    check_node_toolchain,
    check_precommit,
]


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def run_diagnostics(style: Style) -> int:
    """Run every check, print a checklist, and return a process exit code."""
    print(style.bold("Tank World — environment diagnostics"))
    print(style.dim(f"repo: {REPO_ROOT}"))
    print()

    results: list[Result] = []
    for check in CHECKS:
        try:
            result = check()
        except Exception as exc:
            result = Result(
                FAIL,
                check.__name__,
                f"check raised {type(exc).__name__}: {exc}",
                hint=style.dim(traceback.format_exc(limit=1).strip()),
            )
        results.append(result)
        line = f"  [{_icon(style, result.status)}] {result.title}"
        if result.detail:
            line += f"  {style.dim('—')} {result.detail}"
        print(line)
        if result.hint and result.status != OK:
            print(f"           {style.dim('→ ' + result.hint)}")

    failures = sum(1 for r in results if r.status == FAIL)
    warnings = sum(1 for r in results if r.status == WARN)
    passes = sum(1 for r in results if r.status == OK)

    print()
    summary = f"{passes} passed, {warnings} warning(s), {failures} failure(s)"
    if failures:
        print(style.red(style.bold("✗ " + summary)))
        print(style.dim("  Fix the FAIL items above before running the simulation."))
        return 1
    if warnings:
        print(style.yellow(style.bold("✓ " + summary)))
        print(style.dim("  Core is healthy; warnings are optional tooling."))
        return 0
    print(style.green(style.bold("✓ " + summary + " — all good!")))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Tank World environment health check")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    args = parser.parse_args()

    # Keep simulation/backend import logging quiet so the checklist stays readable.
    logging.disable(logging.CRITICAL)

    color = not args.no_color and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    return run_diagnostics(Style(enabled=color))


if __name__ == "__main__":
    sys.exit(main())
