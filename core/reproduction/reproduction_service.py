"""Centralized reproduction service for all reproduction paths."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.reproduction.asexual_factory import (
    create_asexual_offspring,
    maybe_create_banked_offspring,
)
from core.reproduction.mutation_controller import DiversityMutationController
from core.reproduction.sexual_factory import (
    create_post_poker_offspring,
    run_proximity_mating_cycle,
)

if TYPE_CHECKING:
    from core.entities import Fish
    from core.genetics.reproduction import ReproductionMutationContext
    from core.poker.integration.poker_interaction import PokerInteraction
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class ReproductionFrameStats:
    """Per-frame reproduction summary."""

    banked_asexual: int = 0
    trait_asexual: int = 0
    proximity_sexual: int = 0
    emergency_spawns: int = 0

    @property
    def total(self) -> int:
        return (
            self.banked_asexual + self.trait_asexual + self.proximity_sexual + self.emergency_spawns
        )


class ReproductionService:
    """Single owner of reproduction rules (asexual, emergency, post-poker)."""

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine

        self._asexual_checks: int = 0
        self._asexual_triggered: int = 0
        self._banked_asexual_triggered: int = 0
        self._emergency_spawns: int = 0
        self._poker_reproductions: int = 0
        self._proximity_reproductions: int = 0
        self._plant_asexual_reproductions: int = 0
        self._mutation_controller = DiversityMutationController(
            diversity_score_provider=self._get_diversity_score,
            fish_provider=self._get_fish_entities,
        )

        try:
            cooldown = engine.config.ecosystem.emergency_spawn_cooldown
            self._last_emergency_spawn_frame = -cooldown
        except AttributeError:
            self._last_emergency_spawn_frame = -1000

    def update_frame(self, frame: int) -> ReproductionFrameStats:
        """Run reproduction logic for the current frame."""
        fish_list = self._get_fish_entities()
        self._update_cooldowns(fish_list)
        self._mutation_controller.record_diversity_sample(frame)

        fish_count = len(fish_list)

        proximity = self._handle_proximity_mating(fish_list, fish_count)
        fish_count += proximity

        banked = self._handle_banked_asexual_reproduction(fish_list, fish_count)
        fish_count += banked

        trait = self._handle_trait_asexual_reproduction(fish_list, fish_count)
        fish_count += trait

        emergency = self._handle_emergency_spawning(frame, fish_count)

        return ReproductionFrameStats(
            banked_asexual=banked,
            trait_asexual=trait,
            proximity_sexual=proximity,
            emergency_spawns=emergency,
        )

    def handle_post_poker_reproduction(self, poker: PokerInteraction) -> Fish | None:
        """Handle reproduction after a fish-fish poker game."""
        from core.config.fish import POST_POKER_MATING_DISTANCE
        from core.poker.integration.poker_interaction import (
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

        # Ecological viability guard (Proposal #86):
        # Skip spawning another baby if adult ratio or energy levels indicate famine.
        from core.config.fish import POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
        from core.entities.base import LifeStage

        fish_list = self._get_fish_entities()
        if fish_list:
            adult_count = sum(
                1 for f in fish_list if f.life_stage in (LifeStage.ADULT, LifeStage.ELDER)
            )
            adult_fraction = adult_count / len(fish_list)

            total_energy_ratio = sum(f.energy / max(f.max_energy, 1.0) for f in fish_list)
            mean_energy_ratio = total_energy_ratio / len(fish_list)

            if (
                adult_fraction < 0.25
                or mean_energy_ratio < POST_POKER_REPRODUCTION_ENERGY_THRESHOLD
            ):
                return None

        required_credits = self._get_repro_credit_required()
        if required_credits > 0 and not winner._reproduction_component.has_repro_credits(
            required_credits
        ):
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
            if not is_valid_reproduction_mate(fish, winner):
                continue
            eligible_mates.append(fish)

        if not eligible_mates:
            return None

        if not is_post_poker_reproduction_eligible(winner, eligible_mates[0]):
            return None

        mate = self._engine.rng.choice(eligible_mates)

        if self._engine.ecosystem is not None:
            if not self._engine.ecosystem.can_reproduce(
                len(self._engine.entity_manager.get_fish())
            ):
                return None

        baby = self._create_post_poker_offspring(winner, mate)
        if baby is None:
            return None

        if not self._engine.request_spawn(baby, reason="poker_reproduction"):
            return None
        if required_credits > 0:
            winner._reproduction_component.consume_repro_credits(required_credits)
        baby.register_birth()
        lifecycle_system = self._engine.lifecycle_system
        if lifecycle_system is not None:
            lifecycle_system.record_birth()

        self._poker_reproductions += 1
        return baby

    def handle_plant_poker_asexual_reproduction(self, winner_fish: Fish) -> Fish | None:
        """Handle asexual reproduction when fish beats only plants."""
        from core.mixed_poker import should_trigger_plant_poker_asexual_reproduction

        if not should_trigger_plant_poker_asexual_reproduction(winner_fish):
            return None

        required_credits = self._get_repro_credit_required()
        if required_credits > 0 and not winner_fish._reproduction_component.has_repro_credits(
            required_credits
        ):
            return None

        mutation_context = self._mutation_context_for_parents(winner_fish)
        baby = self.create_asexual_offspring(winner_fish, mutation_context=mutation_context)
        if baby is None:
            return None

        if self._engine.request_spawn(baby, reason="poker_reproduction"):
            baby.register_birth()
            if required_credits > 0:
                winner_fish._reproduction_component.consume_repro_credits(required_credits)
            self._plant_asexual_reproductions += 1
            return baby

        return None

    def get_debug_info(self) -> dict:
        """Return reproduction statistics for debugging."""
        return {
            "asexual_checks": self._asexual_checks,
            "asexual_triggered": self._asexual_triggered,
            "banked_asexual_triggered": self._banked_asexual_triggered,
            "emergency_spawns": self._emergency_spawns,
            "last_emergency_spawn_frame": self._last_emergency_spawn_frame,
            "poker_reproductions": self._poker_reproductions,
            "proximity_reproductions": self._proximity_reproductions,
            "plant_asexual_reproductions": self._plant_asexual_reproductions,
        }

    def _get_fish_entities(self) -> list[Fish]:
        return self._engine.entity_manager.get_fish()

    def _update_cooldowns(self, fish_list: list[Fish]) -> None:
        for fish in fish_list:
            fish._reproduction_component.update_cooldown()

    def _get_diversity_score(self) -> float | None:
        ecosystem = self._engine.ecosystem
        if ecosystem is None:
            return None
        diversity_stats = getattr(ecosystem, "genetic_diversity_stats", None)
        if diversity_stats is None:
            return None
        score = diversity_stats.get_diversity_score()
        return None if score is None else float(score)

    def _mutation_context_for_parents(self, *parents: Fish) -> ReproductionMutationContext:
        return self._mutation_controller.context_for_parents(*parents)

    def _handle_banked_asexual_reproduction(self, fish_list: list[Fish], fish_count: int) -> int:
        spawned = 0
        ecosystem = self._engine.ecosystem
        required_credits = self._get_repro_credit_required()

        if ecosystem is not None and fish_count >= ecosystem.max_population:
            return spawned

        for fish in fish_list:
            if ecosystem is not None and not ecosystem.can_reproduce(fish_count):
                break
            if required_credits > 0 and not fish._reproduction_component.has_repro_credits(
                required_credits
            ):
                continue

            mutation_context = self._mutation_context_for_parents(fish)
            baby = self.maybe_create_banked_offspring(fish, mutation_context=mutation_context)
            if baby is None:
                continue

            if self._engine.request_spawn(baby, reason="banked_asexual_reproduction"):
                baby.register_birth()
                lifecycle_system = self._engine.lifecycle_system
                if lifecycle_system is not None:
                    lifecycle_system.record_birth()
                if required_credits > 0:
                    fish._reproduction_component.consume_repro_credits(required_credits)
                self._banked_asexual_triggered += 1
                spawned += 1
                fish_count += 1

        return spawned

    def _handle_trait_asexual_reproduction(self, fish_list: list[Fish], fish_count: int) -> int:
        spawned = 0
        ecosystem = self._engine.ecosystem
        required_credits = self._get_repro_credit_required()

        if ecosystem is not None and fish_count >= ecosystem.max_population:
            return spawned

        for fish in fish_list:
            if required_credits > 0 and not fish._reproduction_component.has_repro_credits(
                required_credits
            ):
                continue
            life_stage = fish.life_stage
            if life_stage is None:
                continue
            if not fish._reproduction_component.can_asexually_reproduce(
                life_stage, fish.energy, fish.max_energy
            ):
                continue

            self._asexual_checks += 1
            asexual_trait = fish.genome.behavioral.asexual_reproduction_chance.value
            rng = fish.environment.rng
            if rng.random() < asexual_trait:
                mutation_context = self._mutation_context_for_parents(fish)
                try:
                    baby = fish._create_asexual_offspring(mutation_context=mutation_context)
                except TypeError:
                    baby = fish._create_asexual_offspring()
                if baby is not None:
                    if self._engine.request_spawn(baby, reason="asexual_reproduction"):
                        baby.register_birth()
                        if required_credits > 0:
                            fish._reproduction_component.consume_repro_credits(required_credits)
                        self._asexual_triggered += 1
                        spawned += 1
                        fish_count += 1

        return spawned

    def _handle_proximity_mating(self, fish_list: list[Fish], fish_count: int) -> int:
        spawned = run_proximity_mating_cycle(
            engine=self._engine,
            fish_list=fish_list,
            fish_count=fish_count,
            required_credits=self._get_repro_credit_required(),
            mutation_context_provider=self._mutation_context_for_parents,
        )
        self._proximity_reproductions += spawned
        return spawned

    def _handle_emergency_spawning(self, frame: int, fish_count: int) -> int:
        ecosystem = self._engine.ecosystem
        if ecosystem is None:
            return 0

        eco_cfg = self._engine.config.ecosystem

        if fish_count == 0:
            logger.info("Fish extinct! Force spawning...")
            if self._spawn_emergency_fish():
                self._last_emergency_spawn_frame = frame
                self._emergency_spawns += 1
                return 1
            return 0

        if fish_count >= eco_cfg.max_population:
            return 0

        frames_since_last_spawn = frame - self._last_emergency_spawn_frame
        if frames_since_last_spawn < eco_cfg.emergency_spawn_cooldown:
            return 0

        if fish_count < eco_cfg.critical_population_threshold:
            spawn_probability = 1.0
        else:
            population_ratio = (fish_count - eco_cfg.critical_population_threshold) / (
                eco_cfg.max_population - eco_cfg.critical_population_threshold
            )
            spawn_probability = (1.0 - population_ratio) ** 2 * 0.3

        if self._engine.rng.random() < spawn_probability:
            if self._spawn_emergency_fish():
                self._last_emergency_spawn_frame = frame
                self._emergency_spawns += 1
                if fish_count < eco_cfg.critical_population_threshold:
                    logger.info("Emergency fish spawned! fish_count now: %d", fish_count + 1)
                return 1

        return 0

    def _spawn_emergency_fish(self) -> bool:
        """Spawn an emergency fish to maintain population.

        Uses diversity-aware selection: instead of always cloning the healthiest
        fish, selects a parent that balances health with genetic uniqueness.
        This prevents emergency spawning from creating monocultures when the
        population is low.

        The cloned genome gets light mutation to maintain diversity.
        """
        from core import entities, movement_strategy
        from core.genetics import Genome

        environment = self._engine.environment
        ecosystem = self._engine.ecosystem
        if environment is None or ecosystem is None:
            return False

        # Try to clone from a surviving fish, using diversity-aware selection
        fish_list = self._get_fish_entities()
        if fish_list:
            parent = self._select_diverse_parent(fish_list)
            mutation_context = self._mutation_context_for_parents(parent)
            # Clone with light mutation to maintain diversity
            genome = Genome.clone_with_mutation(
                parent=parent.genome,
                rng=self._engine.rng,
                mutation_context=mutation_context,
            )
            generation = parent.generation  # Inherit generation for tracking
        else:
            # No fish to clone from - create random genome (extinction recovery)
            genome = Genome.random(use_algorithm=True, rng=self._engine.rng)
            generation = 0

        # Pool-aware per-kind policy mutation for emergency spawns
        pool = getattr(environment, "genome_code_pool", None)
        if pool is not None:
            from core.genetics.code_policy_traits import (
                mutate_code_policies,
                validate_code_policy_ids,
            )

            mutate_code_policies(genome.behavioral, pool, self._engine.rng)
            validate_code_policy_ids(genome.behavioral, pool, self._engine.rng)

        bounds = environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds
        spawn_margin = self._engine.config.ecosystem.spawn_margin_pixels
        x = self._engine.rng.randint(int(min_x) + spawn_margin, int(max_x) - spawn_margin)
        y = self._engine.rng.randint(int(min_y) + spawn_margin, int(max_y) - spawn_margin)

        # Pass parent_id so emergency clones appear in the lineage tree
        # under their donor rather than being orphaned to "root".
        parent_id = parent.fish_id if fish_list else None
        new_fish = entities.Fish(
            environment,
            movement_strategy.AlgorithmicMovement(),
            self._engine.config.display.files["schooling_fish"][0],
            x,
            y,
            4,
            genome=genome,
            generation=generation,
            ecosystem=ecosystem,
            parent_id=parent_id,
        )
        new_fish.register_birth()

        lifecycle_system = self._engine.lifecycle_system
        if lifecycle_system is not None:
            lifecycle_system.record_emergency_spawn()

        return bool(self._engine.request_spawn(new_fish, reason="emergency_spawn"))

    def _select_diverse_parent(self, fish_list: list[Fish]) -> Fish:
        """Select a parent for emergency spawning that balances health and diversity.

        Scores each fish by combining energy ratio (health) with a diversity bonus
        that rewards genetically unique individuals. This prevents emergency
        spawning from repeatedly cloning the same dominant genotype.

        For small populations (<=3), falls back to healthiest fish to avoid
        expensive diversity calculations when they don't matter much.

        Args:
            fish_list: Non-empty list of living fish

        Returns:
            Selected parent fish
        """
        if len(fish_list) <= 3:
            # Small population: just pick the healthiest
            return max(fish_list, key=lambda f: f.energy / max(f.max_energy, 1.0))

        from core.genetics.diversity import diversity_bonus

        genomes = [f.genome for f in fish_list]
        best_fish = fish_list[0]
        best_score = -1.0

        for i, fish in enumerate(fish_list):
            energy_ratio = fish.energy / max(fish.max_energy, 1.0)
            # Diversity bonus rewards genetically unique fish (0.0 to 0.15)
            d_bonus = diversity_bonus(genomes[i], genomes, sigma=0.5, bonus_weight=0.15)
            score = energy_ratio * 0.7 + d_bonus * 0.3 + (energy_ratio * d_bonus)
            if score > best_score:
                best_score = score
                best_fish = fish

        return best_fish

    def _get_repro_credit_required(self) -> float:
        soccer_cfg = self._engine.config.soccer
        if not soccer_cfg.enabled or soccer_cfg.repro_reward_mode != "credits":
            return 0.0
        return max(0.0, soccer_cfg.repro_credit_required)

    @staticmethod
    def maybe_create_banked_offspring(
        fish: Fish,
        mutation_context: ReproductionMutationContext | None = None,
    ) -> Fish | None:
        return maybe_create_banked_offspring(fish, mutation_context=mutation_context)

    def _create_post_poker_offspring(self, winner: Fish, mate: Fish) -> Fish | None:
        return create_post_poker_offspring(
            winner,
            mate,
            self._engine,
            self._mutation_context_for_parents(winner, mate),
        )

    @staticmethod
    def create_asexual_offspring(
        fish: Fish,
        mutation_context: ReproductionMutationContext | None = None,
    ) -> Fish | None:
        return create_asexual_offspring(fish, mutation_context=mutation_context)
