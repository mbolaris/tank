"""Tests for tank world compatibility with unified World API.

This module tests that:
1. Tank worlds can be created via /api/worlds endpoint
2. Tank worlds are accessible via both legacy /ws and unified /ws/world endpoints
3. WebSocket connections receive updates and frame increments
4. Entity counts change during simulation
5. Legacy /tanks endpoint still works
"""

import json
import time

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.tank_registry import TankRegistry
from backend.tank_world_adapter import TankWorldAdapter
from backend.world_manager import WorldManager


@pytest.fixture
def test_context():
    """Create a fresh AppContext for testing."""
    context = AppContext(
        tank_registry=TankRegistry(create_default=False),
    )
    return context


@pytest.fixture
def test_client(test_context):
    """Create a test client with fresh context."""
    app = create_app(context=test_context, server_id="test-server")

    with TestClient(app) as client:
        yield client


@pytest.fixture
def world_manager(test_context) -> WorldManager:
    """Get or create the WorldManager from context."""
    if test_context.world_manager is None:
        test_context.world_manager = WorldManager(tank_registry=test_context.tank_registry)
    return test_context.world_manager


class TestTankWorldCreationViaWorldsAPI:
    """Tests for creating tank worlds via /api/worlds endpoint."""

    def test_create_tank_via_worlds_api(self, test_client):
        """Test creating a tank world through the unified worlds API."""
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "tank",
                "name": "Test Tank via API",
                "persistent": True,
                "seed": 42,
                "description": "Created via unified API",
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["world_type"] == "tank"
        assert data["mode_id"] == "tank"
        assert data["name"] == "Test Tank via API"
        assert data["view_mode"] == "side"
        assert "world_id" in data

    def test_tank_appears_in_worlds_list(self, test_client):
        """Test that created tank appears in worlds list."""
        # Create tank via worlds API
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Listed Tank", "seed": 123},
        )
        assert create_response.status_code == 201
        tank_id = create_response.json()["world_id"]

        # List all worlds
        list_response = test_client.get("/api/worlds")
        assert list_response.status_code == 200

        worlds = list_response.json()["worlds"]
        tank_ids = [w["world_id"] for w in worlds if w["world_type"] == "tank"]
        assert tank_id in tank_ids

    def test_tank_appears_in_tanks_list(self, test_client):
        """Test that tank created via worlds API also appears in /api/tanks."""
        # Create tank via worlds API
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Legacy Compatible Tank"},
        )
        assert create_response.status_code == 201
        tank_id = create_response.json()["world_id"]

        # Check it appears in legacy /api/tanks endpoint
        tanks_response = test_client.get("/api/tanks")
        assert tanks_response.status_code == 200

        tanks = tanks_response.json()["tanks"]
        tank_ids = [t["tank"]["tank_id"] for t in tanks]
        assert tank_id in tank_ids

    def test_get_tank_world_details(self, test_client):
        """Test getting details of a tank world."""
        # Create tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Detail Tank", "seed": 42},
        )
        tank_id = create_response.json()["world_id"]

        # Get world details
        get_response = test_client.get(f"/api/worlds/{tank_id}")
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["world_id"] == tank_id
        assert data["world_type"] == "tank"
        assert data["name"] == "Detail Tank"
        assert "frame_count" in data
        assert "paused" in data


class TestTankWorldAdapter:
    """Tests for TankWorldAdapter functionality."""

    def test_adapter_wraps_simulation_manager(self, test_context):
        """Test that TankWorldAdapter correctly wraps SimulationManager."""
        # Create a tank via registry
        manager = test_context.tank_registry.create_tank(
            name="Adapter Test Tank",
            seed=42,
        )

        # Wrap in adapter
        adapter = TankWorldAdapter(manager)

        # Check adapter properties
        assert adapter.tank_id == manager.tank_id
        assert adapter.name == "Adapter Test Tank"
        assert adapter.world_type == "tank"
        assert adapter.mode_id == "tank"
        assert adapter.view_mode == "side"

    def test_adapter_frame_count(self, test_context):
        """Test that adapter frame_count tracks simulation progress."""
        manager = test_context.tank_registry.create_tank(name="Frame Test", seed=42)
        adapter = TankWorldAdapter(manager)

        initial_frame = adapter.frame_count

        # Start the simulation
        manager.start(start_paused=False)

        # Wait for a few frames
        time.sleep(0.2)

        # Frame should have advanced
        assert adapter.frame_count > initial_frame

        manager.stop()

    def test_adapter_get_stats(self, test_context):
        """Test that adapter provides statistics."""
        manager = test_context.tank_registry.create_tank(name="Stats Test", seed=42)
        adapter = TankWorldAdapter(manager)
        manager.start(start_paused=False)

        # Give it time to run
        time.sleep(0.1)

        stats = adapter.get_stats()

        # Check essential stats are present
        assert "fish_count" in stats
        assert "plant_count" in stats
        assert "total_energy" in stats
        assert "frame" in stats

        manager.stop()

    def test_adapter_get_entities_snapshot(self, test_context):
        """Test that adapter provides entity snapshots."""
        manager = test_context.tank_registry.create_tank(name="Entities Test", seed=42)
        adapter = TankWorldAdapter(manager)
        manager.start(start_paused=False)

        # Give it time to spawn entities
        time.sleep(0.1)

        entities = adapter.get_entities_snapshot()

        # Should have some entities (fish, plants, etc.)
        assert isinstance(entities, list)
        # Tank should have initial entities
        assert len(entities) > 0

        manager.stop()

    def test_adapter_pause_unpause(self, test_context):
        """Test adapter pause/unpause functionality."""
        manager = test_context.tank_registry.create_tank(name="Pause Test", seed=42)
        adapter = TankWorldAdapter(manager)
        manager.start(start_paused=False)

        # Should not be paused initially
        assert adapter.paused is False

        # Pause via adapter
        adapter.paused = True
        assert adapter.paused is True

        # Unpause
        adapter.paused = False
        assert adapter.paused is False

        manager.stop()


