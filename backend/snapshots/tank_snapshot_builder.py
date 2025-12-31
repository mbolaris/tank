"""Tank-specific entity snapshot builder.

This module provides the TankSnapshotBuilder class that converts tank world
entities (Fish, Plant, Crab, Food, PlantNectar, Castle) to EntitySnapshot DTOs
for the frontend.

This is the reference implementation of the SnapshotBuilder protocol.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional, Set

from backend.state_payloads import EntitySnapshot
from core import entities

logger = logging.getLogger(__name__)


class TankSnapshotBuilder:
    """Build `EntitySnapshot` instances from tank world entities.

    This class implements the SnapshotBuilder protocol for tank-specific
    entity types: Fish, Plant, Crab, Food, PlantNectar, and Castle.

    It handles:
    - Stable ID generation for entities without intrinsic IDs
    - Z-ordering for proper rendering layers
    - Type-specific field extraction (genome data, effects, etc.)
    """

    def __init__(self) -> None:
        # Stable ID generation for entities without internal IDs (Food, PlantNectar, etc.)
        # Maps Python id() -> stable_id to avoid ID reuse when memory is recycled
        self._entity_stable_ids: Dict[int, int] = {}
        self._next_food_id: int = 0
        self._next_nectar_id: int = 0
        self._next_other_id: int = 0

    def collect(self, live_entities: Iterable[entities.Agent]) -> List[EntitySnapshot]:
        """Collect and sort snapshots for all *live_entities*.

        Also prunes stable-ID mappings for entities no longer present.
        """

        snapshots: List[EntitySnapshot] = []
        current_entity_ids: Set[int] = set()

        for entity in live_entities:
            current_entity_ids.add(id(entity))
            snapshot = self.to_snapshot(entity)
            if snapshot is not None:
                snapshots.append(snapshot)

        self._prune_stale_ids(current_entity_ids)

        z_order = {
            "castle": 0,
            "plant": 1,
            "plant_nectar": 2,  # Same layer as food
            "food": 2,
            "fish": 4,
            "crab": 10,  # Render crab in front of everything
        }
        snapshots.sort(key=lambda snapshot: z_order.get(snapshot.type, 999))
        return snapshots

    def build(
        self,
        step_result: Any,  # StepResult from core.worlds.interfaces
        world: Any,
    ) -> List[EntitySnapshot]:
        """Build snapshots from StepResult.

        For Tank, we still use entities_list from the world since that's
        the authoritative source of entity data. Future worlds may get
        entities directly from step_result.snapshot.

        Args:
            step_result: The StepResult from world.reset() or world.step()
            world: The world backend (TankWorldBackendAdapter or similar)

        Returns:
            List of EntitySnapshot DTOs sorted by z-order
        """
        # Tank uses entities_list directly - access via adapter's underlying world
        # TankWorldBackendAdapter exposes .world property for underlying TankWorld
        if hasattr(world, "world") and world.world is not None:
            entities = world.world.entities_list
        elif hasattr(world, "entities_list"):
            entities = world.entities_list
        else:
            entities = []
        return self.collect(entities)

    def _prune_stale_ids(self, current_entity_ids: Set[int]) -> None:
        stale_ids = set(self._entity_stable_ids.keys()) - current_entity_ids
        for stale_id in stale_ids:
            del self._entity_stable_ids[stale_id]

    def to_snapshot(self, entity: entities.Agent) -> Optional[EntitySnapshot]:
        """Convert a single entity to an `EntitySnapshot`."""

        try:
            from core.config.entities import (
                FISH_ID_OFFSET,
                FOOD_ID_OFFSET,
                NECTAR_ID_OFFSET,
                PLANT_ID_OFFSET,
            )

            stable_id: int
            python_id = id(entity)

            if isinstance(entity, entities.Fish) and hasattr(entity, "fish_id"):
                stable_id = entity.fish_id + FISH_ID_OFFSET
            elif isinstance(entity, entities.Plant) and hasattr(entity, "plant_id"):
                stable_id = entity.plant_id + PLANT_ID_OFFSET
            elif isinstance(entity, entities.PlantNectar):
                if python_id in self._entity_stable_ids:
                    stable_id = self._entity_stable_ids[python_id]
                else:
                    stable_id = self._next_nectar_id + NECTAR_ID_OFFSET
                    self._entity_stable_ids[python_id] = stable_id
                    self._next_nectar_id += 1
            elif isinstance(entity, entities.Food):
                if python_id in self._entity_stable_ids:
                    stable_id = self._entity_stable_ids[python_id]
                else:
                    stable_id = self._next_food_id + FOOD_ID_OFFSET
                    self._entity_stable_ids[python_id] = stable_id
                    self._next_food_id += 1
            else:
                if python_id in self._entity_stable_ids:
                    stable_id = self._entity_stable_ids[python_id]
                else:
                    stable_id = self._next_other_id + 5_000_000  # Offset for other entities
                    self._entity_stable_ids[python_id] = stable_id
                    self._next_other_id += 1

            base_data = {
                "id": stable_id,
                "x": round(entity.pos.x, 2),
                "y": round(entity.pos.y, 2),
                "width": round(entity.width, 2),
                "height": round(entity.height, 2),
                "vel_x": round(entity.vel.x, 2) if hasattr(entity, "vel") else 0,
                "vel_y": round(entity.vel.y, 2) if hasattr(entity, "vel") else 0,
            }

            if isinstance(entity, entities.Fish):
                genome_data = None
                if hasattr(entity, "genome"):
                    genome_data = {
                        "speed": round(entity.genome.speed_modifier, 2),
                        "size": round(entity._lifecycle_component.size, 2),  # Includes baby stage growth
                        "color_hue": round(entity.genome.physical.color_hue.value, 3),
                        "template_id": entity.genome.physical.template_id.value,
                        "fin_size": round(entity.genome.physical.fin_size.value, 2),
                        "tail_size": round(entity.genome.physical.tail_size.value, 2),
                        "body_aspect": round(entity.genome.physical.body_aspect.value, 2),
                        "eye_size": round(entity.genome.physical.eye_size.value, 2),
                        "pattern_intensity": round(entity.genome.physical.pattern_intensity.value, 2),
                        "pattern_type": entity.genome.physical.pattern_type.value,
                    }

                species_label = None
                sprite_name = getattr(entity, "species", "")
                if "george" in sprite_name:
                    species_label = "solo"
                elif "school" in sprite_name:
                    species_label = "schooling"

                if species_label is None and hasattr(entity, "genome"):
                    behavior_algorithm = entity.genome.behavioral.behavior_algorithm.value
                    algo_id = getattr(behavior_algorithm, "algorithm_id", "").lower()
                    if "neural" in algo_id:
                        species_label = "neural"
                    elif "school" in algo_id:
                        species_label = "schooling"
                    else:
                        species_label = "algorithmic"

                return EntitySnapshot(
                    type="fish",
                    energy=round(entity.energy, 1),
                    generation=entity.generation if hasattr(entity, "generation") else 0,
                    age=entity._lifecycle_component.age,
                    species=species_label,
                    genome_data=genome_data,
                    poker_effect_state=entity.visual_state.poker_effect_state
                    if hasattr(entity, "visual_state")
                    else None,
                    birth_effect_timer=entity.visual_state.birth_effect_timer
                    if hasattr(entity, "visual_state")
                    else 0,
                    death_effect_state=entity.visual_state.death_effect_state
                    if hasattr(entity, "visual_state")
                    else None,
                    max_energy=round(entity.max_energy, 1) if hasattr(entity, "max_energy") else 100.0,
                    **base_data,
                )

            if isinstance(entity, entities.PlantNectar):
                source_plant = getattr(entity, "source_plant", None)
                source_plant_id = id(source_plant) if source_plant is not None else None

                # Default to nectar position if a source plant is unavailable.
                source_plant_x = (
                    source_plant.pos.x + source_plant.width / 2
                    if source_plant is not None
                    else entity.pos.x
                )
                source_plant_y = (
                    source_plant.pos.y + source_plant.height
                    if source_plant is not None
                    else entity.pos.y
                )

                genome = getattr(source_plant, "genome", None)
                floral_type = getattr(genome, "floral_type", 0)
                floral_petals = getattr(genome, "floral_petals", 0)
                floral_layers = getattr(genome, "floral_layers", 0)
                floral_spin = getattr(genome, "floral_spin", 0)
                floral_hue = getattr(genome, "floral_hue", 0)
                floral_saturation = getattr(genome, "floral_saturation", 0)

                return EntitySnapshot(
                    type="plant_nectar",
                    energy=round(entity.energy, 1) if hasattr(entity, "energy") else 50,
                    source_plant_id=source_plant_id,
                    source_plant_x=round(source_plant_x, 2),
                    source_plant_y=round(source_plant_y, 2),
                    floral_type=floral_type,
                    floral_petals=floral_petals,
                    floral_layers=floral_layers,
                    floral_spin=round(floral_spin, 2),
                    floral_hue=round(floral_hue, 3),
                    floral_saturation=round(floral_saturation, 2),
                    **base_data,
                )

            if isinstance(entity, entities.Food):
                return EntitySnapshot(
                    type="food",
                    food_type=entity.food_type if hasattr(entity, "food_type") else 0,
                    **base_data,
                )

            if isinstance(entity, entities.Plant):
                genome_dict = None
                if hasattr(entity, "genome"):
                    g = entity.genome
                    # Optimize: Send only visual traits and use compact rule format
                    genome_dict = {
                        "axiom": g.axiom,
                        "angle": round(g.angle, 2),
                        "length_ratio": round(g.length_ratio, 2),
                        "branch_probability": round(g.branch_probability, 2),
                        "curve_factor": round(g.curve_factor, 2),
                        "color_hue": round(g.color_hue, 3),
                        "color_saturation": round(g.color_saturation, 2),
                        "stem_thickness": round(g.stem_thickness, 2),
                        "leaf_density": round(g.leaf_density, 2),
                        "type": g.type,
                        # Floral traits
                        "floral_type": g.floral_type,
                        "floral_petals": g.floral_petals,
                        "floral_layers": g.floral_layers,
                        "floral_spin": round(g.floral_spin, 2),
                        "floral_hue": round(g.floral_hue, 3),
                        "floral_saturation": round(g.floral_saturation, 2),
                        # Compact rules: [[inp, out, prob], ...] instead of list of dicts
                        "production_rules": [
                            [inp, out, prob] for inp, out, prob in g._production_rules
                        ],
                    }

                return EntitySnapshot(
                    type="plant",
                    energy=round(entity.energy, 1) if hasattr(entity, "energy") else 0,
                    max_energy=round(entity.max_energy, 1) if hasattr(entity, "max_energy") else 100,
                    genome=genome_dict,
                    size_multiplier=entity.get_size_multiplier()
                    if hasattr(entity, "get_size_multiplier")
                    else 1.0,
                    iterations=entity.get_fractal_iterations()
                    if hasattr(entity, "get_fractal_iterations")
                    else 3,
                    nectar_ready=entity.nectar_cooldown == 0
                    and entity.energy >= 50.0
                    and entity.energy / entity.max_energy >= 0.90
                    if hasattr(entity, "nectar_cooldown")
                    else False,
                    age=entity.age if hasattr(entity, "age") else 0,
                    plant_type=2,  # Mark as fractal-capable for backward compat if needed
                    poker_effect_state=entity.poker_effect_state
                    if hasattr(entity, "poker_effect_state")
                    else None,
                    **base_data,
                )

            if isinstance(entity, entities.Crab):
                return EntitySnapshot(
                    type="crab",
                    energy=entity.energy if hasattr(entity, "energy") else 100,
                    can_hunt=entity.can_hunt() if hasattr(entity, "can_hunt") else True,
                    **base_data,
                )

            if isinstance(entity, entities.Castle):
                return EntitySnapshot(type="castle", **base_data)

            return None
        except Exception as exc:
            logger.error("Error converting entity to snapshot: %s", exc, exc_info=True)
            return None
