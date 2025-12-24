"""Visual state containers for entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class FishVisualState:
    """Transient rendering-only state for fish."""

    poker_effect_state: Optional[Dict[str, Any]] = None
    poker_effect_timer: int = 0
    birth_effect_timer: int = 0
    death_effect_state: Optional[Dict[str, Any]] = None
    death_effect_timer: int = 0
