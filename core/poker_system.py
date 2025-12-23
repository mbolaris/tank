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
from typing import TYPE_CHECKING, Any, Dict, List, Set, Union

from core.config.ecosystem import (
    FISH_POKER_MAX_DISTANCE,
    FISH_POKER_MIN_DISTANCE,
)
from core.config.plants import (
    PLANT_POKER_MAX_DISTANCE,
    PLANT_POKER_MIN_DISTANCE,
)
from core.config.server import POKER_ACTIVITY_ENABLED
from core.config.simulation import (
    SKILL_GAME_THROTTLE_THRESHOLD_1,
    SKILL_GAME_THROTTLE_THRESHOLD_2,
)
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
    from core.simulation_engine import SimulationEngine
    from core.simulation_runtime import SimulationContext

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

    def __init__(
        self,
        engine: "SimulationEngine",
        max_events: int = 100,
        context: "SimulationContext | None" = None,
    ) -> None:
        """Initialize the poker system.

        Args:
            engine: The simulation engine
            max_events: Maximum number of poker events to keep in history
        """
        super().__init__(engine, "Poker", context=context)
        self.poker_events: deque = deque(maxlen=max_events)
        self._max_events = max_events
        self._games_played: int = 0
        self._total_energy_transferred: float = 0.0
        self._fish_wins: int = 0
        self._plant_wins: int = 0
        self._ties: int = 0
        # Throttle counter for mixed poker games at high populations
        self._throttle_counter: int = 0

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
        """Handle poker outcomes, including event logging.

        Args:
            poker: The completed poker interaction
        """
        self.add_poker_event(poker)
        # Note: Reproduction is now handled separately by the simulator,
        # not via poker result fields

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

        Finds groups of fish and plants that are in poker proximity
        and initiates mixed poker games with up to POKER_MAX_PLAYERS players.

        PERFORMANCE OPTIMIZATIONS:
        - Single combined spatial query instead of separate fish+plant queries
        - Inline proximity check to avoid method call overhead
        - Pre-compute squared distances to avoid sqrt
        - Use local variables for frequently accessed attributes
        - Cache entity positions to avoid repeated attribute access
        - Skip spatial query for entities with no nearby_poker_entities method

        THROTTLING:
        - Under 100 entities: every frame
        - 100-200 entities: every 2 frames
        - 200+ entities: every 3 frames
        """
        from core.entities import Fish
        from core.entities.plant import Plant

        if not POKER_ACTIVITY_ENABLED:
            return

        # Throttle based on population size
        all_entities = self._engine.get_all_entities()
        entity_count = len(all_entities)
        throttle_interval = 1  # Default: every frame
        if entity_count >= SKILL_GAME_THROTTLE_THRESHOLD_2:
            throttle_interval = 3
        elif entity_count >= SKILL_GAME_THROTTLE_THRESHOLD_1:
            throttle_interval = 2

        self._throttle_counter += 1
        if self._throttle_counter < throttle_interval:
            return
        self._throttle_counter = 0

        # Early exit if not enough entities
        if entity_count < 2:
            return

        all_entities_set = set(all_entities)

        # Performance: Use type() for exact match (faster than isinstance),
        # but include a duck-typing fallback to avoid issues if modules are reloaded.
        fish_list = [e for e in all_entities if type(e) is Fish or hasattr(e, "fish_id")]

        # For plants, we need isinstance since we also check is_dead
        plant_list = [e for e in all_entities if isinstance(e, Plant) and not e.is_dead()]

        # Need at least 1 fish and 1 other entity for poker
        n_fish = len(fish_list)
        n_plants = len(plant_list)
        if n_fish < 1 or (n_fish + n_plants) < 2:
            return

        # Combine into one list for proximity checking
        all_poker_entities: List[PokerPlayer] = fish_list + plant_list  # type: ignore

        # Pre-compute squared proximity values
        proximity_max = max(FISH_POKER_MAX_DISTANCE, PLANT_POKER_MAX_DISTANCE)
        proximity_min = min(FISH_POKER_MIN_DISTANCE, PLANT_POKER_MIN_DISTANCE)
        proximity_max_sq = proximity_max * proximity_max
        proximity_min_sq = proximity_min * proximity_min

        # Cache entity center positions for fast access
        # Store as (center_x, center_y) tuples
        entity_centers: Dict[PokerPlayer, tuple] = {}
        for e in all_poker_entities:
            entity_centers[e] = (e.pos.x + e.width * 0.5, e.pos.y + e.height * 0.5)

        # Build adjacency graph for entities in poker proximity
        entity_contacts: Dict[PokerPlayer, Set[PokerPlayer]] = {e: set() for e in all_poker_entities}

        environment = self._engine.environment
        poker_entity_set = set(all_poker_entities)

        for entity in all_poker_entities:
            if entity not in all_entities_set:
                continue

            e1_cx, e1_cy = entity_centers[entity]

            # Get nearby entities - OPTIMIZATION: Single combined query
            search_radius = proximity_max + max(entity.width, entity.height) * 0.5
            nearby: List[PokerPlayer] = []

            if environment is not None:
                # OPTIMIZATION: Use nearby_poker_entities if available, else combined query
                if hasattr(environment, "nearby_poker_entities"):
                    nearby = environment.nearby_poker_entities(entity, radius=search_radius)
                else:
                    # Get nearby fish and plants in single pass through nearby_agents
                    if hasattr(environment, "nearby_agents"):
                        nearby_all = environment.nearby_agents(entity, radius=search_radius)
                        nearby = [e for e in nearby_all if e in poker_entity_set]
                    else:
                        # Fallback to separate queries
                        if hasattr(environment, "nearby_evolving_agents"):
                            nearby.extend(environment.nearby_evolving_agents(entity, radius=search_radius))
                        if hasattr(environment, "nearby_agents_by_type"):
                            nearby_plants = environment.nearby_agents_by_type(entity, radius=search_radius, agent_class=Plant)
                            for plant in nearby_plants:
                                if plant not in nearby:
                                    nearby.append(plant)
            else:
                nearby = [e for e in all_poker_entities if e is not entity]

            for other in nearby:
                if other is entity:
                    continue
                if other not in all_entities_set:
                    continue
                # Skip if already connected (avoid redundant checks)
                entity_contact_set = entity_contacts[entity]
                if other in entity_contact_set:
                    continue

                # Safety check: entity may have been removed/died during iteration
                if other not in entity_centers:
                    continue

                e2_cx, e2_cy = entity_centers[other]
                dx = e1_cx - e2_cx
                dy = e1_cy - e2_cy
                distance_sq = dx * dx + dy * dy

                # Must be within max distance but farther than min distance
                if proximity_min_sq < distance_sq <= proximity_max_sq:
                    entity_contact_set.add(other)
                    entity_contacts[other].add(entity)

        # Find connected components using DFS
        visited: Set[PokerPlayer] = set()
        processed: Set[PokerPlayer] = set()
        removed_entities: Set[PokerPlayer] = set()

        for start_entity in all_poker_entities:
            if start_entity in visited or start_entity in removed_entities:
                continue
            if start_entity not in all_entities_set:
                continue

            # Build connected group via DFS
            group: List[PokerPlayer] = []
            stack = [start_entity]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue

                visited.add(current)
                if current not in removed_entities and current in all_entities_set:
                    group.append(current)

                # Direct access - all poker entities are in the dict
                for neighbor in entity_contacts[current]:
                    if neighbor not in visited:
                        stack.append(neighbor)

            # Need at least 2 players for poker
            if len(group) < 2:
                continue

            # Filter to only unprocessed entities
            valid_players = [p for p in group if p not in processed]
            if len(valid_players) < 2:
                continue

            # Filter to only ready players (not on cooldown, not pregnant, etc.)
            ready_players = self._get_ready_poker_players(valid_players)
            if len(ready_players) < 2:
                continue

            # IMPORTANT: Ensure ALL players in the group are within max distance of each other
            # The DFS can connect A-B-C where A and C are far apart (chain connection)
            # We need to filter to only players that are ALL mutually within proximity
            ready_players = self._filter_mutually_proximate_players(
                ready_players, proximity_max
            )
            if len(ready_players) < 2:
                continue

            # Limit to max players FIRST, before checking fish count
            # This prevents truncation from removing all fish after the check passed
            if len(ready_players) > POKER_MAX_PLAYERS:
                ready_players = ready_players[:POKER_MAX_PLAYERS]

            # IMPORTANT: Require at least 1 fish in the game (after truncation)
            # Plant-only poker games are not allowed
            fish_in_group = [p for p in ready_players if isinstance(p, Fish) or hasattr(p, "fish_id")]
            if len(fish_in_group) < 1:
                continue

            # Play mixed poker game
            try:
                poker = MixedPokerInteraction(ready_players)
                if poker.play_poker():
                    self._record_and_apply_mixed_poker_outcome(poker)

                    # Check for deaths
                    for player in ready_players:
                        if (isinstance(player, Fish) or hasattr(player, "fish_id")) and player.is_dead():
                            if player in all_entities_set:
                                self._engine.record_fish_death(player)
                                removed_entities.add(player)
                                all_entities_set.discard(player)
                        elif isinstance(player, Plant) and player.is_dead():
                            if player in all_entities_set:
                                player.die()
                                self._engine.remove_entity(player)
                                removed_entities.add(player)
                                all_entities_set.discard(player)

                processed.update(ready_players)

            except Exception:
                logger.exception("Mixed poker game error")

    def _filter_mutually_proximate_players(
        self, players: List[PokerPlayer], max_distance: float
    ) -> List[PokerPlayer]:
        """Filter players to only those where ALL are within max_distance of each other.

        This prevents chain-connected players (A near B, B near C, but A far from C)
        from ending up in the same poker game.

        PERFORMANCE OPTIMIZATIONS:
        - Use squared distances throughout (avoid sqrt)
        - Use 2D list instead of dict (no hash/get overhead)
        - Pre-cache player positions
        - Early exit when best possible group is found
        - Inline distance calculations

        Args:
            players: List of potential players
            max_distance: Maximum distance between any two players

        Returns:
            Largest subset where all players are mutually within max_distance
        """
        n = len(players)
        if n <= 2:
            # For 2 players, they were already verified as proximate
            return players

        # Pre-compute squared max distance (avoid sqrt entirely)
        max_dist_sq = max_distance * max_distance

        # Pre-cache player positions for faster access
        positions = [(p.pos.x + p.width / 2, p.pos.y + p.height / 2) for p in players]

        # OPTIMIZATION: Use 2D list instead of dict for O(1) access without hash overhead
        # Build adjacency matrix as boolean: True = within distance
        # Only upper triangle needed (i < j)
        adjacent = [[False] * n for _ in range(n)]

        for i in range(n):
            x1, y1 = positions[i]
            for j in range(i + 1, n):
                x2, y2 = positions[j]
                dx = x1 - x2
                dy = y1 - y2
                if dx * dx + dy * dy <= max_dist_sq:
                    adjacent[i][j] = True
                    adjacent[j][i] = True  # Symmetric

        # Simple greedy approach: start with each player, build largest valid group
        best_group: List[int] = []
        best_size = 0

        for start_idx in range(n):
            # Early exit: can't beat current best if remaining players aren't enough
            if n - start_idx <= best_size:
                break

            group = [start_idx]
            adj_row = adjacent[start_idx]  # Cache row for start player

            for candidate_idx in range(start_idx + 1, n):
                # Quick check: must be adjacent to start player
                if not adj_row[candidate_idx]:
                    continue

                # Check if candidate is within distance of ALL current group members
                can_add = True
                for member_idx in group:
                    if not adjacent[member_idx][candidate_idx]:
                        can_add = False
                        break
                if can_add:
                    group.append(candidate_idx)

            if len(group) > best_size:
                best_group = group
                best_size = len(group)
                # Early exit if we found a group with all remaining players
                if best_size == n - start_idx:
                    break

        return [players[i] for i in best_group]

    def _get_ready_poker_players(self, players: List[PokerPlayer]) -> List[PokerPlayer]:
        """Filter players to those ready to play poker.

        Args:
            players: List of potential players (fish and plants)

        Returns:
            List of players ready to play (not on cooldown, not pregnant, etc.)
        """
        from core.entities import Fish
        from core.entities.plant import Plant

        ready = []
        for player in players:
            # Check cooldown
            if getattr(player, "poker_cooldown", 0) > 0:
                continue

            # Fish-specific checks
            if isinstance(player, Fish):
                if player.energy < MixedPokerInteraction.MIN_ENERGY_TO_PLAY:
                    continue

            # Plant-specific checks
            if isinstance(player, Plant):
                if player.is_dead():
                    continue

            ready.append(player)

        return ready

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
            # Use plant poker event format for games with plants
            winner_is_fish = result.winner_type == "fish"

            # Safely get hand descriptions (hands can be None if player folded)
            winner_hand_desc = "Unknown"
            if result.winner_hand is not None:
                winner_hand_desc = result.winner_hand.description

            loser_hand_desc = "Folded"
            if result.loser_hands and result.loser_hands[0] is not None:
                loser_hand_desc = result.loser_hands[0].description

            self._engine.add_plant_poker_event(
                fish_id=result.winner_id if winner_is_fish else (result.loser_ids[0] if result.loser_ids else 0),
                plant_id=result.winner_id if not winner_is_fish else 0,
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
