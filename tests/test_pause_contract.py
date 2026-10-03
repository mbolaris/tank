"""Pause acknowledges accepted state and invalidates same-frame publication."""

from backend.simulation_runner import SimulationRunner


def test_pause_resume_ack_and_snapshot_agree():
    runner = SimulationRunner(seed=42, world_id="pause-contract")
    before = runner.get_state(force_full=True, allow_delta=False)
    assert before.stats.to_dict()["paused"] is False
    assert runner.handle_command("pause") == {"success": True, "paused": True}
    paused = runner.get_state(force_full=True, allow_delta=False)
    assert paused.stats.to_dict()["paused"] is True
    assert runner.handle_command("resume") == {"success": True, "paused": False}
    assert runner.get_state(force_full=True, allow_delta=False).stats.to_dict()["paused"] is False


def test_command_reset_changes_evidence_run_identity():
    runner = SimulationRunner(seed=42, world_id="reset-contract")
    previous = runner.foraging_history.run_id
    runner.handle_command("reset")
    assert runner.foraging_history.run_id != previous


async def test_broadcast_delivers_pause_changes_without_advancing_a_frame(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from backend.broadcast import broadcast_updates_for_world

    async def no_wait(_delay):
        pass

    monkeypatch.setattr("backend.broadcast.asyncio.sleep", no_wait)
    delivered = []

    class Client:
        async def send_bytes(self, payload):
            delivered.append(payload)

    class Adapter:
        connected_clients = {Client()}
        world_id = "pause-contract"
        world_type = "tank"

        def __init__(self):
            self.states = iter([False, True, True, False])

        async def get_state_async(self, **kwargs):
            try:
                paused = next(self.states)
            except StopIteration:
                raise asyncio.CancelledError from None
            return SimpleNamespace(frame=10, stats={"paused": paused})

        def serialize_state(self, state):
            return str(state.stats["paused"]).encode()

    import pytest

    with pytest.raises(asyncio.CancelledError):
        await broadcast_updates_for_world(Adapter())
    assert delivered == [b"False", b"True", b"False"]
