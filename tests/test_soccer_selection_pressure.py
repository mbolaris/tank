"""Selection pressure integrity checks for the soccer minigame."""

from __future__ import annotations

import random

from core.code_pool import create_default_genome_code_pool
from core.experiments.soccer_evolution import create_population
from core.genetics import Genome
from core.genetics.code_policy_traits import CodePolicyMutationConfig, mutate_code_policies
from core.minigames.soccer import apply_soccer_entry_fees, apply_soccer_rewards


class DummyEnergyEntity:
    """Test double for energy ledger validation."""

    def __init__(self, fish_id: int, energy: float, max_energy: float) -> None:
        self.fish_id = fish_id
        self.energy = energy
        self.max_energy = max_energy
        self.calls: list[tuple[float, str]] = []

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        if amount >= 0:
            applied = min(amount, self.max_energy - self.energy)
        else:
            applied = max(amount, -self.energy)
        self.energy += applied
        self.calls.append((applied, source))
        return applied


def test_soccer_rewards_pot_payout_via_ledger() -> None:
    """Winners receive entry-fee payouts through modify_energy()."""
    left = DummyEnergyEntity(fish_id=1, energy=50.0, max_energy=200.0)
    right = DummyEnergyEntity(fish_id=2, energy=50.0, max_energy=200.0)

    entry_fees = apply_soccer_entry_fees([left, right], entry_fee_energy=10.0)
    rewards = apply_soccer_rewards(
        {"left_1": left, "right_1": right},
        "left",
        reward_mode="pot_payout",
        entry_fees=entry_fees,
    )

    assert entry_fees == {1: 10.0, 2: 10.0}
    assert rewards == {"left_1": 20.0}
    assert left.energy == 60.0
    assert right.energy == 40.0
    assert left.calls == [(-10.0, "soccer_entry_fee"), (20.0, "soccer_win")]
    assert right.calls == [(-10.0, "soccer_entry_fee")]


def test_soccer_rewards_draw_refunds_entry_fees() -> None:
    """Draws refund entry fees to avoid silent energy sinks."""
    left = DummyEnergyEntity(fish_id=1, energy=50.0, max_energy=200.0)
    right = DummyEnergyEntity(fish_id=2, energy=50.0, max_energy=200.0)

    entry_fees = apply_soccer_entry_fees([left, right], entry_fee_energy=10.0)
    rewards = apply_soccer_rewards(
        {"left_1": left, "right_1": right},
        "draw",
        reward_mode="pot_payout",
        entry_fees=entry_fees,
    )

    assert entry_fees == {1: 10.0, 2: 10.0}
    assert rewards == {"left_1": 10.0, "right_1": 10.0}
    assert left.energy == 50.0
    assert right.energy == 50.0
    assert left.calls == [(-10.0, "soccer_entry_fee"), (10.0, "soccer_draw_refund")]
    assert right.calls == [(-10.0, "soccer_entry_fee"), (10.0, "soccer_draw_refund")]


def test_soccer_policy_mutation_changes_distribution() -> None:
    """Policy mutation should change the soccer policy distribution."""
    rng = random.Random(42)
    pool = create_default_genome_code_pool()
    population = create_population(rng, 20, pool)

    initial_ids = {g.behavioral.soccer_policy_id.value for g in population}
    assert len(initial_ids) == 1

    config = CodePolicyMutationConfig(
        swap_probability=1.0,
        drop_probability=0.0,
        param_mutation_rate=0.0,
    )

    mutated_ids = set()
    for genome in population:
        child = Genome.clone_with_mutation(genome, rng=rng)
        mutate_code_policies(child.behavioral, pool, rng, config=config)
        mutated_ids.add(child.behavioral.soccer_policy_id.value)

    assert mutated_ids != initial_ids
    assert len(mutated_ids) > 1
