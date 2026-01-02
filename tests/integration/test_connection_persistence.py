#!/usr/bin/env python3
"""Test script to verify connection persistence works correctly."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.connection_manager import ConnectionManager, TankConnection
from backend.connection_persistence import load_connections, save_connections


def _run_connection_persistence():
    """Test that connections can be saved and restored."""
    print("=" * 60)
    print("Testing Connection Persistence")
    print("=" * 60)

    # Clean up any existing connections file
    connections_file = Path("data/connections.json")
    if connections_file.exists():
        print(f"Removing existing {connections_file}")
        connections_file.unlink()

    # Create a connection manager
    manager1 = ConnectionManager()

    # Add test connections
    print("\n1. Creating test connections...")
    test_connections = [
        TankConnection(
            id="tank1->tank2",
            source_tank_id="tank1-uuid-1234",
            destination_tank_id="tank2-uuid-5678",
            probability=25,
            direction="right",
        ),
        TankConnection(
            id="tank2->tank3",
            source_tank_id="tank2-uuid-5678",
            destination_tank_id="tank3-uuid-9012",
            probability=50,
            direction="left",
            source_server_id="server-a",
            destination_server_id="server-b",
        ),
        TankConnection(
            id="tank3->tank1",
            source_tank_id="tank3-uuid-9012",
            destination_tank_id="tank1-uuid-1234",
            probability=75,
            direction="right",
        ),
    ]

    for conn in test_connections:
        manager1.add_connection(conn)
        print(f"  Added: {conn.id} ({conn.probability}% {conn.direction})")

    # Save connections
    print("\n2. Saving connections to disk...")
    success = save_connections(manager1)
    print(f"  Save result: {'SUCCESS' if success else 'FAILED'}")

    if not success:
        print("❌ FAILED: Could not save connections")
        return False

    # Verify file exists
    if not connections_file.exists():
        print(f"❌ FAILED: File {connections_file} was not created")
        return False

    print(f"  File created: {connections_file}")

    # Read and display file contents
    with open(connections_file) as f:
        data = json.load(f)
    print(f"  File contains {len(data.get('connections', []))} connection(s)")

    # Create a new manager and load connections
    print("\n3. Loading connections from disk into new manager...")
    manager2 = ConnectionManager()
    restored_count = load_connections(manager2)
    print(f"  Restored {restored_count} connection(s)")

    if restored_count != len(test_connections):
        print(f"❌ FAILED: Expected {len(test_connections)} connections, got {restored_count}")
        return False

    # Verify each connection
    print("\n4. Verifying restored connections match originals...")
    all_match = True
    for original in test_connections:
        restored = manager2.get_connection(original.id)
        if not restored:
            print(f"  ❌ Connection {original.id} not found in restored manager")
            all_match = False
            continue

        # Check all fields match
        if (
            original.source_tank_id != restored.source_tank_id
            or original.destination_tank_id != restored.destination_tank_id
            or original.probability != restored.probability
            or original.direction != restored.direction
            or original.source_server_id != restored.source_server_id
            or original.destination_server_id != restored.destination_server_id
        ):
            print(f"  ❌ Connection {original.id} fields don't match")
            print(f"     Original: {original}")
            print(f"     Restored: {restored}")
            all_match = False
        else:
            print(f"  ✓ {original.id} matches")

    # Clean up
    print("\n5. Cleaning up test file...")
    connections_file.unlink()
    print(f"  Removed {connections_file}")

    # Final result
    print("\n" + "=" * 60)
    if all_match:
        print("✅ SUCCESS: All tests passed!")
        print("Connection persistence is working correctly.")
    else:
        print("❌ FAILED: Some connections did not match")
    print("=" * 60)

    return all_match


def test_connection_persistence():
    assert _run_connection_persistence()


if __name__ == "__main__":
    success = _run_connection_persistence()
    sys.exit(0 if success else 1)