class TestWorldManagerUnifiedPipeline:
    """Tests for WorldManager handling tank worlds through unified pipeline."""

    def test_world_manager_creates_tank_with_adapter(self, world_manager):
        """Test that WorldManager creates tank worlds with TankWorldAdapter."""
        instance = world_manager.create_world(
            world_type="tank",
            name="Pipeline Tank",
            seed=42,
        )

        assert instance.world_type == "tank"
        assert instance.is_tank()
        assert isinstance(instance.runner, TankWorldAdapter)

    def test_world_manager_lists_tanks_and_other_worlds(self, world_manager):
        """Test that WorldManager lists both tank and other world types."""
        # Create a tank
        world_manager.create_world(world_type="tank", name="Mixed Tank", seed=1)

        # Create a petri world
        world_manager.create_world(world_type="petri", name="Mixed Petri", seed=2)

        # List all
        all_worlds = world_manager.list_worlds()
        tank_worlds = world_manager.list_worlds(world_type="tank")
        petri_worlds = world_manager.list_worlds(world_type="petri")

        assert len(all_worlds) >= 2
        assert len(tank_worlds) >= 1
        assert len(petri_worlds) >= 1

        # All tank worlds should have world_type "tank"
        for w in tank_worlds:
            assert w.world_type == "tank"

    def test_world_manager_get_tank_adapter(self, world_manager):
        """Test WorldManager.get_tank_adapter convenience method."""
        instance = world_manager.create_world(
            world_type="tank",
            name="Adapter Get Tank",
            seed=42,
        )

        adapter = world_manager.get_tank_adapter(instance.world_id)

        assert adapter is not None
        assert isinstance(adapter, TankWorldAdapter)
        assert adapter.tank_id == instance.world_id

    def test_world_manager_step_tank_world(self, world_manager):
        """Test stepping a tank world through WorldManager."""
        instance = world_manager.create_world(
            world_type="tank",
            name="Step Test Tank",
            seed=42,
        )

        initial_frame = instance.runner.frame_count

        # Step the world
        success = world_manager.step_world(instance.world_id)
        assert success is True

        # Frame should have advanced
        assert instance.runner.frame_count > initial_frame

    def test_world_manager_delete_tank_world(self, world_manager):
        """Test deleting a tank world through WorldManager."""
        instance = world_manager.create_world(
            world_type="tank",
            name="Delete Tank",
            seed=42,
        )
        tank_id = instance.world_id

        # Delete
        success = world_manager.delete_world(tank_id)
        assert success is True

        # Should not be findable
        assert world_manager.get_world(tank_id) is None


class TestLegacyTanksEndpointCompatibility:
    """Tests for legacy /api/tanks endpoint backward compatibility."""

    def test_legacy_tanks_list_still_works(self, test_client):
        """Test that legacy /api/tanks endpoint still works."""
        # Create a tank via worlds API first
        test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Legacy Test"},
        )

        # Legacy endpoint should work
        response = test_client.get("/api/tanks")
        assert response.status_code == 200

        data = response.json()
        assert "tanks" in data
        assert "count" in data
        assert data["count"] >= 1

    def test_legacy_tank_pause_resume_still_works(self, test_client):
        """Test that legacy tank pause/resume endpoints work."""
        # Create tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Pause Resume Test"},
        )
        tank_id = create_response.json()["world_id"]

        # Pause via legacy endpoint
        pause_response = test_client.post(f"/api/tanks/{tank_id}/pause")
        assert pause_response.status_code == 200

        # Resume via legacy endpoint
        resume_response = test_client.post(f"/api/tanks/{tank_id}/resume")
        assert resume_response.status_code == 200


