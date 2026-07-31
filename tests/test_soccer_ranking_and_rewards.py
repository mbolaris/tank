"""Unit tests for soccer individual ranking, rewards, and caps."""

import pytest

from typing import Any
from unittest.mock import Mock

from core.agents.components.reproduction_component import ReproductionComponent
from core.minigames.soccer.fish_stats import SoccerFishStats, SoccerFishStatsTracker
from core.minigames.soccer.rewards import (
    apply_soccer_repro_rewards,
    calculate_soccer_individual_rewards,
)
from core.minigames.soccer.types import SoccerMinigameOutcome


def _outcome(**overrides: Any) -> SoccerMinigameOutcome:
    defaults: dict[str, Any] = {
        "match_id": "m1",
        "match_counter": 0,
        "winner_team": "left",
        "score_left": 2,
        "score_right": 1,
        "frames": 1800,
        "seed": 1,
        "selection_seed": 1,
        "message": "Left Team Wins!",
        "rewarded": {},
        "entry_fees": {1: 5.0, 2: 5.0},
        "energy_deltas": {1: 5.0, 2: -5.0},
        "repro_credit_deltas": {},
        "teams": {"left": [1], "right": [2]},
        "goals_by_fish": {},
        "assists_by_fish": {},
    }
    defaults.update(overrides)
    return SoccerMinigameOutcome(**defaults)


def test_goals_rank_above_passive_wins():
    """A goal outranks simply being on the winning side, match for match.

    Both fish play exactly one match here. Comparing a fish with two wins
    against a fish with one goal would be an aggregate question, not this one -
    contribution_score is additive, so enough wins are meant to add up.
    """
    tracker = SoccerFishStatsTracker()
    # Fish 1 wins without scoring; Fish 2 scores but loses.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0, 2: 5.0},
            energy_deltas={1: 5.0, 2: -5.0},
            teams={"left": [1], "right": [2]},
            goals_by_fish={2: 1},
        )
    )

    leaders = tracker.leaders(10)
    assert len(leaders) == 2
    assert leaders[0]["fish_id"] == 2
    assert leaders[1]["fish_id"] == 1


def test_assists_improve_rank_below_goals_but_above_passive_wins():
    """Per match played: goal > assist > win. Each fish plays exactly once."""
    tracker = SoccerFishStatsTracker()
    # Match 1: Fish 1 wins passively, Fish 2 assists but loses.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0, 2: 5.0},
            energy_deltas={1: 5.0, 2: -5.0},
            teams={"left": [1], "right": [2]},
            assists_by_fish={2: 1},
        )
    )
    # Match 2: Fish 3 wins passively, Fish 4 scores but loses.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={3: 5.0, 4: 5.0},
            energy_deltas={3: 5.0, 4: -5.0},
            teams={"left": [3], "right": [4]},
            goals_by_fish={4: 1},
        )
    )

    leaders = tracker.leaders(10)
    assert leaders[0]["fish_id"] == 4  # goal
    assert leaders[1]["fish_id"] == 2  # assist
    assert {leaders[2]["fish_id"], leaders[3]["fish_id"]} == {1, 3}  # passive wins


def test_net_energy_helps_break_ties():
    tracker = SoccerFishStatsTracker()
    # Fish 1: 1 goal, +10 energy
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0},
            energy_deltas={1: 10.0},
            goals_by_fish={1: 1},
        )
    )
    # Fish 2: 1 goal, +5 energy
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={2: 5.0},
            energy_deltas={2: 5.0},
            goals_by_fish={2: 1},
        )
    )

    leaders = tracker.leaders(10)
    assert leaders[0]["fish_id"] == 1
    assert leaders[1]["fish_id"] == 2


def test_wins_count_toward_rank_rather_than_only_breaking_ties():
    """Wins must be a real term, not decoration.

    Ranking used to be a lexicographic tuple in which ``wins`` sat behind
    ``net_energy``. Two fish practically never tie on a float, so wins decided
    nothing: a fish could win every match it played and still rank below one
    that lost every match with a marginally better energy balance. This pins
    the fix - identical goals and energy, so only the win separates them.
    """
    tracker = SoccerFishStatsTracker()
    # Fish 1: 1 goal, wins.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0},
            energy_deltas={1: 10.0},
            goals_by_fish={1: 1},
            teams={"left": [1]},
        )
    )
    # Fish 2: 1 goal, same energy, loses.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={2: 5.0},
            energy_deltas={2: 10.0},
            goals_by_fish={2: 1},
            teams={"right": [2]},
        )
    )

    leaders = tracker.leaders(10)
    assert leaders[0]["fish_id"] == 1
    assert leaders[1]["fish_id"] == 2
    gap = leaders[0]["contribution_score"] - leaders[1]["contribution_score"]
    assert gap == pytest.approx(
        SoccerFishStats.WIN_WEIGHT
    ), "the win should move the score by its full weight, not a rounding error"


