"""Entity transfer logic for Tank World Net.

This module handles serialization and deserialization of entities
for transferring between tanks.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def serialize_entity_for_transfer(entity: Any) -> Optional[Dict[str, Any]]:
    """Serialize an entity for transfer to another tank.

    Args:
        entity: The entity to serialize (Fish, FractalPlant, etc.)

    Returns:
        Dictionary containing all entity state, or None if entity cannot be transferred
    """
    from core.entities.fish import Fish
    from core.entities.fractal_plant import FractalPlant

    if isinstance(entity, Fish):
        return _serialize_fish(entity)
    elif isinstance(entity, FractalPlant):
        return _serialize_plant(entity)
    else:
        # Food and other resources cannot be transferred
        logger.warning(f"Cannot transfer entity of type {type(entity).__name__}")
        return None


def _serialize_fish(fish: Any) -> Dict[str, Any]:
    """Serialize a Fish entity."""
    return {
        "type": "fish",
        "id": fish.fish_id,
        "species": fish.species,
        "x": fish.pos.x,
        "y": fish.pos.y,
        "vel_x": fish.vel.x,
        "vel_y": fish.vel.y,
        "speed": fish.speed,
        "energy": fish.energy,
        "max_energy": fish.max_energy,
        "age": fish.age,
        "max_age": fish.max_age,
        "generation": fish.generation,
        "parent_id": fish.parent_id if hasattr(fish, "parent_id") else None,
        "genome_data": {
            "speed_modifier": fish.genome.speed_modifier,
            "size_modifier": fish.genome.size_modifier,
            "vision_range": fish.genome.vision_range,
            "metabolism_rate": fish.genome.metabolism_rate,
            "max_energy": fish.genome.max_energy,
            "fertility": fish.genome.fertility,
            "color_hue": fish.genome.color_hue,
            "aggression": fish.genome.aggression,
            "social_tendency": fish.genome.social_tendency,
            "template_id": fish.genome.template_id,
            # Skip algorithms for now - they don't have to_dict methods
            # "behavior_algorithm": fish.genome.behavior_algorithm.to_dict() if fish.genome.behavior_algorithm else None,
            "poker_strategy_algorithm": fish.genome.poker_strategy_algorithm.to_dict() if fish.genome.poker_strategy_algorithm else None,
        },
        "memory": {
            "food_memories": list(fish.memory.food_memories) if hasattr(fish, "memory") else [],
            "predator_last_seen": fish.memory.predator_last_seen if hasattr(fish, "memory") else 0,
        },
        "reproduction_cooldown": fish.reproduction_cooldown,
    }


def _serialize_plant(plant: Any) -> Dict[str, Any]:
    """Serialize a FractalPlant entity."""
    # Get plant ID - try both id and plant_id
    plant_id = getattr(plant, 'id', getattr(plant, 'plant_id', None))
    return {
        "type": "fractal_plant",
        "id": plant_id,
        "x": plant.pos.x,
        "y": plant.pos.y,
        "energy": plant.energy,
        "max_energy": plant.max_energy,
        "age": plant.age,
        "generation": getattr(plant, "generation", 0),  # FractalPlant doesn't have generation
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
            "fitness_score": plant.genome.fitness_score,
        },
        "growth_stage": plant.growth_stage if hasattr(plant, "growth_stage") else 1.0,
        "nectar_ready": plant.nectar_ready if hasattr(plant, "nectar_ready") else False,
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
        from core.entities.fish import Fish
        from core.genetics import Genome
        from core.movement_strategy import AlgorithmicMovement

        # Recreate genome
        genome_data = data["genome_data"]

        # Skip recreating behavior algorithms for now
        # They will be created randomly when the fish is initialized

        genome = Genome(
            speed_modifier=genome_data.get("speed_modifier", 1.0),
            size_modifier=genome_data.get("size_modifier", 1.0),
            vision_range=genome_data.get("vision_range", 1.0),
            metabolism_rate=genome_data.get("metabolism_rate", 1.0),
            max_energy=genome_data.get("max_energy", 1.0),
            fertility=genome_data.get("fertility", 1.0),
            color_hue=genome_data.get("color_hue", 0.5),
            aggression=genome_data.get("aggression", 0.5),
            social_tendency=genome_data.get("social_tendency", 0.5),
            template_id=genome_data.get("template_id", 0),
            # behavior_algorithm will be set by Fish.__init__
        )

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

        # Restore additional state via internal components (age/max_age/max_energy are read-only properties)
        fish._lifecycle_component.age = data["age"]
        fish._lifecycle_component.max_age = data["max_age"]
        fish._lifecycle_component.update_life_stage()  # Update life stage based on restored age
        fish._energy_component.max_energy = data["max_energy"]
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
            floral_type=genome_data.get("floral_type", "spiral"),
            floral_petals=genome_data.get("floral_petals", 5),
            floral_layers=genome_data.get("floral_layers", 3),
            floral_spin=genome_data.get("floral_spin", 0.3),
            floral_hue=genome_data.get("floral_hue", 0.12),
            floral_saturation=genome_data.get("floral_saturation", 0.8),
            fitness_score=genome_data.get("fitness_score", 0.0),
        )

        # Create plant
        plant = FractalPlant(
            x=data["x"],
            y=data["y"],
            plant_type=data.get("plant_type", genome_data.get("fractal_type", "lsystem")),
            genome=genome,
            generation=data.get("generation", 0),
            environment=target_world.engine.environment,
            ecosystem=target_world.engine.ecosystem,
        )

        # Restore additional state
        plant.age = data["age"]
        plant.energy = data["energy"]
        plant.max_energy = data["max_energy"]
        if hasattr(plant, "growth_stage"):
            plant.growth_stage = data.get("growth_stage", 1.0)
        if hasattr(plant, "nectar_ready"):
            plant.nectar_ready = data.get("nectar_ready", False)

        return plant
    except Exception as e:
        logger.error(f"Failed to deserialize plant: {e}", exc_info=True)
        return None
