"""Tank connection manager for automated migrations."""

import logging
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TankConnection:
    """Represents a connection between two tanks for entity migration.

    Supports both local (same-server) and remote (cross-server) connections.
    For remote connections, source_server_id and destination_server_id identify
    the servers hosting each tank.
    """

    id: str
    source_tank_id: str
    destination_tank_id: str
    probability: int  # 0-100, percentage chance of migration per check
    direction: str = "right"  # "left" or "right" - which boundary triggers migration
    source_server_id: Optional[str] = None  # Server hosting source tank (None = local)
    destination_server_id: Optional[str] = None  # Server hosting destination tank (None = local)

    def is_remote(self) -> bool:
        """Check if this is a cross-server connection.

        Returns:
            True if source and destination are on different servers
        """
        # If either is None, consider it local
        if self.source_server_id is None or self.destination_server_id is None:
            return False
        return self.source_server_id != self.destination_server_id

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "sourceId": self.source_tank_id,
            "destinationId": self.destination_tank_id,
            "probability": self.probability,
            "direction": self.direction,
        }
        if self.source_server_id:
            result["sourceServerId"] = self.source_server_id
        if self.destination_server_id:
            result["destinationServerId"] = self.destination_server_id
        return result

    @staticmethod
    def from_dict(data: Dict) -> "TankConnection":
        """Create from dictionary (supports both snake_case and camelCase).

        Args:
            data: Dictionary containing connection data

        Returns:
            TankConnection instance

        Raises:
            ValueError: If required fields (sourceId/source_tank_id or
                       destinationId/destination_tank_id) are missing
        """
        # Extract required fields with fallback to snake_case
        source_tank_id = data.get("sourceId", data.get("source_tank_id"))
        destination_tank_id = data.get("destinationId", data.get("destination_tank_id"))

        # Validate required fields
        if not source_tank_id:
            raise ValueError("Missing required field: sourceId or source_tank_id")
        if not destination_tank_id:
            raise ValueError("Missing required field: destinationId or destination_tank_id")

        # Generate ID if not provided
        connection_id = data.get("id", f"{source_tank_id}->{destination_tank_id}")

        return TankConnection(
            id=connection_id,
            source_tank_id=source_tank_id,
            destination_tank_id=destination_tank_id,
            probability=data.get("probability", 25),
            direction=data.get("direction", "right"),
            source_server_id=data.get("sourceServerId", data.get("source_server_id")),
            destination_server_id=data.get("destinationServerId", data.get("destination_server_id")),
        )


