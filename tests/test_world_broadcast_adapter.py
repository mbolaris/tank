"""Tests for WorldSnapshotAdapter broadcast behavior.

These tests verify:
1. Tank runners get their state passthrough with actual force_full/allow_delta params
2. Non-tank runners emit WorldUpdatePayload with mode_id and view_mode
3. serialize_state handles both payload types correctly
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MockFullStatePayload:
    """Mock tank state payload with to_json method."""

    frame: int
    entities: list[Any]
    stats: dict[str, Any]

    def to_json(self) -> str:
        import json

        return json.dumps(
            {"type": "full", "frame": self.frame, "entities": [], "stats": self.stats}
        )


@dataclass
class MockDeltaStatePayload:
    """Mock delta state payload."""

    frame: int
    delta: dict[str, Any]

    def to_json(self) -> str:
        import json

        return json.dumps({"type": "delta", "frame": self.frame, "delta": self.delta})


class MockTankRunner:
    """Mock runner that behaves like TankWorldAdapter with get_state()."""

    def __init__(self) -> None:
        self.world_id = "mock-tank-id"
        self.world_type = "tank"
        self.mode_id = "tank"
        self.view_mode = "side"
        self.frame_count = 100
        self.paused = False
        self._last_force_full: bool | None = None
        self._last_allow_delta: bool | None = None

    def get_state(
        self, force_full: bool = False, allow_delta: bool = True
    ) -> MockFullStatePayload | MockDeltaStatePayload:
        """Return mock state, recording the params passed."""
        self._last_force_full = force_full
        self._last_allow_delta = allow_delta
        if force_full or not allow_delta:
            return MockFullStatePayload(
                frame=self.frame_count, entities=[], stats={"fish_count": 10}
            )
        return MockDeltaStatePayload(frame=self.frame_count, delta={"added": [], "removed": []})

    def get_entities_snapshot(self) -> list[Any]:
        return []

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> None:
        self.frame_count += 1

    def get_stats(self) -> dict[str, Any]:
        return {"fish_count": 10}

    def get_world_info(self) -> dict[str, str]:
        return {"mode_id": self.mode_id, "world_type": self.world_type}

    def reset(self, seed: int | None = None, config: dict[str, Any] | None = None) -> None:
        self.frame_count = 0


class MockWorldRunner:
    """Mock runner for non-tank worlds (petri, soccer)."""

    def __init__(self) -> None:
        self.world_id = "mock-petri-id"
        self.world_type = "petri"
        self.mode_id = "petri"
        self.view_mode = "topdown"
        self.frame_count = 50
        self.paused = False

    def get_entities_snapshot(self) -> list[Any]:
        return []

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> None:
        self.frame_count += 1

    def get_stats(self) -> dict[str, Any]:
        return {"microbe_count": 5}

    def get_world_info(self) -> dict[str, str]:
        return {"mode_id": self.mode_id, "world_type": self.world_type}

    def reset(self, seed: int | None = None, config: dict[str, Any] | None = None) -> None:
        self.frame_count = 0


class TestWorldSnapshotAdapterTankBroadcast:
    """Tests verifying tank broadcast path honors params and preserves state richness."""

    def test_tank_runner_get_state_passes_force_full_param(self) -> None:
        """Verify force_full param is passed through to tank runner, not hardcoded."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockTankRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
            use_runner_state=True,
        )

        # Call with force_full=False (the default that was being ignored)
        adapter.get_state(force_full=False, allow_delta=True)
        assert runner._last_force_full is False, "force_full should be passed through"
        assert runner._last_allow_delta is True, "allow_delta should be passed through"

        # Call with force_full=True
        adapter.get_state(force_full=True, allow_delta=False)
        assert runner._last_force_full is True
        assert runner._last_allow_delta is False

    def test_tank_runner_returns_rich_state_directly(self) -> None:
        """Verify tank state is returned directly, not re-wrapped into minimal payload."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockTankRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
            use_runner_state=True,
        )

        state = adapter.get_state(force_full=True, allow_delta=False)

        # Should be the runner's payload directly, not WorldUpdatePayload
        assert isinstance(state, MockFullStatePayload), "Tank state should be returned directly"
        assert state.stats == {"fish_count": 10}, "Stats should be preserved"

    def test_serialize_state_handles_tank_payload(self) -> None:
        """Verify serialize_state works with tank payloads that have to_json()."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockTankRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
            use_runner_state=True,
        )

        state = adapter.get_state(force_full=True)
        serialized = adapter.serialize_state(state)

        assert isinstance(serialized, bytes)
        assert b'"fish_count": 10' in serialized or b'"fish_count":10' in serialized


class TestWorldSnapshotAdapterNonTankBroadcast:
    """Tests verifying non-tank worlds emit WorldUpdatePayload with mode_id."""

    def test_non_tank_runner_returns_world_update_payload(self) -> None:
        """Verify non-tank runners return WorldUpdatePayload with mode_id/view_mode."""
        from backend.snapshots.world_snapshot import WorldUpdatePayload
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockWorldRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,  # Don't step for this test
            use_runner_state=False,
        )

        state = adapter.get_state()

        assert isinstance(state, WorldUpdatePayload)
        assert state.mode_id == "petri"
        assert state.view_mode == "topdown"
        assert state.snapshot.frame == 50
        assert state.snapshot.world_type == "petri"

    def test_serialize_state_handles_world_update_payload(self) -> None:
        """Verify serialize_state works with WorldUpdatePayload."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockWorldRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
            use_runner_state=False,
        )

        state = adapter.get_state()
        serialized = adapter.serialize_state(state)

        assert isinstance(serialized, bytes)
        # Should contain the mode_id in the payload
        assert b'"mode_id"' in serialized or b"mode_id" in serialized
