"""Connection persistence for Tank World Net.

This module handles saving and loading tank connections (migration tubes)
to/from disk, enabling connections to persist across server restarts.
"""

import json
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from backend.atomic_json import write_json_atomic

logger = logging.getLogger(__name__)

# File for storing connections
CONNECTIONS_FILE = Path("data/connections.json")


def save_connections(connection_manager) -> bool:
    """Save all connections to disk.

    Args:
        connection_manager: ConnectionManager instance

    Returns:
        True if save succeeded, False otherwise
    """
    try:
        # Ensure data directory exists
        CONNECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Get all connections
        connections = connection_manager.list_connections()

        # Serialize connections
        data = {
            "version": "1.0",
            "connections": [conn.to_dict() for conn in connections],
        }

        write_json_atomic(CONNECTIONS_FILE, data)

        logger.info(f"Saved {len(connections)} connection(s) to {CONNECTIONS_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to save connections: {e}", exc_info=True)
        return False


def prune_stale_connections(
    connection_manager: Any,
    live_world_ids: Iterable[str],
    local_server_id: str | None = None,
) -> int:
    """Drop local connections whose source or destination world is gone.

    Removal is written straight back to disk. Without that, a connection to a
    deleted world is only forgotten in memory: the next start reloads it from
    ``connections.json`` and the migration scheduler warns "world not found"
    every couple of seconds, forever. Connections with a remote end are kept,
    since this server cannot know which worlds another server hosts.

    Returns:
        Number of connections removed
    """
    if connection_manager is None:
        return 0
    removed = connection_manager.validate_connections(
        list(live_world_ids), local_server_id=local_server_id
    )
    if not isinstance(removed, int) or removed <= 0:
        return 0
    logger.info(f"Pruned {removed} connection(s) to worlds that no longer exist")
    save_connections(connection_manager)
    return removed


def load_connections(
    connection_manager,
    world_manager: Any = None,
    local_server_id: str | None = None,
) -> int:
    """Load connections from disk and restore to connection manager.

    Args:
        connection_manager: ConnectionManager instance
        world_manager: When given, connections to worlds it does not hold are
            pruned (and the file rewritten) right after loading. Pass it only
            once saved worlds have been restored, or live links get pruned.
        local_server_id: This server's id, so connections stamped with it
            still count as local when pruning

    Returns:
        Number of connections restored (after pruning)
    """
    try:
        if not CONNECTIONS_FILE.exists():
            logger.info("No saved connections file found")
            return 0

        # Load from file
        with open(CONNECTIONS_FILE) as f:
            data = json.load(f)

        # Validate format
        if "connections" not in data:
            logger.error("Invalid connections file: missing 'connections' field")
            return 0

        # Import TankConnection here to avoid circular imports
        from backend.connection_manager import TankConnection

        # Restore connections
        restored_count = 0
        for conn_data in data["connections"]:
            try:
                connection = TankConnection.from_dict(conn_data)
                connection_manager.add_connection(connection)
                restored_count += 1
            except ValueError as e:
                # Validation error - malformed connection data
                logger.error(
                    f"Invalid connection data in connections.json: {e}. "
                    f"Connection data: {conn_data}"
                )
                continue
            except Exception as e:
                # Unexpected error
                logger.error(
                    f"Failed to restore connection {conn_data.get('id')}: {e}", exc_info=True
                )
                continue

        if world_manager is not None:
            live_world_ids = [instance.world_id for instance in world_manager]
            restored_count -= prune_stale_connections(
                connection_manager, live_world_ids, local_server_id
            )

        logger.info(f"Restored {restored_count} connection(s) from {CONNECTIONS_FILE}")
        return restored_count

    except Exception as e:
        logger.error(f"Failed to load connections: {e}", exc_info=True)
        return 0
