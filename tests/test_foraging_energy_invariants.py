"""Deterministic guards on the foraging energy economy.

Why this exists instead of a short benchmark sentinel
-----------------------------------------------------
The obvious guard against an energy-economy regression is "run survival_5k for
a few hundred frames in PR CI and check the ecosystem looks healthy". That was
measured and does not work. Comparing the current tree against the pre-revert
(regressed) tree of d94ae59d, same platform, identical benchmark and config:

* At 1000 frames the whole world has produced 3-12 deaths, so
  ``starvation_rate`` is noise and ``avg_energy`` is actually *higher* on the
  regressed tree.
* At 3000 frames over 12 seeds the distributions overlap almost entirely -
  healthy 0.891 +/- 0.056 vs regressed 0.906 +/- 0.044 starvation rate. The
  healthiest-looking regressed seed beats the worst healthy seed.
* Even at the full 5000 frames over 12 seeds the score difference is
  550.3 +/- 276 vs 516.1 +/- 261 (t = 0.31); the healthy tree wins on only 5
  of 12 seeds and both trees breach the 0.95 validity gate on exactly 2 of 12.

The dramatic per-seed collapse that motivated the revert (786.6 -> 0.0) is the
validity gate tripping on a knife-edge metric, not a robust effect - both trees
straddle that gate. Detecting the mean score difference would need on the order
of 260 seeds. So an *outcome*-level ecosystem check cannot be made both cheap
and trustworthy, and a flaky gate is worse than none: it teaches people to
ignore red.

What is testable cheaply is the *mechanism*. These tests are deterministic,
need no simulation, and pin the specific behavioural invariant the revert
established.

The invariant
-------------
A fish that can see no food and is *not* about to starve must not spend energy
travelling to a remembered location. Remembered food is stale by construction
(``get_remembered_food_locations`` accepts ``min_strength=0.1`` and food is
consumed on contact), so a well-fed fish paying movement cost for a probably
empty spot is a pure loss against simply holding position.

The converse is deliberately *not* forbidden. A critically-low fish with no
visible food is already dying if it does nothing, so gambling on a remembered
location dominates holding still. ``FoodQualityOptimizer`` still does
exactly that, gated on ``is_critical`` - see
``test_critical_fish_may_still_gamble_on_memory``, which pins that boundary so
the distinction stays intentional rather than accidental.
"""

from __future__ import annotations

import random

import pytest

from core.algorithms.composable import ComposableBehavior
from core.entities.fish import Fish
from core.environment import Environment
from core.math_utils import Vector2
from core.agent_memory import MemoryType
from core.movement_strategy import AlgorithmicMovement


def _make_fish(env: Environment, *, energy_ratio: float) -> Fish:
    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100.0,
        y=100.0,
        speed=2.0,
    )
    fish.vel = Vector2(0.0, 0.0)
    fish.energy = fish.max_energy * energy_ratio
    return fish


def _remember_food_far_away(fish: Fish) -> None:
    """Plant a remembered food location the fish would have to travel to."""
    fish.memory_system.add_memory(MemoryType.FOOD_LOCATION, Vector2(700.0, 500.0))
    assert fish.get_remembered_food_locations(), "memory fixture failed to plant a location"


@pytest.fixture
def env() -> Environment:
    # No Food entities are registered, so nothing is visible to eat.
    return Environment(width=800, height=600, rng=random.Random(42))


# The behaviour these tests guard against was probabilistic
# (``rng.random() < explore_prob``, re-rolled per frame), so a single call can
# come up (0, 0) by luck and pass against a genuinely regressed tree. Sampling
# repeatedly makes the guard reliable: on the regressed tree of d94ae59d the
# well-fed case fires roughly 6% of the time per call, which a single draw
# misses ~94% of the time but 200 draws miss with probability ~3e-6.
_SAMPLES = 200


def _all_decisions(fish: Fish) -> set[tuple[float, float]]:
    behavior = ComposableBehavior()
    return {behavior._execute_food_approach(fish) for _ in range(_SAMPLES)}


def test_well_fed_fish_holds_position_when_no_food_is_visible(env: Environment) -> None:
    """The regression in d94ae59d: a non-critical fish with stale memories swam
    toward them at speed 0.5-0.8 instead of returning (0, 0)."""
    fish = _make_fish(env, energy_ratio=0.8)
    _remember_food_far_away(fish)
    assert not fish.is_critical_energy()

    decisions = _all_decisions(fish)

    assert decisions == {(0.0, 0.0)}, (
        "A well-fed fish with no visible food burned energy travelling toward a "
        f"remembered (stale) location: {decisions - {(0.0, 0.0)}}. Holding position "
        "costs only existence energy; remembered food is usually already eaten."
    )


def test_hungry_but_not_critical_fish_still_holds_position(env: Environment) -> None:
    """The reverted code scaled exploration by ``max(0.1, 1 - energy_ratio)``,
    so merely-hungry fish moved too - the most starving explored hardest,
    spending their last energy on a probably-empty spot. Hunger short of
    critical is not licence to chase stale memories."""
    fish = _make_fish(env, energy_ratio=0.35)
    _remember_food_far_away(fish)
    assert not fish.is_critical_energy()

    decisions = _all_decisions(fish)

    assert decisions == {(0.0, 0.0)}, (
        f"A hungry (non-critical) fish chased a remembered location: "
        f"{decisions - {(0.0, 0.0)}}."
    )


def test_food_approach_is_deterministic_for_a_fixed_state(env: Environment) -> None:
    """The reverted code re-rolled ``rng.random() < explore_prob`` every frame,
    so a fish dithered toward a target instead of committing to it - paying
    movement cost repeatedly without ever arriving. Identical state must yield
    an identical decision."""
    fish = _make_fish(env, energy_ratio=0.8)
    _remember_food_far_away(fish)

    decisions = _all_decisions(fish)

    assert len(decisions) == 1, (
        f"Food approach returned {len(decisions)} distinct velocities for one "
        f"unchanged fish state: {decisions}. A per-frame random re-roll makes "
        "fish dither rather than travel."
    )


def test_critical_fish_may_still_gamble_on_memory(env: Environment) -> None:
    """Pins the deliberate exception, so the boundary stays intentional.

    ``FoodQualityOptimizer`` lets a critically-low fish head for its closest
    remembered location. That is defensible where the well-fed case is not: a
    starving fish that holds position dies for certain. If this test starts
    failing, the exception was removed - decide whether that was intended
    rather than silently losing it.
    """
    from core.algorithms.food_seeking.quality import FoodQualityOptimizer

    fish = _make_fish(env, energy_ratio=0.02)
    _remember_food_far_away(fish)
    assert fish.is_critical_energy(), "fixture did not produce a critical fish"

    strategy = FoodQualityOptimizer()
    vx, vy = strategy.execute(fish)

    assert (vx, vy) != (0.0, 0.0), (
        "A critically-low fish with a remembered food location held position. "
        "Holding still is certain death; this exception is intentional."
    )
