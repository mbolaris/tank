"""FrameContext - explicit per-frame state for pipeline steps.

This module provides the FrameContext dataclass that replaces ad-hoc
engine._pipeline_* attributes with explicit, typed per-frame state.

FrameContext is created at the start of each frame and passed through
all pipeline steps, making data flow explicit and eliminating hidden
coupling between steps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FrameContext:
    """Explicit per-frame state passed through pipeline steps.

    This replaces the ad-hoc engine._pipeline_* attributes that were used
    to pass data between pipeline steps. All per-frame computed values
    should be stored here rather than on the engine.

    Attributes:
        time_modifier: Activity modifier from day/night cycle (0.0-1.0+)
        time_of_day: Current time of day (0.0-1.0, 0=midnight, 0.5=noon)
        new_entities: Entities spawned during entity_act phase
        entities_to_remove: Entities marked for removal during entity_act phase
    """

    # Time values computed in TIME_UPDATE phase, used in ENTITY_ACT
    time_modifier: float = 1.0
    time_of_day: float = 0.5

    # Entity lists computed in ENTITY_ACT phase, used in LIFECYCLE
    new_entities: list[Any] = field(default_factory=list)
    entities_to_remove: list[Any] = field(default_factory=list)
