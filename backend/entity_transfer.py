"""Entity transfer logic for Tank World Net.

This module handles serialization and deserialization of entities
for transferring between tanks.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def serialize_entity_for_transfer(entity: Any, migration_direction: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Serialize an entity for transfer to another tank.

    Args:
        entity: The entity to serialize (Fish, FractalPlant, etc.)
        migration_direction: Optional direction of migration for plants ("left" or "right")

    Returns:
        Dictionary containing all entity state, or None if entity cannot be transferred
    """
    from core.entities.fish import Fish
    from core.entities.fractal_plant import FractalPlant

    if isinstance(entity, Fish):
        return _serialize_fish(entity)
    elif isinstance(entity, FractalPlant):
        return _serialize_plant(entity, migration_direction)
    else:
        # Food and other resources cannot be transferred
        logger.warning(f"Cannot transfer entity of type {type(entity).__name__}")
        return None


def _serialize_fish(fish: Any) -> Dict[str, Any]:
    """Serialize a Fish entity."""
    mutable_state = capture_fish_mutable_state(fish)
    return finalize_fish_serialization(fish, mutable_state)


def capture_fish_mutable_state(fish: Any) -> Dict[str, Any]:
    """Capture mutable state of a fish that must be read under lock."""
    # Capture genome parameters if they are mutable
    # We capture them as dicts here to ensure thread safety
    behavior_params = None
    if fish.genome.behavior_algorithm:
        behavior_params = fish.genome.behavior_algorithm.to_dict()
    
    poker_algo_params = None
    if fish.genome.poker_algorithm:
        poker_algo_params = fish.genome.poker_algorithm.to_dict()
        
    poker_strat_params = None
    if fish.genome.poker_strategy_algorithm:
        poker_strat_params = fish.genome.poker_strategy_algorithm.to_dict()

    return {
        "x": fish.pos.x,
        "y": fish.pos.y,
        "vel_x": fish.vel.x,
        "vel_y": fish.vel.y,
        "energy": fish.energy,
        "age": fish.age,
        "reproduction_cooldown": fish.reproduction_cooldown,
        "food_memories": list(fish.memory.food_memories) if hasattr(fish, "memory") else [],
        "predator_last_seen": fish.memory.predator_last_seen if hasattr(fish, "memory") else 0,
        # Capture algorithm states here as they might change
        "behavior_params": behavior_params,
        "poker_algo_params": poker_algo_params,
        "poker_strat_params": poker_strat_params,
    }


def finalize_fish_serialization(fish: Any, mutable_state: Dict[str, Any]) -> Dict[str, Any]:
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
        "max_age": fish.max_age,
        "generation": fish.generation,
        "parent_id": fish.parent_id if hasattr(fish, "parent_id") else None,
        "genome_data": {
            "size_modifier": fish.genome.size_modifier,
            "fertility": fish.genome.fertility,
            "color_hue": fish.genome.color_hue,
            "aggression": fish.genome.aggression,
            "social_tendency": fish.genome.social_tendency,
            "template_id": fish.genome.template_id,
            # New hunting traits
            "pursuit_aggression": fish.genome.pursuit_aggression,
            "prediction_skill": fish.genome.prediction_skill,
            "hunting_stamina": fish.genome.hunting_stamina,
            # Visual traits
            "fin_size": fish.genome.fin_size,
            "tail_size": fish.genome.tail_size,
            "body_aspect": fish.genome.body_aspect,
            "eye_size": fish.genome.eye_size,
            "pattern_intensity": fish.genome.pattern_intensity,
            "pattern_type": fish.genome.pattern_type,
            # Use captured params
            "behavior_algorithm": mutable_state["behavior_params"],
            "poker_algorithm": mutable_state["poker_algo_params"],
            "poker_strategy_algorithm": mutable_state["poker_strat_params"],
        },
        "memory": {
            "food_memories": mutable_state["food_memories"],
            "predator_last_seen": mutable_state["predator_last_seen"],
        },
        "reproduction_cooldown": mutable_state["reproduction_cooldown"],
    }


def _serialize_plant(plant: Any, migration_direction: Optional[str] = None) -> Dict[str, Any]:
    """Serialize a FractalPlant entity."""
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


