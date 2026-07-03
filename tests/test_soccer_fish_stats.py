"""Unit tests for per-fish soccer standings aggregation."""

from core.minigames.soccer.fish_stats import SoccerFishStatsTracker
from core.minigames.soccer.types import SoccerMinigameOutcome
from core.simulation.event_managers import SoccerEventManager


def _outcome(**overrides) -> SoccerMinigameOutcome:
    defaults = {
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
        "energy_deltas": {1: 8.0, 2: -5.0},
        "repro_credit_deltas": {},
        "teams": {"left": [1], "right": [2]},
        "goals_by_fish": {1: 2},
        "assists_by_fish": {},
    }
    defaults.update(overrides)
    return SoccerMinigameOutcome(**defaults)


def test_tracker_aggregates_wins_goals_and_energy():
    tracker = SoccerFishStatsTracker()
    tracker.record(_outcome())
    tracker.record(
        _outcome(
            match_id="m2",
            winner_team="right",
            energy_deltas={1: -5.0, 2: 6.5},
            goals_by_fish={2: 1},
            assists_by_fish={1: 1},
        )
    )

    leaders = tracker.leaders(10)
    by_id = {row["fish_id"]: row for row in leaders}

    assert by_id[1]["matches"] == 2
    assert by_id[1]["wins"] == 1
    assert by_id[1]["losses"] == 1
    assert by_id[1]["goals"] == 2
    assert by_id[1]["assists"] == 1
    assert by_id[1]["net_energy"] == 3.0

    assert by_id[2]["wins"] == 1
    assert by_id[2]["goals"] == 1
    assert by_id[2]["net_energy"] == 1.5


def test_tracker_counts_draws():
    tracker = SoccerFishStatsTracker()
    tracker.record(_outcome(winner_team="draw", energy_deltas={1: 0.0, 2: 0.0}))

    by_id = {row["fish_id"]: row for row in tracker.leaders(10)}
    assert by_id[1]["draws"] == 1
    assert by_id[1]["wins"] == 0
    assert by_id[1]["losses"] == 0


def test_tracker_ignores_skipped_and_botlike_outcomes():
    tracker = SoccerFishStatsTracker()
    tracker.record(_outcome(skipped=True, skip_reason="not enough players"))
    # Bot wins clear fees and deltas, so there are no participants to credit.
    tracker.record(_outcome(entry_fees={}, energy_deltas={}))

    assert tracker.leaders(10) == []


def test_leaders_ranked_and_capped_to_top_n():
    tracker = SoccerFishStatsTracker()
    # Fish 1..6: fish k wins k matches (all on the left, winner=left).
    for fish_id in range(1, 7):
        for match in range(fish_id):
            tracker.record(
                _outcome(
                    match_id=f"m{fish_id}-{match}",
                    entry_fees={fish_id: 5.0},
                    energy_deltas={fish_id: 1.0},
                    teams={"left": [fish_id], "right": []},
                    goals_by_fish={},
                )
            )

    leaders = tracker.leaders(3)
    assert len(leaders) == 3
    assert [row["fish_id"] for row in leaders] == [6, 5, 4]


def test_tracker_prunes_to_bound():
    tracker = SoccerFishStatsTracker(max_tracked=5)
    for fish_id in range(20):
        tracker.record(
            _outcome(
                match_id=f"m{fish_id}",
                entry_fees={fish_id: 5.0},
                energy_deltas={fish_id: float(fish_id)},
                teams={"left": [fish_id], "right": []},
                goals_by_fish={},
            )
        )

    assert len(tracker.leaders(100)) <= 5


def test_event_manager_exposes_fish_leaders():
    manager = SoccerEventManager(frame_provider=lambda: 42)
    manager.record_outcome(_outcome())

    leaders = manager.fish_leaders(5)
    assert leaders
    assert leaders[0]["fish_id"] == 1
    assert leaders[0]["wins"] == 1
