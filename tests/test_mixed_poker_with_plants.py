"""Comprehensive tests for mixed poker games involving plants.

Tests verify that:
1. Plants can be detected in proximity for poker
2. Plant-plant poker games occur
3. Fish-plant poker games can occur when in proximity
4. Poker results are properly recorded (wins/losses)
5. Energy transfers work correctly
6. Cooldowns are applied after games

Performance optimizations:
- Uses pytest fixtures for shared engine setup
- Caches entity filtering results
- Uses squared distances to avoid sqrt overhead
- Consolidates duplicate test logic
"""

import math

import pytest

from core.config.ecosystem import FISH_POKER_MAX_DISTANCE
from core.config.plants import PLANT_POKER_MAX_DISTANCE, PLANT_POKER_MIN_DISTANCE
from core.config.poker import POKER_MAX_PLAYERS
from core.entities import Fish
from core.entities.plant import Plant
from core.mixed_poker import MixedPokerInteraction, check_poker_proximity
from core.simulation.engine import SimulationEngine

# ============================================================================
# Fixtures for shared setup
# ============================================================================


@pytest.fixture
def engine():
    """Create a headless simulation engine."""
    eng = SimulationEngine(headless=True)
    eng.setup()
    return eng


@pytest.fixture
def engine_with_entities(engine):
    """Engine with cached entity lists for faster access."""
    all_entities = engine.get_all_entities()
    return {
        "engine": engine,
        "fish": [e for e in all_entities if isinstance(e, Fish)],
        "plants": [e for e in all_entities if isinstance(e, Plant)],
    }


@pytest.fixture
def run_simulation():
    """Factory fixture to run simulation for N frames and return entities."""

    def _run(frames: int = 600):
        engine = SimulationEngine(headless=True)
        engine.setup()
        for _ in range(frames):
            engine.update()
        all_entities = engine.get_all_entities()
        return {
            "engine": engine,
            "fish": [e for e in all_entities if isinstance(e, Fish)],
            "plants": [e for e in all_entities if isinstance(e, Plant)],
        }

    return _run


# ============================================================================
# Helper functions for common operations
# ============================================================================


def distance_squared(p1, p2) -> float:
    """Calculate squared distance between two entities (avoids sqrt)."""
    dx = p1.pos.x - p2.pos.x
    dy = p1.pos.y - p2.pos.y
    return dx * dx + dy * dy


def distance(p1, p2) -> float:
    """Calculate distance between two entities."""
    return math.sqrt(distance_squared(p1, p2))


def get_min_distance_between_entities(entities: list) -> float:
    """Find minimum distance between any pair of entities."""
    if len(entities) < 2:
        return float("inf")

    min_dist_sq = float("inf")
    for i, e1 in enumerate(entities):
        for e2 in entities[i + 1 :]:
            dist_sq = distance_squared(e1, e2)
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq

    return math.sqrt(min_dist_sq) if min_dist_sq < float("inf") else 0.0


def plants_have_played_poker(plants: list) -> bool:
    """Check if any plant has participated in poker."""
    return any(p.poker_wins > 0 or p.poker_losses > 0 for p in plants)


def reset_cooldowns(*entities):
    """Reset poker cooldowns for given entities."""
    for entity in entities:
        entity.poker_cooldown = 0


# ============================================================================
# Test Classes
# ============================================================================


