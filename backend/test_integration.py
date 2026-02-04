"""Integration tests for the backend."""

import json
import time

from backend.simulation_runner import SimulationRunner
from backend.state_payloads import FullStatePayload


def test_simulation_runner_lifecycle():
    """Test the complete lifecycle of simulation runner."""
    print("Test: Simulation runner lifecycle")

    runner = SimulationRunner()
    assert runner.engine.frame_count == 0, "Initial frame count should be 0"

    runner.start()
    time.sleep(1)
    assert runner.running, "Simulation should be running"
    assert runner.engine.frame_count > 0, "Frame count should increase"

    runner.stop()
    assert not runner.running, "Simulation should be stopped"
    print("✅ Lifecycle test passed")


def test_state_serialization():
    """Test state can be serialized to JSON."""
    print("Test: State serialization")

    runner = SimulationRunner()
    runner.start()
    time.sleep(0.5)

    state = runner.get_state(force_full=True, allow_delta=False)
    assert isinstance(state, FullStatePayload), "State should be FullStatePayload"

    json_str = state.to_json()
    parsed = json.loads(json_str)
    assert "type" in parsed
    assert "frame" in parsed
    assert "entities" in parsed
    assert "stats" in parsed

    runner.stop()
    print("✅ Serialization test passed")


def test_all_entity_types():
    """Test all entity types are present and valid."""
    print("Test: All entity types")

    runner = SimulationRunner()
    runner.start()
    time.sleep(1)

    state = runner.get_state(force_full=True, allow_delta=False)
    entity_types = {e.type for e in state.entities}

    expected_types = {"fish", "plant", "crab", "castle"}
    assert expected_types.issubset(entity_types), f"Missing types: {expected_types - entity_types}"

    # Test each entity has required fields
    for entity in state.entities:
        assert entity.id is not None
        assert entity.x is not None
        assert entity.y is not None
        assert entity.width > 0
        assert entity.height > 0

        if entity.type == "fish":
            assert entity.energy is not None
            assert entity.species in ["solo", "algorithmic", "neural", "schooling"]
            assert entity.generation is not None
            assert entity.age is not None

    runner.stop()
    print("✅ Entity types test passed")


def test_commands():
    """Test all commands work correctly."""
    print("Test: Commands")

    runner = SimulationRunner()
    runner.start()
    time.sleep(0.5)

    # Test add_food
    initial_food = runner.get_state(force_full=True, allow_delta=False).stats.food_count
    runner.handle_command("add_food")
    time.sleep(0.3)
    new_food = runner.get_state(force_full=True, allow_delta=False).stats.food_count
    assert new_food > initial_food, "Food count should increase"

    # Test pause
    runner.handle_command("pause")
    time.sleep(0.2)
    frame_before = runner.engine.frame_count
    time.sleep(0.5)
    frame_after = runner.engine.frame_count
    assert frame_before == frame_after, "Frame should not change when paused"

    # Test resume
    runner.handle_command("resume")
    time.sleep(0.2)
    frame_before = runner.engine.frame_count
    time.sleep(0.5)
    frame_after = runner.engine.frame_count
    assert frame_after > frame_before, "Frame should increase when resumed"

    # Test reset
    old_frame = runner.engine.frame_count
    runner.handle_command("reset")
    time.sleep(0.5)
    new_frame = runner.engine.frame_count
    assert new_frame < old_frame, "Frame should reset to low number"

    state = runner.get_state()
    assert len(state.entities) > 0, "Entities should exist after reset"

    runner.stop()
    print("✅ Commands test passed")


def test_stats_accuracy():
    """Test stats match actual entity counts."""
    print("Test: Stats accuracy")

    runner = SimulationRunner()
    runner.start()
    time.sleep(1)

    state = runner.get_state()

    # Count entities
    actual_fish = len([e for e in state.entities if e.type == "fish"])
    actual_food = len([e for e in state.entities if e.type == "food"])
    actual_plants = len([e for e in state.entities if e.type == "plant"])

    # Compare with stats
    assert state.stats.fish_count == actual_fish, "Fish count mismatch"
    assert state.stats.food_count == actual_food, "Food count mismatch"
    assert state.stats.plant_count == actual_plants, "Plant count mismatch"

    runner.stop()
    print("✅ Stats accuracy test passed")


def test_performance():
    """Test simulation runs at acceptable FPS."""
    print("Test: Performance")

    runner = SimulationRunner()
    runner.start()

    start_frame = runner.engine.frame_count
    start_time = time.time()
    time.sleep(3)
    end_frame = runner.engine.frame_count
    end_time = time.time()

    frames_elapsed = end_frame - start_frame
    time_elapsed = end_time - start_time
    fps = frames_elapsed / time_elapsed

    assert fps > 20, f"FPS too low: {fps}"
    assert fps < 40, f"FPS too high: {fps}"

    runner.stop()
    print(f"✅ Performance test passed (FPS: {fps:.1f})")


def test_error_handling():
    """Test error handling for invalid commands."""
    print("Test: Error handling")

    runner = SimulationRunner()
    runner.start()
    time.sleep(0.5)

    # Invalid command should not crash
    try:
        runner.handle_command("invalid_command")
        # Should silently ignore
    except Exception as e:
        raise AssertionError(f"Should handle invalid command gracefully: {e}")

    runner.stop()
    print("✅ Error handling test passed")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING INTEGRATION TESTS")
    print("=" * 60)
    print()

    test_simulation_runner_lifecycle()
    test_state_serialization()
    test_all_entity_types()
    test_commands()
    test_stats_accuracy()
    test_performance()
    test_error_handling()

    print()
    print("=" * 60)
    print("ALL INTEGRATION TESTS PASSED ✅")
    print("=" * 60)
