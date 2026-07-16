"""Tests to prevent architectural anti-patterns.

These tests enforce code quality constraints to prevent regression
as the codebase grows.

The "god class" ratchet
-----------------------
New files must stay under ``MAX_LINES_FOR_NEW_FILES``. Files that already
exceed it are grandfathered in ``LEGACY_MAX_LINES``, but each is pinned to
its *current* size as a ceiling. This makes the ratchet only ever tighten:

- A legacy file may shrink freely, but may **not** regrow past its pin.
- When a legacy file is refactored below the limit (or deleted),
  ``test_legacy_list_is_current`` fails until it is removed from
  ``LEGACY_MAX_LINES`` — so wins are harvested, not forgotten.

To re-pin after an intentional, reviewed change, set the value to the new
line count (lowering it whenever you shrink a file keeps the ratchet honest).
The pins are real, enforced numbers — not comments that can drift.
"""

from pathlib import Path

# Files exceeding MAX_LINES_FOR_NEW_FILES, pinned to their current size and
# keyed by repo-relative path. The ratchet only tightens: shrink a file and
# lower its pin; drop it from this dict once it is under the limit.
LEGACY_MAX_LINES: dict[str, int] = {
    "backend/runner/hooks/entity_details_mixin.py": 577,
    "backend/simulation_runner.py": 732,
    "backend/startup_manager.py": 626,
    "backend/state_payloads.py": 809,
    "backend/world_manager.py": 712,
    "backend/world_persistence.py": 636,
    "core/algorithms/base.py": 572,
    "core/algorithms/registry.py": 584,
    "core/behavior/target_memory_transfer_gym.py": 630,
    "core/code_pool/genome_code_pool.py": 641,
    "core/collision_system.py": 509,
    "core/ecosystem.py": 638,
    "core/environment.py": 512,
    "core/evolution_analytics.py": 657,
    "core/entities/fish.py": 810,
    "core/entities/plant.py": 727,
    "core/genetics/plant_genome.py": 761,
    "core/interfaces.py": 665,
    "core/minigames/soccer/engine.py": 778,
    "core/mixed_poker/interaction.py": 728,
    "core/poker/evaluation/auto_evaluate_poker.py": 594,
    "core/poker/evaluation/comprehensive_benchmark.py": 601,
    "core/poker/evaluation/evolution_benchmark_tracker.py": 727,
    "core/poker/human_poker_game.py": 863,
    "core/poker/integration/poker_system.py": 577,
    "core/poker/simulation/hand_engine.py": 754,
    "core/poker/stats/poker_stats_manager.py": 581,
    "core/poker/strategy/composable/strategy.py": 781,
    "core/pursuit/transfer_gym.py": 733,
    "core/reproduction/reproduction_service.py": 547,
    "core/simulation/engine.py": 609,
    "core/solutions/benchmark.py": 549,
    "core/solutions/tracker.py": 590,
    "core/spatial/grid.py": 795,
    "core/transfer/entity_transfer.py": 776,
    # Curated taxonomy lexicons are intentionally kept together so common and
    # scientific names use the same deterministic salience vocabulary.
    "core/taxonomy/naming.py": 523,
    "core/worlds/tank/backend.py": 629,
    "frontend/src/components/AutoEvaluateDisplay.tsx": 656,
    "frontend/src/components/EcosystemStats.tsx": 513,
    "frontend/src/components/EntityInspectorDrawer.tsx": 625,
    "frontend/src/components/TankNetworkMap.tsx": 725,
    "frontend/src/components/TankView.tsx": 593,
    "frontend/src/components/tank_tabs/TankPokerTab.tsx": 532,
    "frontend/src/components/tank_tabs/TankTrendsTab.tsx": 1203,
    "frontend/src/pages/NetworkDashboard.tsx": 1046,
    "frontend/src/renderers/avatar_renderer.ts": 555,
    "frontend/src/renderers/petri/PetriTopDownRenderer.ts": 1392,
    "frontend/src/renderers/tank/TankTopDownRenderer.ts": 1267,
    "frontend/src/types/simulation.ts": 889,
    "frontend/src/utils/plants/nectar.ts": 616,
    "frontend/src/utils/plants/renderers.ts": 1042,
    "frontend/src/utils/renderer.ts": 673,
    "tools/evolve.py": 554,
    "tools/validate_improvement.py": 566,
}

