"""Unit tests for the metrics-history buffer and Trends tab backend features."""

from __future__ import annotations

from backend.metrics_history import MetricsHistory
from backend.state_payloads import PokerStatsPayload, StatsPayload
from backend.world_registry import create_world


def test_metrics_history_capacity_and_interval() -> None:
    """Test that MetricsHistory correctly samples at intervals and respects capacity."""
    history = MetricsHistory(world_id="test-world", sample_interval_frames=5, max_samples=3)

    # Mock stats
    stats = StatsPayload(
        frame=0,
        population=10,
        generation=1,
        max_generation=1,
        births=0,
        deaths=0,
        capacity="10%",
        time="Day",
        death_causes={},
        fish_count=10,
        food_count=5,
        plant_count=5,
        total_energy=1000.0,
        food_energy=100.0,
        live_food_count=2,
        live_food_energy=20.0,
        fish_energy=800.0,
        plant_energy=100.0,
    )
    poker = PokerStatsPayload(
        total_games=10,
        total_fish_games=10,
        total_plant_games=0,
        total_plant_energy_transferred=0.0,
        total_wins=5,
        total_losses=5,
        total_ties=0,
        total_energy_won=50.0,
        total_energy_lost=50.0,
        net_energy=0.0,
        best_hand_rank=0,
        best_hand_name="None",
        showdown_win_rate="50.0%",
    )

    # Feed frames 1 to 20
    for frame in range(1, 21):
        history.maybe_sample(
            frame=frame,
            stats=stats,
            poker=poker,
            soccer=[],
            auto_eval=None,
        )

    # Should only sample at frame 5, 10, 15, 20
    # Capacity is 3, so only the last 3 samples should remain: 10, 15, 20
    assert len(history.samples) == 3
    assert history.samples[0]["frame"] == 10
    assert history.samples[1]["frame"] == 15
    assert history.samples[2]["frame"] == 20
    # Every sample carries a (possibly empty) traits mapping for schema v2.
    assert all("traits" in sample for sample in history.samples)
    assert history.schema_version == 2


def test_is_sample_due_matches_interval() -> None:
    """is_sample_due should only be true on interval boundaries (and never frame 0)."""
    history = MetricsHistory(world_id="test-world", sample_interval_frames=5, max_samples=3)
    assert not history.is_sample_due(0)
    assert not history.is_sample_due(4)
    assert history.is_sample_due(5)
    assert history.is_sample_due(10)
    assert not history.is_sample_due(11)


def test_maybe_sample_records_trait_means() -> None:
    """Trait means passed to maybe_sample are stored under the sample's 'traits' key."""
    history = MetricsHistory(world_id="test-world", sample_interval_frames=5, max_samples=3)
    stats = StatsPayload(
        frame=5,
        population=10,
        generation=1,
        max_generation=1,
        births=0,
        deaths=0,
        capacity="10%",
        time="Day",
        death_causes={},
        fish_count=10,
        food_count=5,
        plant_count=5,
        total_energy=1000.0,
        food_energy=100.0,
        live_food_count=2,
        live_food_energy=20.0,
        fish_energy=800.0,
        plant_energy=100.0,
    )
    poker = PokerStatsPayload(
        total_games=0,
        total_fish_games=0,
        total_plant_games=0,
        total_plant_energy_transferred=0.0,
        total_wins=0,
        total_losses=0,
        total_ties=0,
        total_energy_won=0.0,
        total_energy_lost=0.0,
        net_energy=0.0,
        best_hand_rank=0,
        best_hand_name="None",
        showdown_win_rate="0.0%",
    )

    history.maybe_sample(
        frame=5,
        stats=stats,
        poker=poker,
        soccer=[],
        auto_eval=None,
        trait_means={"pursuit_aggression": 0.51, "speed": 1.02},
    )

    assert history.samples[-1]["traits"] == {"pursuit_aggression": 0.51, "speed": 1.02}
    # Omitting trait_means yields an empty mapping rather than a missing key.
    history.maybe_sample(frame=10, stats=stats, poker=poker, soccer=[], auto_eval=None)
    assert history.samples[-1]["traits"] == {}


def test_maybe_sample_prefers_fish_count_for_population() -> None:
    """History population should mean living fish, not legacy cumulative counters."""
    history = MetricsHistory(world_id="test-world", sample_interval_frames=5, max_samples=3)
    stats = StatsPayload(
        frame=5,
        population=8022,
        generation=1,
        max_generation=1,
        births=0,
        deaths=0,
        capacity="10%",
        time="Day",
        death_causes={},
        fish_count=25,
        food_count=5,
        plant_count=5,
        total_energy=1000.0,
        food_energy=100.0,
        live_food_count=2,
        live_food_energy=20.0,
        fish_energy=800.0,
        plant_energy=100.0,
    )
    poker = PokerStatsPayload(
        total_games=0,
        total_fish_games=0,
        total_plant_games=0,
        total_plant_energy_transferred=0.0,
        total_wins=0,
        total_losses=0,
        total_ties=0,
        total_energy_won=0.0,
        total_energy_lost=0.0,
        net_energy=0.0,
        best_hand_rank=0,
        best_hand_name="None",
        showdown_win_rate="0.0%",
    )

    history.maybe_sample(frame=5, stats=stats, poker=poker, soccer=[], auto_eval=None)

    assert history.samples[-1]["population"] == 25


