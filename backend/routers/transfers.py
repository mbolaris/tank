"""Entity transfer and connection management API endpoints.

This module composes sub-routers for transfer operations:
- Transfer operations: local/remote transfers, transfer history
- Connections: list, create, delete tank connections
"""

import logging

from fastapi import APIRouter

from backend.connection_manager import ConnectionManager
from backend.routers.transfers_connections import setup_connections_subrouter
from backend.routers.transfers_ops import setup_transfer_ops_subrouter
from backend.tank_registry import TankRegistry

logger = logging.getLogger(__name__)


router = APIRouter(tags=["transfers"])


def setup_router(
    tank_registry: TankRegistry,
    connection_manager: ConnectionManager,
) -> APIRouter:
    """Setup the transfers router with required dependencies.

    Args:
        tank_registry: The tank registry instance
        connection_manager: The connection manager instance

    Returns:
        Configured APIRouter
    """
    # Attach sub-routers
    setup_transfer_ops_subrouter(router, tank_registry)
    setup_connections_subrouter(router, connection_manager)

    return router
