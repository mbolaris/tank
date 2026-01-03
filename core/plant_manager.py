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
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol

from core.config.display import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.config.plants import (
    PLANT_CRITICAL_POPULATION,
    PLANT_CULL_INTERVAL,
    PLANT_EMERGENCY_RESPAWN_COOLDOWN,
    PLANT_INITIAL_COUNT,
    PLANT_MATURE_ENERGY,
)
from core.config.server import PLANTS_ENABLED
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
        root_spot_manager: Optional["RootSpotManager"] = None,
    ) -> None:
        """Initialize the plant manager.

        Args:
            environment: Environment for spatial queries
            ecosystem: Ecosystem manager for tracking
            entity_adder: Interface for adding/removing entities
            rng: Random number generator (creates new one if None)
            screen_width: Width of the simulation area
            screen_height: Height of the simulation area
            root_spot_manager: Optional custom root spot manager
        """
        self.environment = environment
        self.ecosystem = ecosystem
        self._entity_adder = entity_adder
        from core.util.rng import require_rng_param

        self.rng = require_rng_param(rng, "__init__")

        # Initialize root spot manager
        if root_spot_manager is not None:
             self.root_spot_manager = root_spot_manager
        else:
             self.root_spot_manager = RootSpotManager(screen_width, screen_height, rng=self.rng)

        # Track reconciliation and respawns
        self._last_reconcile_frame: int = -1
        self._last_emergency_respawn_frame: int = -PLANT_EMERGENCY_RESPAWN_COOLDOWN

        # Deterministic ID generation for plants
        self._next_plant_id: int = 1

    def generate_plant_id(self) -> int:
        """Generate a deterministic, per-engine plant ID."""
        pid = self._next_plant_id
        self._next_plant_id += 1
        return pid

    def _request_spawn(self, entity: "Agent", *, reason: str) -> bool:
        """Request a spawn via the engine mutation queue when available."""
        requester = getattr(self._entity_adder, "request_spawn", None)
        if callable(requester):
            return requester(entity, reason=reason)
        self._entity_adder.add_entity(entity)
        return True

    def _request_remove(self, entity: "Agent", *, reason: str) -> bool:
        """Request a removal via the engine mutation queue when available."""
        requester = getattr(self._entity_adder, "request_remove", None)
        if callable(requester):
            return requester(entity, reason=reason)
        self._entity_adder.remove_entity(entity)
        return True

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

        Creates plants with random baseline poker strategy types. Each plant
        serves as a fixed "sparring partner" for fish to evolve against.

        Args:
            entities: Current entities (for variant balancing)

        Returns:
            Number of plants created
        """
        from core.plants.plant_strategy_types import get_random_strategy_type

        if not self.enabled:
            return 0

        created = 0
        for _ in range(PLANT_INITIAL_COUNT):
            spot = self.root_spot_manager.get_random_empty_spot()
            if spot is None:
                break

            # Create plant with random baseline strategy type
            strategy_type = get_random_strategy_type(rng=self.rng)
            genome = PlantGenome.create_from_strategy_type(strategy_type.value, rng=self.rng)

            plant = Plant(
                environment=self.environment,
                genome=genome,
                root_spot=spot,
                initial_energy=PLANT_MATURE_ENERGY,
                ecosystem=self.ecosystem,
                plant_id=self.generate_plant_id(),
            )

            if not spot.claim(plant):
                continue

            self._request_spawn(plant, reason="initial_plants")
            created += 1

        logger.info(f"Created {created} baseline strategy plants")
        return created

    def respawn_if_low(
        self,
        entities: List["Agent"],
        frame_count: int,
    ) -> bool:
        """Respawn a plant if the population is below minimum.

        Creates plants with random baseline poker strategy types.

        Args:
            entities: All entities in simulation
            frame_count: Current frame for interval checking

        Returns:
            True if a plant was spawned, False otherwise
        """
        from core.plants.plant_strategy_types import get_random_strategy_type

        if not self.enabled:
            return False

        plant_count = sum(1 for entity in entities if isinstance(entity, Plant))

        # Only respawn if below critical threshold
        if plant_count >= PLANT_CRITICAL_POPULATION:
            return False

        # Respect cooldown
        if frame_count - self._last_emergency_respawn_frame < PLANT_EMERGENCY_RESPAWN_COOLDOWN:
            return False

        spot = self.root_spot_manager.get_random_empty_spot()
        if spot is None:
            return False

        # Create plant with random baseline strategy type
        strategy_type = get_random_strategy_type(rng=self.rng)
        genome = PlantGenome.create_from_strategy_type(strategy_type.value, rng=self.rng)

        plant = Plant(
            environment=self.environment,
            genome=genome,
            root_spot=spot,
            initial_energy=PLANT_MATURE_ENERGY,  # Start at full energy
            ecosystem=self.ecosystem,
            plant_id=self.generate_plant_id(),
        )

        if not spot.claim(plant):
            return False

        if not self._request_spawn(plant, reason="emergency_respawn"):
            return False
        self._last_emergency_respawn_frame = frame_count
        logger.info(
            f"Plant respawned (pop={plant_count}, strategy={strategy_type.value}): #{plant.plant_id}"
        )
        return True

    def sprout_new_plant(
        self,
        parent_genome: PlantGenome,
        parent_x: float,
        parent_y: float,
        entities: List["Agent"],
    ) -> Result[Plant, str]:
        """Sprout a new plant from a parent.

        Called when fish consumes plant nectar. For baseline strategy plants,
        offspring is an exact clone of the parent's strategy type.

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

        # Create offspring genome - exact clone for baseline strategy plants
        offspring_genome = PlantGenome.from_parent(
            parent_genome,
            mutation_rate=0.15,
            mutation_strength=0.15,
            rng=self.rng,
        )

        plant = Plant(
            environment=self.environment,
            genome=offspring_genome,
            root_spot=spot,
            initial_energy=30.0,  # Enough to mature in reasonable time
            ecosystem=self.ecosystem,
            plant_id=self.generate_plant_id(),
        )

        if not spot.claim(plant):
            return Err(f"Failed to claim root spot at ({spot.x:.0f}, {spot.y:.0f})")

        self._request_spawn(plant, reason="sprout_new_plant")
        strategy_info = (
            f", strategy={parent_genome.strategy_type}" if parent_genome.strategy_type else ""
        )
        logger.debug(
            f"Sprouted new plant #{plant.plant_id} at ({spot.x:.0f}, {spot.y:.0f}){strategy_info}"
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
                logger.warning(f"Reconcile: Removing plant #{entity.plant_id} - no root_spot!")
                plants_to_remove.append(entity)
                continue

            if getattr(spot, "occupant", None) is entity:
                # Repair stale occupied flag if needed
                if not getattr(spot, "occupied", False):
                    spot.occupied = True
                continue

            # Occupant mismatch - log details
            occupant = getattr(spot, "occupant", None)
            occupant_id = getattr(occupant, "plant_id", "None") if occupant else "None"
            logger.warning(
                f"Reconcile: Removing plant #{entity.plant_id} - "
                f"spot #{spot.spot_id} occupant is #{occupant_id}, not #{entity.plant_id}"
            )
            plants_to_remove.append(entity)

        for plant in plants_to_remove:
            self._request_remove(plant, reason="reconcile_plants")

        if plants_to_remove:
            logger.info(f"Reconcile: Removed {len(plants_to_remove)} orphaned plants")

        return len(plants_to_remove)

    def get_occupied_count(self) -> int:
        """Get number of occupied root spots.

        Returns:
            Number of spots with plants
        """
        return self.root_spot_manager.get_occupied_count()
