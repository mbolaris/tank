"""Tests for RCSSLiteEngine public API and encapsulation.

Verifies that external modules use public API methods rather than
accessing private engine internals.
"""

from __future__ import annotations

import re
from pathlib import Path


def _find_pattern_violations(
    *,
    pattern: str,
    root: str,
    allowed_path_substrings: tuple[str, ...] = (),
    allowed_line_predicate=None,
) -> list[str]:
    """Return 'path:line: text' matches for pattern under root."""
    regex = re.compile(pattern)
    violations: list[str] = []

    for path in Path(root).rglob("*.py"):
        path_str = str(path)
        if any(allowed in path_str for allowed in allowed_path_substrings):
            continue

        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not regex.search(line):
                continue
            if allowed_line_predicate and allowed_line_predicate(path_str, line):
                continue
            violations.append(f"{path_str}:{line_number}: {line.strip()}")

    return violations


def test_no_external_access_to_engine_private_players():
    """Verify no external module accesses engine._players directly."""
    violations = _find_pattern_violations(
        pattern=r"\._players\b",
        root="core/minigames/soccer/",
        allowed_path_substrings=("engine.py",),
    )

    assert not violations, (
        f"Found {len(violations)} external accesses to ._players:\n"
        + "\n".join(violations)
        + "\n\nUse engine.players() or engine.iter_players() instead."
    )


def test_no_external_access_to_engine_private_last_touch():
    """Verify no external module accesses engine._last_touch_* directly."""

    def allowed_line(path_str: str, line: str) -> bool:
        return "match.py" in path_str and "self._last_touch_id" in line

    violations = _find_pattern_violations(
        pattern=r"\._last_touch",
        root="core/minigames/soccer/",
        allowed_path_substrings=("engine.py",),
        allowed_line_predicate=allowed_line,
    )

    assert not violations, (
        f"Found {len(violations)} external accesses to ._last_touch_*:\n"
        + "\n".join(violations)
        + "\n\nUse engine.last_touch_info() instead."
    )


def test_no_external_access_to_engine_private_play_mode():
    """Verify no external module accesses engine._play_mode directly."""
    violations = _find_pattern_violations(
        pattern=r"\._play_mode\b",
        root="core/minigames/soccer/",
        allowed_path_substrings=("engine.py",),
    )

    assert not violations, (
        f"Found {len(violations)} external accesses to ._play_mode:\n"
        + "\n".join(violations)
        + "\n\nUse engine.set_play_mode(...) instead."
    )


def test_engine_set_play_mode_updates_state():
    """Verify set_play_mode updates play_mode and snapshot state."""
    from core.minigames.soccer.engine import RCSSLiteEngine

    engine = RCSSLiteEngine(seed=42)
    engine.set_play_mode("kick_off_right")

    assert engine.play_mode == "kick_off_right"
    assert engine.get_snapshot()["play_mode"] == "kick_off_right"


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
