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
    "core/algorithms/base.py": 785,
    "core/algorithms/energy_management.py": 567,
    "core/algorithms/poker.py": 752,
    "core/algorithms/predator_avoidance.py": 540,
    "core/algorithms/registry.py": 793,
    "core/algorithms/schooling.py": 675,
    "core/algorithms/territory.py": 521,
    "core/code_pool/genome_code_pool.py": 641,
    "core/collision_system.py": 510,
    "core/ecosystem.py": 626,
    "core/enhanced_statistics.py": 657,
    "core/entities/fish.py": 773,
    "core/entities/plant.py": 728,
    "core/genetics/plant_genome.py": 761,
    "core/interfaces.py": 663,
    "core/minigames/soccer/engine.py": 778,
    "core/mixed_poker/interaction.py": 728,
    "core/poker/evaluation/auto_evaluate_poker.py": 594,
    "core/poker/evaluation/comprehensive_benchmark.py": 601,
    "core/poker/evaluation/evolution_benchmark_tracker.py": 623,
    "core/poker/human_poker_game.py": 863,
    "core/poker/integration/poker_system.py": 540,
    "core/poker/simulation/hand_engine.py": 754,
    "core/poker/stats/poker_stats_manager.py": 578,
    "core/poker/strategy/composable/strategy.py": 764,
    "core/reproduction/reproduction_service.py": 642,
    "core/simulation/engine.py": 595,
    "core/solutions/benchmark.py": 543,
    "core/solutions/tracker.py": 590,
    "core/spatial/grid.py": 718,
    "core/transfer/entity_transfer.py": 743,
    "core/worlds/tank/backend.py": 672,
}

# Maximum allowed lines for files not grandfathered in LEGACY_MAX_LINES.
MAX_LINES_FOR_NEW_FILES = 500


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _get_core_python_files() -> list[Path]:
    """Get all Python files in the core directory."""
    core_root = _repo_root() / "core"
    return [path for path in core_root.rglob("*.py") if "__pycache__" not in path.parts]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_new_god_classes() -> None:
    """New files stay under the limit; legacy files may not regrow past their pin.

    A file's ceiling is its pin in ``LEGACY_MAX_LINES`` if listed, otherwise
    ``MAX_LINES_FOR_NEW_FILES``. This prevents both new god classes and the
    silent regrowth of grandfathered ones.
    """
    repo_root = _repo_root()
    violations: list[str] = []

    for path in _get_core_python_files():
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
