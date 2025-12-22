"""Plant management system for fractal plant lifecycle.

This module extracts plant-related responsibilities from SimulationEngine
following the Single Responsibility Principle. PlantManager handles:
- Initial plant creation
- Plant spawning and sprouting
- Root spot management
- Variant selection (LLM beauty contest)
- Plant reconciliation

Design Notes:
    PlantManager receives dependencies via constructor injection rather than
    inheriting or tightly coupling to SimulationEngine. This makes it:
    - Easier to test in isolation
    - Reusable in different contexts
    - Clear about its dependencies
"""

import logging
import random
from typing import Callable, Dict, List, Optional, Protocol, TYPE_CHECKING

from core.config.plants import (
    PLANT_CULL_INTERVAL,
    PLANT_INITIAL_COUNT,
    PLANT_MATURE_ENERGY,
)
from core.config.server import PLANTS_ENABLED
from core.config.display import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.entities.plant import Plant
from core.genetics import PlantGenome
from core.result import Err, Ok, Result
from core.root_spots import RootSpotManager

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.entities import Agent
    from core.environment import Environment

logger = logging.getLogger(__name__)


class EntityAdder(Protocol):
    """Protocol for adding entities to the simulation."""

    def add_entity(self, entity: "Agent") -> None:
        """Add an entity to the simulation."""
        ...

    def remove_entity(self, entity: "Agent") -> None:
        """Remove an entity from the simulation."""
        ...


