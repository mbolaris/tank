"""The ready-first poker grouping must play exactly the games the full graph did.

PokerProximitySystem builds its proximity graph among *ready* fish first (on a
typical frame ~2 of ~65 fish), and only falls back to the all-fish graph when
several candidate groups compete for the frame's single game. These tests run
the same world twice - once as shipped, once with the pre-optimization update
(all-fish graph on every frame) - and require identical trajectories. The
reference is a copy of the old algorithm, not a switch inside the new one, so a
bug in the new branching cannot hide in both runs.
"""

from __future__ import annotations

import hashlib

import pytest

from core.replay.fingerprint import fingerprint_snapshot
from core.replay.fingerprint_stream import _snapshot_for_fingerprint
from core.systems import poker_proximity
from core.systems.base import SystemResult
from core.worlds import WorldRegistry
from core.worlds.interfaces import FAST_STEP_ACTION

# Dense enough that several candidate groups compete within the window: with
# the multi-candidate fallback removed, seed 42 diverges by frame 250
# here (measured 2026-09-23), so this comparison has teeth.
CONFIG = {"headless": True, "initial_fish_count": 60}
FRAMES = 400


def _legacy_do_update(self, frame: int) -> SystemResult:  # type: ignore[no-untyped-def]
    """PokerProximitySystem._do_update before the ready-first path."""
    poker_system = self._engine.poker_system
    if poker_system is None or not poker_system.enabled:
        return SystemResult.empty()
    fish_list = sorted(self._engine._entity_manager.get_fish(), key=poker_proximity._fish_sort_key)
    if len(fish_list) < 2:
        return SystemResult.empty()
    contacts = self._build_proximity_graph(fish_list)
    self._games_triggered += self._process_poker_groups(fish_list, contacts)
    return SystemResult.empty()


def _run(seed: int) -> tuple[str, int]:
    world = WorldRegistry.create_world("tank", seed=seed, config=CONFIG)
    world.reset(seed=seed, config=CONFIG)
    digest = hashlib.sha256()
    for frame in range(1, FRAMES + 1):
        world.step({FAST_STEP_ACTION: True})
        if frame % 25 == 0:
            digest.update(fingerprint_snapshot(_snapshot_for_fingerprint(world)).encode())
    games = world.engine.poker_proximity_system._games_triggered
    return digest.hexdigest(), games


@pytest.mark.parametrize("seed", [42])
def test_ready_first_path_matches_full_graph_path(seed: int, monkeypatch) -> None:
    counts_seen: list[int] = []
    original = poker_proximity._count_groups

    def recording(fish_list, contacts):  # type: ignore[no-untyped-def]
        count = original(fish_list, contacts)
        counts_seen.append(count)
        return count

    monkeypatch.setattr(poker_proximity, "_count_groups", recording)
    shipped_digest, shipped_games = _run(seed)

    monkeypatch.setattr(poker_proximity.PokerProximitySystem, "_do_update", _legacy_do_update)
    full_digest, full_games = _run(seed)

    assert shipped_games > 0, "the comparison is vacuous without poker games"
    assert {0, 1} <= set(counts_seen), "both fast paths should be exercised"
    assert max(counts_seen) >= 2, "the multi-candidate fallback should be exercised"
    assert shipped_games == full_games
    assert shipped_digest == full_digest


def test_count_groups_counts_components_of_two_or_more() -> None:
    a, b, c, d, e = (object() for _ in range(5))
    contacts = {a: [b], b: [a, c], c: [b], d: [e], e: [d]}
    assert poker_proximity._count_groups([a, b, c, d, e], contacts) == 2  # type: ignore[arg-type]
    assert poker_proximity._count_groups([a], {a: []}) == 0  # type: ignore[arg-type]
