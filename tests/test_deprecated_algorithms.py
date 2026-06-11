"""Guards for the staged deprecation of monolithic food-seekers (ADR-006)."""

import random

from core.algorithms.registry import ALL_ALGORITHMS, DEPRECATED_ALGORITHMS


def _all_algorithm_ids() -> set[str]:
    rng = random.Random(0)
    return {cls.random_instance(rng=rng).algorithm_id for cls in ALL_ALGORITHMS}


def test_deprecated_ids_exist_in_registry():
    """Every deprecated id must name a real registered algorithm.

    Fails on typos, and fails at stage 2 (removal) until the metadata list is
    cleaned up alongside the module deletions - which is exactly the reminder
    we want.
    """
    missing = DEPRECATED_ALGORITHMS - _all_algorithm_ids()
    assert not missing, f"DEPRECATED_ALGORITHMS entries not in registry: {sorted(missing)}"


def test_deprecation_is_metadata_only():
    """Stage 1 must not change selection: deprecated algorithms remain selectable.

    ALL_ALGORITHMS feeds rng.choice during genome creation; excluding entries
    changes seeded trajectories and invalidates champions. Removal happens in
    stage 2 together with re-baselining (see ADR-006).
    """
    assert DEPRECATED_ALGORITHMS & _all_algorithm_ids() == DEPRECATED_ALGORITHMS
