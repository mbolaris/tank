"""Tests for world-agnostic API endpoints.

This module tests the /api/worlds and /api/world_types endpoints
for creating and managing worlds of different types.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.world_manager import WorldManager


@pytest.fixture
def test_client():
    """Create a test client with fresh context."""
    # Create a fresh context for testing
    context = AppContext(
        world_manager=WorldManager(),
    )
    app = create_app(context=context, server_id="test-server")

    with TestClient(app) as client:
        yield client


class TestWorldTypesEndpoint:
    """Tests for GET /api/worlds/types endpoint."""

    def test_list_world_types_returns_tank_petri_soccer(self, test_client):
        """Test that world_types endpoint returns tank, petri, and soccer."""
        response = test_client.get("/api/worlds/types")
        assert response.status_code == 200

        types = response.json()
        assert isinstance(types, list)
        assert len(types) >= 3

        mode_ids = {t["mode_id"] for t in types}
        assert "tank" in mode_ids
        assert "petri" in mode_ids
        assert "soccer" in mode_ids

    def test_world_types_have_required_fields(self, test_client):
        """Test that each world type has all required metadata fields."""
        response = test_client.get("/api/worlds/types")
        types = response.json()

        for world_type in types:
            assert "mode_id" in world_type
            assert "world_type" in world_type
            assert "view_mode" in world_type
            assert "display_name" in world_type
            assert "supports_persistence" in world_type
            assert "supports_actions" in world_type
            assert "supports_websocket" in world_type
            assert "supports_transfer" in world_type
            assert "has_fish" in world_type

    def test_tank_supports_persistence(self, test_client):
        """Test that tank world supports persistence."""
        response = test_client.get("/api/worlds/types")
        types = {t["mode_id"]: t for t in response.json()}

        assert types["tank"]["supports_persistence"] is True
        assert types["tank"]["view_mode"] == "side"

    def test_soccer_does_not_support_persistence(self, test_client):
        """Test that soccer world does not support persistence."""
        response = test_client.get("/api/worlds/types")
        types = {t["mode_id"]: t for t in response.json()}

        assert types["soccer"]["supports_persistence"] is False
        assert types["soccer"]["supports_actions"] is True
        assert types["soccer"]["view_mode"] == "topdown"


class TestCreatePetriWorld:
    """Tests for creating petri worlds."""

    def test_create_petri_world(self, test_client):
        """Test creating a petri world."""
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "petri",
                "name": "Test Petri",
                "persistent": False,
                "seed": 42,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["world_type"] == "petri"
        assert data["name"] == "Test Petri"
        assert "world_id" in data

    def test_step_petri_world(self, test_client):
        """Test stepping a petri world advances frame."""
        # Create petri world
        create_response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "petri",
                "name": "Step Test Petri",
                "seed": 42,
            },
        )
        assert create_response.status_code == 201
        world_id = create_response.json()["world_id"]

        # Get initial frame count
        get_response = test_client.get(f"/api/worlds/{world_id}")
        assert get_response.status_code == 200
        initial_frame = get_response.json()["frame_count"]

        # Step the world
        step_response = test_client.post(f"/api/worlds/{world_id}/step")
        assert step_response.status_code == 200

        # Verify frame advanced
        assert step_response.json()["frame_count"] == initial_frame + 1


class TestCreateSoccerWorld:
    """Tests for creating soccer worlds."""

    def test_create_soccer_world(self, test_client):
        """Test creating a soccer world."""
        response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "soccer",
                "name": "Test Soccer",
                "config": {"team_size": 3},
                "seed": 42,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["world_type"] == "soccer"
        assert data["name"] == "Test Soccer"
        assert data["persistent"] is False  # Soccer can't be persistent

    def test_step_soccer_world(self, test_client):
        """Test stepping a soccer world advances frame."""
        # Create soccer world
        create_response = test_client.post(
            "/api/worlds",
            json={
                "world_type": "soccer",
                "name": "Step Test Soccer",
                "config": {"team_size": 1},
                "seed": 42,
            },
        )
        assert create_response.status_code == 201
        world_id = create_response.json()["world_id"]

        # Step the world
        step_response = test_client.post(f"/api/worlds/{world_id}/step")
        assert step_response.status_code == 200
        assert step_response.json()["frame_count"] == 1


class TestWorldOperations:
    """Tests for general world operations."""

    def test_list_worlds(self, test_client):
        """Test listing all worlds."""
        # Create a couple of worlds
        test_client.post(
            "/api/worlds",
            json={"world_type": "petri", "name": "List Test 1", "seed": 1},
        )
        test_client.post(
            "/api/worlds",
            json={"world_type": "soccer", "name": "List Test 2", "seed": 2},
        )

        # List all worlds
        response = test_client.get("/api/worlds")
        assert response.status_code == 200

        data = response.json()
        assert "worlds" in data
        assert "count" in data
        assert data["count"] >= 2

    def test_delete_world(self, test_client):
        """Test deleting a world."""
        # Create a world
        create_response = test_client.post(
            "/api/worlds",
            json={"world_type": "petri", "name": "Delete Test", "seed": 42},
        )
        world_id = create_response.json()["world_id"]

        # Delete it
        delete_response = test_client.delete(f"/api/worlds/{world_id}")
        assert delete_response.status_code == 200

        # Verify it's gone
        get_response = test_client.get(f"/api/worlds/{world_id}")
        assert get_response.status_code == 404

    def test_get_nonexistent_world_returns_404(self, test_client):
        """Test that getting a nonexistent world returns 404."""
        response = test_client.get("/api/worlds/nonexistent-id")
        assert response.status_code == 404

    def test_create_invalid_world_type_returns_400(self, test_client):
        """Test that creating an invalid world type returns 400."""
        response = test_client.post(
            "/api/worlds",
            json={"world_type": "invalid", "name": "Bad World"},
        )
        assert response.status_code == 400
