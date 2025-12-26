#!/usr/bin/env python3
"""Test script to verify connection bug fixes."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.connection_manager import ConnectionManager, TankConnection


def test_from_dict_validation():
    """Test that from_dict validates required fields."""
    print("\n" + "=" * 60)
    print("Testing from_dict() validation for required fields")
    print("=" * 60)

    # Test 1: Missing sourceId
    print("\n1. Testing missing sourceId...")
    try:
        TankConnection.from_dict({
            "destinationId": "tank2-uuid",
            "probability": 25,
        })
        print("  ❌ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")

    # Test 2: Missing destinationId
    print("\n2. Testing missing destinationId...")
    try:
        TankConnection.from_dict({
            "sourceId": "tank1-uuid",
            "probability": 25,
        })
        print("  ❌ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"  ✓ Correctly raised ValueError: {e}")

    # Test 3: Valid connection with both fields
    print("\n3. Testing valid connection data...")
    try:
        conn = TankConnection.from_dict({
            "sourceId": "tank1-uuid",
            "destinationId": "tank2-uuid",
            "probability": 25,
        })
        print(f"  ✓ Successfully created connection: {conn.id}")
    except Exception as e:
        print(f"  ❌ FAILED: Should not raise error: {e}")
        return False

    # Test 4: Valid connection with snake_case fields
    print("\n4. Testing valid connection with snake_case...")
    try:
        conn = TankConnection.from_dict({
            "source_tank_id": "tank1-uuid",
            "destination_tank_id": "tank2-uuid",
            "probability": 50,
        })
        print(f"  ✓ Successfully created connection: {conn.id}")
    except Exception as e:
        print(f"  ❌ FAILED: Should not raise error: {e}")
        return False

    print("\n✅ All validation tests passed!")
    return True


def test_validate_connections_preserves_remote():
    """Test that validate_connections preserves remote connections."""
    print("\n" + "=" * 60)
    print("Testing validate_connections() preserves remote connections")
    print("=" * 60)

    manager = ConnectionManager()

    # Add local connection (both ends on local server)
    print("\n1. Adding local connection...")
    local_conn = TankConnection(
        id="local-conn",
        source_tank_id="tank1-local",
        destination_tank_id="tank2-local",
        probability=25,
        direction="right",
    )
    manager.add_connection(local_conn)
    print(f"  Added: {local_conn.id}")

    # Add remote connection (different servers)
    print("\n2. Adding remote connection...")
    remote_conn = TankConnection(
        id="remote-conn",
        source_tank_id="tank1-server-a",
        destination_tank_id="tank2-server-b",
        probability=50,
        direction="right",
        source_server_id="server-a",
        destination_server_id="server-b",
    )
    manager.add_connection(remote_conn)
    print(f"  Added: {remote_conn.id}")

    # Add hybrid connection (local source, remote dest)
    print("\n3. Adding hybrid connection...")
    hybrid_conn = TankConnection(
        id="hybrid-conn",
        source_tank_id="tank1-local",
        destination_tank_id="tank3-server-c",
        probability=75,
        direction="left",
        source_server_id="local-server",
        destination_server_id="server-c",
    )
    manager.add_connection(hybrid_conn)
    print(f"  Added: {hybrid_conn.id}")

    # Validate with only local tank IDs
    print("\n4. Validating connections (only tank1-local is valid locally)...")
    valid_tank_ids = ["tank1-local"]
    removed_count = manager.validate_connections(valid_tank_ids, local_server_id="local-server")
    print(f"  Removed {removed_count} connection(s)")

    # Check which connections remain
    print("\n5. Checking remaining connections...")
    remaining = manager.list_connections()
    remaining_ids = {conn.id for conn in remaining}

    # Local connection with invalid destination should be removed
    if "local-conn" in remaining_ids:
        print(f"  ❌ FAILED: Local connection should have been removed (tank2-local is not valid)")
        return False
    else:
        print(f"  ✓ Local connection was removed (tank2-local is not valid)")

    # Remote connection should be preserved (can't validate remote tanks)
    if "remote-conn" not in remaining_ids:
        print(f"  ❌ FAILED: Remote connection should have been preserved")
        return False
    else:
        print(f"  ✓ Remote connection was preserved")

    # Hybrid connection should be preserved (destination is remote)
    if "hybrid-conn" not in remaining_ids:
        print(f"  ❌ FAILED: Hybrid connection should have been preserved")
        return False
    else:
        print(f"  ✓ Hybrid connection was preserved")

    print("\n✅ All validation preservation tests passed!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Connection Bug Fixes Test Suite")
    print("=" * 60)

    results = []

    # Test 1: from_dict validation
    results.append(("from_dict() validation", test_from_dict_validation()))

    # Test 2: validate_connections preserves remote
    results.append(("validate_connections() remote preservation", test_validate_connections_preserves_remote()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
