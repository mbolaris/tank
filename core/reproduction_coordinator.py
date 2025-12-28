"""Reproduction coordination for all reproduction events.

This module centralizes all reproduction logic:
- Post-poker sexual reproduction (fish + fish)
- Post-poker asexual reproduction (fish beats plants)
- Integration with ReproductionSystem for asexual/emergency spawns

This follows the Single Responsibility Principle - PokerSystem handles poker,
ReproductionCoordinator handles reproduction triggered by any source.
"""

import logging
import random
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from core.entities import Fish
    from core.poker_interaction import PokerInteraction
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


class ReproductionCoordinator:
    """Single owner of ALL post-poker reproduction logic.
    
    This coordinator extracts reproduction logic from PokerSystem to ensure:
    1. PokerSystem focuses solely on poker game mechanics
    2. Reproduction logic is centralized and testable
    3. Energy transfers and spawning are coordinated properly
    """
    
    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the reproduction coordinator.
        
        Args:
            engine: The simulation engine
        """
        self._engine = engine
        self._poker_reproductions: int = 0
        self._asexual_reproductions: int = 0
    
    @property
    def rng(self) -> random.Random:
        """Get the engine's RNG for deterministic behavior."""
        return self._engine.rng
    
    def handle_post_poker_reproduction(
        self, poker: "PokerInteraction"
    ) -> Optional["Fish"]:
        """Handle reproduction after a fish-fish poker game.
        
        The winner of a poker game may reproduce with a nearby fish of the same
        species. This is sexual reproduction triggered by poker victory.
        
        Args:
            poker: The completed poker interaction
            
        Returns:
            The offspring if reproduction occurred, None otherwise
        """
        from core.entities import Fish
        from core.config.fish import POST_POKER_MATING_DISTANCE
        from core.poker_interaction import (
            is_post_poker_reproduction_eligible,
            is_valid_reproduction_mate,
        )
        
        result = getattr(poker, "result", None)
        if result is None or getattr(result, "is_tie", False):
            return None

        if getattr(result, "fish_count", 0) < 2:
            return None

        if getattr(result, "winner_type", "") != "fish":
            return None

        fish_players = getattr(poker, "fish_players", [])
        winner = None
        for player in fish_players:
            if poker._get_player_id(player) == result.winner_id:
                winner = player
                break

        if winner is None or getattr(winner, "environment", None) is None:
            return None

        max_dist_sq = POST_POKER_MATING_DISTANCE * POST_POKER_MATING_DISTANCE
        winner_cx = winner.pos.x + winner.width * 0.5
        winner_cy = winner.pos.y + winner.height * 0.5

        eligible_mates = []
        for fish in fish_players:
            if fish is winner:
                continue
            if fish.species != winner.species:
                continue
            if hasattr(fish, "is_dead") and fish.is_dead():
                continue
            dx = (fish.pos.x + fish.width * 0.5) - winner_cx
            dy = (fish.pos.y + fish.height * 0.5) - winner_cy
            if dx * dx + dy * dy > max_dist_sq:
                continue
            # Mate only needs to be adult + same species (no energy requirement)
            if not is_valid_reproduction_mate(fish, winner):
                continue
            eligible_mates.append(fish)

        if not eligible_mates:
            return None

        if not is_post_poker_reproduction_eligible(winner, eligible_mates[0]):
            return None

        # Winner-driven reproduction: if winner is eligible, they pick a mate
        mate = self.rng.choice(eligible_mates)

        if self._engine.ecosystem is not None:
            if not self._engine.ecosystem.can_reproduce(len(self._engine.get_fish_list())):
                return None

        baby = self._create_post_poker_offspring(winner, mate)
        if baby is None:
            return None

        if not self._request_spawn(baby, reason="poker_reproduction"):
            return None
        baby.register_birth()
        if hasattr(self._engine, "lifecycle_system"):
            self._engine.lifecycle_system.record_birth()
        
        self._poker_reproductions += 1
        return baby

    def handle_plant_poker_asexual_reproduction(
        self, winner_fish: "Fish"
    ) -> Optional["Fish"]:
        """Handle asexual reproduction when fish beats only plants.
        
        When a fish wins a poker game against only plants (no other fish),
        they may reproduce asexually based on their genetic traits.
        
        Args:
            winner_fish: The fish that won against plants
            
        Returns:
            The offspring if reproduction occurred, None otherwise
        """
        from core.mixed_poker import should_trigger_plant_poker_asexual_reproduction
        
        if not should_trigger_plant_poker_asexual_reproduction(winner_fish):
            return None
        
        # Trigger instant asexual reproduction
        baby = winner_fish._create_asexual_offspring()
        if baby is None:
            return None
        
        if self._request_spawn(baby, reason="poker_reproduction"):
            baby.register_birth()
            self._asexual_reproductions += 1
            return baby
        
        return None

    def _create_post_poker_offspring(
        self, winner: "Fish", mate: "Fish"
    ) -> Optional["Fish"]:
        """Create an offspring from poker winner and mate.
        
        The offspring's genome is a weighted blend of both parents, with the
        winner having higher weight. Energy is contributed by both parents.
        
        Args:
            winner: The poker winner (primary parent)
            mate: The mating partner
            
        Returns:
            The offspring fish, or None if creation failed
        """
        from core.entities import Fish
        from core.config.fish import (
            ENERGY_MAX_DEFAULT,
            FISH_BABY_SIZE,
            FISH_BASE_SPEED,
            POST_POKER_CROSSOVER_WINNER_WEIGHT,
            POST_POKER_MUTATION_RATE,
            POST_POKER_MUTATION_STRENGTH,
            POST_POKER_PARENT_ENERGY_CONTRIBUTION,
            REPRODUCTION_COOLDOWN,
        )
        from core.genetics import Genome, ReproductionParams
        
        if winner.environment is None:
            return None

        offspring_genome = Genome.from_parents_weighted_params(
            parent1=winner.genome,
            parent2=mate.genome,
            parent1_weight=POST_POKER_CROSSOVER_WINNER_WEIGHT,
            params=ReproductionParams(
                mutation_rate=POST_POKER_MUTATION_RATE,
                mutation_strength=POST_POKER_MUTATION_STRENGTH,
            ),
            rng=self.rng,
        )

        baby_max_energy = (
            ENERGY_MAX_DEFAULT
            * FISH_BABY_SIZE
            * offspring_genome.physical.size_modifier.value
        )
        if baby_max_energy <= 0:
            return None

        winner_contrib = max(0.0, winner.energy * POST_POKER_PARENT_ENERGY_CONTRIBUTION)
        mate_contrib = max(0.0, mate.energy * POST_POKER_PARENT_ENERGY_CONTRIBUTION)
        total_contrib = winner_contrib + mate_contrib
        if total_contrib <= 0:
            return None

        if total_contrib > baby_max_energy:
            scale = baby_max_energy / total_contrib
            winner_contrib *= scale
            mate_contrib *= scale
            total_contrib = baby_max_energy

        winner.energy = max(0.0, winner.energy - winner_contrib)
        mate.energy = max(0.0, mate.energy - mate_contrib)

        winner._reproduction_component.reproduction_cooldown = max(
            winner._reproduction_component.reproduction_cooldown,
            REPRODUCTION_COOLDOWN,
        )
        mate._reproduction_component.reproduction_cooldown = max(
            mate._reproduction_component.reproduction_cooldown,
            REPRODUCTION_COOLDOWN,
        )

        (min_x, min_y), (max_x, max_y) = winner.environment.get_bounds()
        mid_x = (winner.pos.x + mate.pos.x) * 0.5
        mid_y = (winner.pos.y + mate.pos.y) * 0.5
        baby_x = mid_x + self.rng.uniform(-30, 30)
        baby_y = mid_y + self.rng.uniform(-30, 30)
        baby_x = max(min_x, min(max_x - 50, baby_x))
        baby_y = max(min_y, min(max_y - 50, baby_y))

        baby = Fish(
            environment=winner.environment,
            movement_strategy=winner.movement_strategy.__class__(),
            species=winner.species,
            x=baby_x,
            y=baby_y,
            speed=FISH_BASE_SPEED,
            genome=offspring_genome,
            generation=max(winner.generation, mate.generation) + 1,
            ecosystem=winner.ecosystem,
            initial_energy=total_contrib,
            parent_id=winner.fish_id,
        )

        if winner.ecosystem is not None:
            composable = winner.genome.behavioral.behavior
            if composable is not None and composable.value is not None:
                behavior_id = composable.value.behavior_id
                algorithm_id = hash(behavior_id) % 1000
                winner.ecosystem.record_reproduction(algorithm_id, is_asexual=False)
            winner.ecosystem.record_mating_attempt(True)

        winner.visual_state.set_birth_effect(60)
        mate.visual_state.set_birth_effect(60)

        source_parent = (
            winner
            if self.rng.random() < POST_POKER_CROSSOVER_WINNER_WEIGHT
            else mate
        )
        baby._skill_game_component.inherit_from_parent(
            source_parent._skill_game_component,
            mutation_rate=POST_POKER_MUTATION_RATE,
        )

        return baby

    def _request_spawn(self, entity: "Fish", *, reason: str) -> bool:
        """Request a spawn via the engine, if available."""
        request_spawn = getattr(self._engine, "request_spawn", None)
        if not callable(request_spawn):
            return False
        return bool(request_spawn(entity, reason=reason))
    
    def get_debug_info(self) -> dict:
        """Return reproduction statistics for debugging."""
        return {
            "poker_reproductions": self._poker_reproductions,
            "asexual_reproductions": self._asexual_reproductions,
            "total_reproductions": self._poker_reproductions + self._asexual_reproductions,
        }