class ConnectionManager:
    """Manages tank connections for automated migrations."""

    def __init__(self):
        """Initialize the connection manager."""
        self._connections: Dict[str, TankConnection] = {}
        self._lock = threading.Lock()
        logger.info("ConnectionManager initialized")

    def add_connection(self, connection: TankConnection) -> None:
        """Add or update a connection.

        Enforces a maximum of 1 connection in each direction between any two tanks.
        A→B and B→A are considered separate connections and both are allowed.
        If a connection already exists with the same source and destination,
        it will be replaced by the new connection.

        Args:
            connection: The connection to add/update
        """
        with self._lock:
            # Check for existing connection with SAME source and destination
            # (opposite direction is allowed - A→B and B→A can coexist)
            to_remove = []
            for existing_id, existing_conn in self._connections.items():
                if (existing_conn.source_tank_id == connection.source_tank_id and
                    existing_conn.destination_tank_id == connection.destination_tank_id):
                    to_remove.append(existing_id)

            # Remove conflicting connections
            for conn_id in to_remove:
                del self._connections[conn_id]
                logger.info(f"Removed duplicate connection {conn_id} (same direction)")

            # Add the new connection
            self._connections[connection.id] = connection
            logger.info(
                f"Added connection: {connection.source_tank_id[:8]} -> "
                f"{connection.destination_tank_id[:8]} ({connection.probability}%, {connection.direction})"
            )

    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection.

        Args:
            connection_id: The connection ID to remove

        Returns:
            True if connection was removed, False if not found
        """
        with self._lock:
            if connection_id in self._connections:
                conn = self._connections.pop(connection_id)
                logger.info(
                    f"Removed connection: {conn.source_tank_id[:8]} -> "
                    f"{conn.destination_tank_id[:8]}"
                )
                return True
            return False

    def get_connection(self, connection_id: str) -> Optional[TankConnection]:
        """Get a specific connection.

        Args:
            connection_id: The connection ID to retrieve

        Returns:
            The connection if found, None otherwise
        """
        with self._lock:
            return self._connections.get(connection_id)

    def list_connections(self) -> List[TankConnection]:
        """Get all connections.

        Returns:
            List of all connections
        """
        with self._lock:
            return list(self._connections.values())

    def get_connections_for_tank(self, tank_id: str, direction: Optional[str] = None) -> List[TankConnection]:
        """Get connections where the tank is the source, optionally filtered by direction.

        Args:
            tank_id: The source tank ID
            direction: Optional direction to filter by ("left" or "right")

        Returns:
            List of matching connections
        """
        with self._lock:
            connections = [
                conn for conn in self._connections.values()
                if conn.source_tank_id == tank_id
            ]

            if direction:
                connections = [c for c in connections if c.direction == direction]

            return connections

    def clear_connections_for_tank(self, tank_id: str) -> int:
        """Remove all connections involving a specific tank.

        Args:
            tank_id: The tank ID to clear connections for

        Returns:
            Number of connections removed
        """
        with self._lock:
            to_remove = [
                conn_id for conn_id, conn in self._connections.items()
                if conn.source_tank_id == tank_id or conn.destination_tank_id == tank_id
            ]
            for conn_id in to_remove:
                del self._connections[conn_id]

            if to_remove:
                logger.info(f"Cleared {len(to_remove)} connections for tank {tank_id[:8]}")

            return len(to_remove)

    def validate_connections(self, valid_tank_ids: List[str], local_server_id: Optional[str] = None) -> int:
        """Remove connections that reference non-existent local tanks.

        Only validates connections where both ends are on the local server.
        Remote connections are preserved since we can't validate tanks on other servers.

        Args:
            valid_tank_ids: List of currently valid local tank IDs
            local_server_id: Optional local server ID for validation

        Returns:
            Number of invalid connections removed
        """
        valid_ids_set = set(valid_tank_ids)
        removed_count = 0

        with self._lock:
            to_remove = []
            for conn_id, conn in self._connections.items():
                # Skip validation for remote connections - we can't verify tanks on other servers
                # A connection is remote if either server_id is set and differs from local
                is_source_local = conn.source_server_id is None or conn.source_server_id == local_server_id
                is_dest_local = conn.destination_server_id is None or conn.destination_server_id == local_server_id

                # Only validate if both ends are supposed to be local tanks
                if is_source_local and is_dest_local:
                    if conn.source_tank_id not in valid_ids_set or conn.destination_tank_id not in valid_ids_set:
                        to_remove.append(conn_id)
                        logger.debug(
                            f"Marking local connection for removal: {conn.source_tank_id[:8]} -> "
                            f"{conn.destination_tank_id[:8]} (tank not in registry)"
                        )
                else:
                    # Log that we're preserving a remote connection
                    logger.debug(
                        f"Preserving remote connection: {conn.source_tank_id[:8]} -> "
                        f"{conn.destination_tank_id[:8]} "
                        f"(source_server={conn.source_server_id}, dest_server={conn.destination_server_id})"
                    )

            for conn_id in to_remove:
                conn = self._connections.pop(conn_id)
                logger.info(
                    f"Removed invalid local connection: {conn.source_tank_id[:8]} -> "
                    f"{conn.destination_tank_id[:8]} (referenced missing tank)"
                )
                removed_count += 1

        return removed_count
