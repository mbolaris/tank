"""Serializers for converting entities to Data Transfer Objects (DTOs).

This module handles the transformation of complex entity objects into
simple dictionaries suitable for JSON serialization and network transmission.
"""

from typing import Any, Dict, Optional

from core.entities.fish import Fish
from core.entities.fractal_plant import FractalPlant
from core.plant_poker_strategy import PlantPokerStrategyAdapter


class FishSerializer:
    """Serializer for Fish entities."""

    @staticmethod
    def to_player_data(fish: Fish, include_aggression: bool = False) -> Dict[str, Any]:
        """Convert fish to poker player data dictionary.

        Args:
            fish: The fish entity
            include_aggression: If True, include aggression field for human poker games

        Returns:
            Dictionary with fish player data
        """
        algo_name = "Unknown"
        composable = fish.genome.behavioral.composable_behavior
        if composable and composable.value:
            algo_name = composable.value.short_description

        genome_data = FishSerializer.to_genome_data(fish)

        player_data = {
            "fish_id": fish.fish_id,
            "name": f"{algo_name[:15]} (Gen {fish.generation})",
            "generation": fish.generation,
            "energy": fish.energy,
            "algorithm": algo_name,
            "genome_data": genome_data,
        }

        if include_aggression:
            player_data["aggression"] = fish.genome.behavioral.aggression.value

        return player_data

    @staticmethod
    def to_genome_data(fish: Fish) -> Optional[Dict[str, Any]]:
        """Extract visual genome data for a fish to mirror tank rendering.

        Returns:
            Dictionary with visual traits or None if genome is missing
        """
        if not hasattr(fish, "genome"):
            return None

        # Handle potential missing attributes with defaults or safe access
        size = getattr(
            fish, "size", fish.genome.physical.size_modifier.value
        )

        return {
            "speed": fish.genome.speed_modifier,
            "size": size,
            "color_hue": fish.genome.physical.color_hue.value,
            "template_id": fish.genome.physical.template_id.value,
            "fin_size": fish.genome.physical.fin_size.value,
            "tail_size": fish.genome.physical.tail_size.value,
            "body_aspect": fish.genome.physical.body_aspect.value,
            "eye_size": fish.genome.physical.eye_size.value,
            "pattern_intensity": fish.genome.physical.pattern_intensity.value,
            "pattern_type": fish.genome.physical.pattern_type.value,
        }


class PlantSerializer:
    """Serializer for Plant entities."""

    @staticmethod
    def to_player_data(plant: FractalPlant) -> Dict[str, Any]:
        """Convert plant to poker player data dictionary.

        Args:
            plant: The plant entity

        Returns:
            Dictionary with plant player data
        """
        return {
            "plant_id": plant.plant_id,
            "name": f"Plant #{plant.plant_id}",
            "generation": getattr(plant, "generation", None),
            "energy": plant.energy,
            "species": "plant",
            "poker_strategy": PlantPokerStrategyAdapter.from_genome(plant.genome),
        }
