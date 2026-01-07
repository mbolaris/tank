"""Tests for WorldSnapshotAdapter broadcast behavior.

These tests verify:
1. All runners delegate to runner.get_state() with correct params
2. serialize_state uses to_json() from unified payload types
3. step_on_access behavior is respected
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class MockFullStatePayload:
    """Mock state payload with to_json method (matches FullStatePayload interface)."""

    frame: int
    entities: list[Any]
    stats: dict[str, Any]
    mode_id: str = "tank"
    world_type: str = "tank"
    view_mode: str = "side"

    def to_json(self) -> str:
        import json

        return json.dumps(
            {
                "type": "update",
                "frame": self.frame,
                "entities": [],
                "stats": self.stats,
                "mode_id": self.mode_id,
                "world_type": self.world_type,
                "view_mode": self.view_mode,
            }
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
    """Mock runner that behaves like SimulationRunner with get_state()."""

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
    """Mock runner for non-tank worlds (petri, soccer) with get_state()."""

    def __init__(self) -> None:
        self.world_id = "mock-petri-id"
        self.world_type = "petri"
        self.mode_id = "petri"
        self.view_mode = "topdown"
        self.frame_count = 50
        self.paused = False
        self._step_count = 0

    def get_state(self, force_full: bool = False, allow_delta: bool = True) -> MockFullStatePayload:
        """All runners now implement get_state() with unified interface."""
        return MockFullStatePayload(
            frame=self.frame_count,
            entities=[],
            stats={"microbe_count": 5},
            mode_id=self.mode_id,
            world_type=self.world_type,
            view_mode=self.view_mode,
        )

    def get_entities_snapshot(self) -> list[Any]:
        return []

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> None:
        self.frame_count += 1
        self._step_count += 1

    def get_stats(self) -> dict[str, Any]:
        return {"microbe_count": 5}

    def get_world_info(self) -> dict[str, str]:
        return {"mode_id": self.mode_id, "world_type": self.world_type}

    def reset(self, seed: int | None = None, config: dict[str, Any] | None = None) -> None:
        self.frame_count = 0


class TestWorldSnapshotAdapterUnifiedBehavior:
    """Tests verifying unified adapter behavior for all runners."""

    def test_adapter_passes_force_full_param_to_runner(self) -> None:
        """Verify force_full param is passed through to runner.get_state()."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockTankRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
        )

        # Call with force_full=False (delta mode)
        adapter.get_state(force_full=False, allow_delta=True)
        assert runner._last_force_full is False, "force_full should be passed through"
        assert runner._last_allow_delta is True, "allow_delta should be passed through"

        # Call with force_full=True (full state mode)
        adapter.get_state(force_full=True, allow_delta=False)
        assert runner._last_force_full is True
        assert runner._last_allow_delta is False

    def test_adapter_returns_runner_state_directly(self) -> None:
        """Verify adapter returns runner's payload directly."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockTankRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
        )

        state = adapter.get_state(force_full=True, allow_delta=False)

        # Should be the runner's payload directly
        assert isinstance(state, MockFullStatePayload), "State should be runner's payload"
        assert state.stats == {"fish_count": 10}, "Stats should be preserved"

    def test_serialize_state_uses_to_json(self) -> None:
        """Verify serialize_state uses to_json() method from unified payloads."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockTankRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
        )

        state = adapter.get_state(force_full=True)
        serialized = adapter.serialize_state(state)

        assert isinstance(serialized, bytes)
        assert b'"fish_count": 10' in serialized or b'"fish_count":10' in serialized


class TestWorldSnapshotAdapterStepOnAccess:
    """Tests verifying step_on_access behavior."""

    def test_step_on_access_true_steps_world(self) -> None:
        """Verify step_on_access=True causes world to step before getting state."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockWorldRunner()
        initial_step_count = runner._step_count
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=True,
        )

        adapter.get_state()

        assert runner._step_count == initial_step_count + 1, "World should have been stepped"

    def test_step_on_access_false_does_not_step(self) -> None:
        """Verify step_on_access=False does not step the world."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockWorldRunner()
        initial_step_count = runner._step_count
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
        )

        adapter.get_state()

        assert runner._step_count == initial_step_count, "World should not have been stepped"


class TestWorldSnapshotAdapterNonTankWorlds:
    """Tests verifying non-tank worlds work with unified path."""

    def test_non_tank_runner_uses_unified_get_state(self) -> None:
        """Verify non-tank runners use the same get_state() interface."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockWorldRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
        )

        state = adapter.get_state()

        # Should return FullStatePayload-like object with mode_id
        assert isinstance(state, MockFullStatePayload)
        assert state.mode_id == "petri"
        assert state.view_mode == "topdown"
        assert state.frame == 50

    def test_non_tank_serialize_state_works(self) -> None:
        """Verify serialize_state works with non-tank payloads."""
        from backend.world_broadcast_adapter import WorldSnapshotAdapter

        runner = MockWorldRunner()
        adapter = WorldSnapshotAdapter(
            world_id=runner.world_id,
            runner=runner,  # type: ignore[arg-type]
            world_type=runner.world_type,
            mode_id=runner.mode_id,
            view_mode=runner.view_mode,
            step_on_access=False,
        )

        state = adapter.get_state()
        serialized = adapter.serialize_state(state)

        assert isinstance(serialized, bytes)
        # Should contain the mode_id in the payload
        assert b'"mode_id"' in serialized or b"mode_id" in serialized