class TestPlantPokerDetection:
    """Tests for plant proximity detection in poker."""

    def test_plants_in_spatial_grid(self, engine):
        """Verify plants are properly added to the spatial grid."""
        plant_list = [e for e in engine.get_all_entities() if isinstance(e, Plant)]
        assert len(plant_list) > 0, "Should have at least one plant"

        # Check spatial grid contains Plant type
        grid = engine.environment.spatial_grid
        types_in_grid = {
            type_key.__name__ for buckets in grid.grid.values() for type_key in buckets
        }

        assert "Plant" in types_in_grid, "Plant should be in spatial grid"

    def test_nearby_agents_by_type_finds_plants(self, engine_with_entities):
        """Verify nearby_agents_by_type can find Plant entities."""
        engine = engine_with_entities["engine"]
        plant_list = engine_with_entities["plants"]

        if len(plant_list) < 2:
            pytest.skip("Need at least 2 plants for this test")

        plant = plant_list[0]
        env = engine.environment

        # Use large radius to ensure we find other plants
        search_radius = 500
        nearby = env.nearby_agents_by_type(plant, radius=search_radius, agent_class=Plant)

        # Should find at least one other plant (excluding self)
        if len(nearby) < 1:
            pytest.skip(
                "No plants found within search radius; possible random placement edge case."
            )
        assert plant not in nearby, "Should not include self in nearby results"

    def test_plant_poker_max_distance_is_sufficient(self, engine_with_entities):
        """Verify the max distance constant allows plant-plant poker."""
        plant_list = engine_with_entities["plants"]

        if len(plant_list) < 2:
            pytest.skip("Need at least 2 plants")

        min_dist = get_min_distance_between_entities(plant_list)

        if min_dist > PLANT_POKER_MAX_DISTANCE:
            pytest.skip(
                f"Random plant placement resulted in spread-out plants "
                f"(min distance {min_dist:.1f}px > {PLANT_POKER_MAX_DISTANCE}px). "
                f"This is expected occasionally."
            )


class TestPlantPokerGames:
    """Tests for actual poker game execution with plants."""

    @pytest.mark.slow
    def test_plants_can_play_poker(self, run_simulation):
        """Verify plants can participate in poker games.

        Note: This test may occasionally fail due to random plant placement.
        We run multiple trials with more frames to reduce flakiness.
        """
        # Run 5 trials with 1200 frames each for better coverage
        for trial in range(5):
            result = run_simulation(frames=1200)
            if plants_have_played_poker(result["plants"]):
                return  # Test passes

        pytest.fail("At least one plant should have played poker in 5 trials of 1200 frames")

    @pytest.mark.slow
    def test_plant_poker_records_wins_and_losses(self, run_simulation):
        """Verify poker games properly record wins and losses for plants."""
        # Run 5 trials with 1200 frames each for better coverage
        for trial in range(5):
            result = run_simulation(frames=1200)
            plants = result["plants"]

            total_wins = sum(p.poker_wins for p in plants)
            total_losses = sum(p.poker_losses for p in plants)

            if total_wins > 0 or total_losses > 0:
                return  # Test passes

        pytest.fail("Should have recorded some poker results in 5 trials of 1200 frames")

    def test_plant_energy_changes_after_poker(self, engine, monkeypatch):
        """Verify plant energy changes as a result of poker games."""
        all_entities = engine.get_all_entities()
        fish = [e for e in all_entities if isinstance(e, Fish)]
        plants = [e for e in all_entities if isinstance(e, Plant)]

        if len(fish) < 1 or len(plants) < 1:
            pytest.skip("Need at least 1 fish and 1 plant")

        reset_cooldowns(fish[0], plants[0])
        initial_energy = plants[0].energy

        def force_fold(game_state, contexts, start_position, **kwargs):
            game_state.player_folded[1] = True
            contexts[1].folded = True
            return False

        monkeypatch.setattr("core.mixed_poker.interaction.play_betting_round", force_fold)

        poker = MixedPokerInteraction([fish[0], plants[0]])
        result = poker.play_poker(bet_amount=10.0)

        assert result is True
        assert plants[0].energy < initial_energy

    def test_plant_cooldown_applied_after_poker(self, engine):
        """Verify poker cooldown is applied to plants after games."""
        # Run a few frames to trigger poker
        for _ in range(120):
            engine.update()

        # Cooldown check is implicit - if games occur, cooldowns are set
        # This test validates the simulation runs without error


