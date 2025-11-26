import unittest
import logging
from backend.connection_manager import ConnectionManager, TankConnection
from backend.tank_registry import TankRegistry

# Configure logging to show info during tests
logging.basicConfig(level=logging.INFO)

class TestConnectorLogic(unittest.TestCase):
    def setUp(self):
        self.connection_manager = ConnectionManager()
        self.tank_registry = TankRegistry(create_default=False)
        self.tank_registry.set_connection_manager(self.connection_manager)

    def test_max_one_connector(self):
        """Test that adding a second connection between two tanks replaces the first."""
        # Create connection A -> B
        conn1 = TankConnection(
            id="A->B",
            source_tank_id="tank_a",
            destination_tank_id="tank_b",
            probability=25,
            direction="right"
        )
        self.connection_manager.add_connection(conn1)
        
        # Verify first connection exists
        self.assertEqual(len(self.connection_manager.list_connections()), 1)
        self.assertEqual(self.connection_manager.get_connection("A->B").probability, 25)

        # Create connection B -> A (should replace A->B)
        conn2 = TankConnection(
            id="B->A",
            source_tank_id="tank_b",
            destination_tank_id="tank_a",
            probability=50,
            direction="left"
        )
        self.connection_manager.add_connection(conn2)

        # Verify only one connection exists and it's the new one
        connections = self.connection_manager.list_connections()
        self.assertEqual(len(connections), 1)
        self.assertEqual(connections[0].id, "B->A")
        self.assertEqual(connections[0].probability, 50)

    def test_cascade_delete(self):
        """Test that removing a tank removes its connections."""
        # Create mock tanks
        tank_a = self.tank_registry.create_tank(name="Tank A", persistent=False)
        tank_b = self.tank_registry.create_tank(name="Tank B", persistent=False)
        
        id_a = tank_a.tank_id
        id_b = tank_b.tank_id
        
        # Create connection
        conn = TankConnection(
            id="A->B",
            source_tank_id=id_a,
            destination_tank_id=id_b,
            probability=25
        )
        self.connection_manager.add_connection(conn)
        
        # Verify connection exists
        self.assertEqual(len(self.connection_manager.list_connections()), 1)
        
        # Remove Tank A
        self.tank_registry.remove_tank(id_a)
        
        # Verify connection is gone
        self.assertEqual(len(self.connection_manager.list_connections()), 0)

    def test_cleanup_invalid_connections(self):
        """Test that validate_connections removes connections to missing tanks."""
        # Create connection between non-existent tanks
        conn = TankConnection(
            id="X->Y",
            source_tank_id="tank_x",
            destination_tank_id="tank_y",
            probability=25
        )
        self.connection_manager.add_connection(conn)
        
        # Verify connection exists
        self.assertEqual(len(self.connection_manager.list_connections()), 1)
        
        # Run validation with empty tank list
        removed = self.connection_manager.validate_connections([])
        
        # Verify connection is gone
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.connection_manager.list_connections()), 0)

if __name__ == '__main__':
    unittest.main()
