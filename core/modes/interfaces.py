"""Mode pack interfaces and shared config conventions.

Mode packs describe high-level simulation modes (tank, petri, soccer) and
normalize configuration inputs before a world backend is constructed.

Canonical config keys (expected across modes):
- screen_width: int
- screen_height: int
- frame_rate: int
- headless: bool

Modes may accept additional keys specific to their worlds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Protocol

ModeConfig = Dict[str, Any]

CANONICAL_MODE_CONFIG_KEYS = (
    "screen_width",
    "screen_height",
    "frame_rate",
    "headless",
)


class ModePack(Protocol):
    """Interface for mode packs used to create and configure worlds."""

    mode_id: str
    world_type: str
    default_view_mode: str
    display_name: str
    snapshot_builder_factory: Callable[[], Any] | None

    # Capability flags
    supports_persistence: bool
    supports_actions: bool
    supports_websocket: bool
    supports_transfer: bool

    def configure(self, config: ModeConfig | None) -> ModeConfig:
        """Normalize config keys and fill defaults for the mode."""


@dataclass
class ModePackDefinition:
    """Concrete mode pack definition with a pluggable normalizer.

    This is the canonical source for world type metadata. Capability flags
    describe what each world type supports:
    - supports_persistence: Can save/restore world state
    - supports_actions: Requires agent actions each step (vs autonomous)
    - supports_websocket: Supports real-time websocket updates
    - supports_transfer: Supports entity transfer between worlds
    """

    mode_id: str
    world_type: str
    default_view_mode: str
    display_name: str
    # Capability flags (defaults for ecosystem-simulation worlds)
    supports_persistence: bool = True
    supports_actions: bool = False
    supports_websocket: bool = True
    supports_transfer: bool = False
    # Optional customization
    snapshot_builder_factory: Callable[[], Any] | None = None
    normalizer: Callable[[ModeConfig], ModeConfig] | None = None

    def configure(self, config: ModeConfig | None) -> ModeConfig:
        normalized = dict(config or {})
        if self.normalizer is None:
            return normalized
        return self.normalizer(normalized)
