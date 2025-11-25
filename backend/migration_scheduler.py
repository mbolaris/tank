"""Background scheduler for automated tank migrations."""

import asyncio
import logging
import random
from typing import Optional

from backend.connection_manager import ConnectionManager
from backend.tank_registry import TankRegistry
from core.entities import Fish
from core.entities.fractal_plant import FractalPlant

logger = logging.getLogger(__name__)


class MigrationScheduler:
    """Schedules and executes automated entity migrations between tanks."""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        tank_registry: TankRegistry,
        check_interval: float = 10.0,
    ):
        """Initialize the migration scheduler.
        
        Args:
            connection_manager: Manager for tank connections
            tank_registry: Registry of all tanks
            check_interval: Seconds between migration checks (default: 10)
        """
        self.connection_manager = connection_manager
        self.tank_registry = tank_registry
        self.check_interval = check_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(f"MigrationScheduler initialized (check_interval={check_interval}s)")
    
    async def start(self) -> None:
        """Start the migration scheduler."""
        if self._running:
            logger.warning("Migration scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="migration_scheduler")
        logger.info("Migration scheduler started")
    
    async def stop(self) -> None:
        """Stop the migration scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Migration scheduler stopped")
    
    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        logger.info("Migration scheduler loop started")
        check_count = 0
        
        try:
            while self._running:
                try:
                    check_count += 1
                    connections = self.connection_manager.list_connections()
                    
                    if check_count % 6 == 0:  # Log every ~60 seconds
                        logger.debug(
                            f"Migration check #{check_count}: {len(connections)} active connections"
                        )
                    
                    for connection in connections:
                        try:
                            await self._check_migration(connection)
                        except Exception as e:
                            logger.error(
                                f"Error checking migration for connection {connection.id}: {e}",
                                exc_info=True,
                            )
                    
                    await asyncio.sleep(self.check_interval)
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in migration scheduler loop: {e}", exc_info=True)
                    await asyncio.sleep(self.check_interval)
        
        except asyncio.CancelledError:
            logger.info("Migration scheduler loop cancelled")
        finally:
            logger.info(f"Migration scheduler loop ended after {check_count} checks")
    
    async def _check_migration(self, connection) -> None:
        """Check if a migration should occur for a connection.
        
        Args:
            connection: The TankConnection to check
        """
        # Roll the dice
        roll = random.randint(1, 100)
        if roll > connection.probability:
            return  # No migration this time
        
        # Get source and destination tanks
        source_manager = self.tank_registry.get_tank(connection.source_tank_id)
        dest_manager = self.tank_registry.get_tank(connection.destination_tank_id)
        
        if not source_manager or not dest_manager:
            logger.warning(
                f"Migration failed: tank not found (source={connection.source_tank_id[:8]}, "
                f"dest={connection.destination_tank_id[:8]})"
            )
            return
        
        # Check if both tanks allow transfers
        if not source_manager.tank_info.allow_transfers:
            return
        if not dest_manager.tank_info.allow_transfers:
            return
        
        # Get eligible entities (fish and plants)
        eligible_entities = []
        for entity in source_manager.world.entities_list:
            if isinstance(entity, (Fish, FractalPlant)):
                eligible_entities.append(entity)
        
        if not eligible_entities:
            return  # No entities to migrate
        
        # Select random entity
        entity = random.choice(eligible_entities)
        entity_id = id(entity)
        entity_type = "fish" if isinstance(entity, Fish) else "plant"
        
        # Perform the migration
        try:
            from backend.entity_transfer import serialize_entity_for_transfer, deserialize_entity
            from backend.transfer_history import log_transfer
            
            # Serialize entity
            entity_data = serialize_entity_for_transfer(entity)
            if entity_data is None:
                logger.warning(f"Cannot serialize {entity_type} for migration")
                return
            
            # Remove from source
            source_manager.world.engine.remove_entity(entity)
            
            # Add to destination
            new_entity = deserialize_entity(entity_data, dest_manager.world)
            if new_entity is None:
                # Failed - try to restore
                restored = deserialize_entity(entity_data, source_manager.world)
                if restored:
                    source_manager.world.engine.add_entity(restored)
                
                log_transfer(
                    entity_type=entity_type,
                    entity_old_id=entity_id,
                    entity_new_id=None,
                    source_tank_id=connection.source_tank_id,
                    source_tank_name=source_manager.tank_info.name,
                    destination_tank_id=connection.destination_tank_id,
                    destination_tank_name=dest_manager.tank_info.name,
                    success=False,
                    error="Failed to deserialize in destination",
                )
                return
            
            dest_manager.world.engine.add_entity(new_entity)
            
            # Log successful migration
            log_transfer(
                entity_type=entity_type,
                entity_old_id=entity_id,
                entity_new_id=id(new_entity),
                source_tank_id=connection.source_tank_id,
                source_tank_name=source_manager.tank_info.name,
                destination_tank_id=connection.destination_tank_id,
                destination_tank_name=dest_manager.tank_info.name,
                success=True,
            )
            
            logger.info(
                f"Migrated {entity_type} from {source_manager.tank_info.name} to "
                f"{dest_manager.tank_info.name} (probability={connection.probability}%)"
            )
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
