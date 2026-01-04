"""Tests for simulation contract invariants and delta tracking."""

from core.worlds.contracts import EnergyDeltaRecord, RemovalRequest, SpawnRequest
from core.worlds.interfaces import StepResult


def test_step_result_contract_fields():
    """Verify StepResult has all required standardized fields."""
    result = StepResult()
    assert hasattr(result, "spawns")
    assert hasattr(result, "removals")
    assert hasattr(result, "energy_deltas")
    assert hasattr(result, "render_hint")

    # Verify default values are empty collections or None
    assert result.spawns == []
    assert result.removals == []
    assert result.energy_deltas == []
    assert result.render_hint is None


def test_engine_delta_tracking(simulation_engine):
    """Verify SimulationEngine tracks spawns and removals in frame deltas."""
    engine = simulation_engine

    # 1. Test Spawn tracking
    from core.entities.fish import Fish
    from core.movement_strategy import AlgorithmicMovement

    # Use environment instead of world
    test_fish = Fish(engine.environment, AlgorithmicMovement(), "fish1.png", 100, 100, speed=1.0)
    engine._entity_mutations.request_spawn(test_fish, reason="test_spawn")

    engine.update()

    # frame_spawns should have captured the spawn
    assert any(
        s.reason == "test_spawn" for s in engine._frame_spawns
    ), "Spawn not tracked in _frame_spawns"
    spawn_req = next(s for s in engine._frame_spawns if s.reason == "test_spawn")
    assert isinstance(spawn_req, SpawnRequest)
    assert spawn_req.entity_type == "fish"

    # 2. Test Removal tracking
    engine._entity_mutations.request_remove(test_fish, reason="test_remove")

    engine.update()

    # frame_removals should have captured the removal
    assert any(
        r.reason == "test_remove" for r in engine._frame_removals
    ), "Removal not tracked in _frame_removals"
    rem_req = next(r for r in engine._frame_removals if r.reason == "test_remove")
    assert isinstance(rem_req, RemovalRequest)
    assert rem_req.entity_type == "fish"


def test_engine_energy_delta_tracking(simulation_engine):
    """Verify SimulationEngine tracks energy deltas in frame deltas."""
    engine = simulation_engine

    # Ensure we have at least one fish
    fish_list = engine.get_fish_list()
    if not fish_list:
        from core.entities.fish import Fish
        from core.movement_strategy import AlgorithmicMovement

        fish = Fish(engine.environment, AlgorithmicMovement(), "fish1.png", 100, 100, speed=1.0)
        engine._add_entity(fish)
        fish_list = [fish]

    fish = fish_list[0]

    # Run update - this should trigger metabolism which records energy burn
    engine.update()

    # frame_energy_deltas should have captured the delta
    assert len(engine._frame_energy_deltas) > 0, "Energy delta not tracked in _frame_energy_deltas"

    # Verify the first matching record for this fish
    assert engine._identity_provider is not None
    _, stable_fish_id = engine._identity_provider.get_identity(fish)

    energy_req = next(
        (r for r in engine._frame_energy_deltas if r.stable_id == stable_fish_id), None
    )
    assert energy_req is not None, f"No energy delta found for fish {stable_fish_id}"

    assert isinstance(energy_req, EnergyDeltaRecord)
    assert energy_req.entity_id == stable_fish_id
    assert energy_req.stable_id == stable_fish_id

    # Metabolism matches -delta (burn)
    # The record stores the signed delta. Metabolism = burn = negative delta.
    assert energy_req.delta < 0
    assert energy_req.source == "metabolism"


def test_delta_reset_every_frame(simulation_engine):
    """Verify frame deltas are cleared at the start of each frame."""
    engine = simulation_engine

    # Manually inject some deltas
    engine._frame_spawns.append(SpawnRequest(entity_type="test", entity_id="1", reason="leaked"))

    # Run update - this should clear frame_spawns first
    engine.update()

    # The "leaked" spawn should be gone
    assert not any(
        s.reason == "leaked" for s in engine._frame_spawns
    ), "Frame deltas not cleared at start of frame"


def test_backend_adapter_returns_deltas(simulation_engine):
    """Verify TankWorldBackendAdapter populates StepResult with deltas."""
    from core.entities.fish import Fish
    from core.movement_strategy import AlgorithmicMovement
    from core.worlds.tank.backend import TankWorldBackendAdapter

    adapter = TankWorldBackendAdapter(seed=42)
    adapter.reset()

    # Request a spawn on the underlying engine
    test_fish = Fish(
        adapter.world.environment, AlgorithmicMovement(), "fish1.png", 100, 100, speed=1.0
    )
    adapter.engine._entity_mutations.request_spawn(test_fish, reason="contract_test")

    # Step the world
    result = adapter.step()

    # StepResult should have the spawn
    assert isinstance(result, StepResult)
    assert any(
        s.reason == "contract_test" for s in result.spawns
    ), "StepResult missing spawns from engine"
    assert result.render_hint is not None
