from __future__ import annotations

from types import SimpleNamespace

from core.entities.base import LifeStage
from core.genetics import BehavioralTraits, GeneticTrait, Genome, PhysicalTraits
from core.reproduction.sexual_factory import ProximityMatingConfig, _find_proximity_mate


def _genome(*, aggression: float, mate_preferences: dict[str, float] | None = None) -> Genome:
    physical = PhysicalTraits(
        size_modifier=GeneticTrait(1.0),
        color_hue=GeneticTrait(0.5),
        template_id=GeneticTrait(0),
        fin_size=GeneticTrait(1.0),
        tail_size=GeneticTrait(1.0),
        body_aspect=GeneticTrait(1.0),
        eye_size=GeneticTrait(1.0),
        pattern_intensity=GeneticTrait(0.5),
        pattern_type=GeneticTrait(0),
        lifespan_modifier=GeneticTrait(1.0),
    )
    behavioral = BehavioralTraits(
        aggression=GeneticTrait(aggression),
        social_tendency=GeneticTrait(0.5),
        pursuit_aggression=GeneticTrait(0.5),
        prediction_skill=GeneticTrait(0.5),
        hunting_stamina=GeneticTrait(0.5),
        asexual_reproduction_chance=GeneticTrait(0.5),
        poker_strategy=GeneticTrait(None),
        mate_preferences=GeneticTrait(mate_preferences or {}),
    )
    return Genome(physical=physical, behavioral=behavioral)


def _fish(fish_id: int, *, x: float, aggression: float, mate_preferences=None):
    return SimpleNamespace(
        fish_id=fish_id,
        species="fish1.png",
        life_stage=LifeStage.ADULT,
        energy=100.0,
        max_energy=100.0,
        width=10.0,
        height=10.0,
        pos=SimpleNamespace(x=x, y=0.0),
        genome=_genome(aggression=aggression, mate_preferences=mate_preferences),
        _reproduction_component=SimpleNamespace(reproduction_cooldown=0),
        is_dead=lambda: False,
    )


def _config() -> ProximityMatingConfig:
    return ProximityMatingConfig(
        max_distance=100.0,
        min_energy_ratio=0.1,
        parent_energy_contribution=0.2,
        mutation_rate=0.1,
        mutation_strength=0.1,
    )


def test_proximity_mating_prefers_heritable_attraction_over_nearest_mate():
    parent = _fish(
        1,
        x=0.0,
        aggression=0.5,
        mate_preferences={"prefer_high_aggression": 1.0},
    )
    nearest_low_aggression = _fish(2, x=10.0, aggression=0.0)
    farther_high_aggression = _fish(3, x=40.0, aggression=1.0)

    mate = _find_proximity_mate(
        parent,
        [parent, nearest_low_aggression, farther_high_aggression],
        set(),
        _config(),
    )

    assert mate is farther_high_aggression


def test_proximity_mating_uses_distance_as_attraction_tiebreaker():
    parent = _fish(1, x=0.0, aggression=0.5)
    nearest = _fish(2, x=10.0, aggression=0.5)
    farther = _fish(3, x=40.0, aggression=0.5)

    mate = _find_proximity_mate(parent, [parent, farther, nearest], set(), _config())

    assert mate is nearest
