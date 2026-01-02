import pytest
import backend.entity_transfer
import core.transfer.entity_transfer


def test_backend_entity_transfer_public_api():
    """Ensure backend.entity_transfer exports key symbols for backward compatibility.

    This test guards against silent breaking changes where symbols move in `core`
    but aren't re-exported by the `backend` shim.
    """
    required_symbols = [
        "serialize_entity_for_transfer",
        "deserialize_entity",
        "_deserialize_fish",  # Legacy private symbol that some tests rely on
    ]

    for symbol in required_symbols:
        assert hasattr(
            backend.entity_transfer, symbol
        ), f"backend.entity_transfer missing required symbol: {symbol}"

        # Verify it's the same object as the core implementation
        backend_obj = getattr(backend.entity_transfer, symbol)
        core_obj = getattr(core.transfer.entity_transfer, symbol)

        assert (
            backend_obj is core_obj
        ), f"backend.entity_transfer.{symbol} should alias core.transfer.entity_transfer.{symbol}"


def test_backend_exports_defined():
    """Ensure __all__ is defined and contains our promises."""
    assert hasattr(backend.entity_transfer, "__all__")

    promises = [
        "serialize_entity_for_transfer",
        "deserialize_entity",
        "_deserialize_fish",
    ]

    for promise in promises:
        assert promise in backend.entity_transfer.__all__
