"""Tests for the agent-commentary feature (the "Board" feed, formerly "Insights").

Covers the storage layer (``backend.commentary_store.CommentaryStore``) and the
REST endpoints (``backend.routers.commentary``) wired through the app factory.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app_factory import AppContext, create_app
from backend.commentary_store import (
    DEFAULT_SEVERITY,
    DEFAULT_TOPIC,
    REACTION_EMOJI,
    TOPICS,
    CommentaryStore,
)
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
    # v2 defaults
    assert c["topic"] == DEFAULT_TOPIC
    assert c["reactions"] == {}


def test_topic_stored_and_coerced():
    store = CommentaryStore()
    assert store.add("a", topic="substrate")["topic"] == "substrate"
    assert store.add("b", topic="environment")["topic"] == "environment"
    assert store.add("c", topic="ui")["topic"] == "ui"
    assert store.add("d", topic="ecosystem")["topic"] == "ecosystem"
    # Unknown topics coerce to default
    assert store.add("e", topic="bogus")["topic"] == DEFAULT_TOPIC
    assert store.add("f", topic=None)["topic"] == DEFAULT_TOPIC
    assert store.add("g", topic="")["topic"] == DEFAULT_TOPIC


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


def test_recent_topic_filter():
    store = CommentaryStore()
    store.add("eco 1", topic="ecosystem")
    store.add("sub 1", topic="substrate")
    store.add("eco 2", topic="ecosystem")
    store.add("env 1", topic="environment")
    store.add("ui 1", topic="ui")

    eco = store.recent(topic="ecosystem")
    assert [c["text"] for c in eco] == ["eco 1", "eco 2"]
    sub = store.recent(topic="substrate")
    assert [c["text"] for c in sub] == ["sub 1"]
    # Topic filter composes with since_id and limit
    assert len(store.recent(topic="ecosystem", limit=1)) == 1
    assert len(store.recent(topic="ecosystem", since_id=2)) == 1


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
# Reaction unit tests
# ---------------------------------------------------------------------------


def test_react_adds_reactor():
    store = CommentaryStore()
    c = store.add("test")
    updated = store.react(c["id"], "👍", "claude")
    assert updated is not None
    assert updated["reactions"] == {"👍": ["claude"]}


def test_react_is_idempotent():
    store = CommentaryStore()
    c = store.add("test")
    store.react(c["id"], "👍", "claude")
    store.react(c["id"], "👍", "claude")
    assert c["reactions"] == {"👍": ["claude"]}


def test_react_invalid_emoji():
    store = CommentaryStore()
    c = store.add("test")
    with pytest.raises(ValueError, match="invalid emoji"):
        store.react(c["id"], "🦄", "claude")


def test_react_unknown_comment_returns_none():
    store = CommentaryStore()
    assert store.react(999, "👍", "claude") is None


def test_unreact_removes_reactor():
    store = CommentaryStore()
    c = store.add("test")
    store.react(c["id"], "👍", "claude")
    store.react(c["id"], "👍", "viewer")
    updated = store.unreact(c["id"], "👍", "claude")
    assert updated is not None
    assert updated["reactions"] == {"👍": ["viewer"]}


def test_unreact_is_idempotent():
    store = CommentaryStore()
    c = store.add("test")
    store.unreact(c["id"], "👍", "claude")  # no-op
    assert c["reactions"] == {}


def test_unreact_cleans_up_empty():
    store = CommentaryStore()
    c = store.add("test")
    store.react(c["id"], "👍", "claude")
    store.unreact(c["id"], "👍", "claude")
    assert "👍" not in c["reactions"]


def test_react_caps_reactors_per_emoji():
    from backend.commentary_store import MAX_REACTORS_PER_EMOJI

    store = CommentaryStore()
    c = store.add("test")
    for i in range(MAX_REACTORS_PER_EMOJI + 10):
        store.react(c["id"], "👍", f"reactor_{i}")
    assert len(c["reactions"]["👍"]) == MAX_REACTORS_PER_EMOJI


def test_react_sanitizes_reactor_name():
    store = CommentaryStore()
    c = store.add("test")
    store.react(c["id"], "👍", "")
    assert c["reactions"]["👍"] == ["anon"]
    store.react(c["id"], "👍", "   ")
    # Empty string is coerced to "anon" - idempotent with the first react
    assert c["reactions"]["👍"] == ["anon"]


# ---------------------------------------------------------------------------
# v1 -> v2 migration
# ---------------------------------------------------------------------------


def test_v1_payload_migrated_to_v2():
    """Loading a v1 payload (no topic/reactions) must add defaults and not fail."""
    v1_payload = {
        "schema_version": 1,
        "world_id": "old-world",
        "max_comments": 200,
        "next_id": 3,
        "comments": [
            {
                "id": 1,
                "created_at": 1700000000.0,
                "frame": 1000,
                "author": "agent",
                "text": "Legacy v1 observation",
                "tags": ["selection"],
                "severity": "info",
                "metrics": None,
            },
            {
                "id": 2,
                "created_at": 1700000100.0,
                "frame": 2000,
                "author": "claude",
                "text": "Second v1 comment",
                "tags": [],
                "severity": "insight",
                "metrics": {"gen": 5},
            },
        ],
    }

    store = CommentaryStore()
    store.load(v1_payload)

    # Schema version must be 2 after loading
    assert store.schema_version == 2

    # All v1 comments get default topic and reactions
    for c in store.comments:
        assert c["topic"] == DEFAULT_TOPIC
        assert c["reactions"] == {}

    # Existing fields are preserved
    assert store.comments[0]["text"] == "Legacy v1 observation"
    assert store.comments[1]["metrics"] == {"gen": 5}

    # IDs continue monotonically
    assert store.add("new v2 comment")["id"] == 3


def test_v2_payload_roundtrips_reactions():
    """Save → load preserves reactions on comments."""
    store = CommentaryStore(world_id="w1")
    c = store.add("test", topic="substrate")
    store.react(c["id"], "👍", "claude")
    store.react(c["id"], "💡", "gpt")

    payload = store.to_payload()

    restored = CommentaryStore()
    restored.load(payload)
    assert restored.comments[0]["topic"] == "substrate"
    assert restored.comments[0]["reactions"] == {"👍": ["claude"], "💡": ["gpt"]}


def test_default_max_comments_is_500():
    """Buffer size should be 500 (raised from 200 in v2)."""
    from backend.commentary_store import DEFAULT_MAX_COMMENTS

    assert DEFAULT_MAX_COMMENTS == 500
    store = CommentaryStore()
    assert store.max_comments == 500


def test_topics_constant():
    """The topic set must be exactly the four defined topics."""
    assert set(TOPICS) == {"ecosystem", "substrate", "environment", "ui"}
    assert DEFAULT_TOPIC == "ecosystem"


def test_reaction_emoji_constant():
    """The reaction palette must be exactly the 8 defined emoji."""
    assert len(REACTION_EMOJI) == 8
    assert "👍" in REACTION_EMOJI
    assert "👎" in REACTION_EMOJI


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
    # v2 fields
    assert comment["topic"] == "ecosystem"
    assert comment["reactions"] == {}

    got = client.get(f"/api/world/{world_id}/commentary")
    assert got.status_code == 200
    body = got.json()
    assert body["count"] == 1
    assert body["comments"][0]["text"] == "Starvation is 91% of deaths"


def test_post_with_topic(client_and_world):
    client, world_id = client_and_world
    resp = client.post(
        f"/api/world/{world_id}/commentary",
        json={"text": "Improve mutation rate", "topic": "substrate"},
    )
    assert resp.status_code == 201
    assert resp.json()["comment"]["topic"] == "substrate"


def test_get_with_topic_filter(client_and_world):
    client, world_id = client_and_world
    client.post(
        f"/api/world/{world_id}/commentary",
        json={"text": "eco note", "topic": "ecosystem"},
    )
    client.post(
        f"/api/world/{world_id}/commentary",
        json={"text": "ui idea", "topic": "ui"},
    )
    client.post(
        f"/api/world/{world_id}/commentary",
        json={"text": "eco note 2", "topic": "ecosystem"},
    )

    # Filter by topic
    resp = client.get(f"/api/world/{world_id}/commentary", params={"topic": "ecosystem"})
    assert resp.status_code == 200
    comments = resp.json()["comments"]
    assert len(comments) == 2
    assert all(c["topic"] == "ecosystem" for c in comments)

    # Filter by topic + limit
    resp = client.get(
        f"/api/world/{world_id}/commentary", params={"topic": "ecosystem", "limit": 1}
    )
    assert resp.json()["count"] == 1


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


# ---------------------------------------------------------------------------
# Reaction REST endpoint tests
# ---------------------------------------------------------------------------


def test_react_via_rest(client_and_world):
    client, world_id = client_and_world
    client.post(f"/api/world/{world_id}/commentary", json={"text": "test"})
    resp = client.post(
        f"/api/world/{world_id}/commentary/1/reactions",
        json={"emoji": "👍", "reactor": "claude"},
    )
    assert resp.status_code == 200
    assert resp.json()["comment"]["reactions"] == {"👍": ["claude"]}


def test_react_invalid_emoji_is_400(client_and_world):
    client, world_id = client_and_world
    client.post(f"/api/world/{world_id}/commentary", json={"text": "test"})
    resp = client.post(
        f"/api/world/{world_id}/commentary/1/reactions",
        json={"emoji": "🦄", "reactor": "claude"},
    )
    assert resp.status_code == 400


def test_react_unknown_comment_is_404(client_and_world):
    client, world_id = client_and_world
    resp = client.post(
        f"/api/world/{world_id}/commentary/999/reactions",
        json={"emoji": "👍", "reactor": "claude"},
    )
    assert resp.status_code == 404


def test_unreact_via_rest(client_and_world):
    client, world_id = client_and_world
    client.post(f"/api/world/{world_id}/commentary", json={"text": "test"})
    client.post(
        f"/api/world/{world_id}/commentary/1/reactions",
        json={"emoji": "👍", "reactor": "claude"},
    )
    resp = client.delete(
        f"/api/world/{world_id}/commentary/1/reactions",
        params={"emoji": "👍", "reactor": "claude"},
    )
    assert resp.status_code == 200
    assert "👍" not in resp.json()["comment"]["reactions"]


def test_unreact_unknown_comment_is_404(client_and_world):
    client, world_id = client_and_world
    resp = client.delete(
        f"/api/world/{world_id}/commentary/999/reactions",
        params={"emoji": "👍", "reactor": "claude"},
    )
    assert resp.status_code == 404
