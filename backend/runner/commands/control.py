import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ControlCommands:
    if TYPE_CHECKING:
        paused: bool
        fast_forward: bool
        world: Any

        def _invalidate_state_cache(self) -> None: ...

    def _cmd_pause(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle 'pause' command."""
        self.paused = True
        logger.info("Simulation paused")
        return None

    def _cmd_resume(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle 'resume' command."""
        self.paused = False
        logger.info("Simulation resumed")
        return None

    def _cmd_reset(self, data: dict[str, Any]) -> dict[str, Any] | None:
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

    def _cmd_fast_forward(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle 'fast_forward' command."""
        enabled = data.get("enabled", False) if data else False
        self.fast_forward = enabled
        logger.info(f"Fast forward {'enabled' if enabled else 'disabled'}")
        return None
