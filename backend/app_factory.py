"""Application factory and context for Fish Tank Simulation API.

This module provides a clean factory pattern for creating the FastAPI app,
avoiding import-time side effects. All singletons are created lazily
within the AppContext.

Design Decision:
----------------
We use an AppContext dataclass to hold all runtime state instead of module-level
globals. This:
1. Makes testing easier (each test gets a fresh context)
2. Avoids cross-test pollution
3. Enables multiple app instances if needed
4. Makes dependencies explicit and injectable

Usage:
------
    # For production (uses default settings from environment)
    app = create_app()

    # For testing (custom configuration)
    app = create_app(server_id="test-server", production_mode=False)
"""

import asyncio
import logging
import os
import platform
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auto_save_service import AutoSaveService
from backend.broadcast import start_broadcast_for_tank, stop_broadcast_for_tank
from backend.connection_manager import ConnectionManager
from backend.discovery_service import DiscoveryService
from backend.logging_config import configure_logging
from backend.migration_scheduler import MigrationScheduler
from backend.models import ServerInfo
from backend.security import setup_security_middleware
from backend.server_client import ServerClient
from backend.startup_manager import StartupManager
from backend.tank_registry import TankRegistry
from backend.world_manager import WorldManager
from core.config.server import DEFAULT_API_PORT

# Type alias for broadcast callbacks
BroadcastCallback = Callable[..., Coroutine[Any, Any, Any]]