class PlantManager:
    """Manages fractal plant lifecycle in the simulation.

    This class encapsulates all plant-related logic that was previously
    spread across SimulationEngine, providing better separation of concerns.

    Attributes:
        root_spot_manager: Manages available planting locations
        environment: Spatial query interface
        ecosystem: Population and stats tracking
        rng: Random number generator for deterministic behavior
    """

    # LLM beauty contest variants (deterministic order for reproducibility)
    FRACTAL_VARIANTS = [
        "cosmic_fern",
        "claude",
        "antigravity",
        "gpt",
        "gpt_codex",
        "sonnet",
        "gemini",
        "lsystem",
    ]

    def __init__(
        self,
        environment: "Environment",
        ecosystem: "EcosystemManager",
        entity_adder: EntityAdder,
        rng: Optional[random.Random] = None,
        screen_width: int = SCREEN_WIDTH,
        screen_height: int = SCREEN_HEIGHT,
    ) -> None:
        """Initialize the plant manager.

        Args:
            environment: Environment for spatial queries
            ecosystem: Ecosystem manager for tracking
            entity_adder: Interface for adding/removing entities
            rng: Random number generator (creates new one if None)
            screen_width: Width of the simulation area
            screen_height: Height of the simulation area
        """
        self.environment = environment
        self.ecosystem = ecosystem
        self._entity_adder = entity_adder
        self.rng = rng if rng is not None else random.Random()

        # Initialize root spot manager
        self.root_spot_manager = RootSpotManager(screen_width, screen_height)

        # Track reconciliation for periodic cleanup
        self._last_reconcile_frame: int = -1

    @property
    def enabled(self) -> bool:
        """Whether plants are enabled in the simulation."""
        return PLANTS_ENABLED

    def block_spots_for_entity(self, entity: "Agent", padding: float = 10.0) -> None:
        """Block root spots near an entity to prevent plant overlap.

        Args:
            entity: Entity that occupies space
            padding: Extra space around entity to block
        """
        self.root_spot_manager.block_spots_for_entity(entity, padding=padding)

    def get_variant_counts(self, entities: List["Agent"]) -> Dict[str, int]:
        """Count plants by variant type.

        Args:
            entities: All entities in simulation

        Returns:
            Dictionary mapping variant names to counts
        """
        counts = dict.fromkeys(self.FRACTAL_VARIANTS, 0)
        for entity in entities:
            if isinstance(entity, Plant):
                variant = getattr(entity.genome, "type", "lsystem")
                if variant not in counts:
                    counts[variant] = 0
                counts[variant] += 1
        return counts

    def pick_balanced_variant(
        self,
        entities: List["Agent"],
        preferred_type: Optional[str] = None,
    ) -> str:
        """Select a variant that balances the LLM beauty contest.

        Prefers underrepresented variants so every LLM gets spotlight time.
        Green lsystem plants get 50% bias for a natural look.

        Args:
            entities: All entities to check current distribution
            preferred_type: Variant to keep in candidate pool

        Returns:
            Selected variant name
        """
        # 50% chance for green lsystem for natural appearance
        if self.rng.random() < 0.5:
            return "lsystem"

        counts = self.get_variant_counts(entities)
        min_count = min(counts.values()) if counts else 0
        underrepresented = [v for v, c in counts.items() if c == min_count]

        candidates = underrepresented.copy()
        if preferred_type and preferred_type not in candidates:
            candidates.append(preferred_type)

        return self.rng.choice(candidates)

    def create_variant_genome(
        self,
        variant: str,
        parent_genome: Optional[PlantGenome] = None,
    ) -> PlantGenome:
        """Create a genome for the specified variant.

        Args:
            variant: Variant type name
            parent_genome: Optional parent for inheritance

        Returns:
            New PlantGenome instance
        """
        variant_factories = {
            "cosmic_fern": PlantGenome.create_cosmic_fern_variant,
            "claude": PlantGenome.create_claude_variant,
            "antigravity": PlantGenome.create_antigravity_variant,
            "gpt": PlantGenome.create_gpt_variant,
            "gpt_codex": PlantGenome.create_gpt_codex_variant,
            "sonnet": PlantGenome.create_sonnet_variant,
            "gemini": PlantGenome.create_gemini_variant,
            "lsystem": PlantGenome.create_random,
        }

        # Inherit from parent if same variant
        if parent_genome and variant == parent_genome.type:
            return PlantGenome.from_parent(
                parent_genome,
                mutation_rate=0.15,
                mutation_strength=0.15,
                rng=self.rng,
            )

        factory = variant_factories.get(variant, PlantGenome.create_random)
        return factory(rng=self.rng)

    def create_initial_plants(self, entities: List["Agent"]) -> int:
        """Create the initial plant population.

        Args:
            entities: Current entities (for variant balancing)

        Returns:
            Number of plants created
        """
        if not self.enabled:
            return 0

        created = 0
        for _ in range(PLANT_INITIAL_COUNT):
            spot = self.root_spot_manager.get_random_empty_spot()
            if spot is None:
                break

            variant = self.pick_balanced_variant(entities)
            genome = self.create_variant_genome(variant)

            plant = Plant(
                environment=self.environment,
                genome=genome,
                root_spot=spot,
                initial_energy=PLANT_MATURE_ENERGY,
                ecosystem=self.ecosystem,
            )

            if not spot.claim(plant):
                continue

            self._entity_adder.add_entity(plant)
            created += 1

        logger.info(f"Created {created} initial fractal plants")
        return created

    def sprout_new_plant(
        self,
        parent_genome: PlantGenome,
        parent_x: float,
        parent_y: float,
        entities: List["Agent"],
    ) -> Result[Plant, str]:
        """Sprout a new plant from a parent.

        Called when fish consumes plant nectar.

        Args:
            parent_genome: Parent plant's genome
            parent_x: Parent X position
            parent_y: Parent Y position
            entities: Current entities for variant balancing

        Returns:
            Ok(plant) if successfully sprouted, Err(reason) otherwise
        """
        if not self.enabled:
            return Err("Plants are disabled")

        spot = self.root_spot_manager.find_spot_for_sprouting(parent_x, parent_y)
        if spot is None:
            return Err(f"No available root spot near ({parent_x:.0f}, {parent_y:.0f})")

        variant = self.pick_balanced_variant(
            entities, preferred_type=parent_genome.type
        )
        offspring_genome = self.create_variant_genome(variant, parent_genome=parent_genome)

        plant = Plant(
            environment=self.environment,
            genome=offspring_genome,
            root_spot=spot,
            initial_energy=30.0,  # Enough to mature in reasonable time
            ecosystem=self.ecosystem,
        )

        if not spot.claim(plant):
            return Err(f"Failed to claim root spot at ({spot.x:.0f}, {spot.y:.0f})")

        self._entity_adder.add_entity(plant)
        logger.debug(
            f"Sprouted new fractal plant #{plant.plant_id} at ({spot.x:.0f}, {spot.y:.0f})"
        )
        return Ok(plant)

    def reconcile_plants(
        self,
        entities: List["Agent"],
        frame_count: int,
    ) -> int:
        """Remove orphaned plants that don't own their root spot.

        Only one plant can own a RootSpot. This cleans up duplicates
        from concurrent migrations or sprouting.

        Args:
            entities: All entities in simulation
            frame_count: Current frame for interval checking

        Returns:
            Number of plants removed
        """
        if not self.enabled:
            return 0

        if PLANT_CULL_INTERVAL <= 0:
            return 0

        if frame_count - self._last_reconcile_frame < PLANT_CULL_INTERVAL:
            return 0

        self._last_reconcile_frame = frame_count

        plants_to_remove: List[Plant] = []
        for entity in entities:
            if not isinstance(entity, Plant):
                continue

            spot = getattr(entity, "root_spot", None)
            if spot is None:
                plants_to_remove.append(entity)
                continue

            if getattr(spot, "occupant", None) is entity:
                # Repair stale occupied flag if needed
                if not getattr(spot, "occupied", False):
                    spot.occupied = True
                continue

            plants_to_remove.append(entity)

        for plant in plants_to_remove:
            self._entity_adder.remove_entity(plant)

        return len(plants_to_remove)

    def get_occupied_count(self) -> int:
        """Get number of occupied root spots.

        Returns:
            Number of spots with plants
        """
        return self.root_spot_manager.get_occupied_count()
