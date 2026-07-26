"""Request/response models for the worlds API."""

from typing import Any

from pydantic import BaseModel


class CreateWorldRequest(BaseModel):
    """Request body for creating a new world."""

    world_type: str
    name: str
    config: dict[str, Any] | None = None
    persistent: bool = True
    seed: int | None = None
    description: str = ""
    start_paused: bool = False


class UpdateWorldModeRequest(BaseModel):
    """Request body for updating world mode."""

    world_type: str


class WorldTypeResponse(BaseModel):
    """Response for a single world type."""

    mode_id: str
    world_type: str
    view_mode: str
    display_name: str
    supports_persistence: bool
    supports_actions: bool
    supports_websocket: bool
    supports_transfer: bool
    has_fish: bool
