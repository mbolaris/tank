"""Tests for tank-only endpoint guards."""

from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.tank_registry import TankRegistry


def _create_client() -> TestClient:
    context = AppContext(tank_registry=TankRegistry(create_default=False))
    app = create_app(context=context, server_id="test-server")
    return TestClient(app)


def _create_soccer_world(client: TestClient) -> str:
    response = client.post(
        "/api/worlds",
        json={"world_type": "soccer", "name": "Guard Test Soccer", "seed": 42},
    )
    assert response.status_code == 201
    return response.json()["world_id"]


def test_tank_snapshot_rejects_soccer_world():
    client = _create_client()
    with client:
        world_id = _create_soccer_world(client)
        response = client.get(f"/api/tanks/{world_id}/snapshot")
        assert response.status_code == 400
        assert "Unsupported for world_type=soccer" in response.json()["error"]


def test_tank_pause_rejects_soccer_world():
    client = _create_client()
    with client:
        world_id = _create_soccer_world(client)
        response = client.post(f"/api/tanks/{world_id}/pause")
        assert response.status_code == 400
        assert "Unsupported for world_type=soccer" in response.json()["error"]


def test_tank_get_rejects_soccer_world():
    client = _create_client()
    with client:
        world_id = _create_soccer_world(client)
        response = client.get(f"/api/tanks/{world_id}")
        assert response.status_code == 400
        assert "Unsupported for world_type=soccer" in response.json()["error"]
