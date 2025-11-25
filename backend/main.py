"""FastAPI backend for fish tank simulation."""

import asyncio
import json
import logging
import os
import platform
import socket
import sys
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Dict, Optional, Set, Any

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

from backend.models import Command, ServerInfo, ServerWithTanks
from backend.simulation_manager import SimulationManager
from backend.tank_registry import TankRegistry, CreateTankRequest
from backend.connection_manager import ConnectionManager, TankConnection
from backend.discovery_service import DiscoveryService
from backend.server_client import ServerClient
from core.constants import DEFAULT_API_PORT, FRAME_RATE

# Global tank registry - manages multiple tank simulations for Tank World Net
tank_registry = TankRegistry(create_default=True)

# Connection manager for tank migrations
connection_manager = ConnectionManager()

# Discovery service for distributed server networking
discovery_service = DiscoveryService()

# Server client for server-to-server communication
server_client = ServerClient()

# Migration scheduler for automated entity migrations
from backend.migration_scheduler import MigrationScheduler
migration_scheduler: Optional[MigrationScheduler] = None  # Will be initialized in lifespan

# Backwards-compatible aliases for the default tank
simulation_manager = tank_registry.default_tank
simulation = simulation_manager.runner
connected_clients = simulation_manager.connected_clients

# Server metadata (can be overridden by environment variables)
SERVER_ID = os.getenv("TANK_SERVER_ID", "local-server")  # Local server ID
SERVER_VERSION = "1.0.0"  # Server version
_server_start_time = time.time()  # Track server uptime

# Allow port override for testing multiple servers
_api_port_override = os.getenv("TANK_API_PORT")
if _api_port_override:
    DEFAULT_API_PORT = int(_api_port_override)


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


# Track background tasks
_heartbeat_task: Optional[asyncio.Task] = None


async def _heartbeat_loop() -> None:
    """Background task to send periodic heartbeats to discovery service."""
    while True:
        try:
            await asyncio.sleep(DiscoveryService.HEARTBEAT_INTERVAL)

            # Update local server info and send heartbeat
            server_info = get_server_info()
            await discovery_service.heartbeat(SERVER_ID, server_info)
            logger.debug("Heartbeat sent to discovery service")

        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    global _heartbeat_task

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
                # Inject connection manager and tank registry for migrations
                manager.runner.connection_manager = connection_manager
                manager.runner.tank_registry = tank_registry
                manager.runner.tank_id = manager.tank_id
                manager.runner._update_environment_migration_context()
                
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

        # Start discovery service
        logger.info("Starting discovery service...")
        try:
            await discovery_service.start()
            logger.info("Discovery service started")

            # Register local server
            local_server_info = get_server_info()
            await discovery_service.register_server(local_server_info)
            logger.info(f"Local server registered: {SERVER_ID}")

            # Start heartbeat loop
            _heartbeat_task = asyncio.create_task(_heartbeat_loop())
            _heartbeat_task.add_done_callback(_handle_task_exception)
            logger.info("Heartbeat task started")

        except Exception as e:
            logger.error(f"Failed to start discovery service: {e}", exc_info=True)
            # Non-fatal - continue without discovery

        # Start server client
        logger.info("Starting server client...")
        try:
            await server_client.start()
            logger.info("Server client started")
        except Exception as e:
            logger.error(f"Failed to start server client: {e}", exc_info=True)
            # Non-fatal - continue without server client

        # Configure TankRegistry with distributed services
        logger.info("Configuring TankRegistry for distributed operations...")
        try:
            tank_registry.set_distributed_services(discovery_service, server_client)
            logger.info("TankRegistry configured for distributed operations")
        except Exception as e:
            logger.error(f"Failed to configure TankRegistry: {e}", exc_info=True)
            # Non-fatal - continue without distributed tank queries

        # Start migration scheduler
        logger.info("Starting migration scheduler...")
        try:
            global migration_scheduler
            migration_scheduler = MigrationScheduler(
                connection_manager=connection_manager,
                tank_registry=tank_registry,
                check_interval=10.0,
                discovery_service=discovery_service,
                server_client=server_client,
                local_server_id=SERVER_ID,
            )
            await migration_scheduler.start()
            logger.info("Migration scheduler started")
        except Exception as e:
            logger.error(f"Failed to start migration scheduler: {e}", exc_info=True)
            # Non-fatal - continue without automated migrations

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

        # Stop migration scheduler
        logger.info("Stopping migration scheduler...")
        if migration_scheduler:
            try:
                await migration_scheduler.stop()
                logger.info("Migration scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping migration scheduler: {e}", exc_info=True)

        # Stop all simulations
        logger.info("Stopping all simulations...")
        try:
            tank_registry.stop_all()
            logger.info("All simulations stopped!")
        except Exception as e:
            logger.error(f"Error stopping simulations: {e}", exc_info=True)

        # Stop heartbeat task
        logger.info("Stopping heartbeat task...")
        if _heartbeat_task and not _heartbeat_task.done():
            _heartbeat_task.cancel()
            try:
                await _heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("Heartbeat task stopped")

        # Stop discovery service
        logger.info("Stopping discovery service...")
        try:
            await discovery_service.stop()
            logger.info("Discovery service stopped")
        except Exception as e:
            logger.error(f"Error stopping discovery service: {e}", exc_info=True)

        # Stop server client
        logger.info("Stopping server client...")
        try:
            await server_client.close()
            logger.info("Server client stopped")
        except Exception as e:
            logger.error(f"Error stopping server client: {e}", exc_info=True)

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


