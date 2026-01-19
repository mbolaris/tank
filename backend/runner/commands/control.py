import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


class ControlCommands:
    def _cmd_pause(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'pause' command."""
        self.paused = True
        logger.info("Simulation paused")
        return None

    def _cmd_resume(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'resume' command."""
        self.paused = False
        logger.info("Simulation resumed")
        return None

    def _cmd_reset(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'reset' command."""
        # Reset the underlying world to a clean frame counter and entities
        if hasattr(self.world, "reset"):
            self.world.reset()
        else:
            self.world.setup()
        self._invalidate_state_cache()
        # Unpause after reset for intuitive behavior
        self.paused = False
        self.fast_forward = False
        logger.info("Simulation reset")
        return None

    def _cmd_fast_forward(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'fast_forward' command."""
        enabled = data.get("enabled", False) if data else False
        self.fast_forward = enabled
        logger.info(f"Fast forward {'enabled' if enabled else 'disabled'}")
        return None