@dataclass
class AppContext:
    """Runtime context holding all application state.

    This replaces module-level globals, making dependencies explicit
    and enabling clean testing without cross-test pollution.
    """

    # Core services (created at construction)
    tank_registry: TankRegistry = field(default_factory=lambda: TankRegistry(create_default=False))
    connection_manager: ConnectionManager = field(default_factory=ConnectionManager)
    discovery_service: DiscoveryService = field(default_factory=DiscoveryService)
    server_client: ServerClient = field(default_factory=ServerClient)

    # Configuration
    server_id: str = field(default_factory=lambda: os.getenv("TANK_SERVER_ID", "local-server"))
    server_version: str = "1.0.0"
    api_port: int = field(
        default_factory=lambda: int(os.getenv("TANK_API_PORT", str(DEFAULT_API_PORT)))
    )
    discovery_server_url: Optional[str] = field(
        default_factory=lambda: os.getenv("DISCOVERY_SERVER_URL")
    )
    production_mode: bool = field(
        default_factory=lambda: os.getenv("PRODUCTION", "false").lower() == "true"
    )
    allowed_origins: list = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Runtime state (initialized during lifespan)
    startup_manager: Optional[StartupManager] = None
    auto_save_service: Optional[AutoSaveService] = None
    migration_scheduler: Optional[MigrationScheduler] = None

    # Timing
    server_start_time: float = field(default_factory=time.time)

    # Logging
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("backend"))

    # World manager (created after tank_registry)
    world_manager: Optional[WorldManager] = None

    def get_server_info(self) -> ServerInfo:
        """Get information about the current server."""
        uptime = time.time() - self.server_start_time

        cpu_percent = None
        memory_mb = None
        logical_cpus = os.cpu_count()
        physical_cpus = None

        try:
            import psutil

            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            physical_cpus = psutil.cpu_count(logical=False)
            if physical_cpus is None:
                physical_cpus = logical_cpus
        except ImportError:
            pass
        except Exception as e:
            self.logger.debug(f"Could not get resource usage: {e}")

        return ServerInfo(
            server_id=self.server_id,
            hostname=socket.gethostname(),
            host=_get_network_ip(),
            port=self.api_port,
            status="online",
            tank_count=self.tank_registry.tank_count,
            version=self.server_version,
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


def _get_network_ip() -> str:
    """Get the network IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def _configure_windows_event_loop(logger: logging.Logger) -> None:
    """Configure asyncio event loop policy on Windows."""
    if platform.system() != "Windows":
        return

    loop_policy = os.getenv("TANK_WINDOWS_EVENT_LOOP", "selector").strip().lower()
    if not loop_policy or loop_policy == "default":
        return

    logger.info("Windows detected - configuring asyncio event loop policy: %s", loop_policy)
    try:
        if loop_policy == "proactor":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        elif loop_policy == "selector":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            logger.warning(
                "Unknown TANK_WINDOWS_EVENT_LOOP=%s (expected selector|proactor|default); leaving default policy",
                loop_policy,
            )
    except Exception as e:
        logger.warning("Could not set Windows event loop policy: %s", e)


def create_app(
    *,
    server_id: Optional[str] = None,
    discovery_server_url: Optional[str] = None,
    production_mode: Optional[bool] = None,
    context: Optional[AppContext] = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    This factory function creates the app with all dependencies properly
    initialized. Use this instead of importing `app` directly for testing.

    Args:
        server_id: Override server ID (default: from TANK_SERVER_ID env var)
        discovery_server_url: Override discovery URL (default: from DISCOVERY_SERVER_URL env var)
        production_mode: Override production mode (default: from PRODUCTION env var)
        context: Pre-configured AppContext (for testing). If None, creates a new one.

    Returns:
        Configured FastAPI application with context attached as app.state.context
    """
    # Configure logging (idempotent)
    logger = configure_logging(extra_loggers=("backend",))

    # Configure Windows event loop
    _configure_windows_event_loop(logger)

    # Create or use provided context
    if context is None:
        context = AppContext()

    # Apply overrides
    if server_id is not None:
        context.server_id = server_id
    if discovery_server_url is not None:
        context.discovery_server_url = discovery_server_url
    if production_mode is not None:
        context.production_mode = production_mode

    context.logger = logger

    # Create lifespan with context closure
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for startup and shutdown."""
        ctx = app.state.context

        try:
            # Create and initialize startup manager
            ctx.startup_manager = StartupManager(
                tank_registry=ctx.tank_registry,
                connection_manager=ctx.connection_manager,
                discovery_service=ctx.discovery_service,
                server_client=ctx.server_client,
                server_id=ctx.server_id,
                discovery_server_url=ctx.discovery_server_url,
                start_broadcast_callback=start_broadcast_for_tank,
                stop_broadcast_callback=stop_broadcast_for_tank,
            )

            await ctx.startup_manager.initialize(get_server_info_callback=ctx.get_server_info)

            ctx.auto_save_service = ctx.startup_manager.auto_save_service
            ctx.migration_scheduler = ctx.startup_manager.migration_scheduler

            # Setup API routers
            ctx.logger.info("Setting up API routers...")
            _setup_routers(app, ctx)
            ctx.logger.info("API routers configured successfully")

            ctx.logger.info("LIFESPAN: Startup complete - yielding control to app")
            yield
            ctx.logger.info("LIFESPAN: Received shutdown signal")

        except Exception as e:
            ctx.logger.error(f"Exception in lifespan startup: {e}", exc_info=True)
            raise
        finally:
            try:
                from core.auto_evaluate_poker import request_shutdown

                request_shutdown()
            except Exception:
                pass

            if ctx.startup_manager:
                await ctx.startup_manager.shutdown()

    # Create the FastAPI app
    app = FastAPI(
        title="Fish Tank Simulation API",
        lifespan=lifespan,
        docs_url=None if context.production_mode else "/docs",
        redoc_url=None if context.production_mode else "/redoc",
    )

    # Attach context to app state for access in routes
    app.state.context = context

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=context.allowed_origins if context.production_mode else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add security middleware
    setup_security_middleware(app, enable_rate_limiting=context.production_mode)

    return app


def _setup_routers(app: FastAPI, ctx: AppContext) -> None:
    """Setup and include all API routers."""
    from backend.routers import discovery, servers, tanks, transfers, websocket
    from backend.routers.solutions import create_solutions_router
    from backend.routers.worlds import setup_worlds_router

    # Create WorldManager if not already created
    if ctx.world_manager is None:
        ctx.world_manager = WorldManager(tank_registry=ctx.tank_registry)

    # Setup discovery router
    discovery_router = discovery.setup_router(ctx.discovery_service)
    app.include_router(discovery_router)

    # Setup transfers router
    transfers_router = transfers.setup_router(
        ctx.tank_registry,
        ctx.connection_manager,
        world_manager=ctx.world_manager,
    )
    app.include_router(transfers_router)

    # Setup tanks router
    tanks_router = tanks.setup_router(
        tank_registry=ctx.tank_registry,
        server_id=ctx.server_id,
        start_broadcast_callback=start_broadcast_for_tank,
        stop_broadcast_callback=stop_broadcast_for_tank,
        auto_save_service=ctx.auto_save_service,
        world_manager=ctx.world_manager,
    )
    app.include_router(tanks_router)

    # Setup servers router
    servers_router = servers.setup_router(
        tank_registry=ctx.tank_registry,
        discovery_service=ctx.discovery_service,
        server_client=ctx.server_client,
        get_server_info_callback=ctx.get_server_info,
    )
    app.include_router(servers_router)

    # Setup websocket routes (with WorldManager for unified endpoint)
    websocket_router = websocket.setup_router(ctx.tank_registry, ctx.world_manager)
    app.include_router(websocket_router)

    # Setup solutions router
    solutions_router = create_solutions_router(ctx.tank_registry)
    app.include_router(solutions_router)

    # Setup worlds router (world-agnostic API)
    worlds_router = setup_worlds_router(ctx.world_manager)
    app.include_router(worlds_router)

    ctx.logger.info("All API routers configured successfully")