# =============================================================================
# Discovery Service Endpoints
# =============================================================================


@app.post("/api/discovery/register")
async def register_server(server_info: ServerInfo):
    """Register a server with the discovery service.

    Args:
        server_info: Server information to register

    Returns:
        Success message and registered server info
    """
    await discovery_service.register_server(server_info)
    return JSONResponse(
        {
            "status": "registered",
            "server_id": server_info.server_id,
            "message": f"Server {server_info.server_id} registered successfully",
        }
    )


@app.post("/api/discovery/heartbeat/{server_id}")
async def send_heartbeat(server_id: str, server_info: Optional[ServerInfo] = None):
    """Record a heartbeat from a server.

    Args:
        server_id: Server ID sending the heartbeat
        server_info: Optional updated server information

    Returns:
        Success message or error if server not registered
    """
    success = await discovery_service.heartbeat(server_id, server_info)

    if not success:
        return JSONResponse(
            {
                "status": "error",
                "message": f"Server {server_id} not registered. Please register first.",
            },
            status_code=404,
        )

    return JSONResponse(
        {
            "status": "ok",
            "server_id": server_id,
            "message": "Heartbeat received",
        }
    )


@app.get("/api/discovery/servers")
async def list_discovery_servers(
    status: Optional[str] = None,
    include_local: bool = True,
):
    """List all servers registered in the discovery service.

    Args:
        status: Optional status filter ("online", "offline", "degraded")
        include_local: Whether to include local server

    Returns:
        List of registered servers
    """
    servers = await discovery_service.list_servers(
        status_filter=status,
        include_local=include_local,
    )

    return JSONResponse(
        {
            "servers": [s.dict() for s in servers],
            "count": len(servers),
        }
    )


@app.delete("/api/discovery/unregister/{server_id}")
async def unregister_server(server_id: str):
    """Unregister a server from the discovery service.

    Args:
        server_id: Server ID to unregister

    Returns:
        Success message or error if not found
    """
    success = await discovery_service.unregister_server(server_id)

    if not success:
        return JSONResponse(
            {"error": f"Server not found: {server_id}"},
            status_code=404,
        )

    return JSONResponse(
        {
            "status": "unregistered",
            "server_id": server_id,
            "message": f"Server {server_id} unregistered successfully",
        }
    )


@app.get("/api/servers/local")
async def get_local_server():
    """Get information about the local server.

    Returns:
        ServerInfo for the local server
    """
    server_info = get_server_info()
    return JSONResponse(server_info.dict())


