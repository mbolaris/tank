"""Poker proximity detection system.

This system detects fish groups eligible for poker games based on proximity.
It runs in the INTERACTION phase, after collision handling but before
the main update is complete.

Architecture Notes:
- Separates poker proximity detection from physical collision handling
- Uses the same spatial queries as CollisionSystem but for a different purpose
- Delegates actual game execution to PokerSystem

Design Rationale:
-----------------
Previously, poker proximity detection was embedded in CollisionSystem,
mixing physical collision handling with game logic. This separation:
1. Makes CollisionSystem focus on physics-related collisions only
2. Makes poker triggering logic easier to modify independently
3. Reduces the size and complexity of CollisionSystem
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from core.config.ecosystem import FISH_POKER_MAX_DISTANCE, FISH_POKER_MIN_DISTANCE
from core.poker_interaction import MAX_PLAYERS as POKER_MAX_PLAYERS
from core.poker_interaction import PokerInteraction, filter_mutually_proximate, get_ready_players
from core.systems.base import BaseSystem, SystemResult
from core.update_phases import UpdatePhase, runs_in_phase

if TYPE_CHECKING:
    from core.entities import Fish
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


@runs_in_phase(UpdatePhase.INTERACTION)
class PokerProximitySystem(BaseSystem):
    """System for detecting fish groups and triggering poker games.

    This system runs in the INTERACTION phase and handles:
    - Detecting fish within poker proximity range
    - Building connected groups of poker-eligible fish
    - Triggering poker games for valid groups

    Design Decision:
        Separated from CollisionSystem to maintain single responsibility.
        CollisionSystem handles physical collisions (eating, predation),
        while this system handles social interactions (poker games).
    """

    def __init__(self, engine: "SimulationEngine") -> None:
        """Initialize the poker proximity system.

        Args:
            engine: The simulation engine
        """
        super().__init__(engine, "PokerProximity")
        # Cumulative stats
        self._groups_detected: int = 0
        self._games_triggered: int = 0
        # Per-frame stats
        self._frame_groups: int = 0
        self._frame_games: int = 0

    def _do_update(self, frame: int) -> Optional[SystemResult]:
        """Detect poker-eligible fish groups and trigger games.

        Returns:
            SystemResult with poker proximity statistics
        """
        if not self._engine.poker_system.enabled:
            return SystemResult.empty()

        # Get all fish
        fish_list = self._engine.get_fish_list()
        if len(fish_list) < 2:
            return SystemResult.empty()

        # Build proximity graph
        fish_poker_contacts = self._build_proximity_graph(fish_list)

        # Process groups and trigger games
        games_triggered = self._process_poker_groups(fish_list, fish_poker_contacts)

        self._frame_games = games_triggered
        self._games_triggered += games_triggered

        result = SystemResult(
            details={
                "groups_detected": self._frame_groups,
                "games_triggered": games_triggered,
            }
        )

        # Reset per-frame counters
        self._frame_groups = 0

        return result

    def _build_proximity_graph(self, fish_list: List["Fish"]) -> Dict["Fish", Set["Fish"]]:
        """Build a graph of fish within poker proximity of each other.

        Args:
            fish_list: List of all fish in simulation

        Returns:
            Adjacency map where fish_poker_contacts[fish] is the set of
            fish within poker range
        """

        fish_poker_contacts: Dict[Fish, Set[Fish]] = {fish: set() for fish in fish_list}

        # Pre-compute squared distance constants
        poker_min_sq = FISH_POKER_MIN_DISTANCE * FISH_POKER_MIN_DISTANCE
        poker_max_sq = FISH_POKER_MAX_DISTANCE * FISH_POKER_MAX_DISTANCE

        fish_set = set(fish_list)
        environment = self._engine.environment

        for fish in fish_list:
            if fish.is_dead():
                continue

            # Get nearby fish using spatial grid
            if environment is not None and hasattr(environment, "nearby_evolving_agents"):
                nearby = environment.nearby_evolving_agents(fish, radius=FISH_POKER_MAX_DISTANCE)
            else:
                nearby = [f for f in fish_list if f is not fish]

            # Cache fish center position
            fish_cx = fish.pos.x + fish.width * 0.5
            fish_cy = fish.pos.y + fish.height * 0.5

            for other in nearby:
                if other is fish or other not in fish_set:
                    continue
                if other.is_dead():
                    continue

                # Calculate center-to-center distance squared
                o_cx = other.pos.x + other.width * 0.5
                o_cy = other.pos.y + other.height * 0.5
                dx = fish_cx - o_cx
                dy = fish_cy - o_cy
                dist_sq = dx * dx + dy * dy

                # Must be within max distance but farther than min distance
                if poker_min_sq < dist_sq <= poker_max_sq:
                    fish_poker_contacts[fish].add(other)

        # Make graph symmetric
        for fish, contacts in fish_poker_contacts.items():
            for contact in contacts:
                if contact in fish_poker_contacts:
                    fish_poker_contacts[contact].add(fish)

        return fish_poker_contacts

    def _process_poker_groups(
        self,
        fish_list: List["Fish"],
        fish_poker_contacts: Dict["Fish", Set["Fish"]],
    ) -> int:
        """Find connected components and trigger poker games.

        Args:
            fish_list: List of all fish
            fish_poker_contacts: Proximity graph

        Returns:
            Number of poker games triggered
        """
        games_triggered = 0
        visited: Set[Fish] = set()
        processed_fish: Set[Fish] = set()

        # PERF: Limit to 1 game per frame to prevent CPU spikes
        # (poker.play_poker() is expensive - can take 10-50ms)
        MAX_GAMES_PER_FRAME = 1

        # Sort key for deterministic processing
        def fish_key(f: "Fish") -> int:
            return f.fish_id

        for fish in sorted(fish_list, key=fish_key):
            if fish in visited or fish.is_dead():
                continue

            # DFS to find connected component
            group: List[Fish] = []
            stack = [fish]

            while stack:
                current = stack.pop()
                if current in visited:
                    continue

                visited.add(current)
                if not current.is_dead():
                    group.append(current)

                # Add connected fish
                contacts = fish_poker_contacts.get(current, set())
                for neighbor in sorted(contacts, key=fish_key):
                    if neighbor not in visited:
                        stack.append(neighbor)

            # Process group if large enough
            if len(group) >= 2:
                self._frame_groups += 1
                self._groups_detected += 1

                # Filter to ready players
                ready_fish = get_ready_players(group)
                if len(ready_fish) < 2:
                    continue

                # Build sub-groups of mutually proximate ready fish
                ready_set = set(ready_fish)
                ready_visited: Set[Fish] = set()

                for start in sorted(ready_fish, key=fish_key):
                    if start in ready_visited:
                        continue

                    # PERF: Stop if we've hit the game limit
                    if games_triggered >= MAX_GAMES_PER_FRAME:
                        break

                    sub_group: List[Fish] = []
                    sub_stack = [start]

                    while sub_stack:
                        current = sub_stack.pop()
                        if current in ready_visited:
                            continue

                        ready_visited.add(current)
                        sub_group.append(current)

                        for neighbor in sorted(
                            fish_poker_contacts.get(current, set()),
                            key=fish_key,
                        ):
                            if neighbor in ready_set and neighbor not in ready_visited:
                                sub_stack.append(neighbor)

                    if len(sub_group) < 2:
                        continue

                    # Ensure mutual proximity
                    sub_group = filter_mutually_proximate(sub_group, FISH_POKER_MAX_DISTANCE)
                    if len(sub_group) < 2:
                        continue

                    # Limit group size
                    if len(sub_group) > POKER_MAX_PLAYERS:
                        sub_group = sub_group[:POKER_MAX_PLAYERS]

                    # Trigger poker game
                    rng = getattr(self._engine, "rng", None)
                    poker = PokerInteraction(sub_group, rng=rng)
                    if poker.play_poker():
                        self._engine.handle_poker_result(poker)
                        games_triggered += 1

                        # Handle deaths from poker
                        for f in sub_group:
                            if f.is_dead():
                                self._engine.record_fish_death(f)

                        processed_fish.update(sub_group)

            # PERF: Early exit if game limit reached
            if games_triggered >= MAX_GAMES_PER_FRAME:
                break

        return games_triggered

    def get_debug_info(self) -> Dict[str, Any]:
        """Return poker proximity statistics for debugging."""
        return {
            **super().get_debug_info(),
            "total_groups_detected": self._groups_detected,
            "total_games_triggered": self._games_triggered,
        }
