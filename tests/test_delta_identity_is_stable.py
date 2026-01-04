"""Tests to verify delta IDs are stable and not raw Python id().

This test ensures that the EntityIdentityProvider produces stable IDs
for entities like Food and PlantNectar that don't have intrinsic IDs.
"""


from core.config.entities import FISH_ID_OFFSET, FOOD_ID_OFFSET
from core.entities import Fish, Food
from core.movement_strategy import AlgorithmicMovement
from core.simulation.engine import SimulationEngine


def test_spawn_delta_ids_are_not_raw_python_id():
    """Verify spawn delta IDs for Fish/Food are stable offsets, not id()."""
    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    # Create a fish and food entity
    fish = Fish(
        environment=engine.environment,
        movement_strategy=AlgorithmicMovement(),
        species="test_fish",
        x=100,
        y=100,
        speed=2.0,
    )
    food = Food(engine.environment, 200, 200, food_type="energy")

    # Request spawns
    engine.request_spawn(fish, reason="test_fish_spawn")
    engine.request_spawn(food, reason="test_food_spawn")

    # Run one frame to apply mutations
    engine.update()

    # Find the spawn deltas
    fish_spawn = next((s for s in engine._frame_spawns if s.reason == "test_fish_spawn"), None)
    food_spawn = next((s for s in engine._frame_spawns if s.reason == "test_food_spawn"), None)

    assert fish_spawn is not None, "Fish spawn not found in _frame_spawns"
    assert food_spawn is not None, "Food spawn not found in _frame_spawns"

    # Verify fish ID uses the offset scheme (fish_id + FISH_ID_OFFSET)
    fish_stable_id = fish.fish_id + FISH_ID_OFFSET
    assert fish_spawn.entity_id == str(fish_stable_id), (
        f"Fish spawn ID should be fish_id + offset ({fish_stable_id}), "
        f"not raw id(). Got: {fish_spawn.entity_id}"
    )

    # Verify food ID uses the offset scheme (not raw Python id())
    food_id_int = int(food_spawn.entity_id)
    assert food_id_int >= FOOD_ID_OFFSET, (
        f"Food spawn ID should be >= FOOD_ID_OFFSET ({FOOD_ID_OFFSET}), "
        f"indicating stable offset scheme. Got: {food_id_int}"
    )

    # Raw Python id() would typically be a large number > 10^10 on 64-bit systems
    assert (
        food_id_int < 10_000_000
    ), f"Food spawn ID looks like raw Python id() (too large). Got: {food_id_int}"


def test_removal_delta_ids_are_not_raw_python_id():
    """Verify removal delta IDs for Food are stable offsets, not id()."""
    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    # Create and add food
    food = Food(engine.environment, 200, 200, food_type="energy")
    engine.request_spawn(food, reason="spawn_for_removal")
    engine.update()

    # Clear spawns and request removal
    engine._frame_spawns.clear()
    engine.request_remove(food, reason="test_food_removal")
    engine.update()

    # Find the removal delta
    food_removal = next(
        (r for r in engine._frame_removals if r.reason == "test_food_removal"), None
    )

    assert food_removal is not None, "Food removal not found in _frame_removals"

    # Verify food ID uses the offset scheme
    food_id_int = int(food_removal.entity_id)
    assert food_id_int >= FOOD_ID_OFFSET, (
        f"Food removal ID should be >= FOOD_ID_OFFSET ({FOOD_ID_OFFSET}), "
        f"indicating stable offset scheme. Got: {food_id_int}"
    )
    assert (
        food_id_int < 10_000_000
    ), f"Food removal ID looks like raw Python id() (too large). Got: {food_id_int}"


def test_delta_ids_stable_across_frames():
    """Verify that the same entity gets the same ID across multiple frames."""
    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    # Create and spawn food
    food = Food(engine.environment, 200, 200, food_type="energy")
    engine.request_spawn(food, reason="stable_id_test")
    engine.update()

    # Get the spawn ID
    food_spawn = next((s for s in engine._frame_spawns if s.reason == "stable_id_test"), None)
    assert food_spawn is not None
    spawn_id = food_spawn.entity_id

    # Run several more frames (food survives)
    for _ in range(5):
        engine.update()

    # Request removal and check ID matches
    engine.request_remove(food, reason="check_stable_id")
    engine.update()

    food_removal = next((r for r in engine._frame_removals if r.reason == "check_stable_id"), None)
    assert food_removal is not None
    removal_id = food_removal.entity_id

    assert spawn_id == removal_id, (
        f"Entity ID changed between spawn ({spawn_id}) and removal ({removal_id}). "
        "IDs must be stable across frames."
    )


def test_energy_delta_ids_use_stable_format():
    """Verify energy delta IDs use identity provider format, matching spawn IDs."""
    from core.sim.events import AteFood

    engine = SimulationEngine(headless=True, seed=42)
    engine.setup()

    # Get initial fish
    fish_list = engine.get_fish_list()
    assert len(fish_list) > 0, "Need at least one fish for this test"
    fish = fish_list[0]

    # Get the fish's spawn ID (stable format)
    assert engine._identity_provider is not None
    _, stable_fish_id = engine._identity_provider.get_identity(fish)

    # Emit an energy event for this fish
    energy_event = AteFood(
        frame=engine.frame_count,
        entity_id=fish.fish_id,  # Raw fish_id
        food_id=9999,
        food_type="test",
        energy_gained=10.0,
    )
    engine._queue_sim_event(energy_event)

    # Run update to process the event
    engine.update()

    # Find the energy delta for our fish
    energy_delta = next((d for d in engine._frame_energy_deltas if d.source == "ate_food"), None)

    assert energy_delta is not None, "Energy delta not found in _frame_energy_deltas"

    # Verify the energy delta ID matches the stable format
    assert energy_delta.entity_id == stable_fish_id, (
        f"Energy delta ID ({energy_delta.entity_id}) should match stable fish ID "
        f"({stable_fish_id}), not raw fish_id ({fish.fish_id})"
    )
    assert energy_delta.stable_id == stable_fish_id, (
        f"Energy delta stable_id ({energy_delta.stable_id}) should match stable fish ID "
        f"({stable_fish_id})"
    )

    # Verify it's using the offset scheme (not raw fish_id)
    energy_id_int = int(energy_delta.entity_id)
    assert energy_id_int >= FISH_ID_OFFSET, (
        f"Energy delta ID should be >= FISH_ID_OFFSET ({FISH_ID_OFFSET}), "
        f"indicating stable offset scheme. Got: {energy_id_int}"
    )
    assert (
        energy_id_int < 10_000_000
    ), f"Energy delta ID looks like raw Python id() (too large). Got: {energy_id_int}"
