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

    def configure(self, config: ModeConfig | None) -> ModeConfig:
        """Normalize config keys and fill defaults for the mode."""


@dataclass
class ModePackDefinition:
    """Concrete mode pack definition with a pluggable normalizer."""

    mode_id: str
    world_type: str
    default_view_mode: str
    display_name: str
    snapshot_builder_factory: Callable[[], Any] | None = None
    normalizer: Callable[[ModeConfig], ModeConfig] | None = None

    def configure(self, config: ModeConfig | None) -> ModeConfig:
        normalized = dict(config or {})
        if self.normalizer is None:
            return normalized
        return self.normalizer(normalized)
