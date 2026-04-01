"""Auto-save service for periodic world state persistence.

This module provides automatic background saving of world states at
configured intervals, ensuring that simulations can be restored after
server restarts.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.world_manager import WorldInstance, WorldManager

logger = logging.getLogger(__name__)

# Default auto-save interval in seconds
DEFAULT_AUTO_SAVE_INTERVAL = 300.0


class AutoSaveService:
    """Background service for auto-saving world states.

    This service manages periodic saves for all persistent worlds
    in the manager, with configurable intervals per world.
    """

    def __init__(self, world_manager: "WorldManager"):
        """Initialize the auto-save service.

        Args:
            world_manager: The world manager to monitor
        """
        self._world_manager = world_manager
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False

    def register_world(self, instance: "WorldInstance") -> None:
        """Enroll a newly created persistent world in auto-save.

        Args:
            instance: The created world instance
        """
        if not self._running or not instance.persistent:
            return

        self._schedule_task(
            self._start_world_autosave(instance),
            name=f"autosave_start_{instance.world_id[:8]}",
        )

    def unregister_world(self, world_id: str) -> None:
        """Remove a deleted world from auto-save tracking.

        Args:
            world_id: The deleted world ID
        """
        if not self._running:
            return

        self._schedule_task(
            self.stop_world_autosave(world_id),
            name=f"autosave_stop_{world_id[:8]}",
        )

    async def start(self) -> None:
        """Start the auto-save service."""
        if self._running:
            logger.warning("Auto-save service already running")
            return

        self._running = True
        logger.info("Auto-save service started")

        # Start auto-save tasks for all persistent worlds
        for instance in self._world_manager:
            if instance.persistent:
                await self._start_world_autosave(instance)

    async def stop(self) -> None:
        """Stop the auto-save service and cancel all tasks."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping auto-save service...")

        # Cancel all auto-save tasks
        for world_id, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Auto-save task cancelled for world {world_id[:8]}")

        self._tasks.clear()
        logger.info("Auto-save service stopped")

    async def _start_world_autosave(self, instance: "WorldInstance") -> None:
        """Start auto-save task for a specific world.

        Args:
            instance: The WorldInstance to auto-save
        """
        world_id = instance.world_id

        if world_id in self._tasks:
            logger.warning(f"Auto-save task already exists for world {world_id[:8]}")
            return

        task = asyncio.create_task(self._autosave_loop(instance), name=f"autosave_{world_id[:8]}")
        self._tasks[world_id] = task
        logger.info(
            f"Started auto-save for world {world_id[:8]} "
            f"(interval: {DEFAULT_AUTO_SAVE_INTERVAL}s)"
        )

    def _schedule_task(self, coro: Coroutine[object, object, object], *, name: str) -> None:
        """Schedule a background auto-save operation on the active loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug("No running event loop available for task %s", name)
            return

        task = loop.create_task(coro, name=name)
        task.add_done_callback(self._handle_background_task)

    @staticmethod
    def _handle_background_task(task: asyncio.Task) -> None:
        """Log unhandled exceptions from background enrollment tasks."""
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug("Background auto-save task %s was cancelled", task.get_name())
        except Exception as exc:
            logger.error(
                "Unhandled exception in auto-save task %s: %s",
                task.get_name(),
                exc,
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    async def stop_world_autosave(self, world_id: str) -> None:
        """Stop auto-save task for a specific world.

        Args:
            world_id: The world ID to stop auto-saving
        """
        task = self._tasks.pop(world_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Auto-save task stopped for world {world_id[:8]}")

    async def _autosave_loop(self, instance: "WorldInstance") -> None:
        """Background loop for periodic world saves.

        Args:
            instance: The WorldInstance to save
        """
        from backend.world_persistence import cleanup_old_snapshots, save_world_state

        world_id = instance.world_id
        interval = DEFAULT_AUTO_SAVE_INTERVAL

        try:
            while self._running:
                # Wait for the configured interval
                await asyncio.sleep(interval)

                # Save the world state
                try:
                    metadata = {
                        "name": instance.name,
                        "description": instance.description,
                        "world_type": instance.world_type,
                    }
                    result = save_world_state(world_id, instance.runner, metadata=metadata)
                    if result:
                        # Cleanup old snapshots to prevent disk bloat
                        cleanup_old_snapshots(world_id, max_snapshots=10)
                    else:
                        logger.warning(f"Auto-save failed for world {world_id[:8]}")

                except Exception as e:
                    logger.error(
                        f"Error during auto-save for world {world_id[:8]}: {e}", exc_info=True
                    )

        except asyncio.CancelledError:
            logger.info(f"Auto-save loop cancelled for world {world_id[:8]}")
            raise
        except Exception as e:
            logger.error(
                f"Fatal error in auto-save loop for world {world_id[:8]}: {e}", exc_info=True
            )

    async def save_world_now(self, world_id: str) -> str | None:
        """Immediately save a specific world (out of band).

        Args:
            world_id: The world ID to save

        Returns:
            Path to saved snapshot, or None if failed
        """
        from backend.world_persistence import save_world_state

        instance = self._world_manager.get_world(world_id)
        if not instance:
            logger.error(f"Cannot save world {world_id[:8]}: not found")
            return None

        try:
            metadata = {
                "name": instance.name,
                "description": instance.description,
                "world_type": instance.world_type,
            }
            result = save_world_state(world_id, instance.runner, metadata=metadata)
            if result:
                logger.info(f"Manual save completed for world {world_id[:8]}")
            return result

        except Exception as e:
            logger.error(f"Error saving world {world_id[:8]}: {e}", exc_info=True)
            return None

    async def save_all_now(self) -> int:
        """Save all persistent worlds immediately.

        Returns:
            Number of worlds successfully saved
        """
        saved_count = 0

        for instance in self._world_manager:
            if not instance.persistent:
                continue

            result = await self.save_world_now(instance.world_id)
            if result:
                saved_count += 1

        logger.info(f"Saved {saved_count} persistent worlds")
        return saved_count

    async def save_all_on_shutdown(self) -> int:
        """Save all persistent worlds before shutdown.

        This should be called during graceful shutdown to ensure
        world state is persisted.

        Returns:
            Number of worlds successfully saved
        """
        logger.info("Saving all worlds before shutdown...")
        saved_count = await self.save_all_now()
        logger.info(f"Shutdown save complete: {saved_count} worlds saved")
        return saved_count
