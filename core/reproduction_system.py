"""Population recovery and asexual reproduction system.

This module handles population maintenance and asexual reproduction:
1. Asexual reproduction triggered by genetic traits
2. Emergency spawning when population is critically low

NOTE: Sexual reproduction (mating after poker games) is handled by PokerSystem.
This system focuses on maintaining minimum population levels and asexual traits.

The system extends BaseSystem for consistent interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.REPRODUCTION
- Manages population recovery (emergency spawns)
- Tracks reproduction statistics for debugging

Why "ReproductionSystem" and not "PopulationRecoverySystem"?
------------------------------------------------------------
The name is kept for backward compatibility with tests and documentation.
The key thing to understand is the responsibility split:
- This system: asexual reproduction + emergency spawning
- PokerSystem: sexual reproduction (mating after poker wins)
"""

import logging
import random
from typing import TYPE_CHECKING, Any, Dict

from core import movement_strategy
from core.genetics import Genome
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


@runs_in_phase(UpdatePhase.REPRODUCTION)
class ReproductionSystem(BaseSystem):
    """Handle asexual reproduction and emergency population recovery.

    This system runs in the REPRODUCTION phase and manages:
    - Asexual reproduction checks (genetic trait-based)
    - Emergency population recovery when fish count is critical

    NOTE: Sexual reproduction (mating) is handled by PokerSystem after
    poker game wins. This system only handles asexual + emergency spawns.
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the reproduction system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, "Reproduction")
        self._asexual_checks: int = 0
        self._asexual_triggered: int = 0
        self._emergency_spawns: int = 0
        
        # Initialize last spawn frame based on config
        # Use a safe default if config isn't fully loaded yet
        try:
            cooldown = engine.config.ecosystem.emergency_spawn_cooldown
            self._last_emergency_spawn_frame = -cooldown
        except AttributeError:
            self._last_emergency_spawn_frame = -1000

    def _do_update(self, frame: int) -> SystemResult:
        """Check for reproduction events each frame.

        Args:
            frame: Current simulation frame number

        Returns:
            SystemResult with reproduction statistics
        """
        initial_asexual = self._asexual_triggered
        initial_emergency = self._emergency_spawns

        # 1. Check asexual reproduction
        self._handle_asexual_reproduction()
        
        # 2. Check emergency spawning
        self._handle_emergency_spawning(frame)

        # Calculate deltas
        asexual_count = self._asexual_triggered - initial_asexual
        emergency_count = self._emergency_spawns - initial_emergency

        return SystemResult(
            entities_affected=asexual_count + emergency_count,
            details={
                "asexual_triggered": asexual_count,
                "emergency_spawns": emergency_count,
            },
        )

    def _handle_asexual_reproduction(self) -> None:
        """Handle fish reproduction by checking for asexual reproduction."""
        from core.entities import Fish

        # Note: We use engine.get_all_entities() which delegates to EntityManager
        # Using specific list getter is faster if available
        if hasattr(self._engine, "get_fish_list"):
            fish_list = self._engine.get_fish_list()
        else:
            all_entities = self._engine.get_all_entities()
            fish_list = [e for e in all_entities if isinstance(e, Fish)]

        if len(fish_list) < 1:
            return
        
        # Skip reproduction if at max population
        ecosystem = self._engine.ecosystem
        if ecosystem is not None and len(fish_list) >= ecosystem.max_population:
            return

        for fish in fish_list:
            if not fish._reproduction_component.can_asexually_reproduce(
                fish._lifecycle_component.life_stage, fish.energy, fish.max_energy
            ):
                continue

            self._asexual_checks += 1

            # Access the trait correctly
            asexual_trait = fish.genome.behavioral.asexual_reproduction_chance.value
            # Use environment RNG for determinism
            rng = getattr(fish.environment, "rng", random)
            if rng.random() < asexual_trait:
                # Trigger instant asexual reproduction
                baby = fish._create_asexual_offspring()
                if baby is not None:
                    # Add baby to simulation
                    self._engine.add_entity(baby)
                    baby.register_birth()
                    self._asexual_triggered += 1

    def _handle_emergency_spawning(self, frame: int) -> None:
        """Handle emergency spawning when population is critical."""
        ecosystem = self._engine.ecosystem
        if ecosystem is None:
            return

        # Get current fish count
        if hasattr(self._engine, "get_fish_list"):
            fish_list = self._engine.get_fish_list()
        else:
            from core.entities import Fish
            fish_list = [e for e in self._engine.get_all_entities() if isinstance(e, Fish)]
            
        fish_count = len(fish_list)
        eco_cfg = self._engine.config.ecosystem

        # Always spawn if fish are extinct
        if fish_count == 0:
            logger.info("Fish extinct! Force spawning...")
            self._spawn_emergency_fish()
            self._last_emergency_spawn_frame = frame
            self._emergency_spawns += 1
            return

        # Check if population is low
        if fish_count >= eco_cfg.max_population:
            return

        # Check cooldown
        frames_since_last_spawn = frame - self._last_emergency_spawn_frame
        if frames_since_last_spawn < eco_cfg.emergency_spawn_cooldown:
            return

        # Calculate probability
        if fish_count < eco_cfg.critical_population_threshold:
            spawn_probability = 1.0
        else:
            population_ratio = (fish_count - eco_cfg.critical_population_threshold) / (
                eco_cfg.max_population - eco_cfg.critical_population_threshold
            )
            spawn_probability = (1.0 - population_ratio) ** 2 * 0.3

        # Attempt spawn
        if self._engine.rng.random() < spawn_probability:
            self._spawn_emergency_fish()
            self._last_emergency_spawn_frame = frame
            self._emergency_spawns += 1
            
            # Log significant spawns
            if fish_count < eco_cfg.critical_population_threshold:
                logger.info(f"Emergency fish spawned! fish_count now: {fish_count + 1}")

    def _spawn_emergency_fish(self) -> None:
        """Spawn a new fish with random genome."""
        from core import entities
        
        environment = self._engine.environment
        ecosystem = self._engine.ecosystem
        if environment is None or ecosystem is None:
            return

        # Generate random genome
        genome = Genome.random(use_algorithm=True, rng=self._engine.rng)

        # Pick random position with margin
        bounds = environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds
        spawn_margin = self._engine.config.ecosystem.spawn_margin_pixels
        x = self._engine.rng.randint(int(min_x) + spawn_margin, int(max_x) - spawn_margin)
        y = self._engine.rng.randint(int(min_y) + spawn_margin, int(max_y) - spawn_margin)

        # Create fish
        new_fish = entities.Fish(
            environment,
            movement_strategy.AlgorithmicMovement(),
            self._engine.config.display.files["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=0,
            ecosystem=ecosystem,
        )
        new_fish.register_birth()
        
        # Record stats via lifecycle system if available
        if hasattr(self._engine, "lifecycle_system"):
            self._engine.lifecycle_system.record_emergency_spawn()

        self._engine.add_entity(new_fish)

    def get_debug_info(self) -> Dict[str, Any]:
        """Return reproduction statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "asexual_checks": self._asexual_checks,
            "asexual_triggered": self._asexual_triggered,
            "emergency_spawns": self._emergency_spawns,
            "last_emergency_spawn_frame": self._last_emergency_spawn_frame,
            "trigger_rate": (
                self._asexual_triggered / self._asexual_checks
                if self._asexual_checks > 0
                else 0.0
            ),
        }
