"""Simulation systems package.

Systems implement per-frame logic on entities and follow BaseSystem.
Execution order is controlled by the explicit phase loop in
`core/simulation/engine.py`. Phase metadata (UpdatePhase + @runs_in_phase)
remains for diagnostics and validation.

See `docs/ARCHITECTURE.md` for the current phase order and system duties.
"""

from core.systems.base import BaseSystem, System, SystemResult
from core.systems.food_spawning import FoodSpawningSystem, SpawnRateConfig

__all__ = [
    "BaseSystem",
    "FoodSpawningSystem",
    "SpawnRateConfig",
    "System",
    "SystemResult",
]