# =============================================================================
# Tank Management Endpoints
# =============================================================================


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
    allow_transfers: bool = True,
    server_id: str = "local-server",
):
    """Create a new tank simulation.

    Args:
        name: Human-readable name for the tank
        description: Description of the tank
        seed: Optional random seed for deterministic behavior
        owner: Optional owner identifier
        is_public: Whether the tank is publicly visible
        allow_transfers: Whether to allow entity transfers
        server_id: Which server to create the tank on (default: local-server)

    Returns:
        The created tank's status
    """
    try:
        # Validate server_id - for now, only local-server is supported
        if server_id != SERVER_ID:
            return JSONResponse(
                {
                    "error": f"Invalid server_id: {server_id}. "
                    f"Only '{SERVER_ID}' is supported in this version."
                },
                status_code=400,
            )

        manager = tank_registry.create_tank(
            name=name,
            description=description,
            seed=seed,
            owner=owner,
            is_public=is_public,
            allow_transfers=allow_transfers,
            server_id=server_id,
        )

        # Inject connection manager and tank registry for migrations
        manager.runner.connection_manager = connection_manager
        manager.runner.tank_registry = tank_registry
        manager.runner.tank_id = manager.tank_id
        manager.runner._update_environment_migration_context()

        # Start the simulation
        manager.start(start_paused=True)

        # Start broadcast task for the new tank
        await start_broadcast_for_tank(manager)

        logger.info(f"Created new tank via API: {manager.tank_id[:8]} ({name}) on server {server_id}")

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


def get_server_info() -> ServerInfo:
    """Get information about the current server.

    Returns:
        ServerInfo object with current server state
    """
    uptime = time.time() - _server_start_time

    # Try to get resource usage (optional)
    cpu_percent = None
    memory_mb = None
    try:
        import psutil

        process = psutil.Process()
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_mb = process.memory_info().rss / 1024 / 1024  # Convert bytes to MB
    except ImportError:
        # psutil not available - that's okay
        pass
    except Exception as e:
        logger.debug(f"Could not get resource usage: {e}")

    return ServerInfo(
        server_id=SERVER_ID,
        hostname=socket.gethostname(),
        host="localhost",  # For now, always localhost
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
        logical_cpus=os.cpu_count(),
    )


@app.get("/api/servers")
async def list_servers():
    """List all servers in the Tank World Network.

    Returns all servers registered in the discovery service, including the local
    server. For each server, includes the list of tanks running on it.

    Returns:
        List of ServerWithTanks objects containing server info and their tanks
    """
    # Get all servers from discovery service
    all_servers = await discovery_service.list_servers()

    # Build response with tanks for each server
    servers_with_tanks = []

    for server in all_servers:
        if server.is_local:
            # For local server, get tanks directly
            tanks = tank_registry.list_tanks(include_private=True)
        else:
            # For remote servers, fetch tanks via API
            try:
                remote_tanks = await server_client.list_tanks(server)
                tanks = remote_tanks if remote_tanks is not None else []
            except Exception as e:
                logger.error(f"Failed to fetch tanks from {server.server_id}: {e}")
                tanks = []

        servers_with_tanks.append(
            ServerWithTanks(
                server=server,
                tanks=tanks,
            ).model_dump()
        )

    return JSONResponse({"servers": servers_with_tanks})


