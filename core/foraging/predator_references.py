"""Reference controllers that establish the predator gym poses a real problem.

Kept beside the gym rather than inside it because they answer a different
question: not "how does this world behave" but "is this world worth measuring
in". :func:`reference_pressures` is the guard the arms run before scoring -
an instrument where hiding is survivable, or where ignoring the predator is
free, would rank controllers by noise while looking authoritative.
"""

from __future__ import annotations

from core.entities.predators import Crab
from core.foraging.predator_gym import (
    MAX_SPEED,
    SCHOOL_SIZE,
    START_Y,
    PredatorResult,
    _PredatorFish,
    _PredatorFood,
    _seek,
    build_predator_schedule,
    run_predator_episode,
)
from core.math_utils import Vector2

__all__ = [
    "FeedAndFleePolicy",
    "FeedIgnoringPredatorPolicy",
    "HidePolicy",
    "reference_pressures",
]


class HidePolicy:
    """Reference: never descend. Establishes that starvation is a real pressure."""

    def velocity(self, fish: _PredatorFish, _active_food: tuple[_PredatorFood, ...]) -> Vector2:
        return _seek(fish.pos, Vector2(fish.pos.x, START_Y), MAX_SPEED)


class FeedIgnoringPredatorPolicy:
    """Reference: chase food, never look down. Establishes predation bites."""

    def velocity(self, fish: _PredatorFish, active_food: tuple[_PredatorFood, ...]) -> Vector2:
        if not active_food:
            return Vector2(0.0, 0.0)
        target = min(active_food, key=lambda food: (food.pos - fish.pos).length())
        return _seek(fish.pos, target.pos, MAX_SPEED)


class FeedAndFleePolicy:
    """Reference: chase food, but climb away from a crab that is close.

    The competent baseline. An evolvable arm that cannot beat this is not
    solving the joint problem, whatever its foraging score elsewhere.
    """

    flee_distance = 90.0

    def velocity(self, fish: _PredatorFish, active_food: tuple[_PredatorFood, ...]) -> Vector2:
        crabs = fish.environment.nearby_agents_by_type(fish, int(self.flee_distance), Crab)
        if crabs:
            nearest = min(crabs, key=lambda crab: (crab.pos - fish.pos).length())
            away = fish.pos - nearest.pos
            if away.length() > 1e-9:
                return _seek(fish.pos, fish.pos + away, MAX_SPEED)
        return FeedIgnoringPredatorPolicy().velocity(fish, active_food)


def reference_pressures(seed: int) -> dict[str, PredatorResult]:
    """Run the three reference arms, asserting both pressures actually bite.

    An instrument where hiding is survivable, or where ignoring the predator
    is free, would report confident numbers about nothing. This is the check
    that the joint problem is really joint, and it runs before any evolvable
    arm is scored.
    """
    schedule = build_predator_schedule(seed)
    results = {
        "hide": run_predator_episode(schedule, [HidePolicy() for _ in range(SCHOOL_SIZE)], seed),
        "feed_ignoring_predator": run_predator_episode(
            schedule, [FeedIgnoringPredatorPolicy() for _ in range(SCHOOL_SIZE)], seed
        ),
        "feed_and_flee": run_predator_episode(
            schedule, [FeedAndFleePolicy() for _ in range(SCHOOL_SIZE)], seed
        ),
    }
    if results["hide"].deaths_starvation == 0:
        raise AssertionError("predator gym: hiding did not starve, so foraging is not required")
    if results["feed_ignoring_predator"].deaths_predation == 0:
        raise AssertionError("predator gym: ignoring the crab was free, so predation is inert")
    return results
