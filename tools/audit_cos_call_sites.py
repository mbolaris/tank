"""Audit which core/ math.cos call sites are actually exercised by the
CI-gated determinism benchmarks, and whether perturbing each live site's
result changes that benchmark's final score.

Context: docs/CROSS_PLATFORM_DIVERGENCE.md found that Windows and CI-Linux
disagree on math.cos in the last ulp. The genetics mutation sampler (the
worst offender) was fixed in PR #914 by replacing random.gauss. 34
math.cos call sites remain in core/ movement, steering, and physics code,
and not all of them are necessarily reachable by a benchmark whose score
CI actually gates on. This tool answers two questions per call site:

1. Reached: does it ever execute during a real run of each gated benchmark?
   A call site that is never reached cannot move that benchmark's score,
   regardless of platform.
2. Sensitive: for reached call sites, does perturbing the returned value by
   a tiny (1e-9 relative) epsilon change the benchmark's final score on one
   platform? A perturbation of that size is far larger than a last-ulp
   difference (~1e-16), so a call site that stays sensitive at 1e-9 is
   certainly sensitive to a real cross-platform ulp difference; a call site
   that is NOT sensitive even at 1e-9 is very unlikely to matter at 1e-16.

Usage:
    python tools/audit_cos_call_sites.py
"""

from __future__ import annotations

import ast
import importlib
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = REPO_ROOT / "core"


@dataclass
class CallSite:
    file: str
    line: int
    func: str


class _CosCallVisitor(ast.NodeVisitor):
    """Collects math.cos(...) call sites for one file, tracking which
    function each call falls inside."""

    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        self.func_stack: list[str] = []
        self.sites: list[CallSite] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.func_stack.append(node.name)
        self.generic_visit(node)
        self.func_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        fn = node.func
        if (
            isinstance(fn, ast.Attribute)
            and fn.attr == "cos"
            and isinstance(fn.value, ast.Name)
            and fn.value.id == "math"
        ):
            self.sites.append(
                CallSite(
                    file=self.rel_path,
                    line=node.lineno,
                    func=self.func_stack[-1] if self.func_stack else "<module>",
                )
            )
        self.generic_visit(node)


def find_call_sites() -> list[CallSite]:
    """Statically locate every math.cos(...) call in core/ via AST (not grep,
    so it can't be fooled by a docstring that merely mentions math.cos)."""
    sites: list[CallSite] = []
    for path in sorted(CORE_DIR.rglob("*.py")):
        if "__pycache__" in path.parts or path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(REPO_ROOT).as_posix()
        visitor = _CosCallVisitor(rel)
        visitor.visit(tree)
        sites.extend(visitor.sites)
    return sites


# --- Reachability tracking -------------------------------------------------

_hits: dict[tuple[str, int], int] = {}
_real_cos = math.cos


def _tracking_cos(x: float) -> float:
    frame = sys._getframe(1)
    filename = frame.f_code.co_filename
    try:
        rel = str(Path(filename).resolve().relative_to(REPO_ROOT).as_posix())
    except ValueError:
        rel = filename
    key = (rel, frame.f_lineno)
    _hits[key] = _hits.get(key, 0) + 1
    return _real_cos(x)


def install_tracking() -> None:
    _hits.clear()
    math.cos = _tracking_cos  # type: ignore[assignment]


def uninstall_tracking() -> dict[tuple[str, int], int]:
    math.cos = _real_cos
    return dict(_hits)


# --- Sensitivity perturbation -----------------------------------------------


def install_perturbed_cos(epsilon: float = 1e-9) -> None:
    def _perturbed(x: float) -> float:
        return _real_cos(x) * (1.0 + epsilon)

    math.cos = _perturbed  # type: ignore[assignment]


def uninstall_perturbed() -> None:
    math.cos = _real_cos


# --- Benchmark probes --------------------------------------------------------