@app.get("/api/servers/{server_id}")
async def get_server(server_id: str):
    """Get information about a specific server.

    Args:
        server_id: The server identifier

    Returns:
        ServerWithTanks object or 404 if not found
    """
    # Look up server in discovery service
    server_info = await discovery_service.get_server(server_id)

    if server_info is None:
        return JSONResponse(
            {"error": f"Server not found: {server_id}"},
            status_code=404,
        )

    # Get tanks for the server
    if server_info.is_local:
        # Local server - get tanks directly
        tanks = tank_registry.list_tanks(include_private=True)
    else:
        # Remote server - fetch via API
        try:
            remote_tanks = await server_client.list_tanks(server_info)
            tanks = remote_tanks if remote_tanks is not None else []
        except Exception as e:
            logger.error(f"Failed to fetch tanks from {server_id}: {e}")
            tanks = []

    return JSONResponse(
        ServerWithTanks(
            server=server_info,
            tanks=tanks,
        ).model_dump()
    )


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

            # Log failed transfer
            from backend.transfer_history import log_transfer

            log_transfer(
                entity_type=entity_data["type"],
                entity_old_id=entity_id,
                entity_new_id=None,
                source_tank_id=source_tank_id,
                source_tank_name=source_manager.tank_info.name,
                destination_tank_id=destination_tank_id,
                destination_tank_name=dest_manager.tank_info.name,
                success=False,
                error="Failed to deserialize entity in destination tank",
            )

            return JSONResponse(
                {"error": "Failed to deserialize entity in destination tank"},
                status_code=500,
            )

        dest_manager.world.engine.add_entity(new_entity)
        logger.info(f"Added entity {new_entity.id} to tank {destination_tank_id[:8]} (was {entity_id})")

        # Log successful transfer
        from backend.transfer_history import log_transfer

        log_transfer(
            entity_type=entity_data["type"],
            entity_old_id=entity_id,
            entity_new_id=new_entity.id,
            source_tank_id=source_tank_id,
            source_tank_name=source_manager.tank_info.name,
            destination_tank_id=destination_tank_id,
            destination_tank_name=dest_manager.tank_info.name,
            success=True,
        )

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

        # Log failed transfer
        from backend.transfer_history import log_transfer

        log_transfer(
            entity_type=entity_data["type"],
            entity_old_id=entity_id,
            entity_new_id=None,
            source_tank_id=source_tank_id,
            source_tank_name=source_manager.tank_info.name,
            destination_tank_id=destination_tank_id,
            destination_tank_name=dest_manager.tank_info.name,
            success=False,
            error=str(e),
        )

        return JSONResponse(
            {"error": f"Transfer failed: {str(e)}"},
            status_code=500,
        )


@app.post("/api/remote-transfer")
async def remote_transfer_entity(
    destination_tank_id: str,
    entity_data: Dict[str, Any],
    source_server_id: str,
    source_tank_id: str,
):
    """Receive an entity from a remote server for cross-server migration.

    This endpoint is called by remote servers to transfer entities to this server.

    Args:
        destination_tank_id: Destination tank ID on this server
        entity_data: Serialized entity data
        source_server_id: Source server ID (for logging)
        source_tank_id: Source tank ID (for logging)

    Returns:
        Success message with new entity ID, or error
    """
    from backend.entity_transfer import deserialize_entity
    from backend.transfer_history import log_transfer

    # Get destination tank
    dest_manager = tank_registry.get_tank(destination_tank_id)
    if dest_manager is None:
        return JSONResponse(
            {"error": f"Destination tank not found: {destination_tank_id}"},
            status_code=404,
        )

    # Check if destination tank allows transfers
    if not dest_manager.tank_info.allow_transfers:
        return JSONResponse(
            {
                "error": f"Tank '{dest_manager.tank_info.name}' does not allow entity transfers"
            },
            status_code=403,
        )

    try:
        # Deserialize and add to destination tank
        new_entity = deserialize_entity(entity_data, dest_manager.world)
        if new_entity is None:
            # Log failed transfer
            log_transfer(
                entity_type=entity_data.get("type", "unknown"),
                entity_old_id=entity_data.get("id", -1),
                entity_new_id=None,
                source_tank_id=f"{source_server_id}:{source_tank_id}",
                source_tank_name=f"Remote tank on {source_server_id}",
                destination_tank_id=destination_tank_id,
                destination_tank_name=dest_manager.tank_info.name,
                success=False,
                error="Failed to deserialize entity",
            )

            return JSONResponse(
                {"error": "Failed to deserialize entity"},
                status_code=500,
            )

        dest_manager.world.engine.add_entity(new_entity)
        logger.info(
            f"Remote transfer: Added entity {new_entity.id} from {source_server_id}:{source_tank_id[:8]} "
            f"to {destination_tank_id[:8]} (was {entity_data.get('id', '?')})"
        )

        # Log successful transfer
        log_transfer(
            entity_type=entity_data.get("type", "unknown"),
            entity_old_id=entity_data.get("id", -1),
            entity_new_id=new_entity.id,
            source_tank_id=f"{source_server_id}:{source_tank_id}",
            source_tank_name=f"Remote tank on {source_server_id}",
            destination_tank_id=destination_tank_id,
            destination_tank_name=dest_manager.tank_info.name,
            success=True,
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Entity transferred successfully from remote server",
                "entity": {
                    "old_id": entity_data.get("id", -1),
                    "new_id": new_entity.id,
                    "type": entity_data.get("type", "unknown"),
                    "source_server": source_server_id,
                    "source_tank": source_tank_id,
                    "destination_tank": destination_tank_id,
                },
            }
        )
    except Exception as e:
        logger.error(f"Remote transfer failed: {e}", exc_info=True)

        # Log failed transfer
        log_transfer(
            entity_type=entity_data.get("type", "unknown"),
            entity_old_id=entity_data.get("id", -1),
            entity_new_id=None,
            source_tank_id=f"{source_server_id}:{source_tank_id}",
            source_tank_name=f"Remote tank on {source_server_id}",
            destination_tank_id=destination_tank_id,
            destination_tank_name=dest_manager.tank_info.name if dest_manager else "Unknown",
            success=False,
            error=str(e),
        )

        return JSONResponse(
            {"error": f"Remote transfer failed: {str(e)}"},
            status_code=500,
        )


