"""Detached presentation snapshot of a completed soccer match.

The league runtime finalizes a match and immediately drops the live engine, so
the very next broadcast payload used to carry ``active_match=null``. The arena
therefore never got to show a full-time card, the final score, or the final
player positions - the match simply vanished mid-celebration.

This module builds a *detached* snapshot used only for display. It is
deliberately **not** a second kind of active match:

- ``active_match`` still means "a match that is currently executing".
- ``presentation_match`` is inert data. It holds no reference to the match, the
  engine, the roster, or any fish, so retaining it cannot keep a finished match
  alive, delay fixture scheduling, or leak mutable simulation state.

Retention is counted in world ticks rather than wall-clock seconds so replays
and tests stay deterministic.
"""

from __future__ import annotations

import copy
from typing import Any

from core.config.display import FRAME_RATE

#: How long a finished match stays on screen, in world ticks. At the standard
#: ``FRAME_RATE`` this is 6 seconds, inside the 5-8s window the design asks for.
#: Ticks (not seconds) keep expiry deterministic under replay and fast-forward.
PRESENTATION_HOLD_SECONDS = 6
PRESENTATION_MATCH_HOLD_TICKS = PRESENTATION_HOLD_SECONDS * FRAME_RATE


def build_presentation_snapshot(
    match_state: dict[str, Any],
    *,
    league_round: int | None = None,
    home_id: str | None = None,
    away_id: str | None = None,
    home_name: str | None = None,
    away_name: str | None = None,
) -> dict[str, Any]:
    """Return a detached full-time snapshot of ``match_state``.

    The input is deep-copied first, so later mutation or deletion of the match
    that produced it cannot alter the returned snapshot.

    ``half`` is deliberately left as the match reported it. Forcing it to 2
    would tell the renderer that sides had swapped even for a match that ended
    before halftime, which is exactly the mislabelling this PR is fixing.
    """
    snapshot = copy.deepcopy(match_state)

    if home_id is not None:
        snapshot["home_id"] = home_id
    if away_id is not None:
        snapshot["away_id"] = away_id
    if home_name is not None:
        snapshot["home_name"] = home_name
    if away_name is not None:
        snapshot["away_name"] = away_name
    if league_round is not None:
        snapshot["league_round"] = league_round

    snapshot["game_over"] = True
    snapshot["play_mode"] = "time_over"

    events = snapshot.get("events")
    if not isinstance(events, list):
        events = []
        snapshot["events"] = events
    if not any(isinstance(e, dict) and e.get("kind") == "full_time" for e in events):
        events.append(_full_time_event(snapshot, len(events)))

    return snapshot


def _full_time_event(snapshot: dict[str, Any], seq: int) -> dict[str, Any]:
    """Build the deterministic full-time event, matching SoccerMatch._emit_event.

    ``SoccerMatch.step`` already emits this when the clock runs out; this is the
    fallback for a match that ended some other way. The id derives only from
    match identity and event data - never wall-clock time or ``hash()``.
    """
    frame = int(snapshot.get("frame", 0) or 0)
    match_id = snapshot.get("match_id", "match")
    return {
        "frame": frame,
        "seq": seq,
        "event_id": f"{match_id}-full_time-{frame}-{seq}",
        "kind": "full_time",
    }
