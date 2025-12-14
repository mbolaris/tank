"""Serializers for converting entities to Data Transfer Objects (DTOs).

This module handles the transformation of complex entity objects into
simple dictionaries suitable for JSON serialization and network transmission.
"""

from typing import Any, Dict, Optional, Union

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
        if fish.genome.behavior_algorithm:
            algo_name = fish.genome.behavior_algorithm.algorithm_id
        
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
            player_data["aggression"] = getattr(fish.genome, "aggression", 0.5)

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
        size = getattr(fish, "size", getattr(fish.genome, "size_modifier", 1.0))
        
        return {
            "speed": fish.genome.speed_modifier,
            "size": size,
            "color_hue": fish.genome.color_hue,
            "template_id": fish.genome.template_id,
            "fin_size": fish.genome.fin_size,
            "tail_size": fish.genome.tail_size,
            "body_aspect": fish.genome.body_aspect,
            "eye_size": fish.genome.eye_size,
            "pattern_intensity": fish.genome.pattern_intensity,
            "pattern_type": fish.genome.pattern_type,
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
