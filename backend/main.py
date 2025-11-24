"""FastAPI backend for fish tank simulation."""

import asyncio
import json
import logging
import platform
import sys
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Dict, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Set up logging with more detail
logging.basicConfig(
    level=logging.INFO,  # Changed to INFO to reduce log noise
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)

# Windows-specific asyncio configuration
if platform.system() == "Windows":
    logger.info("Windows detected - configuring asyncio event loop policy")
    try:
        # Use ProactorEventLoop on Windows for better compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Set WindowsProactorEventLoopPolicy for asyncio")
    except Exception as e:
        logger.warning(f"Could not set Windows event loop policy: {e}")

# Add parent directory to path so we can import from root tank/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models import Command
from backend.simulation_manager import SimulationManager
from backend.tank_registry import TankRegistry, CreateTankRequest
from core.constants import DEFAULT_API_PORT, FRAME_RATE

# Global tank registry - manages multiple tank simulations for Tank World Net
tank_registry = TankRegistry(create_default=True)

# Backwards-compatible aliases for the default tank
simulation_manager = tank_registry.default_tank
simulation = simulation_manager.runner
connected_clients = simulation_manager.connected_clients


def _handle_task_exception(task: asyncio.Task) -> None:
    """Handle exceptions from background tasks."""
    try:
        exc = task.exception()
        if exc is not None:
            logger.error(
                f"Unhandled exception in task {task.get_name()}: {exc}",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
    except asyncio.CancelledError:
        logger.debug(f"Task {task.get_name()} was cancelled")
    except Exception as e:
        logger.error(f"Error getting task exception: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    try:
        # Startup
        logger.info("=" * 60)
        logger.info("LIFESPAN STARTUP: Beginning initialization")
        logger.info(f"Platform: {platform.system()} {platform.release()}")
        logger.info(f"Python: {sys.version}")
        logger.info(f"Tank registry has {tank_registry.tank_count} tank(s)")
        logger.info("=" * 60)

        # Start all tanks in the registry
        logger.info("Starting all tank simulations...")
        try:
            for manager in tank_registry:
                manager.start(start_paused=True)
                logger.info(f"Tank {manager.tank_id[:8]} started")
        except Exception as e:
            logger.error(f"Failed to start simulations: {e}", exc_info=True)
            raise

        # Start broadcast tasks for all tanks
        logger.info("Starting broadcast tasks...")
        try:
            for manager in tank_registry:
                await start_broadcast_for_tank(manager)
                logger.info(f"Broadcast task started for tank {manager.tank_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to start broadcast tasks: {e}", exc_info=True)
            raise

        logger.info("LIFESPAN STARTUP: Complete - yielding control to app")
        yield
        logger.info("LIFESPAN SHUTDOWN: Received shutdown signal")

    except Exception as e:
        logger.error(f"Exception in lifespan startup: {e}", exc_info=True)
        raise
    finally:
        # Shutdown
        logger.info("LIFESPAN SHUTDOWN: Cleaning up resources...")

        # Stop all broadcast tasks
        logger.info("Stopping broadcast tasks...")
        for tank_id in list(_broadcast_tasks.keys()):
            try:
                await stop_broadcast_for_tank(tank_id)
                logger.info(f"Broadcast task stopped for tank {tank_id[:8]}")
            except Exception as e:
                logger.error(f"Error stopping broadcast for tank {tank_id[:8]}: {e}", exc_info=True)

        # Stop all simulations
        logger.info("Stopping all simulations...")
        try:
            tank_registry.stop_all()
            logger.info("All simulations stopped!")
        except Exception as e:
            logger.error(f"Error stopping simulations: {e}", exc_info=True)

        logger.info("LIFESPAN SHUTDOWN: Complete")
        logger.info("=" * 60)


# Create FastAPI app with lifespan handler
app = FastAPI(title="Fish Tank Simulation API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_updates_for_tank(manager: SimulationManager):
    """Broadcast simulation updates to all clients connected to a specific tank.

    Args:
        manager: The SimulationManager to broadcast updates for
    """
    tank_id = manager.tank_id
    logger.info("broadcast_updates[%s]: Task started", tank_id[:8])

    # Unpause simulation now that broadcast task is ready
    # This prevents initial fish from aging before the frontend sees them
    manager.world.paused = False
    logger.info("broadcast_updates[%s]: Simulation unpaused", tank_id[:8])

    frame_count = 0
    last_sent_frame = -1

    try:
        while True:
            try:
                frame_count += 1
                clients = manager.connected_clients

                if clients:
                    if frame_count % 60 == 0:  # Log every 60 frames (~2 seconds)
                        logger.debug(
                            "broadcast_updates[%s]: Frame %d, clients: %d",
                            tank_id[:8],
                            frame_count,
                            len(clients),
                        )

                    try:
                        # Get current state (delta compression handled by manager)
                        state = await manager.get_state_async()
                    except Exception as e:
                        logger.error(
                            "broadcast_updates[%s]: Error getting simulation state: %s",
                            tank_id[:8],
                            e,
                            exc_info=True,
                        )
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    if state.frame == last_sent_frame:
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    last_sent_frame = state.frame

                    try:
                        serialize_start = time.perf_counter()
                        state_payload = manager.serialize_state(state)
                        serialize_ms = (time.perf_counter() - serialize_start) * 1000
                        if serialize_ms > 10:
                            logger.warning(
                                "broadcast_updates[%s]: Serialization exceeded budget %.2f ms (frame %s)",
                                tank_id[:8],
                                serialize_ms,
                                state.frame,
                            )
                    except Exception as e:
                        logger.error(
                            "broadcast_updates[%s]: Error serializing state to JSON: %s",
                            tank_id[:8],
                            e,
                            exc_info=True,
                        )
                        await asyncio.sleep(1 / FRAME_RATE)
                        continue

                    # Broadcast to all clients of this tank
                    disconnected = set()
                    send_start = time.perf_counter()
                    for client in list(clients):  # Copy to avoid modification during iteration
                        try:
                            await client.send_bytes(state_payload)
                        except Exception as e:
                            logger.warning(
                                "broadcast_updates[%s]: Error sending to client, marking for removal: %s",
                                tank_id[:8],
                                e,
                            )
                            disconnected.add(client)

                    send_ms = (time.perf_counter() - send_start) * 1000
                    if send_ms > 100:
                        logger.warning(
                            "broadcast_updates[%s]: Broadcasting to %s clients took %.2f ms",
                            tank_id[:8],
                            len(clients),
                            send_ms,
                        )

                    # Remove disconnected clients
                    if disconnected:
                        logger.info(
                            "broadcast_updates[%s]: Removing %d disconnected clients",
                            tank_id[:8],
                            len(disconnected),
                        )
                        clients.difference_update(disconnected)

            except asyncio.CancelledError:
                logger.info("broadcast_updates[%s]: Task cancelled", tank_id[:8])
                raise
            except Exception as e:
                logger.error(
                    "broadcast_updates[%s]: Unexpected error in main loop: %s",
                    tank_id[:8],
                    e,
                    exc_info=True,
                )
                # Continue running even if there's an error
                await asyncio.sleep(1 / FRAME_RATE)
                continue

            # Wait for next frame
            try:
                await asyncio.sleep(1 / FRAME_RATE)
            except asyncio.CancelledError:
                logger.info("broadcast_updates[%s]: Task cancelled during sleep", tank_id[:8])
                raise

    except asyncio.CancelledError:
        logger.info("broadcast_updates[%s]: Task cancelled (outer handler)", tank_id[:8])
        raise
    except Exception as e:
        logger.error(
            "broadcast_updates[%s]: Fatal error, task exiting: %s",
            tank_id[:8],
            e,
            exc_info=True,
        )
        raise
    finally:
        logger.info("broadcast_updates[%s]: Task ended", tank_id[:8])


# Track broadcast tasks per tank
_broadcast_tasks: Dict[str, asyncio.Task] = {}
# Locks to prevent race conditions when creating broadcast tasks
_broadcast_locks: Dict[str, asyncio.Lock] = {}


async def start_broadcast_for_tank(manager: SimulationManager) -> asyncio.Task:
    """Start a broadcast task for a tank.

    Args:
        manager: The SimulationManager to broadcast for

    Returns:
        The asyncio Task for the broadcast loop
    """
    tank_id = manager.tank_id

    # Create lock for this tank if it doesn't exist
    if tank_id not in _broadcast_locks:
        _broadcast_locks[tank_id] = asyncio.Lock()

    async with _broadcast_locks[tank_id]:
        # Check again inside the lock to avoid creating duplicate tasks
        if tank_id in _broadcast_tasks and not _broadcast_tasks[tank_id].done():
            return _broadcast_tasks[tank_id]

        task = asyncio.create_task(
            broadcast_updates_for_tank(manager),
            name=f"broadcast_{tank_id[:8]}",
        )
        task.add_done_callback(_handle_task_exception)
        _broadcast_tasks[tank_id] = task
        return task


async def stop_broadcast_for_tank(tank_id: str) -> None:
    """Stop the broadcast task for a tank.

    Args:
        tank_id: The tank ID to stop broadcasting for
    """
    task = _broadcast_tasks.pop(tank_id, None)
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@app.get("/")
async def root():
    """Root endpoint."""
    return JSONResponse(
        {
            "message": "Fish Tank Simulation API - Tank World Net",
            "version": "2.0.0",
            "tank_count": tank_registry.tank_count,
            "default_tank_id": tank_registry.default_tank_id,
            "endpoints": {
                "websocket": "/ws",
                "websocket_tank": "/ws/{tank_id}",
                "health": "/health",
                "tanks": "/api/tanks",
                "tank_info": "/api/tank/info",
            },
        }
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    stats = await simulation.get_state_async(force_full=True, allow_delta=False)
    return JSONResponse(
        {
            "status": "healthy",
            "simulation_running": simulation.running,
            "frame": stats.frame,
            "population": stats.stats.population,
        }
    )


@app.get("/api/tank/info")
async def get_tank_info():
    """Get information about the default tank.

    Returns tank metadata for network registration and discovery.
    This endpoint is kept for backwards compatibility.
    """
    return JSONResponse(simulation_manager.get_status())


# =============================================================================
# Tank World Net - Multi-Tank API Endpoints
# =============================================================================


@app.get("/api/tanks")
async def list_tanks(include_private: bool = False):
    """List all tanks in the registry.

    Args:
        include_private: If True, include non-public tanks

    Returns:
        List of tank status objects
    """
    tanks = tank_registry.list_tanks(include_private=include_private)
    return JSONResponse({
        "tanks": tanks,
        "count": len(tanks),
        "default_tank_id": tank_registry.default_tank_id,
    })


@app.post("/api/tanks")
async def create_tank(
    name: str,
    description: str = "",
    seed: Optional[int] = None,
    owner: Optional[str] = None,
    is_public: bool = True,
    allow_transfers: bool = False,
):
    """Create a new tank simulation.

    Args:
        name: Human-readable name for the tank
        description: Description of the tank
        seed: Optional random seed for deterministic behavior
        owner: Optional owner identifier
        is_public: Whether the tank is publicly visible
        allow_transfers: Whether to allow entity transfers

    Returns:
        The created tank's status
    """
    try:
        manager = tank_registry.create_tank(
            name=name,
            description=description,
            seed=seed,
            owner=owner,
            is_public=is_public,
            allow_transfers=allow_transfers,
        )

        # Start the simulation
        manager.start(start_paused=True)

        # Start broadcast task for the new tank
        await start_broadcast_for_tank(manager)

        logger.info(f"Created new tank via API: {manager.tank_id[:8]} ({name})")

        return JSONResponse(manager.get_status(), status_code=201)
    except Exception as e:
        logger.error(f"Error creating tank: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/tanks/{tank_id}")
async def get_tank(tank_id: str):
    """Get information about a specific tank.

    Args:
        tank_id: The unique tank identifier

    Returns:
        Tank status or 404 if not found
    """
    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse(
            {"error": f"Tank not found: {tank_id}"},
            status_code=404,
        )
    return JSONResponse(manager.get_status())


@app.post("/api/tanks/{tank_id}/pause")
async def pause_tank(tank_id: str):
    """Pause a running tank simulation."""

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)
    if not manager.running:
        return JSONResponse({"error": "Tank is not running"}, status_code=400)

    manager.world.paused = True
    return JSONResponse(manager.get_status())


@app.post("/api/tanks/{tank_id}/resume")
async def resume_tank(tank_id: str):
    """Resume a paused tank simulation."""

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)
    if not manager.running:
        return JSONResponse({"error": "Tank is not running"}, status_code=400)

    manager.world.paused = False

    # Ensure broadcast task exists for this tank
    if manager.tank_id not in _broadcast_tasks or _broadcast_tasks[manager.tank_id].done():
        await start_broadcast_for_tank(manager)

    return JSONResponse(manager.get_status())


@app.post("/api/tanks/{tank_id}/start")
async def start_tank(tank_id: str):
    """Start a stopped tank simulation."""

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

    if not manager.running:
        manager.start(start_paused=False)

    if manager.tank_id not in _broadcast_tasks or _broadcast_tasks[manager.tank_id].done():
        await start_broadcast_for_tank(manager)

    return JSONResponse(manager.get_status())


@app.post("/api/tanks/{tank_id}/stop")
async def stop_tank(tank_id: str):
    """Stop a running tank simulation and its broadcast task."""

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

    await stop_broadcast_for_tank(tank_id)

    if manager.running:
        manager.stop()

    manager.world.paused = True

    return JSONResponse(manager.get_status())


@app.post("/api/tanks/{source_tank_id}/transfer")
async def transfer_entity(source_tank_id: str, entity_id: int, destination_tank_id: str):
    """Transfer an entity from one tank to another.

    Args:
        source_tank_id: The tank ID containing the entity
        entity_id: The entity ID to transfer
        destination_tank_id: The tank ID to transfer to

    Returns:
        Success message with entity data, or error if transfer fails
    """
    from backend.entity_transfer import serialize_entity_for_transfer, deserialize_entity

    # Get source tank
    source_manager = tank_registry.get_tank(source_tank_id)
    if source_manager is None:
        return JSONResponse({"error": f"Source tank not found: {source_tank_id}"}, status_code=404)

    # Get destination tank
    dest_manager = tank_registry.get_tank(destination_tank_id)
    if dest_manager is None:
        return JSONResponse({"error": f"Destination tank not found: {destination_tank_id}"}, status_code=404)

    # Check if source tank allows transfers
    if not source_manager.tank_info.allow_transfers:
        return JSONResponse(
            {"error": f"Tank '{source_manager.tank_info.name}' does not allow entity transfers"},
            status_code=403,
        )

    # Check if destination tank allows transfers
    if not dest_manager.tank_info.allow_transfers:
        return JSONResponse(
            {"error": f"Tank '{dest_manager.tank_info.name}' does not allow entity transfers"},
            status_code=403,
        )

    # Find entity in source tank
    source_entity = None
    for entity in source_manager.world.engine.entities_list:
        if entity.id == entity_id:
            source_entity = entity
            break

    if source_entity is None:
        return JSONResponse({"error": f"Entity not found in source tank: {entity_id}"}, status_code=404)

    # Serialize entity
    entity_data = serialize_entity_for_transfer(source_entity)
    if entity_data is None:
        return JSONResponse(
            {"error": f"Entity type {type(source_entity).__name__} cannot be transferred"},
            status_code=400,
        )

    try:
        # Remove from source tank
        source_manager.world.engine.remove_entity(source_entity)
        logger.info(f"Removed entity {entity_id} from tank {source_tank_id[:8]}")

        # Deserialize and add to destination tank
        new_entity = deserialize_entity(entity_data, dest_manager.world)
        if new_entity is None:
            # Transfer failed - try to restore to source tank
            restored_entity = deserialize_entity(entity_data, source_manager.world)
            if restored_entity:
                source_manager.world.engine.add_entity(restored_entity)
            return JSONResponse(
                {"error": "Failed to deserialize entity in destination tank"},
                status_code=500,
            )

        dest_manager.world.engine.add_entity(new_entity)
        logger.info(f"Added entity {new_entity.id} to tank {destination_tank_id[:8]} (was {entity_id})")

        return JSONResponse({
            "success": True,
            "message": f"Entity transferred successfully",
            "entity": {
                "old_id": entity_id,
                "new_id": new_entity.id,
                "type": entity_data["type"],
                "source_tank": source_tank_id,
                "destination_tank": destination_tank_id,
            },
        })
    except Exception as e:
        logger.error(f"Transfer failed: {e}", exc_info=True)
        return JSONResponse(
            {"error": f"Transfer failed: {str(e)}"},
            status_code=500,
        )


@app.delete("/api/tanks/{tank_id}")
async def delete_tank(tank_id: str):
    """Delete a tank from the registry.

    Args:
        tank_id: The tank ID to delete

    Returns:
        Success message or 404 if not found
    """
    # Don't allow deleting the default tank
    if tank_id == tank_registry.default_tank_id and tank_registry.tank_count == 1:
        return JSONResponse(
            {"error": "Cannot delete the last remaining tank"},
            status_code=400,
        )

    # Stop broadcast first
    await stop_broadcast_for_tank(tank_id)

    # Remove from registry
    if tank_registry.remove_tank(tank_id):
        logger.info(f"Deleted tank via API: {tank_id[:8]}")
        return JSONResponse({"message": f"Tank {tank_id} deleted"})
    else:
        return JSONResponse(
            {"error": f"Tank not found: {tank_id}"},
            status_code=404,
        )


@app.get("/api/tanks/{tank_id}/lineage")
async def get_tank_lineage(tank_id: str):
    """Get phylogenetic lineage data for a specific tank.

    Args:
        tank_id: The tank ID to get lineage for

    Returns:
        List of lineage records or 404 if tank not found
    """
    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse(
            {"error": f"Tank not found: {tank_id}"},
            status_code=404,
        )

    try:
        from core.entities import Fish
        alive_fish_ids = {
            fish.fish_id for fish in manager.world.entities_list
            if isinstance(fish, Fish)
        }
        lineage_data = manager.world.ecosystem.get_lineage_data(alive_fish_ids)
        return JSONResponse(lineage_data)
    except Exception as e:
        logger.error(f"Error getting lineage data for tank {tank_id[:8]}: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/tanks/{tank_id}/snapshot")
async def get_tank_snapshot(tank_id: str):
    """Get a single state snapshot for a tank (for thumbnails).
    
    Args:
        tank_id: The tank ID to get snapshot for
        
    Returns:
        Current simulation state or 404 if tank not found
    """
    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse(
            {"error": f"Tank not found: {tank_id}"},
            status_code=404,
        )
    
    try:
        # Get current state (force full state, no delta)
        state = manager.get_state(force_full=True, allow_delta=False)
        return JSONResponse(state.to_dict())
    except Exception as e:
        logger.error(f"Error getting snapshot for tank {tank_id[:8]}: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# =============================================================================
# Legacy Endpoints (for backwards compatibility)
# =============================================================================


@app.get("/api/lineage")
async def get_lineage():
    """Get phylogenetic lineage data for all fish.

    Returns:
        List of lineage records with parent-child relationships for tree visualization
    """
    try:
        # Get alive fish IDs from current entities
        from core.entities import Fish
        alive_fish_ids = {
            fish.fish_id for fish in simulation.world.entities_list
            if isinstance(fish, Fish)
        }

        # Get lineage data from ecosystem manager with alive status
        lineage_data = simulation.world.ecosystem.get_lineage_data(alive_fish_ids)
        logger.info(f"Lineage API: Returning {len(lineage_data)} lineage records ({len(alive_fish_ids)} alive)")
        if len(lineage_data) == 0:
            logger.warning("Lineage API: lineage_log is empty! This should contain records for all fish ever born.")
            logger.warning(
                f"Lineage API: Current stats - total_births: {simulation.world.ecosystem.total_births}, "
                f"next_fish_id: {simulation.world.ecosystem.next_fish_id}"
            )
        return JSONResponse(lineage_data)
    except Exception as e:
        logger.error(f"Error getting lineage data: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def handle_websocket_connection(websocket: WebSocket, manager: SimulationManager):
    """Handle a WebSocket connection for a specific tank.

    Args:
        websocket: The WebSocket connection
        manager: The SimulationManager for this connection
    """
    client_id = id(websocket)
    tank_id = manager.tank_id[:8]

    try:
        await websocket.accept()
        logger.info(f"WebSocket[{tank_id}]: Accepted connection from client {client_id}")
    except Exception as e:
        logger.error(f"WebSocket[{tank_id}]: Error accepting connection from client {client_id}: {e}", exc_info=True)
        return

    manager.add_client(websocket)
    logger.info(f"WebSocket[{tank_id}]: Client {client_id} added. Total clients: {manager.client_count}")

    try:
        while True:
            try:
                # Receive messages from client
                logger.debug(f"WebSocket[{tank_id}]: Waiting for message from client {client_id}")
                data = await websocket.receive_text()
                logger.debug(f"WebSocket[{tank_id}]: Received message from client {client_id}: {data[:100]}...")

                try:
                    # Parse command
                    command_data = json.loads(data)
                    command = Command(**command_data)
                    logger.info(f"WebSocket[{tank_id}]: Client {client_id} sent command: {command.command}")

                    # Handle command using the manager's runner
                    result = await manager.handle_command_async(command.command, command.data)

                    # Send response
                    if result is not None:
                        # Command returned a result (e.g., poker game state)
                        await websocket.send_json(result)
                    else:
                        # Send acknowledgment for commands that don't return data
                        await websocket.send_json(
                            {"type": "ack", "command": command.command, "status": "success"}
                        )
                    logger.debug(f"WebSocket[{tank_id}]: Sent response to client {client_id}")

                except json.JSONDecodeError as e:
                    logger.warning(f"WebSocket[{tank_id}]: Invalid JSON from client {client_id}: {e}")
                    await websocket.send_json({"type": "error", "message": f"Invalid JSON: {str(e)}"})
                except Exception as e:
                    logger.error(f"WebSocket[{tank_id}]: Error handling command from client {client_id}: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": str(e)})

            except WebSocketDisconnect:
                # Re-raise to be handled by outer exception handler
                raise
            except asyncio.CancelledError:
                logger.info(f"WebSocket[{tank_id}]: Connection cancelled for client {client_id}")
                raise
            except Exception as e:
                logger.error(f"WebSocket[{tank_id}]: Error in message loop for client {client_id}: {e}", exc_info=True)
                break

    except WebSocketDisconnect as e:
        disconnect_code = e.code if hasattr(e, 'code') else 'unknown'
        logger.info(f"WebSocket[{tank_id}]: Client {client_id} disconnected normally (code: {disconnect_code})")
    except Exception as e:
        logger.error(f"WebSocket[{tank_id}]: Unexpected error for client {client_id}: {e}", exc_info=True)
    finally:
        manager.remove_client(websocket)
        logger.info(f"WebSocket[{tank_id}]: Client {client_id} removed. Total clients: {manager.client_count}")


@app.get("/api/evaluation-history")
async def get_evaluation_history():
    """Get the full history of the evolution benchmark."""
    if not simulation_runner:
        return []
    return simulation_runner.get_full_evaluation_history()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for the default tank (backwards compatible)."""
    client_id = id(websocket)
    logger.info(f"WebSocket: New connection attempt from client {client_id} (default tank)")

    manager = tank_registry.default_tank
    if manager is None:
        logger.error(f"WebSocket: No default tank available for client {client_id}")
        await websocket.close(code=1011, reason="No default tank available")
        return

    await handle_websocket_connection(websocket, manager)


@app.websocket("/ws/{tank_id}")
async def websocket_tank_endpoint(websocket: WebSocket, tank_id: str):
    """WebSocket endpoint for a specific tank.

    Args:
        websocket: The WebSocket connection
        tank_id: The tank ID to connect to
    """
    client_id = id(websocket)
    logger.info(f"WebSocket: New connection attempt from client {client_id} for tank {tank_id[:8]}")

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        logger.warning(f"WebSocket: Tank {tank_id[:8]} not found for client {client_id}")
        await websocket.close(code=4004, reason=f"Tank not found: {tank_id}")
        return

    await handle_websocket_connection(websocket, manager)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_API_PORT)
