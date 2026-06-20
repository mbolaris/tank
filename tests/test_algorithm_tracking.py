"""Per-algorithm stats tracking: registration and telemetry share one id space.

Regression test for ARCHITECTURE_REVIEW item 6: ``_init_algorithm_stats`` used
to key stats by the enumerate index of the legacy ``ALL_ALGORITHMS`` classes,
while telemetry keyed by the composable ``behavior_id`` hash. The two id spaces
never matched, so per-algorithm counters were never recorded. Both sides now
derive the key from ``behavior_id`` via ``stable_algorithm_id``.
"""

from __future__ import annotations

from core.algorithms.composable.behavior import ComposableBehavior
from core.ecosystem import EcosystemManager
from core.util.stable_hash import stable_algorithm_id


def _some_behavior_id() -> str:
    return ComposableBehavior.all_behavior_ids()[0]


def test_stats_registered_over_all_behavior_ids():
    eco = EcosystemManager(max_population=50)
    expected = {stable_algorithm_id(bid) for bid in ComposableBehavior.all_behavior_ids()}
    assert set(eco.algorithm_stats) == expected
    # 384 = 4 (threat) x 6 (food) x 4 (social) x 4 (poker)
    assert len(eco.algorithm_stats) == 384


def test_all_behavior_ids_have_distinct_stable_ids():
    """No CRC32 collisions across the fixed behavior_id set (else stats merge)."""
    ids = [stable_algorithm_id(bid) for bid in ComposableBehavior.all_behavior_ids()]
    assert len(set(ids)) == len(ids)


def test_registration_id_matches_telemetry_id():
    """The whole point: a behavior_id's registered key is the id telemetry emits."""
    eco = EcosystemManager(max_population=50)
    bid = _some_behavior_id()
    algo_id = stable_algorithm_id(bid)
    assert algo_id in eco.algorithm_stats
    assert eco.algorithm_stats[algo_id].algorithm_name == bid


def test_counters_record_against_the_shared_id():
    eco = EcosystemManager(max_population=50)
    algo_id = stable_algorithm_id(_some_behavior_id())

    eco.record_birth(fish_id=1, generation=0, algorithm_id=algo_id)
    eco.record_birth(fish_id=2, generation=0, algorithm_id=algo_id)
    eco.record_reproduction(algorithm_id=algo_id)
    eco.record_food_eaten(algorithm_id=algo_id)
    eco.record_death(fish_id=1, generation=0, age=100, cause="starvation", algorithm_id=algo_id)

    stats = eco.algorithm_stats[algo_id]
    assert stats.total_births == 2
    assert stats.total_reproductions == 1
    assert stats.total_food_eaten == 1
    assert stats.total_deaths == 1
    assert stats.deaths_starvation == 1
    assert stats.current_population == 1  # 2 born - 1 died
    assert stats.total_lifespan == 100


def test_unregistered_id_is_ignored_not_crashed():
    """A behavior_id not in the (complete) registry must not raise."""
    eco = EcosystemManager(max_population=50)
    eco.record_birth(fish_id=1, generation=0, algorithm_id=stable_algorithm_id("not-a-real-id"))
    # No matching bucket -> nothing recorded, no exception.
    assert all(s.total_births == 0 for s in eco.algorithm_stats.values())


def test_report_generation_smoke():
    eco = EcosystemManager(max_population=50)
    algo_id = stable_algorithm_id(_some_behavior_id())
    for i in range(5):
        eco.record_birth(fish_id=100 + i, generation=1, algorithm_id=algo_id)
        eco.record_food_eaten(algorithm_id=algo_id)
    for i in range(3):
        eco.record_death(
            fish_id=100 + i, generation=1, age=150, cause="old_age", algorithm_id=algo_id
        )
    eco.record_reproduction(algorithm_id=algo_id)

    report = eco.get_algorithm_performance_report(min_sample_size=2)
    assert "ALGORITHM PERFORMANCE REPORT" in report
    assert "TOP PERFORMING ALGORITHMS" in report