# Maximum allowed lines for files not grandfathered in LEGACY_MAX_LINES.
MAX_LINES_FOR_NEW_FILES = 500


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _get_monitored_source_files() -> list[Path]:
    """Get all monitored Python and Frontend source files."""
    import os

    repo_root = _repo_root()
    source_files: list[Path] = []

    # Python source roots
    py_roots = [repo_root / "core", repo_root / "backend", repo_root / "tools"]
    for root in py_roots:
        if root.exists():
            for r, dirs, files in os.walk(root):
                # Prune excluded directories like __pycache__, tests/
                dirs[:] = [
                    d
                    for d in dirs
                    if d not in ("__pycache__", "tests", "node_modules", ".venv", ".git")
                ]
                for f in files:
                    if f.endswith(".py"):
                        source_files.append(Path(r) / f)

    # Frontend source roots
    fe_root = repo_root / "frontend" / "src"
    if fe_root.exists():
        fe_exts = (".ts", ".tsx", ".js", ".jsx", ".css")
        for r, dirs, files in os.walk(fe_root):
            dirs[:] = [d for d in dirs if d not in ("node_modules", "dist", "build")]
            for f in files:
                if f.lower().endswith(fe_exts):
                    source_files.append(Path(r) / f)

    return source_files


def _line_count(path: Path) -> int:
    from tests.ast_utils import get_file_content

    return len(get_file_content(path).splitlines())


def test_no_new_god_classes() -> None:
    """New files stay under the limit; legacy files may not regrow past their pin.

    A file's ceiling is its pin in ``LEGACY_MAX_LINES`` if listed, otherwise
    ``MAX_LINES_FOR_NEW_FILES``. This prevents both new god classes and the
    silent regrowth of grandfathered ones.
    """
    repo_root = _repo_root()
    violations: list[str] = []

    for path in _get_monitored_source_files():
        rel = path.relative_to(repo_root).as_posix()
        try:
            line_count = _line_count(path)
        except OSError:
            continue

        ceiling = LEGACY_MAX_LINES.get(rel, MAX_LINES_FOR_NEW_FILES)
        if line_count > ceiling:
            if rel in LEGACY_MAX_LINES:
                violations.append(
                    f"  {rel}: {line_count} lines — grandfathered file grew past its "
                    f"pin of {ceiling}"
                )
            else:
                violations.append(f"  {rel}: {line_count} lines (limit {MAX_LINES_FOR_NEW_FILES})")

    if violations:
        raise AssertionError(
            "God-class line limit exceeded:\n" + "\n".join(sorted(violations)) + "\n\nOptions:\n"
            "  1. Refactor into smaller modules (preferred)\n"
            "  2. If a legacy file changed intentionally, re-pin its value in "
            "LEGACY_MAX_LINES (a new file needs a justified entry)."
        )


def test_legacy_list_is_current() -> None:
    """Every grandfathered file must still exist and still exceed the limit.

    This harvests wins so the ratchet can only tighten: when a legacy file is
    refactored under the limit or deleted, this fails until the entry is
    removed from ``LEGACY_MAX_LINES``. It is what keeps the pins from rotting
    into stale numbers that no longer describe the code.
    """
    repo_root = _repo_root()
    stale: list[str] = []

    for rel, pinned in sorted(LEGACY_MAX_LINES.items()):
        path = repo_root / rel
        if not path.exists():
            stale.append(f"  {rel}: no longer exists — remove it from LEGACY_MAX_LINES")
            continue
        line_count = _line_count(path)
        if line_count <= MAX_LINES_FOR_NEW_FILES:
            stale.append(
                f"  {rel}: now {line_count} lines (<= {MAX_LINES_FOR_NEW_FILES}) — "
                "remove it from LEGACY_MAX_LINES; it is no longer a god class"
            )

    if stale:
        raise AssertionError(
            "LEGACY_MAX_LINES is out of date (the ratchet must only tighten):\n" + "\n".join(stale)
        )
