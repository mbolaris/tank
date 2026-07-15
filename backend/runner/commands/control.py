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

        def _create_error_response(self, error_msg: str) -> dict[str, Any]: ...

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

    def _cmd_set_local_resource_patches(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Toggle the experimental local resource patches at runtime."""
        if not data or "enabled" not in data:
            return self._create_error_response("Missing 'enabled' parameter")

        engine = getattr(self.world, "engine", None)
        if engine is None or getattr(engine, "food_spawning_system", None) is None:
            return self._create_error_response("Food spawning system is not available")

        enabled = bool(data["enabled"])
        system = engine.food_spawning_system
        system.config.local_resource_patches_enabled = enabled

        if enabled:
            # Queue the markers immediately; normal spawn-phase processing will
            # apply the mutation and continue regrowth on subsequent frames.
            system._ensure_resource_patches()
        else:
            for patch in list(system._resource_patches):
                engine.request_remove(patch, reason="local_resource_patches_disabled")
            system._resource_patches.clear()

        logger.info("Local resource patches %s", "enabled" if enabled else "disabled")
        return {"success": True, "enabled": enabled}
