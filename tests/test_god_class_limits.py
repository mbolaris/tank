"""Tests to prevent architectural anti-patterns.

These tests enforce code quality constraints to prevent regression
as the codebase grows.
"""

from pathlib import Path
from typing import List, Set, Tuple

# Files that currently exceed the limit.
# As we refactor these, remove them from the list.
LEGACY_EXCEEDS: Set[str] = {
    "fish.py",  # 1201 lines - needs component extraction
    "engine.py",  # 991 lines - orchestrator, hard to split safely
    "ecosystem.py",  # 987 lines - facade for trackers
    "environment.py",  # 882 lines - spatial grid + entities
    "plant_genome.py",  # 850 lines - complex genetics
    "strategy.py",  # composable poker strategy
    "poker.py",  # algorithms/poker.py
    "plant.py",  # entities/plant.py
    "human_poker_game.py",
    "behavioral.py",  # genetics/behavioral.py
    "evolution_benchmark_tracker.py",
    "world.py",  # soccer_training world
    "interaction.py",  # mixed_poker interaction
    "schooling.py",
    "base.py",  # algorithms/base.py
    "number_guessing.py",  # skills game
    "enhanced_statistics.py",
    "registry.py",  # algorithms/registry.py
    "hand_engine.py",  # poker simulation
    "energy_management.py",
    "comprehensive_benchmark.py",
    "predator_avoidance.py",
    "auto_evaluate_poker.py",
    "poker_stats_manager.py",
    "rock_paper_scissors.py",
    "poker_system.py",
    "genome_code_pool.py",
    "territory.py",
    "tracker.py",  # solutions/tracker.py
    "actions.py",  # composable/actions.py
    "backend.py",  # soccer/backend.py
    "benchmark.py",  # solutions/benchmark.py
    "interfaces.py",
    "collision_system.py",
    "poker_adapter.py",  # skills/games/poker_adapter.py
    "reproduction_service.py",
    "tank_snapshot_builder.py",
    "plant_strategy_types.py",
    "genetic_stats.py",
    "plant_manager.py",
    "skill_game_system.py",
    "standard.py",  # poker/strategy/implementations/standard.py
}

# Maximum allowed lines for NEW files
MAX_LINES_FOR_NEW_FILES = 500


def _get_core_python_files() -> List[Path]:
    """Get all Python files in the core directory."""
    core_root = Path(__file__).resolve().parents[1] / "core"
    return [path for path in core_root.rglob("*.py") if "__pycache__" not in path.parts]


def test_no_new_god_classes() -> None:
    """New files should not exceed the line limit.

    Existing large files are grandfathered in via LEGACY_EXCEEDS,
    but new files must stay under the limit.

    This prevents architectural debt from accumulating.
    """
    violations: List[Tuple[str, int]] = []

    for path in _get_core_python_files():
        # Skip grandfathered files
        if path.name in LEGACY_EXCEEDS:
            continue

        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except Exception:
            continue

        if line_count > MAX_LINES_FOR_NEW_FILES:
            violations.append((str(path.relative_to(path.parents[2])), line_count))

    if violations:
        violation_list = "\n".join(f"  {path}: {lines} lines" for path, lines in sorted(violations))
        raise AssertionError(
            f"Files exceeding {MAX_LINES_FOR_NEW_FILES} lines (not in legacy list):\n"
            f"{violation_list}\n\n"
            f"Options:\n"
            f"  1. Refactor into smaller modules\n"
            f"  2. Add to LEGACY_EXCEEDS if truly needed (requires justification)"
        )


def test_legacy_exceeds_shrinking() -> None:
    """Track that we're reducing the legacy files, not growing the list.

    This test documents the current count of legacy files.
    Update EXPECTED_LEGACY_COUNT when you refactor files.
    """
    EXPECTED_LEGACY_COUNT = 51  # Current count as of 2026-01-01

    actual_count = len(LEGACY_EXCEEDS)

    # Allow shrinking (good!) but not growing
    if actual_count > EXPECTED_LEGACY_COUNT:
        raise AssertionError(
            f"LEGACY_EXCEEDS grew from {EXPECTED_LEGACY_COUNT} to {actual_count}.\n"
            f"Adding new files to the legacy list is discouraged.\n"
            f"Consider refactoring instead."
        )
