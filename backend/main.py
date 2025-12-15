"""FastAPI backend for fish tank simulation."""

import asyncio
import json
import os
import platform
import socket
import sys
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.logging_config import configure_logging
from backend.security import setup_security_middleware

# Add parent directory to path so we can import from root tank/ directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.models import Command, ServerInfo
from backend.server_client import ServerClient
from backend.simulation_manager import SimulationManager
from backend.tank_registry import TankRegistry
from core.constants import DEFAULT_API_PORT, FRAME_RATE

# Configure logging once for the backend stack (includes uvicorn)
logger = configure_logging(extra_loggers=("backend",))

# Windows-specific asyncio configuration
if platform.system() == "Windows":
    logger.info("Windows detected - configuring asyncio event loop policy")
    try:
        # Use ProactorEventLoop on Windows for better compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Set WindowsProactorEventLoopPolicy for asyncio")
    except Exception as e:
        logger.warning(f"Could not set Windows event loop policy: {e}")

# Global tank registry - manages multiple tank simulations for Tank World Net
# Note: create_default=False because we'll restore from snapshots first
tank_registry = TankRegistry(create_default=False)

# Connection manager for tank migrations
connection_manager = ConnectionManager()

# Discovery service for distributed server networking
discovery_service = DiscoveryService()

# Server client for server-to-server communication
server_client = ServerClient()

# Migration scheduler for automated entity migrations
from backend.migration_scheduler import MigrationScheduler

migration_scheduler: Optional[MigrationScheduler] = None  # Will be initialized in lifespan

# Auto-save service for periodic tank state persistence
from backend.auto_save_service import AutoSaveService
from backend.startup_manager import StartupManager

auto_save_service: Optional[AutoSaveService] = None  # Will be initialized in lifespan

# Backwards-compatible aliases for the default tank (will be set after tank restoration)
simulation_manager = None
simulation = None
connected_clients = None

# Server metadata (can be overridden by environment variables)
SERVER_ID = os.getenv("TANK_SERVER_ID", "local-server")  # Local server ID
SERVER_VERSION = "1.0.0"  # Server version
_server_start_time = time.time()  # Track server uptime

# Startup manager for clean initialization/shutdown
startup_manager: Optional[StartupManager] = None

# Production settings
PRODUCTION_MODE = os.getenv("PRODUCTION", "false").lower() == "true"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")  # Comma-separated list

# Allow port override for testing multiple servers
_api_port_override = os.getenv("TANK_API_PORT")
if _api_port_override:
    DEFAULT_API_PORT = int(_api_port_override)

# Discovery hub configuration
DISCOVERY_SERVER_URL = os.getenv("DISCOVERY_SERVER_URL")  # e.g., "http://192.168.1.10:8000"


def _get_network_ip() -> str:
    """Get the network IP address of this machine.

    Returns:
        Network IP address, or "localhost" if unable to determine
    """
    try:
        # Create a socket and connect to an external address to determine local IP
        # This doesn't actually send data, just determines which interface would be used
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        # Fallback to localhost if we can't determine network IP
        logger.debug(f"Could not determine network IP: {e}")
        return "localhost"


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


def get_server_info() -> ServerInfo:
    """Get information about the current server."""

    uptime = time.time() - _server_start_time

    # Try to get resource usage (optional)
    cpu_percent = None
    memory_mb = None
    logical_cpus = os.cpu_count()
    physical_cpus = None
    try:
        import psutil

        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_mb = process.memory_info().rss / 1024 / 1024  # Convert bytes to MB
        physical_cpus = psutil.cpu_count(logical=False)
        if physical_cpus is None:
            physical_cpus = logical_cpus
    except ImportError:
        # psutil not available - that's okay
        pass
    except Exception as e:
        logger.debug(f"Could not get resource usage: {e}")

    return ServerInfo(
        server_id=SERVER_ID,
        hostname=socket.gethostname(),
        host=_get_network_ip(),  # Use actual network IP for distributed setups
        port=DEFAULT_API_PORT,
        status="online",
        tank_count=tank_registry.tank_count,
        version=SERVER_VERSION,
        uptime_seconds=uptime,
        cpu_percent=cpu_percent,
        memory_mb=memory_mb,
        is_local=True,
        platform=platform.system(),
        architecture=platform.machine(),
        hardware_model=platform.processor() or None,
        logical_cpus=logical_cpus,
        physical_cpus=physical_cpus,
    )


