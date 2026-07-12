"""Ratchet on hasattr()/getattr() usage in core/.

The protocol layer (core/interfaces.py, core/world.py, ADR-002) is the
project's contract mechanism. Every ``hasattr``/``getattr`` call in core is a
contract the code declares but does not trust: the fallback branch silently
hides wiring bugs instead of failing loudly (the same silent-fallback problem
ADR-007 removed). This ratchet keeps the count from growing and harvests every
cleanup, one module at a time — the same discipline as
``test_god_class_limits.py``.

When a check is genuinely needed, prefer:
- adding the missing member to the protocol (``World``, ``core/interfaces.py``)
  and accessing it directly;
- an explicit ``isinstance`` check against a ``@runtime_checkable`` protocol;
- an ``X | None`` attribute that always exists and is checked for ``None``.

Counts are raw occurrences of ``hasattr(`` / ``getattr(`` per file (comments
included — cheap, deterministic, and good enough for a ratchet).
"""

import re
from pathlib import Path

# Allowance for files not pinned below. A couple of dynamic checks can be
# legitimate (e.g. duck-typing at a true serialization boundary); a file that
# needs more than this is leaning on hasattr instead of its protocols.
MAX_DYNAMIC_ATTR_CHECKS_FOR_NEW_FILES = 2

# Grandfathered files, pinned at their measured counts (2026-07). Pins are
# ceilings: a pinned file may shrink freely but may not regrow. When a file
# drops to the allowance or below, test_pinned_list_is_current fails until its
# entry is removed — the ratchet only tightens.
LEGACY_DYNAMIC_ATTR_COUNTS = {
    "core/algorithms/base.py": 4,
    "core/algorithms/composable/actions.py": 4,
    "core/algorithms/composable/food_selection.py": 8,
    "core/algorithms/food_seeking/cooperative.py": 5,
    "core/algorithms/food_seeking/quality.py": 3,
    "core/code_pool/genome_code_pool.py": 4,
    "core/ecosystem_reporting.py": 3,
    "core/entities/base.py": 6,
    "core/entities/fish.py": 13,
    "core/entities/goal_zone.py": 3,
    "core/entities/plant.py": 8,
    "core/entities/predators.py": 8,
    "core/environment.py": 8,
    "core/fish/visual_geometry.py": 5,
    # +4 (2026-07): target_pursuit_module rides the same loop-over-field-name
    # pattern already used for the per-kind policy traits below, rather than
    # duplicating inherit_behavior_graph()'s call site per field (which would
    # cost far more lines than 4 getattr calls - see the god-class ratchet,
    # this file was already near its own line-count ceiling).
    "core/genetics/behavioral_inheritance.py": 20,
    "core/genetics/code_policy_traits.py": 9,
    # +1 (2026-07): validate() loops over ("behavior_graph",
    # "target_pursuit_module") instead of duplicating the validation call per
    # field, mirroring the per-kind-policy loop already in this file.
    "core/genetics/genome.py": 5,
    "core/genetics/genome_codec.py": 9,
    "core/genetics/trait.py": 8,
    "core/genetics/trait_utils.py": 3,
    "core/minigames/soccer/evaluator.py": 5,
    "core/minigames/soccer/fish_stats.py": 3,
    "core/minigames/soccer/league/provider.py": 23,
    "core/minigames/soccer/league_runtime.py": 14,
    "core/minigames/soccer/participant.py": 7,
    "core/minigames/soccer/policy_adapter.py": 7,
    "core/minigames/soccer/rewards.py": 5,
    "core/minigames/soccer/scheduler.py": 16,
    "core/minigames/soccer/selection.py": 3,
    "core/mixed_poker/interaction.py": 15,
    "core/movement/considerations.py": 4,
    "core/plant/energy_component.py": 5,
    "core/plant/migration_component.py": 6,
    "core/plant_manager.py": 8,
    "core/poker/evaluation/periodic_benchmark.py": 3,
    "core/poker/integration/poker_interaction.py": 9,
    "core/poker/integration/poker_rewards.py": 5,
    "core/poker/integration/poker_system.py": 13,
    "core/poker/integration/poker_table_planner.py": 9,
    "core/poker/integration/post_poker_reproduction.py": 6,
    "core/poker/stats/poker_stats_manager.py": 3,
    "core/policies/movement_policy_runner.py": 4,
    "core/reproduction/asexual_factory.py": 4,
    "core/reproduction/mutation_controller.py": 3,
    "core/reproduction/niche_cost.py": 18,
    "core/reproduction/reproduction_service.py": 15,
    "core/reproduction/sexual_factory.py": 4,
    "core/serializers.py": 3,
    "core/services/stats/genetic_stats.py": 20,
    "core/services/stats/trait_trends.py": 6,
    "core/simulation/engine.py": 5,
    "core/simulation/entity_manager.py": 6,
    "core/solutions/tracker.py": 12,
    "core/spatial/bounds.py": 4,
    "core/statistics_utils.py": 3,
    "core/systems/entity_lifecycle.py": 6,
    "core/systems/soccer_system.py": 15,
    "core/transfer/entity_transfer.py": 19,
    "core/util/mutations.py": 8,
    "core/util/rng.py": 3,
    "core/worlds/petri/environment.py": 5,
    "core/worlds/shared/movement_observations.py": 5,
    "core/worlds/shared/tank_like_phase_hooks.py": 8,
    "core/worlds/tank/backend.py": 7,
    "core/worlds/tank/observation_builder.py": 7,
    "core/worlds/tank/pack.py": 5,
}

