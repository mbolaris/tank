"""Auto-save service for periodic tank state persistence.

This module provides automatic background saving of tank states at
configured intervals, ensuring that simulations can be restored after
server restarts.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from backend.simulation_manager import SimulationManager
    from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)


class AutoSaveService:
    """Background service for auto-saving tank states.

    This service manages periodic saves for all persistent tanks
    in the registry, with configurable intervals per tank.
    """

    def __init__(self, tank_registry: "TankRegistry"):
        """Initialize the auto-save service.

        Args:
            tank_registry: The tank registry to monitor
        """
        self._tank_registry = tank_registry
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    async def start(self) -> None:
        """Start the auto-save service."""
        if self._running:
            logger.warning("Auto-save service already running")
            return

        self._running = True
        logger.info("Auto-save service started")

        # Start auto-save tasks for all persistent tanks
        for manager in self._tank_registry:
            if manager.tank_info.persistent:
                await self._start_tank_autosave(manager)

    async def stop(self) -> None:
        """Stop the auto-save service and cancel all tasks."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping auto-save service...")

        # Cancel all auto-save tasks
        for tank_id, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Auto-save task cancelled for tank {tank_id[:8]}")

        self._tasks.clear()
        logger.info("Auto-save service stopped")

    async def _start_tank_autosave(self, manager: "SimulationManager") -> None:
        """Start auto-save task for a specific tank.

        Args:
            manager: The SimulationManager to auto-save
        """
        tank_id = manager.tank_id

        if tank_id in self._tasks:
            logger.warning(f"Auto-save task already exists for tank {tank_id[:8]}")
            return

        task = asyncio.create_task(self._autosave_loop(manager), name=f"autosave_{tank_id[:8]}")
        self._tasks[tank_id] = task
        logger.info(
            f"Started auto-save for tank {tank_id[:8]} "
            f"(interval: {manager.tank_info.auto_save_interval}s)"
        )

    async def stop_tank_autosave(self, tank_id: str) -> None:
        """Stop auto-save task for a specific tank.

        Args:
            tank_id: The tank ID to stop auto-saving
        """
        task = self._tasks.pop(tank_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Auto-save task stopped for tank {tank_id[:8]}")

    async def _autosave_loop(self, manager: "SimulationManager") -> None:
        """Background loop for periodic tank saves.

        Args:
            manager: The SimulationManager to save
        """
        from backend.tank_persistence import cleanup_old_snapshots, save_snapshot_data

        tank_id = manager.tank_id
        interval = manager.tank_info.auto_save_interval
        loop = asyncio.get_running_loop()

        try:
            while self._running:
                # Wait for the configured interval
                await asyncio.sleep(interval)

                # Save the tank state
                try:
                    # 1. Capture state (fast, thread-safe, holds lock briefly)
                    snapshot = manager.capture_state_for_save()

                    if snapshot:
                        # 2. Write to disk (slow, run in thread pool to avoid blocking event loop)
                        snapshot_path = await loop.run_in_executor(
                            None, save_snapshot_data, tank_id, snapshot
                        )

                        if snapshot_path:
                            logger.info(f"Auto-saved tank {tank_id[:8]} to {snapshot_path}")

                            # Cleanup old snapshots (keep last 10)
                            # Also run in executor as it involves file I/O
                            deleted = await loop.run_in_executor(
                                None, cleanup_old_snapshots, tank_id, 10
                            )
                            if deleted > 0:
                                logger.debug(
                                    f"Cleaned up {deleted} old snapshots for tank {tank_id[:8]}"
                                )
                        else:
                            logger.error(f"Auto-save failed for tank {tank_id[:8]}")
                    else:
                        logger.warning(
                            f"Could not capture state for auto-save of tank {tank_id[:8]}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error during auto-save for tank {tank_id[:8]}: {e}", exc_info=True
                    )

        except asyncio.CancelledError:
            logger.info(f"Auto-save loop cancelled for tank {tank_id[:8]}")
            raise
        except Exception as e:
            logger.error(
                f"Fatal error in auto-save loop for tank {tank_id[:8]}: {e}", exc_info=True
            )

    async def save_tank_now(self, tank_id: str) -> Optional[str]:
        """Immediately save a specific tank (out of band).

        Args:
            tank_id: The tank ID to save

        Returns:
            Path to saved snapshot, or None if failed
        """
        from backend.tank_persistence import cleanup_old_snapshots, save_snapshot_data

        manager = self._tank_registry.get_tank(tank_id)
        if not manager:
            logger.error(f"Cannot save tank {tank_id[:8]}: not found")
            return None

        loop = asyncio.get_running_loop()

        try:
            # 1. Capture state
            snapshot = manager.capture_state_for_save()

            if snapshot:
                # 2. Write to disk in thread pool
                snapshot_path = await loop.run_in_executor(
                    None, save_snapshot_data, tank_id, snapshot
                )

                if snapshot_path:
                    logger.info(f"Manual save completed for tank {tank_id[:8]}")
                    await loop.run_in_executor(None, cleanup_old_snapshots, tank_id, 10)
                    return snapshot_path
                else:
                    logger.error(f"Manual save failed for tank {tank_id[:8]}")
                    return None
            else:
                logger.error(f"Manual save failed: could not capture state for tank {tank_id[:8]}")
                return None

        except Exception as e:
            logger.error(f"Error saving tank {tank_id[:8]}: {e}", exc_info=True)
            return None

    async def save_all_now(self) -> int:
        """Save all persistent tanks immediately.

        Returns:
            Number of tanks successfully saved
        """
        saved_count = 0

        for manager in self._tank_registry:
            if not manager.tank_info.persistent:
                continue

            result = await self.save_tank_now(manager.tank_id)
            if result:
                saved_count += 1

        logger.info(f"Saved {saved_count} persistent tanks")
        return saved_count
