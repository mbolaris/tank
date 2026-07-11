"""Focused, JSON-friendly tracing for headless simulation debugging.

The normal headless loop deliberately uses the cheap ``world.update()`` path,
which does not materialize a :class:`~core.worlds.interfaces.StepResult`.
Debugging is opt-in, so this module provides the slower, observable path used
by ``main.py --debug-frame`` and ``--debug-entity`` without adding work to
normal simulations or benchmarks.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, cast

from core.worlds.interfaces import StepResult


def _jsonable(value: Any) -> Any:
    """Convert step-result values into stable JSON-compatible structures."""
    if is_dataclass(value):
        return _jsonable(asdict(cast(Any, value)))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value, key=str)]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _jsonable(value.to_dict())
    return value


def _contains_entity(value: Any, entity_id: str) -> bool:
    """Return whether a nested event/output refers to *entity_id*.

    Entity IDs appear under several names in the existing event contracts
    (``entity_id``, ``stable_id``, ``fish_id``, ``winner_id``, and so on), so a
    recursive check keeps the tracer useful across poker, soccer, and core
    lifecycle records without changing those contracts.
    """
    if is_dataclass(value):
        return _contains_entity(asdict(cast(Any, value)), entity_id)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _contains_entity(value.to_dict(), entity_id)
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in {"frame", "match_counter"}:
                continue
            if (
                str(key)
                in {
                    "id",
                    "entity_id",
                    "stable_id",
                    "fish_id",
                    "winner_id",
                    "loser_id",
                    "plant_id",
                    "source_plant_id",
                    "scorer_id",
                    "assist_id",
                }
                and str(item) == entity_id
            ):
                return True
            if _contains_entity(item, entity_id):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_entity(item, entity_id) for item in value)
    return False


def _event_happened_on_frame(event: Any, frame: int) -> bool:
    """Exclude old entries returned by the backend's bounded event history."""
    if not isinstance(event, Mapping):
        return True
    data = event.get("data")
    if isinstance(data, Mapping) and "frame" in data:
        return bool(data["frame"] == frame)
    return bool(event.get("frame", frame) == frame)


class DebugTraceCollector:
    """Collect selected per-frame outputs for human or machine inspection."""

    def __init__(
        self,
        *,
        seed: int | None,
        max_frames: int,
        debug_frame: int | None = None,
        debug_entity: str | None = None,
    ) -> None:
        if debug_frame is not None and debug_frame < 1:
            raise ValueError("debug_frame must be >= 1")
        self.debug_frame = debug_frame
        self.debug_entity = str(debug_entity) if debug_entity is not None else None
        self._document: dict[str, Any] = {
            "schema_version": 1,
            "seed": seed,
            "max_frames": max_frames,
            "debug_frame": debug_frame,
            "debug_entity": self.debug_entity,
            "frames": [],
        }

    @property
    def frames(self) -> list[dict[str, Any]]:
        """Return the collected frame records."""
        return cast(list[dict[str, Any]], self._document["frames"])

    def record(self, result: StepResult) -> None:
        """Record a step when it matches the configured frame/entity filters."""
        frame = int(result.info.get("frame", result.snapshot.get("frame", 0)))
        if self.debug_frame is not None and frame != self.debug_frame:
            return

        events = [event for event in result.events if _event_happened_on_frame(event, frame)]
        outputs: dict[str, list[Any]] = {
            "energy_deltas": result.energy_deltas,
            "spawns": result.spawns,
            "removals": result.removals,
            "events": events,
        }
        if self.debug_entity is not None:
            outputs = {
                name: [item for item in values if _contains_entity(item, self.debug_entity)]
                for name, values in outputs.items()
            }

        record: dict[str, Any] = {
            "frame": frame,
            **{name: _jsonable(values) for name, values in outputs.items()},
        }

        entities = result.snapshot.get("entities")
        if isinstance(entities, list) and self.debug_entity is not None:
            record["entities"] = [
                _jsonable(entity)
                for entity in entities
                if _contains_entity(entity, self.debug_entity)
            ]
        self.frames.append(record)

    def to_dict(self) -> dict[str, Any]:
        """Return the complete trace document with a compact summary."""
        document = dict(self._document)
        document["summary"] = {
            "frames_recorded": len(self.frames),
            "energy_deltas": sum(len(frame["energy_deltas"]) for frame in self.frames),
            "spawns": sum(len(frame["spawns"]) for frame in self.frames),
            "removals": sum(len(frame["removals"]) for frame in self.frames),
            "events": sum(len(frame["events"]) for frame in self.frames),
        }
        return document

    def write(self, path: str | Path) -> None:
        """Write the trace as indented JSON."""
        import json

        Path(path).write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
        )
