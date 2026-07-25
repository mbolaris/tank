"""The broadcast loop must actually hit its configured rate.

Regression test for a pacing bug where every wait in the loop was a fixed
``1 / FRAME_RATE`` quantum -- including an unconditional sleep after each
successful send. Since that quantum is half the 15 Hz send period, any
overshoot rounded up to a whole extra frame and the loop settled at ~9 Hz
(62% of configured) instead of 15 Hz.

Marked ``slow``: these measure a real wall-clock rate, so they need seconds of
elapsed time and are sensitive to scheduling jitter on a loaded runner.
"""

from __future__ import annotations

import asyncio
import time

import pytest

pytest.importorskip("pytest_asyncio")

from starlette.websockets import WebSocketState

from backend.broadcast import broadcast_updates_for_world
from core.config.display import FRAME_RATE

BROADCAST_HZ = 15.0
BUILD_SECONDS = 0.010  # stand-in for collecting stats + entity snapshots
SEND_SECONDS = 0.003


class _FakeClient:
    """Records the wall-clock time of every send."""

    def __init__(self) -> None:
        self.client_state = WebSocketState.CONNECTED
        self.sends: list[float] = []

    async def send_bytes(self, payload: bytes) -> None:
        await asyncio.sleep(SEND_SECONDS)
        self.sends.append(time.perf_counter())

    async def close(self) -> None:  # pragma: no cover - only on disconnect paths
        pass


class _FakeAdapter:
    """Adapter whose world advances at exactly FRAME_RATE."""

    world_id = "cadence-test"
    world_type = "tank"
    mode_id = "tank"
    view_mode = "side"

    def __init__(self) -> None:
        self.client = _FakeClient()
        self._clients = {self.client}
        self._t0 = time.perf_counter()
        self.get_state_calls = 0

    @property
    def connected_clients(self):
        return self._clients

    def add_client(self, websocket) -> None:
        self._clients.add(websocket)

    def remove_client(self, websocket) -> None:
        self._clients.discard(websocket)

    async def get_state_async(self, force_full: bool = False, allow_delta: bool = True):
        await asyncio.sleep(BUILD_SECONDS)
        self.get_state_calls += 1
        frame = int((time.perf_counter() - self._t0) * FRAME_RATE)
        return type("_State", (), {"frame": frame})()

    def serialize_state(self, state) -> bytes:
        return b"x" * 4096

    async def handle_command_async(self, command, data=None):  # pragma: no cover
        return None


@pytest.mark.slow
@pytest.mark.asyncio
async def test_broadcast_achieves_configured_rate(monkeypatch) -> None:
    """The loop must deliver close to BROADCAST_HZ, not a fraction of it."""
    monkeypatch.setenv("BROADCAST_HZ", str(BROADCAST_HZ))

    adapter = _FakeAdapter()
    duration = 3.0

    task = asyncio.create_task(broadcast_updates_for_world(adapter, world_id="cadence-test"))
    started = time.perf_counter()
    await asyncio.sleep(duration)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    elapsed = time.perf_counter() - started

    sends = adapter.client.sends
    actual_hz = len(sends) / elapsed

    # The old fixed-quantum pacing produced ~62% of the configured rate.
    # Allow generous slack for CI scheduling jitter but stay well above that.
    assert actual_hz >= BROADCAST_HZ * 0.85, (
        f"broadcast ran at {actual_hz:.2f} Hz, expected >= "
        f"{BROADCAST_HZ * 0.85:.2f} Hz (configured {BROADCAST_HZ} Hz)"
    )
    assert actual_hz <= BROADCAST_HZ * 1.15, (
        f"broadcast ran at {actual_hz:.2f} Hz, faster than the configured "
        f"{BROADCAST_HZ} Hz -- pacing is not being honoured"
    )


@pytest.mark.slow
@pytest.mark.asyncio
async def test_broadcast_does_not_waste_state_builds(monkeypatch) -> None:
    """Every get_state build should result in a send.

    Building state costs a world-lock acquisition on the simulation thread, so
    a build whose frame is then discarded is contention paid for nothing.
    """
    monkeypatch.setenv("BROADCAST_HZ", str(BROADCAST_HZ))

    adapter = _FakeAdapter()
    task = asyncio.create_task(broadcast_updates_for_world(adapter, world_id="cadence-test"))
    await asyncio.sleep(3.0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    sends = len(adapter.client.sends)
    # A couple of duplicate-frame polls are acceptable; a systematic 1:2 ratio
    # (the old behaviour under load) is not.
    assert adapter.get_state_calls <= sends + 3, (
        f"{adapter.get_state_calls} state builds for only {sends} sends -- "
        "duplicate-frame polling is burning world-lock acquisitions"
    )
