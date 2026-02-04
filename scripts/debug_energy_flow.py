#!/usr/bin/env python
"""Debug energy flow during poker and reproduction thresholds.

This script is intended for manual debugging. It:
- Spawns two adult fish at high energy
- Runs a single poker hand between them
- Prints energy deltas and whether they meet the post-poker reproduction threshold
"""

from __future__ import annotations

from core.config.fish import POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
from core.entities import Fish, LifeStage
from core.genetics import Genome
from core.movement_strategy import AlgorithmicMovement
from core.poker_interaction import PokerInteraction
from core.simulation.engine import SimulationEngine


def test_energy_flow() -> None:
    """Trace energy through a poker game."""
    print("=" * 70)
    print("ENERGY FLOW DEBUG TEST")
    print("=" * 70)

    engine = SimulationEngine(headless=True, seed=42)
    engine.config.ecosystem.initial_fish_count = 0
    engine.config.server.plants_enabled = False
    engine.setup()

    env = engine.environment
    ecosystem = engine.ecosystem
    assert env is not None
    assert ecosystem is not None

    genome1 = Genome.random(use_algorithm=True, rng=engine.rng)
    genome2 = Genome.random(use_algorithm=True, rng=engine.rng)

    fish1 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        genome=genome1,
        generation=1,
        ecosystem=ecosystem,
        initial_energy=100.0,
    )
    fish2 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=120,
        y=100,
        speed=2.0,
        genome=genome2,
        generation=1,
        ecosystem=ecosystem,
        initial_energy=100.0,
    )

    fish1.age = 100
    fish2.age = 100
    fish1.force_life_stage(LifeStage.ADULT)
    fish2.force_life_stage(LifeStage.ADULT)
    fish1._reproduction_component.reproduction_cooldown = 0
    fish2._reproduction_component.reproduction_cooldown = 0

    fish_by_id = {fish1.fish_id: fish1, fish2.fish_id: fish2}
    before = {fish1.fish_id: fish1.energy, fish2.fish_id: fish2.energy}

    print("\nBEFORE POKER:")
    for fish in (fish1, fish2):
        pct = fish.energy / fish.max_energy * 100 if fish.max_energy else 0.0
        print(f"  Fish #{fish.fish_id}: {fish.energy:.1f} / {fish.max_energy:.1f} ({pct:.1f}%)")

    poker = PokerInteraction([fish1, fish2], rng=engine.rng)
    success = poker.play_poker()
    if not success:
        print("\nPoker did not run (not ready / failed).")
        return

    print("\nAFTER POKER:")
    for fish in (fish1, fish2):
        pct = fish.energy / fish.max_energy * 100 if fish.max_energy else 0.0
        print(f"  Fish #{fish.fish_id}: {fish.energy:.1f} / {fish.max_energy:.1f} ({pct:.1f}%)")

    result = poker.result
    if result is None:
        print("\nNo poker result was recorded.")
        return

    winner = fish_by_id.get(result.winner_id)
    assert winner is not None
    winner_gain = winner.energy - before[winner.fish_id]

    print("\nPOKER RESULT:")
    print(f"  Winner: Fish #{result.winner_id}")
    print(f"  Winner net energy change: {winner_gain:.1f}")
    print(f"  Energy transferred: {result.energy_transferred:.1f}")
    print(f"  House cut: {result.house_cut:.1f}")

    threshold = winner.max_energy * POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
    print("\nREPRODUCTION THRESHOLD CHECK:")
    print(f"  Threshold ({POST_POKER_REPRODUCTION_ENERGY_THRESHOLD:.0%}): {threshold:.1f}")
    print(f"  Winner above threshold: {winner.energy >= threshold}")


if __name__ == "__main__":
    test_energy_flow()
