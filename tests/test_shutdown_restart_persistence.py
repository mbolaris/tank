import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from backend.startup_manager import StartupManager
from backend.world_manager import WorldManager
from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.server_client import ServerClient
from core.entities.base import Castle
from core.entities.fish import Fish, Genome
from core.movement_strategy import AlgorithmicMovement


@pytest.fixture
def mock_managers():
    """Provide mocks for StartupManager dependencies."""
    connection_manager = MagicMock(spec=ConnectionManager)
    discovery_service = MagicMock(spec=DiscoveryService)
    discovery_service.start = AsyncMock()
    discovery_service.stop = AsyncMock()

    server_client = MagicMock(spec=ServerClient)
    server_client.start = AsyncMock()
    server_client.close = AsyncMock()

    return connection_manager, discovery_service, server_client


@pytest.mark.asyncio
async def test_full_shutdown_restart_cycle(mock_data_dir, mock_managers):
    """Verify that multiple worlds persist across a full shutdown/restart cycle."""
    connection_manager, discovery_service, server_client = mock_managers

    # --- PHASE 1: INITIAL STARTUP & SETUP ---

    # Create first instance of managers
    world_manager_1 = WorldManager()
    startup_manager_1 = StartupManager(
        world_manager=world_manager_1,
        connection_manager=connection_manager,
        discovery_service=discovery_service,
        server_client=server_client,
        server_id="server-test-1",
    )

    # Initialize (creates default world)
    mock_get_server_info = MagicMock(return_value={})
    await startup_manager_1.initialize(mock_get_server_info)

    # Verify default world exists
    assert world_manager_1.world_count == 1
    default_world_id = world_manager_1.default_world_id

    # Create a second world (Petri)
    petri_world_instance = world_manager_1.create_world(
        world_type="petri",
        name="Microcosmos",
        persistent=True,
    )
    petri_world_id = petri_world_instance.world_id

    assert world_manager_1.world_count == 2

    # Add entities to Default World (Tank)
    # Update existing Castle in Default World (Tank)
    # Note: TankWorld creates a default castle. We'll modify it to verify persistence.
    # Pause to prevent auto-spawning interference
    default_world = world_manager_1.get_world(default_world_id).runner.world
    default_world.paused = True
    existing_castles = [e for e in default_world.engine.entities_list if isinstance(e, Castle)]
    if existing_castles:
        castle = existing_castles[0]
        castle.pos.x = 100
        castle.pos.y = 100
    else:
        # Fallback if factory changes default population
        castle = Castle(environment=default_world.engine.environment, x=100, y=100)
        default_world.engine.add_entity(castle)

    # Add entities to Petri World
    petri_world = petri_world_instance.runner.world
    petri_world.paused = True
    # Reset phase so we can add entities directly (test setup privilege)
    petri_world.engine._current_phase = None
    petri_world.engine.entities_list.clear()  # Clear default stuff

    # Add 1 fish
    # We must use AlgorithmicMovement for Fish now
    petri_fish = Fish(
        environment=petri_world.engine.environment,
        movement_strategy=AlgorithmicMovement(),
        species="petri_fish_1",
        x=0,
        y=0,
        speed=5.0,
        genome=Genome.random(rng=petri_world.engine.rng),
        ecosystem=petri_world.engine.ecosystem,
    )
    petri_world.engine.add_entity(petri_fish)

    # --- PHASE 2: SHUTDOWN (SAVE) ---

    # This should trigger auto_save_service.save_all_on_shutdown()
    await startup_manager_1.shutdown()

    # Verify files exist on disk (via mock_data_dir which maps to tmp_path)
    # The world persistence module uses DATA_DIR. mock_data_dir patches it.
    import backend.world_persistence as wp

    assert (wp.DATA_DIR / default_world_id).exists()
    assert (wp.DATA_DIR / petri_world_id).exists()

    # --- PHASE 3: RESTART (RESTORE) ---

    # Create NEW instances for the restart
    world_manager_2 = WorldManager()
    startup_manager_2 = StartupManager(
        world_manager=world_manager_2,
        connection_manager=connection_manager,
        discovery_service=discovery_service,
        server_client=server_client,
        server_id="server-test-1",  # Same ID
    )

    try:
        # Initialize (should detect saved worlds and restore them)
        await startup_manager_2.initialize(mock_get_server_info)

        # --- PHASE 4: VERIFICATION ---

        # Should recall BOTH worlds
        assert world_manager_2.world_count == 2

        # Verify Default World
        restored_default = world_manager_2.get_world(default_world_id)
        assert restored_default is not None
        assert restored_default.name == "World 1"  # Default name
        entities_default = restored_default.runner.world.engine.entities_list
        assert (
            len(entities_default) >= 1
        )  # Should have Castle (and potentially default spawned entities if logic ran)
        # Check for Castle
        castles = [e for e in entities_default if isinstance(e, Castle)]
        assert len(castles) == 1
        assert castles[0].pos.x == 100

        # Verify Petri World
        restored_petri = world_manager_2.get_world(petri_world_id)
        assert restored_petri is not None
        assert restored_petri.name == "Microcosmos"
        assert restored_petri.world_type == "petri"
        entities_petri = restored_petri.runner.world.engine.entities_list
        assert len(entities_petri) == 1  # Should have our Fish
        assert isinstance(entities_petri[0], Fish)
    finally:
        await startup_manager_2.shutdown()
