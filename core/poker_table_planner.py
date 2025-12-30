"""Mixed poker table planning and effect application.

This module provides clean separation of concerns for mixed poker games:
- MixedPokerTablePlanner: Forms tables from eligible fish (fish-initiated)
- PokerEffects: Value object for game outcomes
- MixedPokerEffectApplier: Applies effects to entities

Design Philosophy:
    Poker should OUTPUT effects, not directly mutate entities.
    The engine/lifecycle system applies effects in one place.

Table Formation:
    Fish-initiated only. Plants don't initiate poker - fish do.
    For each eligible fish, query nearby entities, form a table.
    This eliminates the global graph + DFS complexity.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Set, Union

from core.config.server import POKER_ACTIVITY_ENABLED
from core.mixed_poker import MixedPokerInteraction

if TYPE_CHECKING:
    from core.entities import Fish
    from core.entities.plant import Plant
    from core.environment import Environment
    import random

# Type alias
PokerPlayer = Union["Fish", "Plant"]


@dataclass
class PokerEffects:
    """Value object describing effects from a poker game.

    Poker games produce effects that should be applied by the engine,
    not directly by the poker system. This decouples game logic from
    entity mutation.
    """

    # Energy changes are already applied by MixedPokerInteraction
    # These flags tell the engine what post-game actions to take

    dead_fish: List["Fish"] = field(default_factory=list)
    dead_plants: List["Plant"] = field(default_factory=list)
    babies: List["Fish"] = field(default_factory=list)
    cooldowns_applied: bool = True  # MixedPokerInteraction applies these


@dataclass
class PlannedTable:
    """A planned poker table with fish initiator and other players."""

    initiator: "Fish"
    players: List[PokerPlayer]


class MixedPokerTablePlanner:
    """Plans poker tables using fish-initiated local queries.

    Algorithm:
        1. Collect eligible fish (alive, energy >= min, not on cooldown)
        2. Sort by stable ID for determinism
        3. For each fish not yet assigned:
           a. Query nearby poker entities
           b. Filter to eligible opponents
           c. Pick up to MAX_PLAYERS (closest-first, tie by ID)
           d. If group size >= 2: schedule table, mark all assigned

    This replaces the global adjacency graph + DFS approach with
    simple local queries. Much easier to reason about correctness.
    """

    def __init__(
        self,
        environment: "Environment",
        max_players: int,
        max_distance: float,
        min_energy: float,
        max_tables_per_tick: int = 10,
        rng: Optional["random.Random"] = None,
    ) -> None:
        """Initialize the table planner.

        Args:
            environment: Spatial query provider
            max_players: Maximum players per table
            max_distance: Maximum distance between all players
            min_energy: Minimum energy to play poker
            max_tables_per_tick: Budget - max tables to form per tick
            rng: Random generator for determinism
        """
        self.environment = environment
        self.max_players = max_players
        self.max_distance = max_distance
        self.min_energy = min_energy
        self.max_tables_per_tick = max_tables_per_tick
        self.rng = rng

    def plan_tables(
        self,
        fish_list: List["Fish"],
        plant_list: List["Plant"],
    ) -> List[PlannedTable]:
        """Plan poker tables for this tick.

        Fish-initiated: each eligible fish can form a table with nearby
        fish and plants. Plants cannot initiate.

        Args:
            fish_list: All living fish
            plant_list: All living plants

        Returns:
            List of planned tables (up to max_tables_per_tick)
        """
        if not POKER_ACTIVITY_ENABLED:
            return []

        from core.entities import Fish
        from core.entities.plant import Plant

        # Collect eligible fish initiators
        eligible_fish = [f for f in fish_list if self._is_eligible_initiator(f)]

        if not eligible_fish:
            return []

        # Sort by fish_id for deterministic order
        eligible_fish.sort(key=lambda f: f.fish_id)

        # Build set of all poker-eligible entities for fast lookup
        eligible_plants = [p for p in plant_list if self._is_eligible_plant(p)]
        all_eligible: Set[PokerPlayer] = set(eligible_fish) | set(eligible_plants)

        # Track who has been assigned this tick
        assigned: Set[PokerPlayer] = set()
        tables: List[PlannedTable] = []

        max_dist_sq = self.max_distance * self.max_distance

        for fish in eligible_fish:
            # Budget check
            if len(tables) >= self.max_tables_per_tick:
                break

            # Skip if already assigned
            if fish in assigned:
                continue

            # Query nearby poker entities
            candidates = self._get_nearby_candidates(fish, all_eligible, assigned)

            if not candidates:
                continue

            # Filter to those actually within max_distance
            fish_cx = fish.pos.x + fish.width * 0.5
            fish_cy = fish.pos.y + fish.height * 0.5

            nearby_valid: List[tuple] = []  # (distance_sq, player)
            for candidate in candidates:
                c_cx = candidate.pos.x + candidate.width * 0.5
                c_cy = candidate.pos.y + candidate.height * 0.5
                dx = fish_cx - c_cx
                dy = fish_cy - c_cy
                dist_sq = dx * dx + dy * dy

                if dist_sq <= max_dist_sq:
                    nearby_valid.append((dist_sq, candidate))

            if not nearby_valid:
                continue

            # Sort by distance, then by ID for determinism
            nearby_valid.sort(key=lambda x: (x[0], self._get_stable_id(x[1])))

            # Build table: initiator + up to (max_players - 1) others
            table_players: List[PokerPlayer] = [fish]
            for _, candidate in nearby_valid:
                if len(table_players) >= self.max_players:
                    break
                # Verify mutual proximity (all players within max_distance of each other)
                if self._is_mutually_proximate(table_players, candidate, max_dist_sq):
                    table_players.append(candidate)

            # Need at least 2 players
            if len(table_players) >= 2:
                tables.append(PlannedTable(initiator=fish, players=table_players))
                assigned.update(table_players)

        return tables

    def _is_eligible_initiator(self, fish: "Fish") -> bool:
        """Check if fish can initiate a poker game."""
        if getattr(fish, "poker_cooldown", 0) > 0:
            return False
        if fish.energy < self.min_energy:
            return False
        if hasattr(fish, "is_dead") and fish.is_dead():
            return False
        return True

    def _is_eligible_plant(self, plant: "Plant") -> bool:
        """Check if plant can participate in poker."""
        can_play = getattr(plant, "can_play_poker", None)
        if callable(can_play):
            return can_play()
        if getattr(plant, "poker_cooldown", 0) > 0:
            return False
        if hasattr(plant, "is_dead") and plant.is_dead():
            return False
        return True

    def _get_nearby_candidates(
        self,
        fish: "Fish",
        all_eligible: Set[PokerPlayer],
        assigned: Set[PokerPlayer],
    ) -> List[PokerPlayer]:
        """Get nearby poker-eligible entities."""
        if self.environment is None:
            return []

        search_radius = self.max_distance + max(fish.width, fish.height) * 0.5

        # Use specialized query if available
        if hasattr(self.environment, "nearby_poker_entities"):
            nearby = self.environment.nearby_poker_entities(fish, radius=search_radius)
        elif hasattr(self.environment, "nearby_agents"):
            nearby = self.environment.nearby_agents(fish, radius=search_radius)
        else:
            return []

        # Filter to eligible and not-assigned
        return [e for e in nearby if e in all_eligible and e not in assigned and e is not fish]

    def _is_mutually_proximate(
        self,
        current_players: List[PokerPlayer],
        candidate: PokerPlayer,
        max_dist_sq: float,
    ) -> bool:
        """Check if candidate is within max_distance of ALL current players."""
        c_cx = candidate.pos.x + candidate.width * 0.5
        c_cy = candidate.pos.y + candidate.height * 0.5

        for player in current_players:
            p_cx = player.pos.x + player.width * 0.5
            p_cy = player.pos.y + player.height * 0.5
            dx = c_cx - p_cx
            dy = c_cy - p_cy
            if dx * dx + dy * dy > max_dist_sq:
                return False
        return True

    def _get_stable_id(self, entity: PokerPlayer) -> int:
        """Get a stable ID for deterministic sorting."""
        if hasattr(entity, "fish_id"):
            return entity.fish_id
        if hasattr(entity, "plant_id"):
            return entity.plant_id + 1_000_000  # Offset to separate from fish
        return id(entity)
