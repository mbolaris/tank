"""The diversity tracker's per-genome cache must never go stale.

GeneticDiversityTracker reads each fish's genome traits every frame; it now
extracts them once per genome, on the assumption the genome's other caches
already rest on - genomes do not change after creation. These tests run a real
tank (births, deaths, poker, mutation) and check every live fish's cached
values against a fresh extraction.
"""

from __future__ import annotations

from core.entities import Fish
from core.genetic_diversity_tracker import _diversity_profile
from core.worlds import WorldRegistry
from core.worlds.interfaces import FAST_STEP_ACTION


def _fresh(genome) -> tuple:  # type: ignore[no-untyped-def]
    saved = genome._diversity_profile_cache
    object.__setattr__(genome, "_diversity_profile_cache", None)
    try:
        return _diversity_profile(genome)
    finally:
        object.__setattr__(genome, "_diversity_profile_cache", saved)


def test_cached_profiles_match_fresh_extraction_after_a_real_run() -> None:
    config = {"headless": True, "initial_fish_count": 40}
    world = WorldRegistry.create_world("tank", seed=42, config=config)
    world.reset(seed=42, config=config)
    founders = {e.fish_id for e in world.entities_list if isinstance(e, Fish)}
    for _ in range(500):
        world.step({FAST_STEP_ACTION: True})

    fish = [e for e in world.entities_list if isinstance(e, Fish)]
    assert any(f.fish_id not in founders for f in fish), "fish born mid-run should be covered"
    cached = [f.genome._diversity_profile_cache for f in fish]
    assert fish and all(c is not None for c in cached), "the tracker should have cached them"
    for f, profile in zip(fish, cached, strict=True):
        assert profile == _fresh(f.genome)


def test_invalidate_caches_clears_the_profile() -> None:
    config = {"headless": True}
    world = WorldRegistry.create_world("tank", seed=7, config=config)
    world.reset(seed=7, config=config)
    world.step({FAST_STEP_ACTION: True})
    genome = next(e for e in world.entities_list if isinstance(e, Fish)).genome
    assert genome._diversity_profile_cache is not None
    genome.invalidate_caches()
    assert genome._diversity_profile_cache is None
