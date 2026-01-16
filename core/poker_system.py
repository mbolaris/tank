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
from typing import TYPE_CHECKING, Any, Dict, List, Union

from core.config.ecosystem import FISH_POKER_MAX_DISTANCE
from core.config.plants import PLANT_POKER_MAX_DISTANCE
from core.config.server import POKER_ACTIVITY_ENABLED
from core.mixed_poker import MixedPokerInteraction
from core.poker_interaction import MAX_PLAYERS as POKER_MAX_PLAYERS
from core.poker_interaction import PokerInteraction
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

        # Delegate post-poker reproduction to the ReproductionService
        reproduction_service = getattr(self._engine, "reproduction_service", None)
        if reproduction_service is not None:
            baby = reproduction_service.handle_post_poker_reproduction(poker)
            if baby is not None:
                return

        # Fallback: check if reproduction was handled elsewhere
        if (
            poker.result is not None
            and getattr(poker.result, "reproduction_occurred", False)
            and getattr(poker.result, "offspring", None) is not None
        ):
            if self._request_spawn(poker.result.offspring, reason="poker_reproduction"):
                register_birth = getattr(poker.result.offspring, "register_birth", None)
                if register_birth is not None:
                    register_birth()
                lifecycle_system = getattr(self._engine, "lifecycle_system", None)
                if lifecycle_system is not None:
                    lifecycle_system.record_birth()

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
        players = getattr(poker, "players", None)
        num_players = len(players) if players is not None else 2

        if result.winner_id == -1 or result.is_tie:
            # Tie - use winner_hand or first loser_hand for description
            hand_desc = result.winner_hand.description if result.winner_hand else "Unknown"
            if num_players == 2 and players is not None:
                get_id_0 = getattr(players[0], "get_poker_id", None)
                get_id_1 = getattr(players[1], "get_poker_id", None)
                p1_id = get_id_0() if get_id_0 is not None else 0
                p2_id = get_id_1() if get_id_1 is not None else 0
                message = f"Fish #{p1_id} vs Fish #{p2_id} - TIE! ({hand_desc})"
            elif players is not None:
                player_list = ", ".join(f"#{p.get_poker_id()}" for p in players)
                message = f"Fish {player_list} - TIE! ({hand_desc})"
            else:
                message = f"TIE! ({hand_desc})"
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
        loser_hand_desc = (
            result.loser_hands[0].description
            if result.loser_hands and result.loser_hands[0]
            else "Unknown"
        )

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
                            self._engine.request_remove(player, reason="poker_plant_death")
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
        add_plant_poker_event = getattr(self._engine, "add_plant_poker_event", None)
        if add_plant_poker_event is not None and result.plant_count > 0:
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
                    elif (
                        isinstance(player, Plant)
                        and result.loser_ids
                        and player_poker_id in result.loser_ids
                    ):
                        plant_display_id = player.plant_id
                else:
                    # Plant won - find plant winner and fish loser
                    if isinstance(player, Plant) and player_poker_id == result.winner_id:
                        plant_display_id = player.plant_id
                    elif (
                        isinstance(player, Fish)
                        and result.loser_ids
                        and player_poker_id in result.loser_ids
                    ):
                        fish_display_id = player.fish_id

            add_plant_poker_event(
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

            from core.ecosystem_stats import MixedPokerOutcomeRecord

            ecosystem.record_mixed_poker_outcome_record(
                MixedPokerOutcomeRecord(
                    fish_delta=fish_delta,
                    plant_delta=plant_delta,
                    house_cut=float(getattr(result, "house_cut", 0.0) or 0.0),
                    winner_type=str(getattr(result, "winner_type", "")),
                )
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

            if winner_fish is not None:
                # Delegate to ReproductionService
                reproduction_service = getattr(self._engine, "reproduction_service", None)
                if reproduction_service is not None:
                    reproduction_service.handle_plant_poker_asexual_reproduction(winner_fish)

    # =========================================================================
    # Spawn Helper
    # =========================================================================

    def _request_spawn(self, entity: "Fish", *, reason: str) -> bool:
        """Request a spawn via the engine, if available."""
        request_spawn = getattr(self._engine, "request_spawn", None)
        if not callable(request_spawn):
            return False
        return bool(request_spawn(entity, reason=reason))
