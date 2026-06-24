"""Tests for the agent-commentary feature (the "Insights" feed).

Covers the storage layer (``backend.commentary_store.CommentaryStore``) and the
REST endpoints (``backend.routers.commentary``) wired through the app factory.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.commentary_store import DEFAULT_SEVERITY, CommentaryStore
from backend.world_manager import WorldManager

# ---------------------------------------------------------------------------
# CommentaryStore unit tests (no server)
# ---------------------------------------------------------------------------


def test_add_returns_stamped_comment():
    store = CommentaryStore(world_id="w1")
    c = store.add(
        "Selection is real",
        author="claude",
        tags=["selection"],
        severity="insight",
        metrics={"max_generation": 12},
        frame=41500,
    )
    assert c["id"] == 1
    assert c["frame"] == 41500
    assert c["author"] == "claude"
    assert c["text"] == "Selection is real"
    assert c["tags"] == ["selection"]
    assert c["severity"] == "insight"
    assert c["metrics"] == {"max_generation": 12}
    assert isinstance(c["created_at"], float)


def test_text_is_stripped_and_empty_rejected():
    store = CommentaryStore()
    assert store.add("  hello  ")["text"] == "hello"
    with pytest.raises(ValueError):
        store.add("   ")
    with pytest.raises(ValueError):
        store.add("")


def test_text_truncated_to_cap():
    from backend.commentary_store import MAX_TEXT_LEN

    store = CommentaryStore()
    c = store.add("x" * (MAX_TEXT_LEN + 500))
    assert len(c["text"]) == MAX_TEXT_LEN


def test_tags_accept_string_or_list_and_are_capped():
    from backend.commentary_store import MAX_TAGS

    store = CommentaryStore()
    assert store.add("a", tags="selection, foraging")["tags"] == ["selection", "foraging"]
    assert store.add("b", tags=["one", "two"])["tags"] == ["one", "two"]
    many = store.add("c", tags=[f"t{i}" for i in range(MAX_TAGS + 5)])
    assert len(many["tags"]) == MAX_TAGS
    # Non-string junk is ignored.
    assert store.add("d", tags=[1, None, "ok"])["tags"] == ["ok"]


def test_invalid_severity_defaults():
    store = CommentaryStore()
    assert store.add("a", severity="bogus")["severity"] == DEFAULT_SEVERITY
    assert store.add("b", severity=None)["severity"] == DEFAULT_SEVERITY
    assert store.add("c", severity="WARNING")["severity"] == "warning"


def test_metrics_are_sanitized():
    store = CommentaryStore()
    # Non-scalar values are dropped; scalars are kept.
    c = store.add("a", metrics={"gen": 12, "rate": 0.5, "note": "ok", "bad": [1, 2]})
    assert c["metrics"] == {"gen": 12, "rate": 0.5, "note": "ok"}
    # A non-dict, or an all-junk dict, yields None.
    assert store.add("b", metrics="nope")["metrics"] is None
    assert store.add("c", metrics={"bad": [1]})["metrics"] is None


def test_recent_limit_and_since_id():
    store = CommentaryStore()
    for i in range(5):
        store.add(f"comment {i}")
    assert [c["id"] for c in store.recent()] == [1, 2, 3, 4, 5]
    assert [c["id"] for c in store.recent(limit=2)] == [4, 5]
    assert [c["id"] for c in store.recent(since_id=3)] == [4, 5]
    assert store.recent(since_id=5) == []


def test_ring_buffer_drops_oldest():
    store = CommentaryStore(max_comments=3)
    for i in range(5):
        store.add(f"c{i}")
    ids = [c["id"] for c in store.comments]
    assert ids == [3, 4, 5]  # oldest two dropped, ids stay monotonic


def test_clear():
    store = CommentaryStore()
    store.add("a")
    store.add("b")
    assert store.clear() == 2
    assert store.comments == []


def test_payload_roundtrip_preserves_monotonic_ids():
    store = CommentaryStore(world_id="w1")
    store.add("a")
    store.add("b")
    payload = store.to_payload()

    restored = CommentaryStore()
    restored.load(payload)
    assert [c["id"] for c in restored.comments] == [1, 2]
    # New ids continue after the restored maximum.
    assert restored.add("c")["id"] == 3


def test_load_tolerates_garbage():
    store = CommentaryStore()
    store.load(None)
    store.load({"unexpected": True})
    assert store.comments == []
    assert store.add("a")["id"] == 1


# ---------------------------------------------------------------------------
# REST endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture
def client_and_world():
    """Create a test client with a fresh paused tank world; yield (client, world_id)."""
    context = AppContext(world_manager=WorldManager())
    app = create_app(context=context, server_id="test-server")
    with TestClient(app) as client:
        resp = client.post(
            "/api/worlds",
            json={
                "world_type": "tank",
                "name": "Commentary Test",
                "persistent": False,
                "seed": 42,
                "start_paused": True,
            },
        )
        assert resp.status_code == 201, resp.text
        world_id = resp.json()["world_id"]
        yield client, world_id


def test_post_and_get_comment(client_and_world):
    client, world_id = client_and_world
    resp = client.post(
        f"/api/world/{world_id}/commentary",
        json={
            "text": "Starvation is 91% of deaths",
            "author": "claude",
            "tags": "foraging",
            "severity": "warning",
            "metrics": {"starvation_pct": 0.91},
        },
    )
    assert resp.status_code == 201, resp.text
    comment = resp.json()["comment"]
    assert comment["id"] == 1
    assert comment["author"] == "claude"
    assert comment["severity"] == "warning"
    assert comment["tags"] == ["foraging"]
    assert comment["metrics"] == {"starvation_pct": 0.91}
    assert isinstance(comment["frame"], int)

    got = client.get(f"/api/world/{world_id}/commentary")
    assert got.status_code == 200
    body = got.json()
    assert body["count"] == 1
    assert body["comments"][0]["text"] == "Starvation is 91% of deaths"


def test_post_to_default_world(client_and_world):
    client, _ = client_and_world
    resp = client.post("/api/world/default/commentary", json={"text": "via default"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["comment"]["author"] == "agent"  # default author

    got = client.get("/api/world/default/commentary")
    assert got.status_code == 200
    assert any(c["text"] == "via default" for c in got.json()["comments"])


def test_post_empty_text_is_400(client_and_world):
    client, world_id = client_and_world
    resp = client.post(f"/api/world/{world_id}/commentary", json={"text": "   "})
    assert resp.status_code == 400


def test_unknown_world_is_404(client_and_world):
    client, _ = client_and_world
    assert client.get("/api/world/does-not-exist/commentary").status_code == 404
    assert (
        client.post("/api/world/does-not-exist/commentary", json={"text": "hi"}).status_code == 404
    )


def test_get_since_id_filters(client_and_world):
    client, world_id = client_and_world
    for i in range(3):
        client.post(f"/api/world/{world_id}/commentary", json={"text": f"c{i}"})
    body = client.get(f"/api/world/{world_id}/commentary", params={"since_id": 2}).json()
    assert [c["id"] for c in body["comments"]] == [3]


def test_delete_clears(client_and_world):
    client, world_id = client_and_world
    client.post(f"/api/world/{world_id}/commentary", json={"text": "a"})
    resp = client.delete(f"/api/world/{world_id}/commentary")
    assert resp.status_code == 200
    assert resp.json()["cleared"] == 1
    assert client.get(f"/api/world/{world_id}/commentary").json()["count"] == 0
