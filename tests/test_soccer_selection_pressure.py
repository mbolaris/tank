"""Selection pressure integrity checks for the soccer minigame."""

from __future__ import annotations

import random

from core.code_pool import create_default_genome_code_pool
from core.experiments.soccer_evolution import create_population
from core.genetics import Genome
from core.genetics.code_policy_traits import CodePolicyMutationConfig, mutate_code_policies
from core.minigames.soccer import apply_soccer_rewards


class DummyEnergyEntity:
    """Test double for energy ledger validation."""

    def __init__(self, energy: float, max_energy: float) -> None:
        self.energy = energy
        self.max_energy = max_energy
        self.calls: list[tuple[float, str]] = []

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        applied = min(amount, self.max_energy - self.energy)
        self.energy += applied
        self.calls.append((applied, source))
        return applied


def test_soccer_rewards_refill_via_ledger() -> None:
    """Winners receive a max-energy refill through modify_energy()."""
    left = DummyEnergyEntity(energy=20.0, max_energy=100.0)
    right = DummyEnergyEntity(energy=80.0, max_energy=100.0)

    rewards = apply_soccer_rewards({"left_1": left, "right_1": right}, "left")

    assert rewards == {"left_1": 80.0}
    assert left.energy == 100.0
    assert right.energy == 80.0
    assert left.calls == [(80.0, "soccer_win")]
    assert right.calls == []


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
