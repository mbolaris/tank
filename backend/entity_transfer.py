"""Entity transfer logic for Tank World Net.

This module handles serialization and deserialization of entities
for transferring between tanks.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)

SerializedEntity = Dict[str, Any]
TRANSFER_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class TransferError:
    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


class NoRootSpotsError(Exception):
    """Raised when an entity cannot be deserialized because the target tank lacks root spots."""
    pass


@dataclass(frozen=True)
class TransferOutcome:
    value: Optional[Any] = None
    error: Optional[TransferError] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.value is not None


@dataclass(frozen=True)
class TransferContext:
    """Optional contextual information for transfers."""

    migration_direction: Optional[str] = None  # For plants: "left" or "right"


class EntityTransferCodec(Protocol):
    """Codec interface for a transferable entity type."""

    type_name: str

    def can_serialize(self, entity: Any) -> bool:
        """Return True if this codec can serialize *entity*."""

    def serialize(self, entity: Any, ctx: TransferContext) -> SerializedEntity:
        """Serialize *entity* into a JSON-compatible dict."""

    def deserialize(self, data: SerializedEntity, target_world: Any) -> Optional[Any]:
        """Deserialize *data* into an entity in *target_world*."""


class FishTransferCodec:
    type_name = "fish"

    def can_serialize(self, entity: Any) -> bool:
        from core.entities.fish import Fish

        return isinstance(entity, Fish)

    def serialize(self, entity: Any, ctx: TransferContext) -> Dict[str, Any]:
        return _serialize_fish(entity)

    def deserialize(self, data: SerializedEntity, target_world: Any) -> Optional[Any]:
        return _deserialize_fish(data, target_world)


class PlantTransferCodec:
    type_name = "plant"

    def can_serialize(self, entity: Any) -> bool:
        from core.entities.plant import Plant

        return isinstance(entity, Plant)

    def serialize(self, entity: Any, ctx: TransferContext) -> SerializedEntity:
        return _serialize_plant(entity, ctx.migration_direction)

    def deserialize(self, data: SerializedEntity, target_world: Any) -> Optional[Any]:
        return _deserialize_plant(data, target_world)


def _normalize_migration_direction(direction: Optional[str]) -> Optional[str]:
    if direction is None:
        return None
    if direction in {"left", "right"}:
        return direction
    logger.warning("Ignoring invalid migration_direction=%r (expected 'left' or 'right')", direction)
    return None


@dataclass
class TransferRegistry:
    """Registry of transfer codecs.

    This indirection keeps transfer policy (routing by type) separate from
    transfer mechanics (fish/plant serialization). The module exposes a
    DEFAULT_REGISTRY plus function wrappers for backward-compatible imports.
    """

    codecs: List[EntityTransferCodec] = field(default_factory=list)
    codecs_by_type: Dict[str, EntityTransferCodec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.codecs_by_type and self.codecs:
            self.codecs_by_type = {codec.type_name: codec for codec in self.codecs}

    def register(self, codec: EntityTransferCodec) -> None:
        existing = self.codecs_by_type.get(codec.type_name)
        if existing is not None and existing is not codec:
            try:
                self.codecs.remove(existing)
            except ValueError:
                pass
            logger.warning("Overriding existing transfer codec for type=%r", codec.type_name)

        self.codecs.append(codec)
        self.codecs_by_type[codec.type_name] = codec

    def codec_for_entity(self, entity: Any) -> Optional[EntityTransferCodec]:
        for codec in self.codecs:
            try:
                if codec.can_serialize(entity):
                    return codec
            except Exception:
                logger.debug(
                    "Transfer codec can_serialize failed (codec=%r entity=%r)",
                    getattr(codec, "type_name", type(codec).__name__),
                    type(entity).__name__,
                    exc_info=True,
                )
        return None

    def try_serialize_entity(
        self, entity: Any, ctx: TransferContext
    ) -> TransferOutcome:
        codec = self.codec_for_entity(entity)
        if codec is None:
            return TransferOutcome(
                error=TransferError(
                    code="unsupported_entity",
                    message=f"Cannot transfer entity of type {type(entity).__name__}",
                    context={"entity_type": type(entity).__name__},
                )
            )

        try:
            payload = codec.serialize(entity, ctx)
        except Exception as exc:
            return TransferOutcome(
                error=TransferError(
                    code="serialize_failed",
                    message=str(exc),
                    context={"codec": codec.type_name, "entity_type": type(entity).__name__},
                )
            )

        if not isinstance(payload, dict):
            return TransferOutcome(
                error=TransferError(
                    code="invalid_payload",
                    message="Transfer codec returned non-dict payload",
                    context={"codec": codec.type_name, "payload_type": type(payload).__name__},
                )
            )
        existing_type = payload.get("type")
        if existing_type is not None and existing_type != codec.type_name:
            return TransferOutcome(
                error=TransferError(
                    code="type_mismatch",
                    message="Transfer codec returned mismatched type field",
                    context={"codec": codec.type_name, "payload_type": existing_type},
                )
            )
        payload["type"] = codec.type_name
        payload.setdefault("schema_version", TRANSFER_SCHEMA_VERSION)
        return TransferOutcome(value=payload)

    def serialize_entity(self, entity: Any, ctx: TransferContext) -> Optional[SerializedEntity]:
        outcome = self.try_serialize_entity(entity, ctx)
        if not outcome.ok:
            logger.warning(
                "Serialize failed (code=%s entity_type=%s codec=%s): %s",
                outcome.error.code if outcome.error else "unknown",
                type(entity).__name__,
                outcome.error.context.get("codec") if outcome.error else None,
                outcome.error.message if outcome.error else "unknown error",
            )
            return None
        return outcome.value

    def try_deserialize_entity(self, data: SerializedEntity, target_world: Any) -> TransferOutcome:
        if not isinstance(data, dict):
            return TransferOutcome(
                error=TransferError(
                    code="invalid_payload",
                    message="Cannot deserialize entity: expected dict",
                    context={"payload_type": type(data).__name__},
                )
            )
        entity_type = data.get("type")
        if not entity_type:
            return TransferOutcome(
                error=TransferError(
                    code="missing_type",
                    message="Cannot deserialize entity: missing 'type' field",
                )
            )

        codec = self.codecs_by_type.get(entity_type)
        if codec is None:
            return TransferOutcome(
                error=TransferError(
                    code="unknown_type",
                    message=f"Unknown entity type: {entity_type}",
                    context={"entity_type": entity_type},
                )
            )

        try:
            entity = codec.deserialize(data, target_world)
        except NoRootSpotsError:
            return TransferOutcome(
                error=TransferError(
                    code="no_root_spots",
                    message="No available root spots",
                    context={"codec": codec.type_name, "entity_type": entity_type},
                )
            )
        except Exception as exc:
            return TransferOutcome(
                error=TransferError(
                    code="deserialize_failed",
                    message=str(exc),
                    context={"codec": codec.type_name, "entity_type": entity_type},
                )
            )
        if entity is None:
            return TransferOutcome(
                error=TransferError(
                    code="deserialize_returned_none",
                    message="Deserializer returned None",
                    context={"codec": codec.type_name, "entity_type": entity_type},
                )
            )
        return TransferOutcome(value=entity)

    def deserialize_entity(self, data: SerializedEntity, target_world: Any) -> Optional[Any]:
        outcome = self.try_deserialize_entity(data, target_world)
        if not outcome.ok:
            if outcome.error and outcome.error.code == "no_root_spots":
                # Suppress logging for common, expected failure case: no space for plant.
                return None

            logger.error(
                "Deserialize failed (code=%s entity_type=%s codec=%s): %s",
                outcome.error.code if outcome.error else "unknown",
                outcome.error.context.get("entity_type") if outcome.error else None,
                outcome.error.context.get("codec") if outcome.error else None,
                outcome.error.message if outcome.error else "unknown error",
            )
            return None
        return outcome.value


DEFAULT_REGISTRY = TransferRegistry(codecs=[FishTransferCodec(), PlantTransferCodec()])


def _require_keys(data: SerializedEntity, keys: List[str], *, entity_type: str) -> bool:
    missing = [key for key in keys if key not in data]
    if not missing:
        return True
    logger.error("Cannot deserialize %s: missing keys=%s", entity_type, missing)
    return False


def register_transfer_codec(codec: EntityTransferCodec) -> None:
    """Register a new transfer codec (extension point)."""

    DEFAULT_REGISTRY.register(codec)


def serialize_entity_for_transfer(
    entity: Any, migration_direction: Optional[str] = None
) -> Optional[SerializedEntity]:
    """Serialize an entity for transfer to another tank.

    Args:
        entity: The entity to serialize (Fish, Plant, etc.)
        migration_direction: Optional direction of migration for plants ("left" or "right")

    Returns:
        Dictionary containing all entity state, or None if entity cannot be transferred
    """
    ctx = TransferContext(migration_direction=_normalize_migration_direction(migration_direction))
    return DEFAULT_REGISTRY.serialize_entity(entity, ctx)


def try_serialize_entity_for_transfer(
    entity: Any, migration_direction: Optional[str] = None
) -> TransferOutcome:
    ctx = TransferContext(migration_direction=_normalize_migration_direction(migration_direction))
    return DEFAULT_REGISTRY.try_serialize_entity(entity, ctx)


def _serialize_fish(fish: Any) -> SerializedEntity:
    """Serialize a Fish entity."""
    mutable_state = capture_fish_mutable_state(fish)
    return finalize_fish_serialization(fish, mutable_state)


def capture_fish_mutable_state(fish: Any) -> Dict[str, Any]:
    """Capture mutable state of a fish that must be read under lock."""
    # Capture genome parameters if they are mutable
    # We capture them as dicts here to ensure thread safety
    genome_data = fish.genome.to_dict()

    return {
        "x": fish.pos.x,
        "y": fish.pos.y,
        "vel_x": fish.vel.x,
        "vel_y": fish.vel.y,
        "energy": fish.energy,
        "age": fish._lifecycle_component.age,
        "reproduction_cooldown": fish._reproduction_component.reproduction_cooldown,
        "food_memories": list(fish.memory.food_memories) if hasattr(fish, "memory") else [],
        "predator_last_seen": fish.memory.predator_last_seen if hasattr(fish, "memory") else 0,
        "genome_data": genome_data,
    }


def finalize_fish_serialization(fish: Any, mutable_state: Dict[str, Any]) -> SerializedEntity:
    """Construct full fish serialization using captured mutable state."""
    return {
        "type": "fish",
        "id": fish.fish_id,
        "species": fish.species,
        "x": mutable_state["x"],
        "y": mutable_state["y"],
        "vel_x": mutable_state["vel_x"],
        "vel_y": mutable_state["vel_y"],
        "speed": fish.speed,
        "energy": mutable_state["energy"],
        # max_energy is computed from size, not stored (removed in schema v2)
        "age": mutable_state["age"],
        "max_age": fish._lifecycle_component.max_age,
        "generation": fish.generation,
        "parent_id": fish.parent_id if hasattr(fish, "parent_id") else None,
        "genome_data": mutable_state["genome_data"],
        "memory": {
            "food_memories": mutable_state["food_memories"],
            "predator_last_seen": mutable_state["predator_last_seen"],
        },
        "reproduction_cooldown": mutable_state["reproduction_cooldown"],
    }


def _serialize_plant(plant: Any, migration_direction: Optional[str] = None) -> SerializedEntity:
    """Serialize a Plant entity."""
    mutable_state = capture_plant_mutable_state(plant, migration_direction)
    return finalize_plant_serialization(plant, mutable_state)


def capture_plant_mutable_state(plant: Any, migration_direction: Optional[str] = None) -> Dict[str, Any]:
    """Capture mutable state of a plant that must be read under lock."""
    # Get plant ID - try both id and plant_id
    plant_id = getattr(plant, 'id', getattr(plant, 'plant_id', None))
    # Get root spot ID if available
    root_spot_id = plant.root_spot.spot_id if hasattr(plant, 'root_spot') and plant.root_spot else None

    return {
        "id": plant_id,
        "x": plant.pos.x,
        "y": plant.pos.y,
        "root_spot_id": root_spot_id,
        "migration_direction": migration_direction,
        "energy": plant.energy,
        "age": plant.age,
        "poker_cooldown": getattr(plant, "poker_cooldown", 0),
        "nectar_cooldown": getattr(plant, "nectar_cooldown", 0),
        "poker_wins": getattr(plant, "poker_wins", 0),
        "poker_losses": getattr(plant, "poker_losses", 0),
        "nectar_produced": getattr(plant, "nectar_produced", 0),
        "growth_stage": plant.growth_stage if hasattr(plant, "growth_stage") else 1.0,
        "nectar_ready": plant.nectar_ready if hasattr(plant, "nectar_ready") else False,
    }


def finalize_plant_serialization(plant: Any, mutable_state: Dict[str, Any]) -> SerializedEntity:
    """Construct full plant serialization using captured mutable state."""
    return {
        "type": "plant",
        "id": mutable_state["id"],
        "x": mutable_state["x"],
        "y": mutable_state["y"],
        "root_spot_id": mutable_state["root_spot_id"],
        "migration_direction": mutable_state["migration_direction"],
        "energy": mutable_state["energy"],
        "max_energy": plant.max_energy,
        "age": mutable_state["age"],
        "generation": getattr(plant, "generation", 0),
        "poker_cooldown": mutable_state["poker_cooldown"],
        "nectar_cooldown": mutable_state["nectar_cooldown"],
        "poker_wins": mutable_state["poker_wins"],
        "poker_losses": mutable_state["poker_losses"],
        "nectar_produced": mutable_state["nectar_produced"],
        "genome_data": {
            "axiom": plant.genome.axiom,
            "angle": plant.genome.angle,
            "length_ratio": plant.genome.length_ratio,
            "branch_probability": plant.genome.branch_probability,
            "curve_factor": plant.genome.curve_factor,
            "color_hue": plant.genome.color_hue,
            "color_saturation": plant.genome.color_saturation,
            "stem_thickness": plant.genome.stem_thickness,
            "leaf_density": plant.genome.leaf_density,
            "aggression": plant.genome.aggression,
            "bluff_frequency": plant.genome.bluff_frequency,
            "risk_tolerance": plant.genome.risk_tolerance,
            "base_energy_rate": plant.genome.base_energy_rate,
            "growth_efficiency": plant.genome.growth_efficiency,
            "nectar_threshold_ratio": plant.genome.nectar_threshold_ratio,
            "type": plant.genome.type,
            "floral_type": plant.genome.floral_type,
            "floral_petals": plant.genome.floral_petals,
            "floral_layers": plant.genome.floral_layers,
            "floral_spin": plant.genome.floral_spin,
            "floral_hue": plant.genome.floral_hue,
            "floral_saturation": plant.genome.floral_saturation,
        },
        "growth_stage": mutable_state["growth_stage"],
        "nectar_ready": mutable_state["nectar_ready"],
    }


def deserialize_entity(data: Dict[str, Any], target_world: Any) -> Optional[Any]:
    """Deserialize entity data and create a new entity in the target world.

    Args:
        data: Serialized entity data
        target_world: TankWorld instance to add entity to

    Returns:
        The created entity, or None if deserialization failed
    """
    return DEFAULT_REGISTRY.deserialize_entity(data, target_world)


def try_deserialize_entity(data: Dict[str, Any], target_world: Any) -> TransferOutcome:
    return DEFAULT_REGISTRY.try_deserialize_entity(data, target_world)


def _deserialize_fish(data: Dict[str, Any], target_world: Any) -> Optional[Any]:
    """Deserialize and create a Fish entity."""
    try:
        from core.entities.fish import Fish
        from core.genetics import Genome
        from core.movement_strategy import AlgorithmicMovement

        if not _require_keys(
            data,
            ["genome_data", "species", "x", "y", "speed", "generation", "energy"],
            entity_type="fish",
        ):
            return None

        genome_data = data["genome_data"]
        if not isinstance(genome_data, dict):
            logger.error("Cannot deserialize fish: genome_data must be an object")
            return None
        rng = getattr(target_world, "rng", None)
        genome = Genome.from_dict(genome_data, rng=rng, use_algorithm=True)

        # Create movement strategy (AlgorithmicMovement uses genome from fish directly)
        movement = AlgorithmicMovement()

        # Create fish
        fish = Fish(
            environment=target_world.engine.environment,
            movement_strategy=movement,
            species=data["species"],
            x=data["x"],
            y=data["y"],
            speed=data["speed"],
            genome=genome,
            generation=data["generation"],
            fish_id=None,  # Will get new ID in target tank
            ecosystem=target_world.engine.ecosystem,
            initial_energy=data["energy"],
            parent_id=data.get("parent_id"),
            skip_birth_recording=True,  # Prevent phantom "soup_spawn" stats
        )
        fish._lifecycle_component.age = data.get("age", 0)
        if "max_age" in data:
            fish._lifecycle_component.max_age = data["max_age"]
        fish._lifecycle_component.update_life_stage()  # Update life stage based on restored age
        # max_energy is computed from size, so we don't restore it directly
        # Old saves may have max_energy, but it's ignored
        fish.vel.x = data.get("vel_x", 0.0)
        fish.vel.y = data.get("vel_y", 0.0)
        fish._reproduction_component.reproduction_cooldown = data.get("reproduction_cooldown", 0)

        # Restore memory (if applicable)
        if hasattr(fish, "memory") and "memory" in data:
            memory = data["memory"]
            fish.memory.food_memories = memory.get("food_memories", [])
            fish.memory.predator_last_seen = memory.get("predator_last_seen", 0)

        return fish
    except Exception as e:
        logger.error(f"Failed to deserialize fish: {e}", exc_info=True)
        return None


def _deserialize_plant(data: Dict[str, Any], target_world: Any) -> Optional[Any]:
    """Deserialize and create a Plant entity."""
    try:
        from core.entities.plant import Plant
        from core.genetics import PlantGenome

        if not _require_keys(
            data,
            ["genome_data", "x", "y", "energy", "age"],
            entity_type="plant",
        ):
            return None

        # Get root spot manager
        root_spot_manager = getattr(target_world.engine, 'root_spot_manager', None)
        if root_spot_manager is None:
            logger.error("Cannot deserialize plant: root_spot_manager not available")
            return None

        # Find the appropriate root spot
        root_spot = None
        migration_direction = data.get("migration_direction")

        # If plant is migrating, prefer edge spots on the opposite side
        if migration_direction is not None:
            # Plant migrating left appears on right edge, and vice versa
            preferred_edge = "right" if migration_direction == "left" else "left"
            root_spot = root_spot_manager.get_edge_empty_spot(preferred_edge)
            logger.debug(f"Plant migrating from {migration_direction}, placing at {preferred_edge} edge")

        # Fall back to exact spot ID if not migrating
        if root_spot is None:
            root_spot_id = data.get("root_spot_id")
            if root_spot_id is not None:
                root_spot = root_spot_manager.get_spot_by_id(root_spot_id)
                # If spot is occupied, try to claim it (will fail if occupied)
                if root_spot and root_spot.occupied:
                    # Spot is occupied, try to find nearest empty one
                    root_spot = None

        # If no spot by ID, find nearest empty spot to saved position
        if root_spot is None:
            root_spot = root_spot_manager.get_nearest_empty_spot(data["x"], data["y"])

        if root_spot is None:
            raise NoRootSpotsError("No available root spots")

        # Recreate genome
        genome_data = data["genome_data"]
        if not isinstance(genome_data, dict):
            logger.error("Cannot deserialize plant: genome_data must be an object")
            return None
        genome = PlantGenome(
            axiom=genome_data.get("axiom", "F"),
            angle=genome_data.get("angle", 25.0),
            length_ratio=genome_data.get("length_ratio", 0.7),
            branch_probability=genome_data.get("branch_probability", 0.85),
            curve_factor=genome_data.get("curve_factor", 0.1),
            color_hue=genome_data.get("color_hue", 0.33),
            color_saturation=genome_data.get("color_saturation", 0.7),
            stem_thickness=genome_data.get("stem_thickness", 1.0),
            leaf_density=genome_data.get("leaf_density", 0.6),
            aggression=genome_data.get("aggression", 0.4),
            bluff_frequency=genome_data.get("bluff_frequency", 0.15),
            risk_tolerance=genome_data.get("risk_tolerance", 0.5),
            base_energy_rate=genome_data.get("base_energy_rate", 0.02),
            growth_efficiency=genome_data.get("growth_efficiency", 1.0),
            nectar_threshold_ratio=genome_data.get("nectar_threshold_ratio", 0.95),
            type=genome_data.get("type") or genome_data.get("fractal_type", "lsystem"),
            # Floral traits
            floral_type=genome_data.get("floral_type", "spiral"),
            floral_petals=genome_data.get("floral_petals", 5),
            floral_layers=genome_data.get("floral_layers", 3),
            floral_spin=genome_data.get("floral_spin", 0.3),
            floral_hue=genome_data.get("floral_hue", 0.12),
            floral_saturation=genome_data.get("floral_saturation", 0.8),
        )

        # Create plant with proper constructor
        plant = Plant(
            environment=target_world.engine.environment,
            genome=genome,
            root_spot=root_spot,
            initial_energy=data["energy"],
            ecosystem=getattr(target_world.engine, "ecosystem", None),
        )

        # Claim the spot for this plant (may race with concurrent sprouting/migration).
        if not root_spot.claim(plant):
            raise NoRootSpotsError(f"Failed to claim root spot (spot_id={getattr(root_spot, 'spot_id', None)})")

        # Restore additional state
        plant.age = data.get("age", 0)
        if "max_energy" in data:
            plant.max_energy = data["max_energy"]
            if hasattr(plant, "_update_size"):
                plant._update_size()
        # Note: energy is already set via initial_energy parameter
        # Restore poker and nectar state
        if "poker_cooldown" in data:
            plant.poker_cooldown = data["poker_cooldown"]
        if "nectar_cooldown" in data:
            plant.nectar_cooldown = data["nectar_cooldown"]
        if "poker_wins" in data:
            plant.poker_wins = data["poker_wins"]
        if "poker_losses" in data:
            plant.poker_losses = data["poker_losses"]
        if "nectar_produced" in data:
            plant.nectar_produced = data["nectar_produced"]

        return plant
    except NoRootSpotsError:
        raise
    except Exception as e:
        logger.error(f"Failed to deserialize plant: {e}", exc_info=True)
        return None