def finalize_plant_serialization(plant: Any, mutable_state: Dict[str, Any]) -> Dict[str, Any]:
    """Construct full plant serialization using captured mutable state."""
    return {
        "type": "fractal_plant",
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
            "fractal_type": plant.genome.fractal_type,
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
    entity_type = data.get("type")

    if entity_type == "fish":
        return _deserialize_fish(data, target_world)
    elif entity_type == "fractal_plant":
        return _deserialize_plant(data, target_world)
    else:
        logger.error(f"Unknown entity type: {entity_type}")
        return None


def _deserialize_fish(data: Dict[str, Any], target_world: Any) -> Optional[Any]:
    """Deserialize and create a Fish entity."""
    try:
        from core.algorithms import behavior_from_dict
        from core.entities.fish import Fish
        from core.genetics import Genome
        from core.movement_strategy import AlgorithmicMovement

        # Recreate genome
        genome_data = data["genome_data"]

        # Create genome using random() then override with saved values
        genome = Genome.random()
        genome.size_modifier = genome_data.get("size_modifier", 1.0)
        genome.fertility = genome_data.get("fertility", 1.0)
        genome.color_hue = genome_data.get("color_hue", 0.5)
        genome.aggression = genome_data.get("aggression", 0.5)
        genome.social_tendency = genome_data.get("social_tendency", 0.5)
        genome.template_id = genome_data.get("template_id", 0)
        # Hunting traits (with defaults for old saves)
        genome.pursuit_aggression = genome_data.get("pursuit_aggression", 0.5)
        genome.prediction_skill = genome_data.get("prediction_skill", 0.5)
        genome.hunting_stamina = genome_data.get("hunting_stamina", 0.5)
        # Visual traits (with defaults for old saves)
        genome.fin_size = genome_data.get("fin_size", 1.0)
        genome.tail_size = genome_data.get("tail_size", 1.0)
        genome.body_aspect = genome_data.get("body_aspect", 1.0)
        genome.eye_size = genome_data.get("eye_size", 1.0)
        genome.pattern_intensity = genome_data.get("pattern_intensity", 0.5)
        genome.pattern_type = genome_data.get("pattern_type", 0)

        # Restore behavior algorithm if available
        if "behavior_algorithm" in genome_data and genome_data["behavior_algorithm"]:
            genome.behavior_algorithm = behavior_from_dict(genome_data["behavior_algorithm"])
            if genome.behavior_algorithm is None:
                logger.warning("Failed to deserialize behavior_algorithm; Fish.__init__ will assign random")

        # Restore poker algorithm if available
        if "poker_algorithm" in genome_data and genome_data["poker_algorithm"]:
            genome.poker_algorithm = behavior_from_dict(genome_data["poker_algorithm"])
            if genome.poker_algorithm is None:
                logger.warning("Failed to deserialize poker_algorithm; Fish.__init__ will assign random")

        # Restore poker strategy if available
        if "poker_strategy_algorithm" in genome_data and genome_data["poker_strategy_algorithm"]:
            from core.poker.strategy.implementations import PokerStrategyAlgorithm
            genome.poker_strategy_algorithm = PokerStrategyAlgorithm.from_dict(genome_data["poker_strategy_algorithm"])

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
            screen_width=target_world.config.screen_width,
            screen_height=target_world.config.screen_height,
            initial_energy=data["energy"],
            parent_id=data.get("parent_id"),
        )

        # Restore additional state via internal components (age/max_age are read-only properties)
        # Note: max_energy is now computed from fish size, not stored separately
        fish._lifecycle_component.age = data["age"]
        fish._lifecycle_component.max_age = data["max_age"]
        fish._lifecycle_component.update_life_stage()  # Update life stage based on restored age
        # max_energy is computed from size, so we don't restore it directly
        # Old saves may have max_energy, but it's ignored
        fish.vel.x = data["vel_x"]
        fish.vel.y = data["vel_y"]
        fish.reproduction_cooldown = data["reproduction_cooldown"]

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
    """Deserialize and create a FractalPlant entity."""
    try:
        from core.entities.fractal_plant import FractalPlant
        from core.plant_genetics import PlantGenome

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
            logger.warning("Cannot deserialize plant: no available root spots")
            return None

        # Recreate genome
        genome_data = data["genome_data"]
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
            nectar_threshold_ratio=genome_data.get("nectar_threshold_ratio", 0.75),
            fractal_type=genome_data.get("fractal_type", "lsystem"),
            # Floral traits
            floral_type=genome_data.get("floral_type", "spiral"),
            floral_petals=genome_data.get("floral_petals", 5),
            floral_layers=genome_data.get("floral_layers", 3),
            floral_spin=genome_data.get("floral_spin", 0.3),
            floral_hue=genome_data.get("floral_hue", 0.12),
            floral_saturation=genome_data.get("floral_saturation", 0.8),
        )

        # Create plant with proper constructor
        plant = FractalPlant(
            environment=target_world.engine.environment,
            genome=genome,
            root_spot=root_spot,
            initial_energy=data["energy"],
            screen_width=getattr(target_world.engine, 'screen_width', 800),
            screen_height=getattr(target_world.engine, 'screen_height', 600),
        )

        # Claim the spot for this plant
        root_spot.claim(plant)

        # Restore additional state
        plant.age = data["age"]
        plant.max_energy = data["max_energy"]
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
    except Exception as e:
        logger.error(f"Failed to deserialize plant: {e}", exc_info=True)
        return None
