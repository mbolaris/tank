"""World snapshot payloads for world-agnostic WebSocket updates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.state_payloads import EntitySnapshot

try:  # Prefer faster serializer when available
    import orjson
except ImportError:
    orjson = None


@dataclass
class WorldSnapshot:
    """Minimal snapshot schema shared across world types."""

    world_id: str
    world_type: str
    frame: int
    entities: list[EntitySnapshot]

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "world_type": self.world_type,
            "frame": self.frame,
            "entities": [entity.to_full_dict() for entity in self.entities],
        }


@dataclass
class WorldUpdatePayload:
    """Top-level WebSocket payload carrying a world snapshot."""

    snapshot: WorldSnapshot
    mode_id: str | None = None
    view_mode: str | None = None
    type: str = "update"
    world_id: str | None = None
    world_type: str | None = None

    @property
    def frame(self) -> int:
        return self.snapshot.frame

    def to_dict(self) -> dict[str, Any]:
        world_id = self.world_id or self.snapshot.world_id
        world_type = self.world_type or self.snapshot.world_type

        data: dict[str, Any] = {
            "type": self.type,
            "snapshot": self.snapshot.to_dict(),
        }
        if world_id is not None:
            data["world_id"] = world_id
        if world_type is not None:
            data["world_type"] = world_type
        if self.mode_id is not None:
            data["mode_id"] = self.mode_id
        if self.view_mode is not None:
            data["view_mode"] = self.view_mode
        return data

    def to_json(self) -> str:
        data = self.to_dict()
        if orjson:
            return orjson.dumps(data).decode("utf-8")
        return json.dumps(data, separators=(",", ":"))