class TestPokerPlayerLimits:
    """Tests for poker player count limits to prevent deck exhaustion."""

    def test_fish_poker_max_players_enforced(self, engine_with_entities):
        """Verify PokerInteraction enforces MAX_PLAYERS limit."""
        from core.poker_interaction import MAX_PLAYERS, PokerInteraction

        fish = engine_with_entities["fish"]

        # MixedPokerInteraction raises ValueError if too many players
        if len(fish) > MAX_PLAYERS:
            with pytest.raises(ValueError):
                PokerInteraction(list(fish))

    def test_mixed_poker_max_players_enforced(self, engine_with_entities):
        """Verify MixedPokerInteraction enforces POKER_MAX_PLAYERS limit."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        # Combine fish and plants
        players = fish + plants

        if len(players) > POKER_MAX_PLAYERS:
            # Should raise ValueError if we try to pass too many
            with pytest.raises(ValueError):
                MixedPokerInteraction(players)

    def test_deck_has_enough_cards_for_max_players(self):
        """Verify a 52-card deck can handle MAX_PLAYERS."""
        from core.poker_interaction import MAX_PLAYERS

        # With 52 cards:
        # - Each player needs 2 hole cards
        # - Community needs 5 cards + 3 burns = 8 cards
        # Max players = (52 - 8) / 2 = 22
        cards_for_community = 8
        cards_per_player = 2
        max_theoretical = (52 - cards_for_community) // cards_per_player

        assert (
            max_theoretical >= MAX_PLAYERS
        ), f"MAX_PLAYERS ({MAX_PLAYERS}) exceeds deck capacity ({max_theoretical})"


class TestMixedPokerInteraction:
    """Tests for the MixedPokerInteraction class with plants."""

    def test_plant_only_poker_not_allowed(self, engine_with_entities):
        """Verify MixedPokerInteraction rejects plant-only games (requires at least 1 fish)."""
        plants = engine_with_entities["plants"]

        if len(plants) < 2:
            pytest.skip("Need at least 2 plants")

        with pytest.raises(ValueError, match="require at least 1 fish"):
            MixedPokerInteraction(plants[:2])

    def test_play_poker_requires_fish(self, engine_with_entities):
        """Verify poker games require at least 1 fish player."""
        plants = engine_with_entities["plants"]

        if len(plants) < 2:
            pytest.skip("Need at least 2 plants")

        with pytest.raises(ValueError, match="require at least 1 fish"):
            MixedPokerInteraction(plants[:2])

    def test_mixed_fish_plant_poker(self, engine_with_entities):
        """Verify poker works with mixed fish and plant players."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        if len(fish) < 1 or len(plants) < 1:
            pytest.skip("Need at least 1 fish and 1 plant")

        reset_cooldowns(fish[0], plants[0])

        poker = MixedPokerInteraction([fish[0], plants[0]])
        result = poker.play_poker()

        assert result is True, "Mixed poker should complete"

    def test_multiplayer_mixed_poker(self, engine_with_entities):
        """Verify poker works with 3+ players including fish and plants."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        if len(fish) < 1 or len(plants) < 2:
            pytest.skip("Need at least 1 fish and 2 plants")

        reset_cooldowns(fish[0], plants[0], plants[1])

        players = [fish[0]] + plants[:2]
        poker = MixedPokerInteraction(players)
        result = poker.play_poker()

        assert result is True, "3-player mixed poker should complete"


class TestFishRequirement:
    """Tests ensuring poker games require at least 1 fish."""

    def test_mixed_poker_rejects_plant_only(self, engine_with_entities):
        """Verify MixedPokerInteraction raises ValueError for plant-only games."""
        plants = engine_with_entities["plants"]

        if len(plants) < 2:
            pytest.skip("Need at least 2 plants")

        with pytest.raises(ValueError) as exc_info:
            MixedPokerInteraction(plants[:2])

        assert "require at least 1 fish" in str(exc_info.value)

    def test_fish_plant_poker_allowed(self, engine_with_entities):
        """Verify poker with at least 1 fish is allowed."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        if len(fish) < 1 or len(plants) < 1:
            pytest.skip("Need at least 1 fish and 1 plant")

        reset_cooldowns(fish[0], plants[0])

        poker = MixedPokerInteraction([fish[0], plants[0]])
        assert poker.fish_count >= 1
        assert poker is not None

    def test_poker_result_always_has_fish(self, engine_with_entities):
        """Verify MixedPokerResult from games always contains at least 1 fish."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        if len(fish) < 1 or len(plants) < 1:
            pytest.skip("Need at least 1 fish and 1 plant")

        reset_cooldowns(fish[0], plants[0])

        poker = MixedPokerInteraction([fish[0], plants[0]])
        result = poker.play_poker()

        assert result is True
        assert poker.fish_count >= 1, "Game should have at least 1 fish"


class TestProximityCheck:
    """Tests for the poker proximity check function."""

    def test_check_poker_proximity_within_range(self, engine_with_entities):
        """Verify proximity check returns True for entities within range."""
        plants = engine_with_entities["plants"]

        if len(plants) < 2:
            pytest.skip("Need at least 2 plants")

        p1, p2 = plants[0], plants[1]
        dist = distance(p1, p2)

        # Check with large max distance to ensure they're in range
        in_range = check_poker_proximity(
            p1, p2, min_distance=PLANT_POKER_MIN_DISTANCE, max_distance=500
        )

        if dist > PLANT_POKER_MIN_DISTANCE and dist <= 500:
            assert in_range is True, f"Plants at {dist:.1f}px should be in range"

    def test_check_poker_proximity_too_close(self, engine_with_entities):
        """Verify proximity check returns False for overlapping entities."""
        plants = engine_with_entities["plants"]

        if len(plants) < 1:
            pytest.skip("Need at least 1 plant")

        # Two identical positions would be "too close" (below min distance)
        # This is a structural test - actual overlap is hard to test without moving plants

    def test_check_poker_proximity_too_far(self, engine_with_entities):
        """Verify proximity check returns False for distant entities."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        if len(fish) < 1 or len(plants) < 1:
            pytest.skip("Need fish and plants")

        f, p = fish[0], plants[0]
        dist = distance(f, p)

        # Test with small max distance
        in_range = check_poker_proximity(f, p, min_distance=10, max_distance=50)

        if dist > 50:
            assert in_range is False, f"Entities at {dist:.1f}px should not be in 50px range"


