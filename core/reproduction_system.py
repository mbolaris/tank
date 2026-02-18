"""Population recovery and asexual reproduction system.

This system delegates reproduction rules to ReproductionService, which
centralizes all reproduction logic (asexual, emergency, and post-poker).
"""

from typing import TYPE_CHECKING, Any

from core.reproduction_service import ReproductionService
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.simulation import SimulationEngine


@runs_in_phase(UpdatePhase.REPRODUCTION)
class ReproductionSystem(BaseSystem):
    """Handle asexual reproduction and emergency population recovery."""

    def __init__(self, engine: "SimulationEngine") -> None:
        super().__init__(engine, "Reproduction")
        service = engine.reproduction_service
        if service is None:
            raise RuntimeError("ReproductionService must be initialized before ReproductionSystem")
        self._service: ReproductionService = service

    def _do_update(self, frame: int) -> SystemResult:
        stats = self._service.update_frame(frame)
        return SystemResult(
            entities_affected=stats.total,
            details={
                "banked_asexual": stats.banked_asexual,
                "trait_asexual": stats.trait_asexual,
                "emergency_spawns": stats.emergency_spawns,
            },
        )

    def get_debug_info(self) -> dict[str, Any]:
        return {
            **super().get_debug_info(),
            **self._service.get_debug_info(),
        }