def test_metrics_history_serialization_roundtrip() -> None:
    """Test payload round-trip serialization and deserialization."""
    history = MetricsHistory(world_id="test-world", sample_interval_frames=5, max_samples=3)

    # Mock soccer events to increment counters
    soccer_events = [
        {"match_id": "m1", "score_left": 2, "score_right": 1, "skipped": False},
        {"match_id": "m2", "score_left": 0, "score_right": 0, "skipped": True},
    ]

    stats = StatsPayload(
        frame=5,
        population=10,
        generation=1,
        max_generation=1,
        births=2,
        deaths=1,
        capacity="10%",
        time="Day",
        death_causes={},
        fish_count=10,
        food_count=5,
        plant_count=5,
        total_energy=1000.0,
        food_energy=100.0,
        live_food_count=2,
        live_food_energy=20.0,
        fish_energy=800.0,
        plant_energy=100.0,
    )
    poker = PokerStatsPayload(
        total_games=10,
        total_fish_games=10,
        total_plant_games=0,
        total_plant_energy_transferred=0.0,
        total_wins=5,
        total_losses=5,
        total_ties=0,
        total_energy_won=50.0,
        total_energy_lost=50.0,
        net_energy=0.0,
        best_hand_rank=0,
        best_hand_name="None",
        showdown_win_rate="50.0%",
    )

    history.maybe_sample(
        frame=5,
        stats=stats,
        poker=poker,
        soccer=soccer_events,
        auto_eval=None,
    )

    # Verify initial stats
    assert history.soccer_goals_total == 3
    assert history.soccer_matches_completed == 1
    assert history.soccer_matches_skipped == 1

    # Serialize
    payload = history.to_payload()
    assert payload["world_id"] == "test-world"
    assert len(payload["samples"]) == 1

    # Deserialize into new instance
    new_history = MetricsHistory(world_id="new-world")
    new_history.load(payload)

    assert new_history.world_id == "test-world"
    assert len(new_history.samples) == 1
    assert new_history.samples[0]["frame"] == 5
    assert new_history.soccer_goals_total == 3
    assert new_history.soccer_matches_completed == 1
    assert new_history.soccer_matches_skipped == 1
    assert "m1" in new_history.processed_soccer_match_ids


def test_metrics_collection_determinism_guard() -> None:
    """Test that stats/metrics collection does not perturb the simulation RNG/state."""
    # We run two simulations using the same seed.
    # Sim A runs step-by-step and simulates calling stats collection with metrics history.
    # Sim B runs step-by-step without calling stats collection.
    # The final state of entities and spatial grids must be completely identical.
    seed = 42
    world_a, _ = create_world("tank", seed=seed, headless=True)
    world_b, _ = create_world("tank", seed=seed, headless=True)

    world_a.reset(seed=seed)
    world_b.reset(seed=seed)

    # Simulate World A with stats collection (creates metrics samples)
    from backend.simulation_runner import SimulationRunner

    runner_a = SimulationRunner(seed=seed, world_type="tank")
    runner_a.world = world_a
    # Manually step and collect stats
    for frame in range(1, 21):
        world_a.step()
        # Call collect_stats, which samples metrics history
        runner_a._collect_stats(frame=frame)

    # Simulate World B without any stats collection
    for _ in range(1, 21):
        world_b.step()

    # Compare snapshots of entities
    snap_a = world_a.get_current_snapshot()
    snap_b = world_b.get_current_snapshot()

    # Frame count, dimensions, paused state, and entity count/attributes must match
    assert snap_a["frame"] == snap_b["frame"]
    assert snap_a["paused"] == snap_b["paused"]

    # Compare serialized entities
    entities_a = world_a.get_entities_for_snapshot()
    entities_b = world_b.get_entities_for_snapshot()

    assert len(entities_a) == len(entities_b)
    for ent_a, ent_b in zip(entities_a, entities_b, strict=True):
        assert type(ent_a) == type(ent_b)
        assert ent_a.pos.x == ent_b.pos.x
        assert ent_a.pos.y == ent_b.pos.y
        if hasattr(ent_a, "energy") or hasattr(ent_b, "energy"):
            assert getattr(ent_a, "energy", None) == getattr(ent_b, "energy", None)


def test_metrics_history_resets_with_simulation() -> None:
    """Reset should start fresh metrics and link persistence to the new world."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(seed=42, world_type="tank")
    old_history = runner.metrics_history
    old_history.samples.append({"frame": 500})

    runner.reset(seed=43)

    assert runner.metrics_history is not old_history
    assert runner.metrics_history.world_id == runner.world_id
    assert runner.metrics_history.samples == []
    assert runner.world.runner is runner


def test_metrics_history_persistence_link_survives_world_switch() -> None:
    """Hot-swapped adapters should retain access to the runner's metrics history."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(seed=42, world_type="tank")

    runner.switch_world_type("petri")

    assert runner.world.runner is runner
    assert runner.metrics_history.world_id == runner.world_id


def test_metrics_history_samples_without_state_request() -> None:
    """Stepping the runner should collect due metrics without a WebSocket client."""
    from backend.simulation_runner import SimulationRunner

    runner = SimulationRunner(seed=42, world_type="tank")
    runner.metrics_history.sample_interval_frames = 1

    runner.step()

    assert [sample["frame"] for sample in runner.metrics_history.samples] == [1]


def test_runner_samples_populate_trait_means() -> None:
    """A live tank runner should record real population trait means in samples."""
    from backend.simulation_runner import SimulationRunner
    from core.services.stats.trait_trends import EVOLUTION_TRAIT_KEYS

    runner = SimulationRunner(seed=42, world_type="tank")
    runner.metrics_history.sample_interval_frames = 1

    for _ in range(3):
        runner.step()

    assert runner.metrics_history.samples, "expected at least one sample"
    traits = runner.metrics_history.samples[-1]["traits"]
    # A freshly seeded tank has fish, so trait means should be present and valid.
    assert traits, "expected non-empty trait means for a populated tank"
    assert set(traits).issubset(set(EVOLUTION_TRAIT_KEYS))
    assert all(isinstance(v, float) for v in traits.values())
