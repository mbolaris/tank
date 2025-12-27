"""Poker event management system for simulation engines.

This module handles poker interactions and event history tracking.
The system extends BaseSystem for consistent interface and lifecycle management.

Architecture Notes:
- Extends BaseSystem for uniform system management
- Runs in UpdatePhase.INTERACTION
- Manages poker event history with configurable max size
- Tracks poker statistics for debugging and analysis
- Handles mixed poker games (fish + plants) via handle_mixed_poker_games()
"""

import logging
from collections import deque
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union

from core.config.ecosystem import (
    FISH_POKER_MAX_DISTANCE,
    FISH_POKER_MIN_DISTANCE,
)
from core.config.plants import (
    PLANT_POKER_MAX_DISTANCE,
    PLANT_POKER_MIN_DISTANCE,
)
from core.config.server import POKER_ACTIVITY_ENABLED
from core.mixed_poker import (
    MixedPokerInteraction,
    should_trigger_plant_poker_asexual_reproduction,
)
from core.poker_interaction import (
    PokerInteraction,
    MAX_PLAYERS as POKER_MAX_PLAYERS,
)
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.plant import Plant
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)

# Type alias for poker-eligible entities
PokerPlayer = Union["Fish", "Plant"]


@runs_in_phase(UpdatePhase.INTERACTION)
class PokerSystem(BaseSystem):
    """Handle poker interactions and event history.

    This system runs in the INTERACTION phase and manages:
    - Poker event history for UI display
    - Poker result processing (energy transfer, reproduction)
    - Statistics tracking for debugging

    Attributes:
        poker_events: Deque of recent poker events (capped at max_events)
        _games_played: Total number of poker games played
        _total_energy_transferred: Total energy transferred via poker
    """

    def __init__(self, engine: "SimulationEngine", max_events: int = 100) -> None:
        """Initialize the poker system.

        Args:
            engine: The simulation engine
            max_events: Maximum number of poker events to keep in history
        """
        super().__init__(engine, "Poker")
        self.poker_events: deque = deque(maxlen=max_events)
        self._max_events = max_events
        self._games_played: int = 0
        self._total_energy_transferred: float = 0.0
        self._fish_wins: int = 0
        self._plant_wins: int = 0
        self._ties: int = 0

    def _do_update(self, frame: int) -> SystemResult:
        """Poker system doesn't have per-frame logic.

        Poker games are triggered by collision/proximity detection
        in the collision system. This method exists for interface
        consistency but performs no action.

        Args:
            frame: Current simulation frame number

        Returns:
            Empty SystemResult (poker is event-driven, not frame-driven)
        """
        return SystemResult.empty()

    def handle_poker_result(self, poker: PokerInteraction) -> None:
        """Handle poker outcomes, including event logging and reproduction.

        Args:
            poker: The completed poker interaction
        """
        self.add_poker_event(poker)
        
        # Attempt post-poker reproduction for fish-fish games
        baby = self._attempt_post_poker_reproduction(poker)
        if baby is not None:
            return
        
        # Fallback: check if reproduction was handled elsewhere
        if (
            poker.result is not None
            and getattr(poker.result, "reproduction_occurred", False)
            and getattr(poker.result, "offspring", None) is not None
        ):
            self._engine.add_entity(poker.result.offspring)
            if hasattr(poker.result.offspring, "register_birth"):
                poker.result.offspring.register_birth()
            if hasattr(self._engine, "lifecycle_system"):
                self._engine.lifecycle_system.record_birth()

    def _add_poker_event_to_history(
        self,
        winner_id: int,
        loser_id: int,
        winner_hand: str,
        loser_hand: str,
        energy_transferred: float,
        message: str,
    ) -> None:
        """Add a poker event to the history.

        Args:
            winner_id: ID of the winning entity
            loser_id: ID of the losing entity
            winner_hand: Description of winner's hand
            loser_hand: Description of loser's hand
            energy_transferred: Amount of energy transferred
            message: Human-readable message describing the outcome
        """
        event = {
            "frame": self._engine.frame_count,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winner_hand": winner_hand,
            "loser_hand": loser_hand,
            "energy_transferred": energy_transferred,
            "message": message,
        }
        self.poker_events.append(event)
        self._games_played += 1
        self._total_energy_transferred += energy_transferred

    def add_poker_event(self, poker: PokerInteraction) -> None:
        """Add a poker event to the recent events list.

        Args:
            poker: The completed poker interaction
        """
        if poker.result is None:
            return

        result = poker.result
        # Get player count from poker.players (MixedPokerInteraction stores players list)
        num_players = len(poker.players) if hasattr(poker, 'players') else 2

        if result.winner_id == -1 or result.is_tie:
            # Tie - use winner_hand or first loser_hand for description
            hand_desc = result.winner_hand.description if result.winner_hand else "Unknown"
            if num_players == 2:
                p1_id = poker.players[0].get_poker_id() if hasattr(poker.players[0], 'get_poker_id') else 0
                p2_id = poker.players[1].get_poker_id() if hasattr(poker.players[1], 'get_poker_id') else 0
                message = f"Fish #{p1_id} vs Fish #{p2_id} - TIE! ({hand_desc})"
            else:
                player_list = ", ".join(f"#{p.get_poker_id()}" for p in poker.players)
                message = f"Fish {player_list} - TIE! ({hand_desc})"
            self._ties += 1
        else:
            # Use winner_hand from result
            winner_desc = result.winner_hand.description if result.winner_hand else "Unknown"

            if num_players == 2:
                message = (
                    f"Fish #{result.winner_id} beats Fish #{result.loser_ids[0] if result.loser_ids else 0} "
                    f"with {winner_desc}! (+{result.energy_transferred:.1f} energy)"
                )
            else:
                loser_list = ", ".join(f"#{lid}" for lid in result.loser_ids)
                message = (
                    f"Fish #{result.winner_id} beats Fish {loser_list} "
                    f"with {winner_desc}! (+{result.energy_transferred:.1f} energy)"
                )
            self._fish_wins += 1

        # Get winner and loser hand descriptions
        winner_hand_desc = result.winner_hand.description if result.winner_hand else "Unknown"
        loser_hand_desc = result.loser_hands[0].description if result.loser_hands and result.loser_hands[0] else "Unknown"

        self._add_poker_event_to_history(
            result.winner_id,
            result.loser_ids[0] if result.loser_ids else -1,
            winner_hand_desc,
            loser_hand_desc,
            result.energy_transferred,
            message,
        )

        emitter = getattr(self._engine, "_emit_poker_outcome", None)
        if emitter is not None:
            emitter(result)

    def add_plant_poker_event(
        self,
        fish_id: int,
        plant_id: int,
        fish_won: bool,
        fish_hand: str,
        plant_hand: str,
        energy_transferred: float,
    ) -> None:
        """Record a poker event between a fish and a plant.

        Args:
            fish_id: ID of the fish player
            plant_id: ID of the plant player
            fish_won: True if fish won, False if plant won
            fish_hand: Description of fish's hand
            plant_hand: Description of plant's hand
            energy_transferred: Amount of energy transferred
        """
        if fish_won:
            winner_id = fish_id
            loser_id = -3  # Sentinel for plant
            winner_hand = fish_hand
            loser_hand = plant_hand
            message = f"Fish #{fish_id} beats Plant #{plant_id} with {fish_hand}! (+{energy_transferred:.1f}⚡)"
            self._fish_wins += 1
        else:
            winner_id = -3
            loser_id = fish_id
            winner_hand = plant_hand
            loser_hand = fish_hand
            message = f"Plant #{plant_id} beats Fish #{fish_id} with {plant_hand}! (+{energy_transferred:.1f}⚡)"
            self._plant_wins += 1

        event = {
            "frame": self._engine.frame_count,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "winner_hand": winner_hand,
            "loser_hand": loser_hand,
            "energy_transferred": energy_transferred,
            "message": message,
            "is_plant": True,
            "plant_id": plant_id,
        }

        self.poker_events.append(event)
        self._games_played += 1
        self._total_energy_transferred += energy_transferred

        emitter = getattr(self._engine, "_emit_poker_outcome", None)
        if emitter is not None:
            emitter(
                SimpleNamespace(
                    winner_id=winner_id if winner_id != -3 else plant_id,
                    loser_ids=[loser_id],
                    winner_type="plant" if winner_id == -3 else "fish",
                    loser_types=["fish" if winner_id == -3 else "plant"],
                    energy_transferred=energy_transferred,
                    winner_hand=winner_hand,
                    loser_hands=[loser_hand],
                    is_tie=False,
                    house_cut=0.0,
                )
            )

    def get_recent_poker_events(self, max_age_frames: int) -> List[Dict[str, Any]]:
        """Get recent poker events within a frame window.

        Args:
            max_age_frames: Maximum age of events to include (in frames)

        Returns:
            List of poker events within the specified time window
        """
        return [
            event
            for event in self.poker_events
            if self._engine.frame_count - event["frame"] < max_age_frames
        ]

    def get_debug_info(self) -> Dict[str, Any]:
        """Return poker statistics for debugging.

        Returns:
            Dictionary containing system state and statistics
        """
        return {
            **super().get_debug_info(),
            "games_played": self._games_played,
            "total_energy_transferred": self._total_energy_transferred,
            "fish_wins": self._fish_wins,
            "plant_wins": self._plant_wins,
            "ties": self._ties,
            "events_in_history": len(self.poker_events),
            "max_events": self._max_events,
            "avg_energy_per_game": (
                self._total_energy_transferred / self._games_played
                if self._games_played > 0
                else 0.0
            ),
        }

    # =========================================================================
    # Mixed Poker Game Logic (fish + plants)
    # =========================================================================

    def handle_mixed_poker_games(self) -> None:
        """Handle poker games between any mix of fish and plants.

        Orchestration-only method. Delegates to:
        - MixedPokerTablePlanner: Forms tables via fish-initiated local queries
        - MixedPokerInteraction: Plays the actual poker game
        - _record_and_apply_mixed_poker_outcome: Records stats and handles reproduction

        Design Philosophy:
            Fish initiate poker (plants don't). For each eligible fish, we query
            nearby entities and form a table. This replaces the complex global
            graph + DFS approach with simple local queries.

        Throttling:
            Uses a per-tick budget (max_tables_per_tick) instead of population-based
            frame skipping. This provides more stable behavior.
        """
        from core.entities import Fish
        from core.entities.plant import Plant
        from core.poker_table_planner import MixedPokerTablePlanner

        if not POKER_ACTIVITY_ENABLED:
            return

        # Get entity lists
        all_entities = self._engine.get_all_entities()
        if len(all_entities) < 2:
            return

        fish_list = [e for e in all_entities if isinstance(e, Fish) and not e.is_dead()]
        plant_list = [e for e in all_entities if isinstance(e, Plant) and not e.is_dead()]

        if len(fish_list) < 1:
            return

        # Get proximity config
        max_distance = max(FISH_POKER_MAX_DISTANCE, PLANT_POKER_MAX_DISTANCE)

        # Plan tables using fish-initiated local queries
        planner = MixedPokerTablePlanner(
            environment=self._engine.environment,
            max_players=POKER_MAX_PLAYERS,
            max_distance=max_distance,
            min_energy=MixedPokerInteraction.MIN_ENERGY_TO_PLAY,
            max_tables_per_tick=10,  # Budget: at most 10 games per tick
            rng=self._engine.rng,
        )

        tables = planner.plan_tables(fish_list, plant_list)

        if not tables:
            return

        # Track entities for death checking
        all_entities_set = set(all_entities)

        # Play games at each table
        for table in tables:
            try:
                poker = MixedPokerInteraction(table.players, rng=self._engine.rng)
                if not poker.play_poker():
                    continue

                # Record stats and handle reproduction
                self._record_and_apply_mixed_poker_outcome(poker)

                # Check for deaths and let engine handle removal
                for player in table.players:
                    if isinstance(player, Fish) and player.is_dead():
                        if player in all_entities_set:
                            self._engine.record_fish_death(player)
                            all_entities_set.discard(player)
                    elif isinstance(player, Plant) and player.is_dead():
                        if player in all_entities_set:
                            player.die()
                            self._engine.remove_entity(player)
                            all_entities_set.discard(player)

            except Exception:
                logger.exception("Mixed poker game error")

    def _record_and_apply_mixed_poker_outcome(self, poker: MixedPokerInteraction) -> None:
        """Record and apply the outcome of a mixed poker game.

        Records energy transfers and ecosystem statistics, applies house cut logic
        based on winner type, and triggers asexual reproduction if applicable.

        Args:
            poker: The completed poker interaction
        """
        if poker.result is None:
            return

        result = poker.result

        # Add poker event for display
        if hasattr(self._engine, "add_plant_poker_event") and result.plant_count > 0:
            from core.entities import Fish
            from core.entities.plant import Plant

            # Use plant poker event format for games with plants
            winner_is_fish = result.winner_type == "fish"

            # Safely get hand descriptions (hands can be None if player folded)
            winner_hand_desc = "Unknown"
            if result.winner_hand is not None:
                winner_hand_desc = result.winner_hand.description

            loser_hand_desc = "Folded"
            if result.loser_hands and result.loser_hands[0] is not None:
                loser_hand_desc = result.loser_hands[0].description

            # Get actual display IDs (not offset IDs from get_poker_id())
            # result.winner_id and loser_ids contain offset IDs
            # We need the actual entity IDs for display
            fish_display_id = 0
            plant_display_id = 0

            for player in poker.players:
                player_poker_id = poker._get_player_id(player)
                if winner_is_fish:
                    # Fish won - find fish winner and plant loser
                    if isinstance(player, Fish) and player_poker_id == result.winner_id:
                        fish_display_id = player.fish_id
                    elif isinstance(player, Plant) and result.loser_ids and player_poker_id in result.loser_ids:
                        plant_display_id = player.plant_id
                else:
                    # Plant won - find plant winner and fish loser
                    if isinstance(player, Plant) and player_poker_id == result.winner_id:
                        plant_display_id = player.plant_id
                    elif isinstance(player, Fish) and result.loser_ids and player_poker_id in result.loser_ids:
                        fish_display_id = player.fish_id

            self._engine.add_plant_poker_event(
                fish_id=fish_display_id,
                plant_id=plant_display_id,
                fish_won=winner_is_fish,
                fish_hand=winner_hand_desc,
                plant_hand=loser_hand_desc,
                energy_transferred=abs(result.energy_transferred),
            )

        # Record mixed fish+plant poker energy economy with correct attribution.
        ecosystem = self._engine.ecosystem
        if ecosystem is not None and result.plant_count > 0:
            from core.entities import Fish
            from core.entities.plant import Plant

            initial = getattr(poker, "_initial_player_energies", None)
            fish_delta = 0.0
            plant_delta = 0.0

            if initial is not None and len(initial) == len(poker.players):
                for idx, player in enumerate(poker.players):
                    delta = getattr(player, "energy", 0.0) - float(initial[idx])
                    if isinstance(player, Fish):
                        fish_delta += delta
                    elif isinstance(player, Plant):
                        plant_delta += delta

            ecosystem.record_mixed_poker_outcome(
                fish_delta=fish_delta,
                plant_delta=plant_delta,
                house_cut=float(getattr(result, "house_cut", 0.0) or 0.0),
                winner_type=str(getattr(result, "winner_type", "")),
            )

        if result.plant_count == 0:
            emitter = getattr(self._engine, "_emit_poker_outcome", None)
            if emitter is not None:
                emitter(result)

        # Trigger asexual reproduction if fish won against only plants
        # (fish_count == 1 means only the winner was a fish, all opponents were plants)
        if (
            result.winner_type == "fish"
            and result.fish_count == 1
            and result.plant_count > 0
            and not result.is_tie
        ):
            # Find the winning fish from the poker interaction
            winner_fish = None
            for player in poker.fish_players:
                if poker._get_player_id(player) == result.winner_id:
                    winner_fish = player
                    break

            if winner_fish is not None and should_trigger_plant_poker_asexual_reproduction(winner_fish):
                # Trigger instant asexual reproduction
                baby = winner_fish._create_asexual_offspring()
                if baby is not None:
                    self._engine.add_entity(baby)
                    baby.register_birth()

    # =========================================================================
    # Post-Poker Fish-Fish Reproduction
    # =========================================================================

    def _attempt_post_poker_reproduction(self, poker: PokerInteraction) -> Optional["Fish"]:
        """Attempt to reproduce after a fish-fish poker game.
        
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
        # DETERMINISM: Always use engine RNG, never fall back to global random
        rng = self._engine.rng
        mate = rng.choice(eligible_mates)

        if self._engine.ecosystem is not None:
            if not self._engine.ecosystem.can_reproduce(len(self._engine.get_fish_list())):
                return None

        baby = self._create_post_poker_offspring(winner, mate, rng)
        if baby is None:
            return None

        self._engine.add_entity(baby)
        baby.register_birth()
        if hasattr(self._engine, "lifecycle_system"):
            self._engine.lifecycle_system.record_birth()
        return baby

    def _create_post_poker_offspring(
        self, winner: "Fish", mate: "Fish", rng
    ) -> Optional["Fish"]:
        """Create an offspring from poker winner and mate.
        
        The offspring's genome is a weighted blend of both parents, with the
        winner having higher weight. Energy is contributed by both parents.
        
        Args:
            winner: The poker winner (primary parent)
            mate: The mating partner
            rng: Random number generator for deterministic behavior
            
        Returns:
            The offspring fish, or None if creation failed
        """
        from core.entities import Fish
        from core.config.fish import (
            ENERGY_MAX_DEFAULT,
            FISH_BABY_SIZE,
            FISH_BASE_SPEED,
            POST_POKER_CROSSOVER_WINNER_WEIGHT,
            POST_POKER_MATING_DISTANCE,
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
            rng=rng,
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
        baby_x = mid_x + rng.uniform(-30, 30)
        baby_y = mid_y + rng.uniform(-30, 30)
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
            if rng.random() < POST_POKER_CROSSOVER_WINNER_WEIGHT
            else mate
        )
        baby._skill_game_component.inherit_from_parent(
            source_parent._skill_game_component,
            mutation_rate=POST_POKER_MUTATION_RATE,
        )

        return baby
