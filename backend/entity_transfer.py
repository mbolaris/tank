"""Entity transfer logic for Tank World Net.

This module is a compatibility shim exporting symbols from core.transfer.entity_transfer.
"""

from core.transfer.entity_transfer import (
    DEFAULT_REGISTRY,
    TRANSFER_SCHEMA_VERSION,
    EntityTransferCodec,
    FishTransferCodec,
    NoRootSpotsError,
    PlantTransferCodec,
    SerializedEntity,
    TransferContext,
    TransferError,
    TransferOutcome,
    TransferRegistry,
    _deserialize_fish,
    capture_fish_mutable_state,
    capture_plant_mutable_state,
    deserialize_entity,
    finalize_fish_serialization,
    finalize_plant_serialization,
    register_transfer_codec,
    serialize_entity_for_transfer,
    try_deserialize_entity,
    try_serialize_entity_for_transfer,
)

# Re-export for compatibility
__all__ = [
    "DEFAULT_REGISTRY",
    "EntityTransferCodec",
    "FishTransferCodec",
    "NoRootSpotsError",
    "PlantTransferCodec",
    "SerializedEntity",
    "TRANSFER_SCHEMA_VERSION",
    "TransferContext",
    "TransferError",
    "TransferOutcome",
    "TransferRegistry",
    "capture_fish_mutable_state",
    "capture_plant_mutable_state",
    "deserialize_entity",
    "finalize_fish_serialization",
    "finalize_plant_serialization",
    "register_transfer_codec",
    "serialize_entity_for_transfer",
    "try_deserialize_entity",
    "try_serialize_entity_for_transfer",
    "_deserialize_fish",
]
