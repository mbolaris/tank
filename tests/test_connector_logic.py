import logging
import unittest

from backend.connection_manager import ConnectionManager, TankConnection
from backend.world_manager import WorldManager

# Configure logging to show info during tests
logging.basicConfig(level=logging.INFO)


class TestConnectorLogic(unittest.TestCase):
    def setUp(self):
        self.connection_manager = ConnectionManager()
        self.world_manager = WorldManager()
        self.world_manager.set_connection_manager(self.connection_manager)

    def test_max_one_connector(self):
        """Test that adding a duplicate connection replaces it, but opposite direction is allowed."""
        # Create connection A -> B
        conn1 = TankConnection(
            id="A->B",
            source_world_id="tank_a",
            destination_world_id="tank_b",
            probability=25,
            direction="right",
        )
        self.connection_manager.add_connection(conn1)

        # Verify first connection exists
        self.assertEqual(len(self.connection_manager.list_connections()), 1)
        self.assertEqual(self.connection_manager.get_connection("A->B").probability, 25)

        # Create connection B -> A (opposite direction - should be allowed)
        conn2 = TankConnection(
            id="B->A",
            source_world_id="tank_b",
            destination_world_id="tank_a",
            probability=50,
            direction="left",
        )
        self.connection_manager.add_connection(conn2)

        # Verify BOTH connections exist (bidirectional allowed)
        connections = self.connection_manager.list_connections()
        self.assertEqual(len(connections), 2)

        # Now add a duplicate A->B with different probability - should replace
        conn3 = TankConnection(
            id="A->B-v2",
            source_world_id="tank_a",
            destination_world_id="tank_b",
            probability=75,
            direction="right",
        )
        self.connection_manager.add_connection(conn3)

        # Verify still 2 connections (duplicate replaced, opposite direction preserved)
        connections = self.connection_manager.list_connections()
        self.assertEqual(len(connections), 2)

        # The A->B connection should have the new ID and probability
        a_to_b = [
            c
            for c in connections
            if c.source_world_id == "tank_a" and c.destination_world_id == "tank_b"
        ]
        self.assertEqual(len(a_to_b), 1)
        self.assertEqual(a_to_b[0].id, "A->B-v2")
        self.assertEqual(a_to_b[0].probability, 75)

    def test_cascade_delete(self):
        """Test that removing a tank (world) removes its connections."""
        # Create mock tanks
        tank_a = self.world_manager.create_world(name="Tank A", world_type="tank", persistent=False)
        tank_b = self.world_manager.create_world(name="Tank B", world_type="tank", persistent=False)

        id_a = tank_a.world_id
        id_b = tank_b.world_id

        # Create connection
        conn = TankConnection(
            id="A->B", source_world_id=id_a, destination_world_id=id_b, probability=25
        )
        self.connection_manager.add_connection(conn)

        # Verify connection exists
        self.assertEqual(len(self.connection_manager.list_connections()), 1)

        # Remove Tank A
        self.world_manager.delete_world(id_a)

        # Verify connection is gone
        self.assertEqual(len(self.connection_manager.list_connections()), 0)

    def test_cleanup_invalid_connections(self):
        """Test that validate_connections removes connections to missing tanks."""
        # Create connection between non-existent tanks
        conn = TankConnection(
            id="X->Y", source_world_id="tank_x", destination_world_id="tank_y", probability=25
        )
        self.connection_manager.add_connection(conn)

        # Verify connection exists
        self.assertEqual(len(self.connection_manager.list_connections()), 1)

        # Run validation with empty tank list
        removed = self.connection_manager.validate_connections([])

        # Verify connection is gone
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.connection_manager.list_connections()), 0)


if __name__ == "__main__":
    unittest.main()