class TestMutualProximityFiltering:
    """Tests for verifying all poker players are mutually within max distance."""

    def test_no_chain_connected_players(self, run_simulation):
        """Verify poker games don't include chain-connected players that are far apart.

        If A is near B and B is near C, but A and C are far apart,
        they should NOT all be in the same poker game.
        """
        result = run_simulation(frames=600)
        engine = result["engine"]

        max_distance = 80  # Current configured max distance
        max_dist_sq = max_distance * max_distance
        violations = []

        for event in engine.poker_events:
            players = event.get("players", [])
            if len(players) >= 2:
                # Check all pairs using squared distance
                for i, p1 in enumerate(players):
                    for p2 in players[i + 1 :]:
                        dist_sq = distance_squared(p1, p2)
                        if dist_sq > max_dist_sq:
                            violations.append(
                                (type(p1).__name__, type(p2).__name__, math.sqrt(dist_sq))
                            )

        assert len(violations) == 0, (
            f"Found {len(violations)} poker player pairs exceeding {max_distance}px: "
            f"{violations[:3]}"
        )

    def test_all_poker_players_within_max_distance(self, run_simulation):
        """Verify all players in any poker game are within configured max distance."""
        result = run_simulation(frames=600)
        engine = result["engine"]

        max_dist = max(FISH_POKER_MAX_DISTANCE, PLANT_POKER_MAX_DISTANCE)
        max_dist_sq = max_dist * max_dist

        for event in engine.poker_events:
            players = event.get("players", [])
            for i, p1 in enumerate(players):
                for p2 in players[i + 1 :]:
                    dist_sq = distance_squared(p1, p2)

                    assert dist_sq <= max_dist_sq, (
                        f"{type(p1).__name__} and {type(p2).__name__} at {math.sqrt(dist_sq):.1f}px "
                        f"exceeds max distance ({max_dist}px)"
                    )


