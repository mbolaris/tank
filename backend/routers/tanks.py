"""Tank management API endpoints.

This module composes sub-routers for tank operations:
- CRUD: list, create, get, delete
- Lifecycle: pause, resume, start, stop, fast_forward
- Persistence: save, load, snapshots
- Inspection: evaluation-history, evolution-benchmark, lineage, snapshot, transfer-stats
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter

from backend.routers.tanks_crud import setup_crud_subrouter
from backend.routers.tanks_inspection import setup_inspection_subrouter
from backend.routers.tanks_lifecycle import setup_lifecycle_subrouter
from backend.routers.tanks_persistence import setup_persistence_subrouter
from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/tanks", tags=["tanks"])


def setup_router(
    tank_registry: TankRegistry,
    server_id: str,
    start_broadcast_callback,
    stop_broadcast_callback,
    auto_save_service: Optional[Any] = None,
) -> APIRouter:
    """Setup the tanks router with required dependencies.

    Args:
        tank_registry: The tank registry instance
        server_id: The local server ID
        start_broadcast_callback: Callback to start broadcast for a tank
        stop_broadcast_callback: Callback to stop broadcast for a tank
        auto_save_service: Optional auto-save service instance

    Returns:
        Configured APIRouter
    """
    # Attach sub-routers
    setup_crud_subrouter(
        router,
        tank_registry,
        server_id,
        start_broadcast_callback,
        stop_broadcast_callback,
        auto_save_service,
    )
    setup_lifecycle_subrouter(
        router,
        tank_registry,
        start_broadcast_callback,
        stop_broadcast_callback,
    )
    setup_persistence_subrouter(
        router,
        tank_registry,
    )
    setup_inspection_subrouter(
        router,
        tank_registry,
    )

    return router
