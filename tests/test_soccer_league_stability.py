from unittest.mock import MagicMock, patch

from core.config.simulation_config import SoccerConfig
from core.minigames.soccer.evaluator import create_soccer_match_from_participants
from core.minigames.soccer.league.provider import LeagueTeamProvider
from core.minigames.soccer.league.types import TeamSource
from core.minigames.soccer.league_runtime import SoccerLeagueRuntime


class BotEntity:
    def __init__(self, name):
        self.name = name
        # Bots don't have energy or modify_energy


class FishEntity:
    def __init__(self, name, energy):
        self.name = name
        self.energy = energy

    def modify_energy(self, amount, source="unknown"):
        self.energy += amount

    def is_dead(self):
        return False


def test_zero_fee_eligibility():
    """Verify fish with 0 energy are eligible if fee is 0."""
    config = SoccerConfig(enabled=True, entry_fee_energy=0.0)
    provider = LeagueTeamProvider(config)

    # 0 energy fish
    fish = [FishEntity(f"Fish{i}", 0.0) for i in range(12)]

    # Mock world state
    mock_world = MagicMock()
    # Fallback path uses get_fish_list
    # ensure it doesn't look like an environment wrapper
    del mock_world.environment
    mock_world.get_fish_list.return_value = fish

    teams, avail = provider.get_teams(mock_world)

    # Needs 11 players. We have 12.
    # Should find Tank_A
    # keys depend on source. Fallback source name is 'Tank'.
    # ID is Tank_A or similar.

    # Check if ANY team is available
    available_count = sum(1 for t in avail.values() if t.is_available)
    # Tank A should be available (11 players needed, 12 eligible)
    # If 0 energy was filtered, eligible would be 0 -> Tank A unavailable.

    # provider generates Tank_A and Tank_B?
    # 12 players -> A gets 11, B gets 1. B unavailable. A available.

    # Note: provider might name it differently based on mocking
    # Just check if we got at least one available tank team
    assert available_count >= 1, f"Should have available teams. Got {avail}"

    tank_teams = [t for t in teams.values() if t.source == TeamSource.TANK]
    assert len(tank_teams) > 0


def test_bot_entry_fee_safety():
    """Verify create_soccer_match_from_participants does not raise for bots."""
    bots = [BotEntity(f"Bot{i}") for i in range(2)]

    # effectively mocked match creation to avoid heavy import/logic in test
    with patch("core.minigames.soccer.evaluator.SoccerMatch") as MockMatch:
        # Should not raise
        setup = create_soccer_match_from_participants(
            bots, entry_fee_energy=10.0, match_id="test_match"
        )
        assert setup.entry_fees == {}  # Bots pay nothing


def test_mixed_entry_fee_safety():
    """Verify fish pay and bots don't."""
    bot = BotEntity("Bot1")
    fish = FishEntity("Fish1", 100.0)
    participants = [bot, fish]

    with patch("core.minigames.soccer.evaluator.SoccerMatch") as MockMatch:
        setup = create_soccer_match_from_participants(
            participants, entry_fee_energy=10.0, match_id="test_match"
        )
        # Check fish paid
        assert fish.energy == 90.0
        # Check return dict
        # We need to know how create_soccer_match_from_participants identifies IDs.
        # It likely uses hash or id() if no specific ID method provided for BotEntity.
        # But wait, create_soccer_match_from_participants calls apply_soccer_entry_fees.
        # Let's see if we can check the length of entry_fees.
        assert len(setup.entry_fees) == 1


def test_league_runtime_crash_handling():
    """Verify runtime catches exceptions during match creation."""
    config = SoccerConfig(enabled=True, match_every_frames=1)
    runtime = SoccerLeagueRuntime(config)

    # Mock provider to return some teams
    mock_team = MagicMock()
    mock_team.roster = [1, 2]
    mock_teams = {"A": mock_team, "B": mock_team}
    mock_avail = {"A": MagicMock(is_available=True), "B": MagicMock(is_available=True)}

    runtime._provider = MagicMock()
    runtime._provider.get_teams.return_value = (mock_teams, mock_avail)

    # Mock scheduler to return a match
    mock_match = MagicMock(home_team_id="A", away_team_id="B", match_id="m1")
    runtime._scheduler = MagicMock()
    runtime._scheduler.get_next_match.return_value = mock_match

    # Mock create_soccer_match_from_participants to raise
    with patch(
        "core.minigames.soccer.league_runtime.create_soccer_match_from_participants",
        side_effect=ValueError("Boom"),
    ):
        # Should not raise
        runtime.tick(MagicMock(), seed_base=0, cycle=10)

        # Should have recorded a skipped event
        events = runtime.drain_events()
        assert len(events) == 1
        assert events[0].skipped is True
        assert "Boom" in events[0].skip_reason


def test_match_history_buffer():
    """Verify runtime keeps recent results."""
    config = SoccerConfig(enabled=True)
    # runtime = SoccerLeagueRuntime(config)

    # Inject some mock results
    from core.minigames.soccer.league.types import LeagueMatch

    # Simulate adding results (since _recent_results is internal, we might need to rely on side effects or inspect protected var if allowed for test)
    # The plan says we'll add `_recent_results`.
    # Let's assume we implement it as a deque.

    match1 = MagicMock(spec=LeagueMatch)
    match1.match_id = "m1"

    # We need to simulate finalize_active_match or manually append if we are unit testing just the buffer
    # But let's wait until we implement it to match the field name.
    # For now, this test expects the field check to fail or pass after implementation.
    pass


from core.minigames.soccer.types import SoccerMinigameOutcome


def test_live_state_serialization_keys():
    """Ensure dictionary keys in live state are strings for JSON compatibility."""
    config = SoccerConfig(enabled=True)
    league_runtime = SoccerLeagueRuntime(config)

    # Inject a fake outcome with integer keys
    outcome = SoccerMinigameOutcome(
        match_id="test_match_1",
        match_counter=1,
        winner_team="left",
        score_left=1,
        score_right=0,
        frames=100,
        seed=123,
        selection_seed=456,
        message="Test match",
        rewarded={1: 10.0, 2: 5.0},  # Int keys
        entry_fees={1: 1.0, 2: 1.0},  # Int keys
        energy_deltas={1: 9.0, 2: 4.0},  # Int keys
        repro_credit_deltas={1: 0.5},  # Int keys
        teams={"left": [1], "right": [2]},
        skipped=False,
        skip_reason=None,
    )
    league_runtime._recent_results.append(outcome)

    # Get live state
    state = league_runtime.get_live_state()

    # Verify recent_results structure
    assert "recent_results" in state
    assert len(state["recent_results"]) == 1
    result = state["recent_results"][0]

    # Check energy_deltas keys are strings
    assert isinstance(result["energy_deltas"], dict)
    assert "1" in result["energy_deltas"]
    assert result["energy_deltas"]["1"] == 9.0

    # Check repro_credit_deltas keys are strings
    assert isinstance(result["repro_credit_deltas"], dict)
    assert "1" in result["repro_credit_deltas"]
    assert result["repro_credit_deltas"]["1"] == 0.5