# Note: _heartbeat_loop and _heartbeat_task now managed by StartupManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown.

    Now uses StartupManager for clean separation of concerns and better testability.
    """
    global startup_manager, auto_save_service, migration_scheduler
    global simulation_manager, simulation, connected_clients

    try:
        # Create and initialize startup manager
        startup_manager = StartupManager(
            tank_registry=tank_registry,
            connection_manager=connection_manager,
            discovery_service=discovery_service,
            server_client=server_client,
            server_id=SERVER_ID,
            discovery_server_url=DISCOVERY_SERVER_URL,
            start_broadcast_callback=start_broadcast_for_tank,
            stop_broadcast_callback=stop_broadcast_for_tank,
        )

        # Perform all initialization steps
        await startup_manager.initialize(get_server_info_callback=get_server_info)

        # Update backwards-compatible aliases
        simulation_manager = tank_registry.default_tank
        if simulation_manager:
            simulation = simulation_manager.runner
            connected_clients = simulation_manager.connected_clients
            logger.info(f"Default tank set: {simulation_manager.tank_id[:8]}")

        # Update global references to services
        auto_save_service = startup_manager.auto_save_service
        migration_scheduler = startup_manager.migration_scheduler

        # Setup API routers (must be done after all dependencies are initialized)
        logger.info("Setting up API routers...")
        try:
            setup_routers()
            logger.info("API routers configured successfully")
        except Exception as e:
            logger.error(f"Failed to setup API routers: {e}", exc_info=True)
            raise  # Fatal - routers are required for API functionality

        logger.info("LIFESPAN: Startup complete - yielding control to app")
        yield
        logger.info("LIFESPAN: Received shutdown signal")

    except Exception as e:
        logger.error(f"Exception in lifespan startup: {e}", exc_info=True)
        raise
    finally:
        # Shutdown using startup manager
        if startup_manager:
            await startup_manager.shutdown()


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Fish Tank Simulation API",
    lifespan=lifespan,
    docs_url=None if PRODUCTION_MODE else "/docs",  # Disable docs in production
    redoc_url=None if PRODUCTION_MODE else "/redoc",
)

# Add CORS middleware (environment-aware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if PRODUCTION_MODE else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add security middleware (rate limiting, security headers)
setup_security_middleware(app, enable_rate_limiting=PRODUCTION_MODE)


# =============================================================================
# Router Setup - Modular API organization
# =============================================================================

def setup_routers():
    """Setup and include all API routers after dependencies are initialized."""
    from backend.routers import discovery, servers, tanks, transfers

    # Setup discovery router
    discovery_router = discovery.setup_router(discovery_service)
    app.include_router(discovery_router)

    # Setup transfers router
    transfers_router = transfers.setup_router(tank_registry, connection_manager)
    app.include_router(transfers_router)

    # Setup tanks router
    tanks_router = tanks.setup_router(
        tank_registry=tank_registry,
        server_id=SERVER_ID,
        start_broadcast_callback=start_broadcast_for_tank,
        stop_broadcast_callback=stop_broadcast_for_tank,
        auto_save_service=auto_save_service,
    )
    app.include_router(tanks_router)

    # Setup servers router
    servers_router = servers.setup_router(
        tank_registry=tank_registry,
        discovery_service=discovery_service,
        server_client=server_client,
        get_server_info_callback=get_server_info,
    )
    app.include_router(servers_router)

    logger.info("All API routers configured successfully")


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


# =============================================================================
# Helper Functions for Transfer Operations
# =============================================================================


def log_transfer_success(
    entity_data: Dict[str, Any],
    old_id: int,
    new_id: int,
    source_tank_id: str,
    source_tank_name: str,
    dest_tank_id: str,
    dest_tank_name: str,
) -> None:
    """Log a successful entity transfer.

    Args:
        entity_data: Serialized entity data
        old_id: Original entity ID
        new_id: New entity ID in destination tank
        source_tank_id: Source tank identifier
        source_tank_name: Source tank name
        dest_tank_id: Destination tank identifier
        dest_tank_name: Destination tank name
    """
    from backend.transfer_history import log_transfer

    log_transfer(
        entity_type=entity_data.get("type", "unknown"),
        entity_old_id=old_id,
        entity_new_id=new_id,
        source_tank_id=source_tank_id,
        source_tank_name=source_tank_name,
        destination_tank_id=dest_tank_id,
        destination_tank_name=dest_tank_name,
        success=True,
    )


def log_transfer_failure(
    entity_data: Dict[str, Any],
    old_id: int,
    source_tank_id: str,
    source_tank_name: str,
    dest_tank_id: str,
    dest_tank_name: str,
    error: str,
) -> None:
    """Log a failed entity transfer.

    Args:
        entity_data: Serialized entity data
        old_id: Original entity ID
        source_tank_id: Source tank identifier
        source_tank_name: Source tank name
        dest_tank_id: Destination tank identifier
        dest_tank_name: Destination tank name
        error: Error message describing the failure
    """
    from backend.transfer_history import log_transfer

    log_transfer(
        entity_type=entity_data.get("type", "unknown"),
        entity_old_id=old_id,
        entity_new_id=None,
        source_tank_id=source_tank_id,
        source_tank_name=source_tank_name,
        destination_tank_id=dest_tank_id,
        destination_tank_name=dest_tank_name,
        success=False,
        error=error,
    )


# =============================================================================
# API Endpoints
# =============================================================================


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


# =============================================================================

# =============================================================================
# NOTE: Discovery, Transfer, Tank, and Server endpoints now in backend/routers/
# - Discovery: backend/routers/discovery.py
# - Transfers: backend/routers/transfers.py
# - Tanks: backend/routers/tanks.py
# - Servers: backend/routers/servers.py
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
    if not simulation:
        return []
    return simulation.get_full_evaluation_history()


@app.get("/api/evolution-benchmark")
async def get_evolution_benchmark():
    """Get evolution benchmark tracking data.

    Returns longitudinal tracking data for poker skill evolution including:
    - history: List of benchmark snapshots over time
    - improvement: Metrics showing skill progression
    - latest: Most recent benchmark snapshot

    This measures pure poker playing strength vs baseline opponents,
    independent of ecosystem dynamics.
    """
    if not simulation:
        return JSONResponse(
            {"status": "not_available", "history": [], "improvement": {}, "latest": None}
        )
    return JSONResponse(simulation.get_evolution_benchmark_data())


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
    import logging

    import uvicorn

    # Reduce noisy access logs from Uvicorn (e.g. "GET /... 200 OK").
    # `access_log=False` disables the default access logs and we also set
    # the `uvicorn.access` logger to WARNING to be extra sure.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_API_PORT, access_log=False)