_DYNAMIC_ATTR_PATTERN = re.compile(r"\b(?:hasattr|getattr)\s*\(")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_core_files() -> list[Path]:
    root = _repo_root() / "core"
    return [
        p
        for p in sorted(root.rglob("*.py"))
        if "__pycache__" not in p.parts and "tests" not in p.parts
    ]


def _dynamic_attr_count(path: Path) -> int:
    return len(_DYNAMIC_ATTR_PATTERN.findall(path.read_text(encoding="utf-8")))


def test_no_new_dynamic_attr_checks() -> None:
    """New core files stay within the allowance; pinned files may not regrow."""
    repo_root = _repo_root()
    violations: list[str] = []

    for path in _iter_core_files():
        rel = path.relative_to(repo_root).as_posix()
        count = _dynamic_attr_count(path)
        ceiling = LEGACY_DYNAMIC_ATTR_COUNTS.get(rel, MAX_DYNAMIC_ATTR_CHECKS_FOR_NEW_FILES)
        if count > ceiling:
            if rel in LEGACY_DYNAMIC_ATTR_COUNTS:
                violations.append(
                    f"  {rel}: {count} hasattr/getattr calls — grew past its pin of {ceiling}"
                )
            else:
                violations.append(
                    f"  {rel}: {count} hasattr/getattr calls "
                    f"(allowance {MAX_DYNAMIC_ATTR_CHECKS_FOR_NEW_FILES})"
                )

    if violations:
        raise AssertionError(
            "hasattr/getattr ratchet exceeded:\n" + "\n".join(sorted(violations)) + "\n\nOptions:\n"
            "  1. Add the missing member to the relevant protocol (core/world.py,\n"
            "     core/interfaces.py) and access it directly (preferred)\n"
            "  2. Use isinstance() against a @runtime_checkable protocol\n"
            "  3. If the dynamic check is genuinely required (true serialization\n"
            "     boundary), re-pin the file in LEGACY_DYNAMIC_ATTR_COUNTS with a\n"
            "     justification in the PR."
        )


def test_pinned_list_is_current() -> None:
    """Every pinned file must still exist and still exceed the allowance.

    This harvests wins so the ratchet can only tighten: when a file is cleaned
    to the allowance or below (or deleted), this fails until its entry is
    removed from ``LEGACY_DYNAMIC_ATTR_COUNTS``.
    """
    repo_root = _repo_root()
    stale: list[str] = []

    for rel, pinned in sorted(LEGACY_DYNAMIC_ATTR_COUNTS.items()):
        path = repo_root / rel
        if not path.exists():
            stale.append(f"  {rel}: no longer exists — remove it from LEGACY_DYNAMIC_ATTR_COUNTS")
            continue
        count = _dynamic_attr_count(path)
        if count <= MAX_DYNAMIC_ATTR_CHECKS_FOR_NEW_FILES:
            stale.append(
                f"  {rel}: now {count} hasattr/getattr calls "
                f"(<= {MAX_DYNAMIC_ATTR_CHECKS_FOR_NEW_FILES}) — remove it from "
                "LEGACY_DYNAMIC_ATTR_COUNTS; it is clean"
            )

    if stale:
        raise AssertionError(
            "LEGACY_DYNAMIC_ATTR_COUNTS is out of date (the ratchet must only tighten):\n"
            + "\n".join(stale)
        )