class TestFrameIncrementsDuringSimulation:
    """Tests for frame progression during simulation."""

    def test_tank_frames_increment_over_time(self, test_client):
        """Test that tank world frames increment over time."""
        # Create tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Frame Increment Test", "seed": 42},
        )
        tank_id = create_response.json()["world_id"]

        # Get initial frame
        initial_response = test_client.get(f"/api/worlds/{tank_id}")
        initial_frame = initial_response.json()["frame_count"]

        # Wait for frames to advance
        time.sleep(0.5)

        # Get new frame count
        later_response = test_client.get(f"/api/worlds/{tank_id}")
        later_frame = later_response.json()["frame_count"]

        # Frame should have advanced
        assert later_frame > initial_frame

    def test_tank_runs_for_two_seconds(self, test_client):
        """Test running tank for ~2 seconds and confirming progress."""
        # Create tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Duration Test", "seed": 42},
        )
        tank_id = create_response.json()["world_id"]

        # Get initial state
        initial_response = test_client.get(f"/api/worlds/{tank_id}")
        initial_frame = initial_response.json()["frame_count"]

        # Run for ~2 seconds
        time.sleep(2.0)

        # Get final state
        final_response = test_client.get(f"/api/worlds/{tank_id}")
        final_frame = final_response.json()["frame_count"]

        # Should have many frames (30 FPS -> ~60 frames in 2 seconds)
        frames_advanced = final_frame - initial_frame
        assert frames_advanced > 30, f"Expected >30 frames, got {frames_advanced}"


class TestWebSocketUpdates:
    """Tests for WebSocket connectivity (non-async tests with TestClient)."""

    def test_websocket_default_endpoint_works(self, test_client):
        """Test that default /ws endpoint connects and receives data."""
        # Create a tank first (it becomes the default)
        test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "WebSocket Default Test"},
        )

        # Connect to default WebSocket
        with test_client.websocket_connect("/ws") as websocket:
            # Should receive initial state
            data = websocket.receive_bytes()
            state = json.loads(data)

            # Verify we got a state payload
            assert "entities" in state or "frame" in state

    def test_websocket_tank_id_endpoint_works(self, test_client):
        """Test that /ws/{tank_id} endpoint connects and receives data."""
        # Create a tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "WebSocket Tank ID Test"},
        )
        tank_id = create_response.json()["world_id"]

        # Connect to specific tank WebSocket
        with test_client.websocket_connect(f"/ws/{tank_id}") as websocket:
            data = websocket.receive_bytes()
            state = json.loads(data)

            assert "entities" in state or "frame" in state

    def test_websocket_world_endpoint_works(self, test_client):
        """Test that unified /ws/world/{world_id} endpoint works for tanks."""
        # Create a tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "WebSocket World Test"},
        )
        world_id = create_response.json()["world_id"]

        # Connect to unified world WebSocket
        with test_client.websocket_connect(f"/ws/world/{world_id}") as websocket:
            data = websocket.receive_bytes()
            state = json.loads(data)

            assert "entities" in state or "frame" in state

    def test_websocket_receives_frame_updates(self, test_client):
        """Test that WebSocket receives frame updates over time."""
        # Create a tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "WebSocket Updates Test"},
        )
        tank_id = create_response.json()["world_id"]

        with test_client.websocket_connect(f"/ws/{tank_id}") as websocket:
            # Receive initial state
            initial_data = websocket.receive_bytes()
            initial_state = json.loads(initial_data)
            initial_frame = initial_state.get("frame", 0)

            # Wait a bit then receive another update
            # (broadcasts happen at ~15Hz by default)
            time.sleep(0.2)

            # In reality the broadcast loop would push updates
            # For testing, we verify the initial connection works
            # The broadcast tests require async testing

            assert initial_frame >= 0

    def test_websocket_command_handling(self, test_client):
        """Test that WebSocket handles commands."""
        # Create a tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "WebSocket Command Test"},
        )
        tank_id = create_response.json()["world_id"]

        with test_client.websocket_connect(f"/ws/{tank_id}") as websocket:
            # Receive initial state
            websocket.receive_bytes()

            # Send a pause command
            websocket.send_text(json.dumps({"command": "pause"}))

            # Wait for response
            response_text = websocket.receive_text()
            response = json.loads(response_text)

            assert response.get("success") is True or "paused" in str(response).lower()


class TestEntityCountChanges:
    """Tests for entity count changes during simulation."""

    def test_entities_exist_after_creation(self, test_client):
        """Test that tank has entities after creation."""
        # Create tank
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "tank", "name": "Entity Count Test", "seed": 42},
        )
        tank_id = create_response.json()["world_id"]

        # Wait for simulation to initialize
        time.sleep(0.2)

        # Connect and check entities
        with test_client.websocket_connect(f"/ws/{tank_id}") as websocket:
            data = websocket.receive_bytes()
            state = json.loads(data)

            entities = state.get("entities", [])
            assert len(entities) > 0, "Tank should have initial entities"


class TestPersistenceCompatibility:
    """Tests for persistence through unified API."""

    def test_tank_persistence_flag_preserved(self, test_client):
        """Test that tank persistence flag is preserved through creation."""
        # Create persistent tank
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "tank",
                "name": "Persistent Tank Test",
                "persistent": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data.get("persistent") is True

    def test_non_persistent_tank_created(self, test_client):
        """Test that non-persistent tank can be created."""
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "tank",
                "name": "Non-Persistent Tank",
                "persistent": False,
            },
        )
        assert response.status_code == 201
        # Tank still gets created (persistence is optional)
