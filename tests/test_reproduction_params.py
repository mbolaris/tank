import random

import pytest

from core.agents.components.reproduction_component import ReproductionComponent
from core.entities import LifeStage
from core.genetics import Genome, ReproductionMutationContext, ReproductionParams
from core.genetics.reproduction import DANGER_SUB_BEHAVIOR_SWITCH_RATE


def test_from_parents_weighted_params_matches_direct_call() -> None:
    rng = random.Random(123)
    parent1 = Genome.random(use_algorithm=False, rng=rng)
    parent2 = Genome.random(use_algorithm=False, rng=rng)

    params = ReproductionParams(mutation_rate=0.0, mutation_strength=0.0)

    child_direct = Genome.from_parents_weighted(
        parent1=parent1,
        parent2=parent2,
        parent1_weight=0.6,
        mutation_rate=0.0,
        mutation_strength=0.0,
        rng=random.Random(999),
    )
    child_params = Genome.from_parents_weighted_params(
        parent1=parent1,
        parent2=parent2,
        parent1_weight=0.6,
        params=params,
        rng=random.Random(999),
    )

    assert child_params.debug_snapshot() == child_direct.debug_snapshot()


def test_low_diversity_without_stall_signal_does_not_escalate_mutation() -> None:
    params = ReproductionParams(mutation_rate=0.15, mutation_strength=0.15)

    rate, strength = params.adaptive_mutation(ReproductionMutationContext(diversity_score=0.11))

    assert rate == pytest.approx(0.15)
    assert strength == pytest.approx(0.15)


def test_declining_low_diversity_escalates_with_bounds() -> None:
    params = ReproductionParams(mutation_rate=0.15, mutation_strength=0.15)

    rate, strength = params.adaptive_mutation(
        ReproductionMutationContext(diversity_score=0.11, diversity_slope=-0.00001)
    )

    assert rate == pytest.approx(0.35)
    assert strength == pytest.approx(0.25)


def test_lineage_preservation_blocks_escalation() -> None:
    params = ReproductionParams(mutation_rate=0.15, mutation_strength=0.15)

    rate, strength = params.adaptive_mutation(
        ReproductionMutationContext(
            diversity_score=0.11,
            diversity_slope=-0.00001,
            preserve_parent_lineage=True,
        )
    )

    assert rate == pytest.approx(0.15)
    assert strength == pytest.approx(0.15)


def test_danger_zone_escalates_behavior_switch_rate_only_when_active() -> None:
    inactive = ReproductionMutationContext(diversity_score=0.11)
    active = ReproductionMutationContext(diversity_score=0.11, diversity_slope=-0.00001)

    assert inactive.sub_behavior_switch_rate(0.08) == pytest.approx(0.08)
    assert active.sub_behavior_switch_rate(0.08) == pytest.approx(DANGER_SUB_BEHAVIOR_SWITCH_RATE)


def test_protected_lineage_gets_modest_asexual_energy_relief() -> None:
    component = ReproductionComponent()
    protected = ReproductionMutationContext(preserve_parent_lineage=True)

    assert not component.can_asexually_reproduce(LifeStage.ADULT, 86.0, 100.0)
    assert component.can_asexually_reproduce(LifeStage.ADULT, 86.0, 100.0, protected)


def test_protected_lineage_still_requires_adult_and_cooldown() -> None:
    component = ReproductionComponent()
    protected = ReproductionMutationContext(preserve_parent_lineage=True)

    assert not component.can_asexually_reproduce(LifeStage.BABY, 100.0, 100.0, protected)

    component.reproduction_cooldown = 1
    assert not component.can_asexually_reproduce(LifeStage.ADULT, 100.0, 100.0, protected)