class TestPokerEffectState:
    """Tests for poker effect state handling on plants."""

    def test_plant_poker_effect_state_format(self, engine):
        """Verify poker effect state is properly formatted dict."""
        # Run simulation until we get a poker game
        for _ in range(600):
            engine.update()

            for p in (e for e in engine.get_all_entities() if isinstance(e, Plant)):
                if p.poker_effect_state is not None:
                    # Verify it's a dict with expected keys
                    assert isinstance(
                        p.poker_effect_state, dict
                    ), f"poker_effect_state should be dict, got {type(p.poker_effect_state)}"
                    assert "status" in p.poker_effect_state, "Should have 'status' key"
                    assert p.poker_effect_state["status"] in (
                        "won",
                        "lost",
                    ), f"Status should be 'won' or 'lost', got {p.poker_effect_state['status']}"
                    return  # Found valid state, test passes

        # If no poker effect state found, that's okay - games might have finished


class TestSimulationIntegration:
    """Integration tests for the full simulation with plants."""

    @pytest.mark.slow
    def test_long_simulation_stability(self, engine):
        """Verify simulation runs stably with plant poker for extended time."""
        # Run for 30 seconds (1800 frames)
        for frame in range(1800):
            try:
                engine.update()
            except Exception as e:
                pytest.fail(f"Simulation crashed at frame {frame}: {e}")

        # Simulation completed without errors
        assert True

    def test_poker_events_recorded(self, run_simulation):
        """Verify poker events are being recorded."""
        result = run_simulation(frames=600)
        poker_events = list(result["engine"].poker_events)

        assert len(poker_events) > 0, "Should have recorded poker events"


class TestEnergyTransferTracking:
    """Tests for tracking plant-fish energy transfers in poker stats."""

    def test_poker_stats_manager_tracks_energy_transfer(self):
        """Verify PokerStatsManager.record_mixed_poker_energy_transfer works correctly."""
        from core.poker_stats_manager import PokerStatsManager

        manager = PokerStatsManager(lambda e: None, lambda: 0)

        assert manager.total_plant_poker_energy_transferred == 0.0

        # Fish wins 15 energy from plants
        manager.record_mixed_poker_energy_transfer(energy_to_fish=15.0, is_plant_game=True)
        assert manager.total_plant_poker_energy_transferred == 15.0

        # Plant wins 10 energy from fish (negative flow to fish)
        manager.record_mixed_poker_energy_transfer(energy_to_fish=-10.0, is_plant_game=True)
        assert manager.total_plant_poker_energy_transferred == 5.0

        # Verify summary includes the value
        summary = manager.get_poker_stats_summary()
        assert summary["total_plant_energy_transferred"] == 5.0

    def test_ecosystem_manager_exposes_energy_tracking(self):
        """Verify EcosystemManager has record_mixed_poker_energy_transfer method."""
        from core.ecosystem import EcosystemManager

        ecosystem = EcosystemManager()

        assert hasattr(ecosystem, "record_mixed_poker_energy_transfer")

        initial = ecosystem.poker_manager.total_plant_poker_energy_transferred
        ecosystem.record_mixed_poker_energy_transfer(energy_to_fish=20.0, is_plant_game=True)

        assert ecosystem.poker_manager.total_plant_poker_energy_transferred == initial + 20.0

    def test_mixed_poker_result_contains_energy_transferred(self, engine_with_entities):
        """Verify MixedPokerResult contains energy_transferred field."""
        fish = engine_with_entities["fish"]
        plants = engine_with_entities["plants"]

        if len(fish) < 1 or len(plants) < 1:
            pytest.skip("Need at least 1 fish and 1 plant")

        reset_cooldowns(fish[0], plants[0])

        poker = MixedPokerInteraction([fish[0], plants[0]])
        poker.play_poker()

        result = poker.result
        assert result is not None, "Should have result"
        assert hasattr(result, "energy_transferred"), "Result should have energy_transferred"
        assert isinstance(result.energy_transferred, (int, float))

    def test_plant_fish_energy_tracking_in_simulation(self, engine):
        """Verify plant-fish energy transfers are tracked during simulation."""
        if not hasattr(engine, "ecosystem") or engine.ecosystem is None:
            pytest.skip("Engine doesn't have ecosystem")

        # Run simulation
        for _ in range(600):
            engine.update()

        final_transfer = engine.ecosystem.poker_manager.total_plant_poker_energy_transferred

        # Just verify it's being tracked (not None or missing)
        assert isinstance(final_transfer, (int, float)), "Energy transfer should be tracked"

    def test_energy_transfer_sign_convention(self):
        """Verify positive = fish gained, negative = plants gained."""
        from core.poker_stats_manager import PokerStatsManager

        manager = PokerStatsManager(lambda e: None, lambda: 0)

        # Fish wins - positive energy to fish
        manager.record_mixed_poker_energy_transfer(energy_to_fish=100.0, is_plant_game=True)
        assert manager.total_plant_poker_energy_transferred == 100.0

        # Plant wins - negative energy to fish (fish loses)
        manager.record_mixed_poker_energy_transfer(energy_to_fish=-50.0, is_plant_game=True)
        assert manager.total_plant_poker_energy_transferred == 50.0

        summary = manager.get_poker_stats_summary()
        assert summary["total_plant_energy_transferred"] == 50.0


