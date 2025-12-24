"""Pytest configuration for integration tests.

All tests in this directory are automatically marked as integration tests.
"""

import pytest


# Mark all tests in this directory as integration tests
def pytest_collection_modifyitems(items):
    """Auto-mark all tests in tests/integration/ as integration tests."""
    for item in items:
        if "/integration/" in str(item.fspath) or "\\integration\\" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
