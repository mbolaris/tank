"""Tests for RCSSLiteEngine public API and encapsulation.

Verifies that external modules use public API methods rather than
accessing private engine internals.
"""

import subprocess


def test_no_external_access_to_engine_private_players():
    """Verify no external module accesses engine._players directly."""
    # Use grep to find any access to _engine._players outside engine.py
    result = subprocess.run(
        [
            "grep",
            "-r",
            "-n",
            "--include=*.py",
            r"\._players",
            "core/minigames/soccer/",
        ],
        capture_output=True,
        text=True,
    )

    # Filter out engine.py itself (which is allowed to access _players)
    violations = []
    for line in result.stdout.splitlines():
        if "engine.py:" not in line:
            violations.append(line)

    assert not violations, (
        f"Found {len(violations)} external accesses to ._players:\n"
        + "\n".join(violations)
        + "\n\nUse engine.players() or engine.iter_players() instead."
    )


def test_no_external_access_to_engine_private_last_touch():
    """Verify no external module accesses engine._last_touch_* directly."""
    # Use grep to find any access to _engine._last_touch outside engine.py
    result = subprocess.run(
        [
            "grep",
            "-r",
            "-n",
            "--include=*.py",
            r"\._last_touch",
            "core/minigames/soccer/",
        ],
        capture_output=True,
        text=True,
    )

    # Filter out:
    # 1. engine.py itself (which is allowed to access _last_touch_*)
    # 2. match.py's own _last_touch_id (different from engine's)
    violations = []
    for line in result.stdout.splitlines():
        # Skip engine.py
        if "engine.py:" in line:
            continue
        # Skip match.py's own _last_touch_id field
        if "match.py:" in line and "self._last_touch_id" in line:
            continue
        # Everything else is a violation
        violations.append(line)

    assert not violations, (
        f"Found {len(violations)} external accesses to ._last_touch_*:\n"
        + "\n".join(violations)
        + "\n\nUse engine.last_touch_info() instead."
    )


def test_engine_public_api_exists():
    """Verify that RCSSLiteEngine has the expected public API methods."""
    from core.minigames.soccer.engine import RCSSLiteEngine

    engine = RCSSLiteEngine(seed=42)

    # Check public API methods exist
    assert hasattr(engine, "players"), "Missing players() method"
    assert hasattr(engine, "iter_players"), "Missing iter_players() method"
    assert hasattr(engine, "last_touch_info"), "Missing last_touch_info() method"
    assert callable(engine.players)
    assert callable(engine.iter_players)
    assert callable(engine.last_touch_info)


def test_engine_last_touch_info_structure():
    """Verify last_touch_info() returns expected structure."""
    from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector

    engine = RCSSLiteEngine(seed=42)
    engine.add_player("left_1", "left", RCSSVector(-10, 0))

    touch_info = engine.last_touch_info()

    # Check structure
    assert isinstance(touch_info, dict)
    assert "player_id" in touch_info
    assert "cycle" in touch_info
    assert "prev_player_id" in touch_info
    assert "prev_cycle" in touch_info

    # Initial state
    assert touch_info["player_id"] is None
    assert touch_info["cycle"] == -1
    assert touch_info["prev_player_id"] is None
    assert touch_info["prev_cycle"] == -1


def test_engine_players_returns_copy():
    """Verify players() returns a copy, not internal state."""
    from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector

    engine = RCSSLiteEngine(seed=42)
    engine.add_player("left_1", "left", RCSSVector(-10, 0))
    engine.add_player("right_1", "right", RCSSVector(10, 0))

    players1 = engine.players()
    players2 = engine.players()

    # Should be equal but not the same object
    assert players1 == players2
    assert players1 is not players2

    # Modifying returned dict shouldn't affect engine
    players1.clear()
    assert len(engine.players()) == 2


def test_engine_iter_players():
    """Verify iter_players() works correctly."""
    from core.minigames.soccer.engine import RCSSLiteEngine, RCSSVector

    engine = RCSSLiteEngine(seed=42)
    engine.add_player("left_1", "left", RCSSVector(-10, 0))
    engine.add_player("right_1", "right", RCSSVector(10, 0))

    # Should be able to iterate
    players_list = list(engine.iter_players())
    assert len(players_list) == 2

    # Check that we got player states
    player_ids = {p.player_id for p in players_list}
    assert player_ids == {"left_1", "right_1"}
