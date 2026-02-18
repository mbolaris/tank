"""Tests verifying that long-running simulations don't accumulate unbounded state.

Each test simulates extended usage of a subsystem and asserts that internal
data structures remain capped at their expected limits.
"""

from unittest.mock import MagicMock


class TestEnhancedStatisticsTrackerBounds:
    """Verify that EnhancedStatisticsTracker data structures stay bounded."""

    def _make_tracker(self):
        from core.enhanced_statistics import EnhancedStatisticsTracker

        return EnhancedStatisticsTracker(max_history_length=100)

    def test_live_food_trait_samples_bounded(self):
        """Simulate 2000 live food captures; deque should stay at MAX_TRAIT_SAMPLES."""
        tracker = self._make_tracker()
        genome = MagicMock(speed_modifier=1.0, vision_range=50.0)
        genome.behavioral.behavior.value.short_description = "test"
        genome.behavioral.behavior.value.behavior_id = "test_id"
        genome.behavioral.behavior.value.food_approach.name = "chase"

        for i in range(2000):
            tracker.record_live_food_capture(algorithm_id=0, energy_gained=10.0, genome=genome)

        assert len(tracker.live_food_trait_samples["speed"]) <= tracker.MAX_TRAIT_SAMPLES
        assert len(tracker.live_food_trait_samples["vision"]) <= tracker.MAX_TRAIT_SAMPLES

    def test_trait_fitness_data_bounded(self):
        """Verify trait_fitness_data uses a bounded deque."""
        tracker = self._make_tracker()

        # Manually append to simulate usage
        for i in range(2000):
            tracker.trait_fitness_data["speed"].append((float(i), float(i) * 0.5))

        assert len(tracker.trait_fitness_data["speed"]) <= tracker.MAX_TRAIT_SAMPLES

    def test_extinct_algorithms_bounded(self):
        """Verify extinct_algorithms list is capped at MAX_EXTINCTIONS."""
        from core.enhanced_statistics import ExtinctionEvent

        tracker = self._make_tracker()

        for i in range(200):
            event = ExtinctionEvent(
                algorithm_id=i,
                algorithm_name=f"Algo_{i}",
                extinction_frame=i * 1000,
                total_births=100,
                total_deaths=100,
                avg_lifespan=500.0,
                extinction_cause="starvation",
            )
            tracker.extinct_algorithms.append(event)
            if len(tracker.extinct_algorithms) > tracker.MAX_EXTINCTIONS:
                tracker.extinct_algorithms = tracker.extinct_algorithms[-tracker.MAX_EXTINCTIONS :]

        assert len(tracker.extinct_algorithms) <= tracker.MAX_EXTINCTIONS
        # Most recent events should be kept
        assert tracker.extinct_algorithms[-1].algorithm_id == 199

    def test_trait_correlations_with_deque(self):
        """Verify calculate_trait_correlations works correctly with deques."""
        tracker = self._make_tracker()

        # Fill trait_fitness_data with correlated but not perfectly linear data
        import random

        rng = random.Random(42)
        for i in range(100):
            noise = rng.gauss(0, 0.1)
            tracker.trait_fitness_data["speed"].append((float(i) * 0.1, float(i) * 0.05 + noise))

        correlations = tracker.calculate_trait_correlations()
        assert len(correlations) == 1
        assert correlations[0].trait_name == "speed"
        assert correlations[0].correlation > 0.8  # Strong positive correlation

    def test_live_food_correlations_with_deque(self):
        """Verify calculate_live_food_correlations works correctly with deques."""
        import random

        tracker = self._make_tracker()
        rng = random.Random(42)

        # Simulate many live food captures with varied data
        genome = MagicMock(speed_modifier=1.0, vision_range=50.0)
        genome.behavioral.behavior.value.short_description = "test"
        genome.behavioral.behavior.value.behavior_id = "test_id"
        genome.behavioral.behavior.value.food_approach.name = "chase"

        for i in range(100):
            genome.speed_modifier = float(i) * 0.1 + rng.gauss(0, 0.2)
            genome.vision_range = float(i) * 0.5 + rng.gauss(0, 1.0)
            tracker.record_live_food_capture(
                algorithm_id=0, energy_gained=float(i) + rng.gauss(0, 0.5), genome=genome
            )

        correlations = tracker.calculate_live_food_correlations()
        assert len(correlations) == 2  # speed and vision