@dataclass
class Probe:
    name: str
    module: str
    seed: int = 42
    frame_override: int | None = None
    sensitivity: bool = True

    def run(self) -> dict[str, Any]:
        mod = importlib.import_module(self.module)
        original_frames = getattr(mod, "FRAMES", None)
        if self.frame_override is not None and original_frames is not None:
            mod.FRAMES = self.frame_override  # type: ignore[attr-defined]
        try:
            result: dict[str, Any] = mod.run(self.seed)
        finally:
            if original_frames is not None:
                mod.FRAMES = original_frames  # type: ignore[attr-defined]
        return result


PROBES = [
    # CI-gated (verify-champions / champion-tracked) benchmarks.
    Probe("tank/survival_5k", "benchmarks.tank.survival_5k", frame_override=1500),
    Probe("tank/ecosystem_health_10k", "benchmarks.tank.ecosystem_health_10k", frame_override=1500),
    Probe("soccer/training_5k", "benchmarks.soccer.training_5k", frame_override=1500),
    Probe("soccer/ladder_5k", "benchmarks.soccer.ladder_5k", frame_override=1500),
    Probe("poker/ladder_20k", "benchmarks.poker.ladder_20k", sensitivity=False),
    # Not CI-gated for determinism, but still real project benchmarks - run
    # reachability only, to confirm the "unreached by champions" call sites
    # are exercised by *something* rather than orphaned dead code.
    Probe("tank/foraging_gym", "benchmarks.tank.foraging_gym", sensitivity=False),
    Probe("tank/pursuit_transfer", "benchmarks.tank.pursuit_transfer", sensitivity=False),
    Probe(
        "tank/target_memory_transfer", "benchmarks.tank.target_memory_transfer", sensitivity=False
    ),
]


def main() -> None:
    sites = find_call_sites()
    print(f"Found {len(sites)} static math.cos(...) call sites in core/\n")
    for site in sites:
        print(f"  {site.file}:{site.line} (in {site.func})")
    print()

    reached_by: dict[str, set[tuple[str, int]]] = {}
    scores: dict[str, float] = {}

    for probe in PROBES:
        print(f"=== Reachability probe: {probe.name} ({probe.frame_override} frames) ===")
        install_tracking()
        try:
            result = probe.run()
        except Exception as exc:
            print(f"  ERROR running probe: {exc}")
            uninstall_tracking()
            continue
        hits = uninstall_tracking()
        cos_hits = {k: v for k, v in hits.items() if k[0].startswith("core/")}
        reached_by[probe.name] = set(cos_hits)
        scores[probe.name] = result.get("score", float("nan"))
        print(f"  score={scores[probe.name]}")
        for (file, line), count in sorted(cos_hits.items()):
            print(f"  reached: {file}:{line} x{count}")
        print()

    print("=== Call-site reachability matrix ===")
    header = "file:line".ljust(55) + "".join(p.name.ljust(28) for p in PROBES)
    print(header)
    for site in sites:
        key = (site.file, site.line)
        row = f"{site.file}:{site.line}".ljust(55)
        for probe in PROBES:
            mark = "REACHED" if key in reached_by.get(probe.name, set()) else "-"
            row += mark.ljust(28)
        print(row)

    # Sensitivity pass: for each probe, re-run with perturbed cos and diff score.
    print("\n=== Sensitivity: perturbed (1e-9 relative) cos vs baseline ===")
    for probe in PROBES:
        if not probe.sensitivity or probe.name not in scores:
            continue
        install_perturbed_cos()
        try:
            perturbed_result = probe.run()
        except Exception as exc:
            print(f"{probe.name}: ERROR {exc}")
            uninstall_perturbed()
            continue
        uninstall_perturbed()
        perturbed_score = perturbed_result.get("score", float("nan"))
        baseline_score = scores.get(probe.name, float("nan"))
        diverged = perturbed_score != baseline_score
        print(
            f"{probe.name}: baseline={baseline_score} perturbed={perturbed_score} "
            f"{'DIVERGED' if diverged else 'IDENTICAL'}"
        )


if __name__ == "__main__":
    main()
