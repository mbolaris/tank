from types import SimpleNamespace

from core.ecosystem_stats import GenerationStats
from core.population_tracker import PopulationTracker


def test_update_population_stats_clears_generations_with_no_live_fish():
    tracker = PopulationTracker()
    tracker.generation_stats = {
        0: GenerationStats(generation=0, population=3),
        1: GenerationStats(generation=1, population=4),
        2: GenerationStats(generation=2, population=5),
    }

    tracker.update_population_stats(
        [
            SimpleNamespace(generation=1),
            SimpleNamespace(generation=1),
            SimpleNamespace(generation=2),
        ]
    )

    assert tracker.get_population_by_generation() == {1: 2, 2: 1}
    assert tracker.get_total_population() == 3


def test_update_population_stats_clears_population_when_no_fish_remain():
    tracker = PopulationTracker()
    tracker.generation_stats = {
        0: GenerationStats(generation=0, population=2),
        3: GenerationStats(generation=3, population=1),
    }

    tracker.update_population_stats([])

    assert tracker.get_population_by_generation() == {}
    assert tracker.get_total_population() == 0
