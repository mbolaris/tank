"""Connection persistence for Tank World Net.

This module handles saving and loading tank connections (migration tubes)
to/from disk, enabling connections to persist across server restarts.
"""

import json
import logging
from pathlib import Path

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

        # Write to file
        with open(CONNECTIONS_FILE, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(connections)} connection(s) to {CONNECTIONS_FILE}")
        return True

    except Exception as e:
        logger.error(f"Failed to save connections: {e}", exc_info=True)
        return False


def load_connections(connection_manager) -> int:
    """Load connections from disk and restore to connection manager.

    Args:
        connection_manager: ConnectionManager instance

    Returns:
        Number of connections restored
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
            except Exception as e:
                logger.warning(f"Failed to restore connection {conn_data.get('id')}: {e}")
                continue

        logger.info(f"Restored {restored_count} connection(s) from {CONNECTIONS_FILE}")
        return restored_count

    except Exception as e:
        logger.error(f"Failed to load connections: {e}", exc_info=True)
        return 0