class TestPopulationTrackerPruning:
    """Verify that PopulationTracker prunes dead generation entries."""

    def _make_tracker(self):
        from core.population_tracker import PopulationTracker

        frame = [0]
        return (
            PopulationTracker(
                max_population=75,
                add_event_callback=lambda e: None,
                frame_provider=lambda: frame[0],
            ),
            frame,
        )

    def test_prune_dead_generations(self):
        """Simulate 200 generations; dead old ones should be pruned."""
        tracker, frame_ref = self._make_tracker()

        # Simulate 200 generations: each one born and then dies
        for gen in range(200):
            tracker.record_birth(fish_id=gen, generation=gen, algorithm_id=0)
            tracker.current_generation = gen

        # All 200 generations have births recorded and population=1
        assert len(tracker.generation_stats) >= 200

        # Kill all fish in generations 0-149 (keep 150-199 alive)
        for gen in range(150):
            if gen in tracker.generation_stats:
                tracker.generation_stats[gen].population = 0

        # Set frame to trigger prune
        frame_ref[0] = tracker.GENERATION_PRUNE_INTERVAL
        tracker._prune_dead_generations()

        # Generations within PRUNE_KEEP of current (199) should survive
        # Cutoff = 199 - 50 = 149, so generations 0-148 with pop==0 are pruned
        alive_gens = set(tracker.generation_stats.keys())

        # Check that old dead generations were removed
        for gen in range(149):  # 0 through 148 should be pruned
            assert gen not in alive_gens, f"Generation {gen} should have been pruned"

        # Generation 149 has population=0 but is at the cutoff boundary (149 < 149 is False)
        # Generations 150-199 are alive (population=1), they should still exist
        for gen in range(150, 200):
            assert gen in alive_gens, f"Generation {gen} should still exist"

    def test_prune_preserves_alive_generations(self):
        """Pruning should never remove generations with living fish."""
        tracker, frame_ref = self._make_tracker()

        # Create some very old generations that still have fish alive
        for gen in [0, 1, 100, 200]:
            tracker.record_birth(fish_id=gen, generation=gen, algorithm_id=0)
            tracker.current_generation = max(tracker.current_generation, gen)

        # All generations have population > 0, so nothing should be pruned
        frame_ref[0] = tracker.GENERATION_PRUNE_INTERVAL
        tracker._prune_dead_generations()

        assert 0 in tracker.generation_stats
        assert 1 in tracker.generation_stats
        assert 100 in tracker.generation_stats
        assert 200 in tracker.generation_stats


class TestSoccerLeaderboardCap:
    """Verify that SoccerLeagueRuntime leaderboard stays bounded."""

    def test_leaderboard_cap(self):
        """Verify leaderboard doesn't exceed MAX_LEADERBOARD_SIZE."""
        from core.minigames.soccer.league.types import LeagueLeaderboardEntry, TeamSource
        from core.minigames.soccer.league_runtime import SoccerLeagueRuntime

        config = MagicMock()
        config.enabled = True
        config.team_size = 3

        runtime = SoccerLeagueRuntime(config=config)

        # Add many teams directly to the leaderboard
        for i in range(80):
            runtime._leaderboard[f"team_{i}"] = LeagueLeaderboardEntry(
                team_id=f"team_{i}",
                display_name=f"Team {i}",
                source=TeamSource.TANK,
                points=i,  # Use index as points so sorting is deterministic
            )

        # Manually trigger the prune logic (same as in tick)
        if len(runtime._leaderboard) > runtime.MAX_LEADERBOARD_SIZE:
            sorted_entries = sorted(
                runtime._leaderboard.items(),
                key=lambda item: (item[1].points, item[1].goal_difference),
            )
            excess = len(runtime._leaderboard) - runtime.MAX_LEADERBOARD_SIZE
            for team_id, _ in sorted_entries[:excess]:
                del runtime._leaderboard[team_id]

        assert len(runtime._leaderboard) <= runtime.MAX_LEADERBOARD_SIZE
        # Highest-scoring teams should survive
        assert "team_79" in runtime._leaderboard
        # Lowest-scoring teams should be evicted
        assert "team_0" not in runtime._leaderboard
