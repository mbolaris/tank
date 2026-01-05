from core.simulation.engine import FrameOutputs, SimulationEngine
from core.worlds.contracts import EnergyDeltaRecord, RemovalRequest, SpawnRequest


class MockEntity:
    pass


def test_drain_frame_outputs_clears_buffers():
    """Test that drain_frame_outputs returns data and clears internal buffers."""
    engine = SimulationEngine(headless=True)

    # Manually populate buffers to simulate frame activity
    # (We bypass the complex mutation machinery for this unit test of the drain mechanism)
    spawn_req = SpawnRequest(entity_type="fish", entity_id=1, reason="test")
    removal_req = RemovalRequest(entity_type="plant", entity_id=2, reason="test")
    delta_req = EnergyDeltaRecord(
        entity_id=1, stable_id="1", entity_type="fish", delta=10.0, source="test", metadata={}
    )

    engine._frame_spawns.append(spawn_req)
    engine._frame_removals.append(removal_req)
    engine._frame_energy_deltas.append(delta_req)

    # Drain
    outputs = engine.drain_frame_outputs()

    # Check outputs
    assert isinstance(outputs, FrameOutputs)
    assert len(outputs.spawns) == 1
    assert outputs.spawns[0] == spawn_req
    assert len(outputs.removals) == 1
    assert outputs.removals[0] == removal_req
    assert len(outputs.energy_deltas) == 1
    assert outputs.energy_deltas[0] == delta_req

    # Check buffers are cleared
    assert len(engine._frame_spawns) == 0
    assert len(engine._frame_removals) == 0
    assert len(engine._frame_energy_deltas) == 0

    # Drain again should be empty
    outputs2 = engine.drain_frame_outputs()
    assert len(outputs2.spawns) == 0
    assert len(outputs2.removals) == 0
    assert len(outputs2.energy_deltas) == 0


def test_update_lifecycle_clearing():
    """Verify that update() clears buffers at the start of the frame."""
    engine = SimulationEngine(headless=True)
    engine.setup()

    # Pollute buffers with "previous frame" data that wasn't drained
    engine._frame_spawns.append("old_spawn")  # type: ignore

    # Run update
    engine.update()

    # The old data should be gone (cleared at start of update)
    # The new data (if any) should be from THIS update
    outputs = engine.drain_frame_outputs()
    assert "old_spawn" not in outputs.spawns