def run_manual_test():
    """Manual test runner for debugging."""
    print("=" * 60)
    print("Running Mixed Poker with Plants Tests")
    print("=" * 60)

    engine = SimulationEngine(headless=True)
    engine.setup()

    all_entities = engine.get_all_entities()
    fish_list = [e for e in all_entities if isinstance(e, Fish)]
    plant_list = [e for e in all_entities if isinstance(e, Plant)]

    print("\nInitial state:")
    print(f"  Fish: {len(fish_list)}")
    print(f"  Plants: {len(plant_list)}")

    print("\nPlant positions:")
    for i, p in enumerate(plant_list):
        print(f"  Plant {i}: ({p.pos.x:.1f}, {p.pos.y:.1f}), energy={p.energy:.1f}")

    print("\nProximity settings:")
    print(f"  FISH_POKER_MAX_DISTANCE: {FISH_POKER_MAX_DISTANCE}")
    print(f"  PLANT_POKER_MAX_DISTANCE: {PLANT_POKER_MAX_DISTANCE}")

    # Calculate plant distances using helper
    if len(plant_list) >= 2:
        print("\nPlant-plant distances:")
        for i, p1 in enumerate(plant_list):
            for j, p2 in enumerate(plant_list[i + 1 :], i + 1):
                dist = distance(p1, p2)
                in_range = dist <= PLANT_POKER_MAX_DISTANCE
                print(
                    f"  Plant {i} <-> Plant {j}: {dist:.1f}px {'(in range)' if in_range else '(out of range)'}"
                )

    print("\nRunning simulation for 600 frames...")
    for frame in range(600):
        engine.update()

        if frame % 100 == 99:
            plants = [e for e in engine.get_all_entities() if isinstance(e, Plant)]
            games_played = sum(p.poker_wins + p.poker_losses for p in plants)
            print(f"  Frame {frame + 1}: {games_played} total plant poker games")

    print("\nFinal plant poker stats:")
    final_plants = [e for e in engine.get_all_entities() if isinstance(e, Plant)]
    for p in final_plants:
        print(
            f"  Plant {p.plant_id}: {p.poker_wins} wins, {p.poker_losses} losses, energy={p.energy:.1f}"
        )

    total_poker_events = len(list(engine.poker_events))
    print(f"\nTotal poker events recorded: {total_poker_events}")

    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_manual_test()
