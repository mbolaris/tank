"""Tests for the /api/solutions endpoints.

Regression coverage for a route-shadowing bug found while splitting
``backend/routers/solutions.py`` into ``backend/routers/solutions/``:
``GET /{solution_id}`` was registered before ``/leaderboard``, ``/compare``,
and ``/report``, so Starlette's in-order route matching sent all three to the
single-solution handler instead, which always returned 404 (there is never a
solution ID starting with "leaderboard"). These endpoints are documented as
working in ``solutions/README.md`` but were unreachable in practice.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.world_manager import WorldManager


@pytest.fixture
def test_client():
    """Create a test client with fresh context."""
    context = AppContext(
        world_manager=WorldManager(),
    )
    app = create_app(context=context, server_id="test-server")

    with TestClient(app) as client:
        yield client


class TestSolutionsAggregateEndpoints:
    """The literal-path routes that were previously shadowed by /{solution_id}."""

    def test_leaderboard_is_reachable(self, test_client):
        response = test_client.get("/api/solutions/leaderboard")
        assert response.status_code == 200
        body = response.json()
        assert "leaderboard" in body

    def test_compare_is_reachable(self, test_client):
        response = test_client.get("/api/solutions/compare")
        assert response.status_code == 200
        body = response.json()
        assert "message" in body or "rankings" in body

    def test_report_is_reachable(self, test_client):
        response = test_client.get("/api/solutions/report")
        assert response.status_code == 200
        body = response.json()
        assert "report" in body


class TestSolutionDetailEndpoint:
    """The /{solution_id} catch-all must still work for real lookups."""

    def test_unknown_solution_id_returns_404(self, test_client):
        response = test_client.get("/api/solutions/does-not-exist")
        assert response.status_code == 404

    def test_list_solutions_still_works(self, test_client):
        response = test_client.get("/api/solutions")
        assert response.status_code == 200
        body = response.json()
        assert "solutions" in body
        assert "count" in body