def test_equal_contribution_score_ties_break_on_fish_id():
    """Matches played is not a ranking input (see `_sort_key`'s docstring), so
    two fish with identical goals/assists/wins/draws/net_energy land at an
    exact `contribution_score` tie regardless of how many matches each played.
    The tracker breaks that tie on `fish_id` for determinism.
    """
    tracker = SoccerFishStatsTracker()
    # Fish 1: 1 goal, +10 energy, 0 wins, across 2 matches.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0},
            energy_deltas={1: 5.0},
            goals_by_fish={1: 1},
            teams={"right": [1]},
        )
    )
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0},
            energy_deltas={1: 5.0},
            goals_by_fish={1: 0},
            teams={"right": [1]},
        )
    )
    # Fish 2: 1 goal, +10 energy, 0 wins, in a single match - same totals as
    # fish 1, so contribution_score ties exactly despite the different match
    # counts.
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={2: 5.0},
            energy_deltas={2: 10.0},
            goals_by_fish={2: 1},
            teams={"right": [2]},
        )
    )

    leaders = tracker.leaders(10)
    assert leaders[0]["contribution_score"] == leaders[1]["contribution_score"]
    assert leaders[0]["fish_id"] == 1
    assert leaders[1]["fish_id"] == 2


def create_mock_fish(fish_id: int):
    fish = Mock()
    fish.fish_id = fish_id
    fish.energy = 100.0
    energy_log = []

    def modify_energy(amount: float, source: str = "unknown") -> float:
        fish.energy += amount
        energy_log.append({"amount": amount, "source": source})
        return amount

    fish.modify_energy = modify_energy
    fish._energy_log = energy_log
    return fish


class PublicReproductionFish:
    def __init__(self, fish_id: int) -> None:
        self.fish_id = fish_id
        self.reproduction_component = ReproductionComponent()


def test_goal_rewards_applied():
    fish1 = create_mock_fish(1)
    player_map = {"left_0": fish1}

    # 1 goal: should award 25 energy
    rewards = calculate_soccer_individual_rewards(
        player_map=player_map,
        winner_team="left",
        goals_by_fish={1: 1},
        assists_by_fish={},
    )
    # Fish 1 gets 25 (goal) + 5 (win) = 30
    assert rewards["left_0"] == 30.0


def test_assist_rewards_applied():
    fish1 = create_mock_fish(1)
    player_map = {"left_0": fish1}

    # 1 assist: should award 15 energy
    rewards = calculate_soccer_individual_rewards(
        player_map=player_map,
        winner_team="left",
        goals_by_fish={},
        assists_by_fish={1: 1},
    )
    # Fish 1 gets 15 (assist) + 5 (win) = 20
    assert rewards["left_0"] == 20.0


def test_rewards_capped():
    fish1 = create_mock_fish(1)
    player_map = {"left_0": fish1}

    # 3 goals (75) + 1 win (5) = 80 -> capped at 70 total
    rewards = calculate_soccer_individual_rewards(
        player_map=player_map,
        winner_team="left",
        goals_by_fish={1: 3},
        assists_by_fish={},
    )
    assert rewards["left_0"] == 70.0


def test_repro_rewards_use_public_reproduction_component():
    winner = PublicReproductionFish(1)
    loser = PublicReproductionFish(2)

    deltas = apply_soccer_repro_rewards(
        {"left_0": winner, "right_0": loser},
        "left",
        reward_mode="credits",
        credit_award=1.25,
    )

    assert deltas == {1: 1.25}
    assert winner.reproduction_component.repro_credits == 1.25
    assert loser.reproduction_component.repro_credits == 0.0
    assert not hasattr(winner, "_reproduction_component")


def test_tank_info_recorded_and_displayed():
    tracker = SoccerFishStatsTracker()
    tracker.record(
        _outcome(
            winner_team="left",
            entry_fees={1: 5.0},
            energy_deltas={1: 5.0},
            tank_names_by_fish={1: "Tank Blue"},
            tank_ids_by_fish={1: "blue_id"},
            offspring_count_by_fish={1: 3},
        )
    )
    leaders = tracker.leaders(5)
    assert len(leaders) == 1
    assert leaders[0]["tank_name"] == "Tank Blue"
    assert leaders[0]["tank_id"] == "blue_id"
    assert leaders[0]["offspring_count"] == 3
