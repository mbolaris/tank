"""Centralized reproduction service for all reproduction paths."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.energy.energy_utils import apply_energy_delta

if TYPE_CHECKING:
    from core.entities import Fish
    from core.poker_interaction import PokerInteraction
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class ReproductionFrameStats:
    """Per-frame reproduction summary."""

    banked_asexual: int = 0
    trait_asexual: int = 0
    emergency_spawns: int = 0

    @property
    def total(self) -> int:
        return self.banked_asexual + self.trait_asexual + self.emergency_spawns


class ReproductionService:
    """Single owner of reproduction rules (asexual, emergency, post-poker)."""

    def __init__(self, engine: SimulationEngine) -> None:
        self._engine = engine

        self._asexual_checks: int = 0
        self._asexual_triggered: int = 0
        self._banked_asexual_triggered: int = 0
        self._emergency_spawns: int = 0
        self._poker_reproductions: int = 0
        self._plant_asexual_reproductions: int = 0

        try:
            cooldown = engine.config.ecosystem.emergency_spawn_cooldown
            self._last_emergency_spawn_frame = -cooldown
        except AttributeError:
            self._last_emergency_spawn_frame = -1000

    def update_frame(self, frame: int) -> ReproductionFrameStats:
        """Run reproduction logic for the current frame."""
        fish_list = self._get_fish_list()
        self._update_cooldowns(fish_list)

        fish_count = len(fish_list)

        banked = self._handle_banked_asexual_reproduction(fish_list, fish_count)
        fish_count += banked

        trait = self._handle_trait_asexual_reproduction(fish_list, fish_count)
        fish_count += trait

        emergency = self._handle_emergency_spawning(frame, fish_count)

        return ReproductionFrameStats(
            banked_asexual=banked,
            trait_asexual=trait,
            emergency_spawns=emergency,
        )

    def handle_post_poker_reproduction(self, poker: PokerInteraction) -> Fish | None:
        """Handle reproduction after a fish-fish poker game."""
        from core.config.fish import POST_POKER_MATING_DISTANCE
        from core.poker_interaction import (
            is_post_poker_reproduction_eligible, is_valid_reproduction_mate)

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
            if not self._engine.ecosystem.can_reproduce(len(self._engine.get_fish_list())):
                return None

        baby = self._create_post_poker_offspring(winner, mate)
        if baby is None:
            return None

        if not self._engine.request_spawn(baby, reason="poker_reproduction"):
            return None
        if required_credits > 0:
            winner._reproduction_component.consume_repro_credits(required_credits)
        baby.register_birth()
        lifecycle_system = getattr(self._engine, "lifecycle_system", None)
        if lifecycle_system is not None:
            lifecycle_system.record_birth()

        self._poker_reproductions += 1
        return baby

    def handle_plant_poker_asexual_reproduction(self, winner_fish: Fish) -> Fish | None:
        """Handle asexual reproduction when fish beats only plants."""
        from core.mixed_poker import \
            should_trigger_plant_poker_asexual_reproduction

        if not should_trigger_plant_poker_asexual_reproduction(winner_fish):
            return None

        required_credits = self._get_repro_credit_required()
        if required_credits > 0 and not winner_fish._reproduction_component.has_repro_credits(
            required_credits
        ):
            return None

        baby = winner_fish._create_asexual_offspring()
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
            "plant_asexual_reproductions": self._plant_asexual_reproductions,
        }

    def _get_fish_list(self) -> list[Fish]:
        if hasattr(self._engine, "get_fish_list"):
            return self._engine.get_fish_list()

        from core.entities import Fish

        return [e for e in self._engine.get_all_entities() if isinstance(e, Fish)]

    def _update_cooldowns(self, fish_list: list[Fish]) -> None:
        for fish in fish_list:
            fish._reproduction_component.update_cooldown()

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

            baby = self.maybe_create_banked_offspring(fish)
            if baby is None:
                continue

            if self._engine.request_spawn(baby, reason="banked_asexual_reproduction"):
                baby.register_birth()
                lifecycle_system = getattr(self._engine, "lifecycle_system", None)
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

        IMPROVEMENT: When surviving fish exist, prefer cloning from the healthiest
        one rather than creating a fully random genome. This preserves successful
        genetic traits instead of diluting the gene pool with random genetics.

        The cloned genome gets light mutation to maintain diversity.
        """
        from core import entities, movement_strategy
        from core.genetics import Genome

        environment = self._engine.environment
        ecosystem = self._engine.ecosystem
        if environment is None or ecosystem is None:
            return False

        # Try to clone from a surviving fish if any exist (preserves successful traits)
        fish_list = self._get_fish_list()
        if fish_list:
            # Select the healthiest fish (highest energy ratio) as the template
            best_fish = max(fish_list, key=lambda f: f.energy / max(f.max_energy, 1.0))
            # Clone with light mutation to maintain diversity
            genome = Genome.clone_with_mutation(
                parent=best_fish.genome,
                rng=self._engine.rng,
            )
            generation = best_fish.generation  # Inherit generation for tracking
        else:
            # No fish to clone from - create random genome (extinction recovery)
            genome = Genome.random(use_algorithm=True, rng=self._engine.rng)
            generation = 0

        # Pool-aware per-kind policy mutation for emergency spawns
        pool = getattr(environment, "genome_code_pool", None)
        if pool is not None:
            from core.genetics.code_policy_traits import (
                mutate_code_policies, validate_code_policy_ids)

            mutate_code_policies(genome.behavioral, pool, self._engine.rng)
            validate_code_policy_ids(genome.behavioral, pool, self._engine.rng)

        bounds = environment.get_bounds()
        (min_x, min_y), (max_x, max_y) = bounds
        spawn_margin = self._engine.config.ecosystem.spawn_margin_pixels
        x = self._engine.rng.randint(int(min_x) + spawn_margin, int(max_x) - spawn_margin)
        y = self._engine.rng.randint(int(min_y) + spawn_margin, int(max_y) - spawn_margin)

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
        )
        new_fish.register_birth()

        lifecycle_system = getattr(self._engine, "lifecycle_system", None)
        if lifecycle_system is not None:
            lifecycle_system.record_emergency_spawn()

        return bool(self._engine.request_spawn(new_fish, reason="emergency_spawn"))

    def _get_repro_credit_required(self) -> float:
        config = getattr(self._engine, "config", None)
        soccer_cfg = getattr(config, "soccer", None) if config is not None else None
        if soccer_cfg is None or not getattr(soccer_cfg, "enabled", False):
            return 0.0
        if getattr(soccer_cfg, "repro_reward_mode", "") != "credits":
            return 0.0
        required = float(getattr(soccer_cfg, "repro_credit_required", 0.0))
        return max(0.0, required)

    @staticmethod
    def maybe_create_banked_offspring(fish: Fish) -> Fish | None:
        """Attempt a bank-funded asexual reproduction for a single fish."""
        from core.config.fish import ENERGY_MAX_DEFAULT, FISH_BABY_SIZE
        from core.entities.base import LifeStage

        bank = fish._reproduction_component.overflow_energy_bank
        baby_energy_needed = ENERGY_MAX_DEFAULT * FISH_BABY_SIZE

        life_stage = fish.life_stage

        if (
            fish._reproduction_component.reproduction_cooldown <= 0
            and life_stage == LifeStage.ADULT
            and bank >= baby_energy_needed
        ):
            return fish._create_asexual_offspring()

        return None

    def _create_post_poker_offspring(self, winner: Fish, mate: Fish) -> Fish | None:
        from core.config.fish import (ENERGY_MAX_DEFAULT, FISH_BABY_SIZE,
                                      FISH_BASE_SPEED,
                                      POST_POKER_CROSSOVER_WINNER_WEIGHT,
                                      POST_POKER_MUTATION_RATE,
                                      POST_POKER_MUTATION_STRENGTH,
                                      POST_POKER_PARENT_ENERGY_CONTRIBUTION,
                                      REPRODUCTION_COOLDOWN)
        from core.entities import Fish
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
            rng=self._engine.rng,
        )

        # Pool-aware per-kind policy mutation (prevents cross-kind contamination)
        pool = getattr(winner.environment, "genome_code_pool", None)
        if pool is not None:
            from core.genetics.code_policy_traits import (
                mutate_code_policies, validate_code_policy_ids)

            mutate_code_policies(offspring_genome.behavioral, pool, self._engine.rng)
            validate_code_policy_ids(offspring_genome.behavioral, pool, self._engine.rng)

        baby_max_energy = (
            ENERGY_MAX_DEFAULT * FISH_BABY_SIZE * offspring_genome.physical.size_modifier.value
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

        apply_energy_delta(winner, -winner_contrib, source="post_poker_reproduction")
        apply_energy_delta(mate, -mate_contrib, source="post_poker_reproduction")

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
        baby_x = mid_x + self._engine.rng.uniform(-30, 30)
        baby_y = mid_y + self._engine.rng.uniform(-30, 30)
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
            winner if self._engine.rng.random() < POST_POKER_CROSSOVER_WINNER_WEIGHT else mate
        )
        baby._skill_game_component.inherit_from_parent(
            source_parent._skill_game_component,
            mutation_rate=POST_POKER_MUTATION_RATE,
        )

        return baby