@app.get("/api/transfers")
async def get_transfers(limit: int = 50, tank_id: Optional[str] = None, success_only: bool = False):
    """Get transfer history.

    Args:
        limit: Maximum number of records to return (default 50)
        tank_id: Filter by tank ID (source or destination)
        success_only: Only return successful transfers

    Returns:
        List of transfer records
    """
    from backend.transfer_history import get_transfer_history

    transfers = get_transfer_history(limit=limit, tank_id=tank_id, success_only=success_only)
    return JSONResponse({
        "transfers": transfers,
        "count": len(transfers),
    })


# =============================================================================
# Connection Management API
# =============================================================================


@app.get("/api/connections")
async def list_connections(tank_id: Optional[str] = None):
    """List tank connections.
    
    Args:
        tank_id: Optional tank ID to filter by
        
    Returns:
        List of connections
    """
    if tank_id:
        connections = connection_manager.get_connections_for_tank(tank_id)
    else:
        connections = connection_manager.list_connections()
        
    return JSONResponse({
        "connections": [c.to_dict() for c in connections],
        "count": len(connections),
    })


@app.post("/api/connections")
async def create_connection(connection_data: Dict):
    """Create or update a tank connection.
    
    Args:
        connection_data: Connection data (sourceId, destinationId, probability, direction)
        
    Returns:
        The created connection
    """
    try:
        connection = TankConnection.from_dict(connection_data)
        connection_manager.add_connection(connection)
        return JSONResponse(connection.to_dict())
    except Exception as e:
        logger.error(f"Error creating connection: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=400)


@app.delete("/api/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete a tank connection.
    
    Args:
        connection_id: The connection ID to delete
        
    Returns:
        Success message
    """
    if connection_manager.remove_connection(connection_id):
        return JSONResponse({"success": True})
    else:
        return JSONResponse({"error": "Connection not found"}, status_code=404)


@app.get("/api/transfers/{transfer_id}")
async def get_transfer(transfer_id: str):
    """Get a specific transfer by ID.

    Args:
        transfer_id: The transfer UUID

    Returns:
        Transfer record or 404 if not found
    """
    from backend.transfer_history import get_transfer_by_id

    transfer = get_transfer_by_id(transfer_id)
    if transfer is None:
        return JSONResponse({"error": f"Transfer not found: {transfer_id}"}, status_code=404)

    return JSONResponse(transfer)


@app.get("/api/tanks/{tank_id}/transfer-stats")
async def get_tank_transfer_stats(tank_id: str):
    """Get transfer statistics for a tank.

    Args:
        tank_id: The tank ID

    Returns:
        Transfer statistics
    """
    from backend.transfer_history import get_tank_transfer_stats

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

    stats = get_tank_transfer_stats(tank_id)
    return JSONResponse({
        "tank_id": tank_id,
        "tank_name": manager.tank_info.name,
        **stats,
    })


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


@app.post("/api/tanks/{tank_id}/save")
async def save_tank(tank_id: str):
    """Save tank state to a snapshot file.

    Args:
        tank_id: The tank ID to save

    Returns:
        Success message with snapshot info, or error
    """
    from backend.tank_persistence import save_tank_state, cleanup_old_snapshots

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

    # Save the tank state
    snapshot_path = save_tank_state(tank_id, manager)
    if snapshot_path is None:
        return JSONResponse({"error": "Failed to save tank state"}, status_code=500)

    # Cleanup old snapshots (keep last 10)
    cleanup_old_snapshots(tank_id, max_snapshots=10)

    return JSONResponse({
        "success": True,
        "message": f"Tank saved successfully",
        "snapshot_path": snapshot_path,
        "tank_id": tank_id,
    })


@app.post("/api/tanks/load")
async def load_tank(snapshot_path: str):
    """Load a tank from a snapshot file.

    Args:
        snapshot_path: Path to the snapshot file

    Returns:
        Success message with tank info, or error
    """
    from backend.tank_persistence import load_tank_state, restore_tank_from_snapshot

    # Load snapshot data
    snapshot = load_tank_state(snapshot_path)
    if snapshot is None:
        return JSONResponse({"error": "Failed to load snapshot"}, status_code=400)

    # Extract metadata
    tank_id = snapshot["tank_id"]
    metadata = snapshot["metadata"]

    # Check if tank already exists
    existing_manager = tank_registry.get_tank(tank_id)
    if existing_manager is not None:
        return JSONResponse(
            {"error": f"Tank {tank_id} already exists. Delete it first or use a different snapshot."},
            status_code=409,
        )

    # Create new tank with same ID and metadata
    create_request = CreateTankRequest(
        tank_id=tank_id,
        name=metadata["name"],
        description=metadata.get("description", ""),
        seed=metadata.get("seed"),
        owner=metadata.get("owner"),
        is_public=metadata.get("is_public", True),
        allow_transfers=metadata.get("allow_transfers", True),
    )

    new_manager = tank_registry.create_tank(create_request)
    if new_manager is None:
        return JSONResponse({"error": "Failed to create tank"}, status_code=500)

    # Restore state into the new tank
    if not restore_tank_from_snapshot(snapshot, new_manager.world):
        # Cleanup failed tank
        tank_registry.remove_tank(tank_id)
        return JSONResponse({"error": "Failed to restore tank state"}, status_code=500)

    return JSONResponse({
        "success": True,
        "message": f"Tank loaded successfully",
        "tank_id": tank_id,
        "frame": snapshot["frame"],
        "entity_count": len(snapshot["entities"]),
    })


@app.get("/api/tanks/{tank_id}/snapshots")
async def list_snapshots(tank_id: str):
    """List all available snapshots for a tank.

    Args:
        tank_id: The tank ID

    Returns:
        List of snapshot metadata
    """
    from backend.tank_persistence import list_tank_snapshots

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

    snapshots = list_tank_snapshots(tank_id)
    return JSONResponse({
        "tank_id": tank_id,
        "snapshots": snapshots,
        "count": len(snapshots),
    })


@app.delete("/api/tanks/{tank_id}/snapshots/{snapshot_filename}")
async def delete_tank_snapshot(tank_id: str, snapshot_filename: str):
    """Delete a specific snapshot file.

    Args:
        tank_id: The tank ID
        snapshot_filename: Name of the snapshot file to delete

    Returns:
        Success message or error
    """
    from backend.tank_persistence import delete_snapshot, DATA_DIR

    manager = tank_registry.get_tank(tank_id)
    if manager is None:
        return JSONResponse({"error": f"Tank not found: {tank_id}"}, status_code=404)

    # Build snapshot path
    snapshot_path = DATA_DIR / tank_id / "snapshots" / snapshot_filename

    # Validate filename to prevent directory traversal
    if not snapshot_path.is_relative_to(DATA_DIR / tank_id / "snapshots"):
        return JSONResponse({"error": "Invalid snapshot filename"}, status_code=400)

    if not snapshot_path.exists():
        return JSONResponse({"error": f"Snapshot not found: {snapshot_filename}"}, status_code=404)

    if delete_snapshot(str(snapshot_path)):
        return JSONResponse({"message": f"Snapshot {snapshot_filename} deleted"})
    else:
        return JSONResponse({"error": "Failed to delete snapshot"}, status_code=500)


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
