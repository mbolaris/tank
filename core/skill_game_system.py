"""Skill game interaction system for tank simulations.

This module manages skill game interactions between fish (and potentially plants).
It parallels the poker_system.py but works with the pluggable skill game framework.

IMPORTANT: This is Alife. Games naturally affect fish energy, which determines
survival and reproduction. No explicit fitness evaluation drives selection.

The system:
1. Detects when fish are close enough to play
2. Checks if both fish have enough energy and want to play
3. Runs the skill game and transfers energy based on outcome
4. Updates fish strategies via learning
5. Logs events for observation/debugging
"""

import logging
import random
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Deque, Dict, List, Optional, Tuple

from core.skills.base import SkillGame, SkillGameResult, SkillGameType
from core.skills.config import (
    get_active_skill_game,
    get_skill_game_config,
    SkillGameConfig,
)

if TYPE_CHECKING:
    from core.entities import Fish
    from core.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class SkillGameEvent:
    """Record of a skill game event for history/logging."""

    frame: int
    game_type: str
    player1_id: int
    player2_id: Optional[int]  # None for single-player games
    winner_id: Optional[int]  # None for tie or single-player
    energy_transferred: float
    player1_was_optimal: bool
    player2_was_optimal: bool = False
    details: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "frame": self.frame,
            "game_type": self.game_type,
            "player1_id": self.player1_id,
            "player2_id": self.player2_id,
            "winner_id": self.winner_id,
            "energy_transferred": self.energy_transferred,
            "player1_was_optimal": self.player1_was_optimal,
            "player2_was_optimal": self.player2_was_optimal,
            "details": self.details or {},
        }


class SkillGameSystem:
    """Manages skill game interactions in the simulation.

    This system handles:
    - Detecting potential game encounters
    - Running games between fish
    - Transferring energy based on outcomes
    - Updating fish learning
    - Logging events for observation
    """

    def __init__(
        self,
        engine: "SimulationEngine",
        max_events: int = 100,
        config: Optional[SkillGameConfig] = None,
    ):
        """Initialize the skill game system.

        Args:
            engine: The simulation engine
            max_events: Maximum events to keep in history
            config: Skill game configuration (uses global if None)
        """
        self.engine = engine
        self.config = config or get_skill_game_config()
        self.events: Deque[SkillGameEvent] = deque(maxlen=max_events)

        # Cache the active game instance
        self._active_game: Optional[SkillGame] = None
        self._game_type: Optional[SkillGameType] = None

        # Track cooldowns to prevent spam (fish_id -> frame when can play again)
        self._cooldowns: Dict[int, int] = {}
        self._cooldown_frames = 60  # 2 seconds at 30fps

        # Aggregate stats for observation
        self._total_games_played = 0
        self._total_energy_transferred = 0.0

    def get_active_game(self) -> Optional[SkillGame]:
        """Get the currently active skill game instance.

        Caches the game instance for efficiency.
        """
        current_type = self.config.active_game

        # Check if we need to refresh the game instance
        if self._game_type != current_type or self._active_game is None:
            self._active_game = get_active_skill_game()
            self._game_type = current_type

        return self._active_game

    def can_play(self, fish: "Fish", current_frame: int) -> bool:
        """Check if a fish can play a skill game.

        Args:
            fish: The fish to check
            current_frame: Current simulation frame

        Returns:
            True if fish can play
        """
        # Check energy minimum
        if fish.energy < self.config.min_energy_to_play:
            return False

        # Check cooldown
        if fish.fish_id in self._cooldowns:
            if current_frame < self._cooldowns[fish.fish_id]:
                return False

        return True

    def _set_cooldown(self, fish_id: int, current_frame: int) -> None:
        """Set cooldown for a fish after playing."""
        self._cooldowns[fish_id] = current_frame + self._cooldown_frames

    def should_trigger_game(self, fish1: "Fish", fish2: "Fish") -> bool:
        """Determine if two fish should play a skill game.

        Uses encounter_rate from config to randomize.

        Args:
            fish1: First fish
            fish2: Second fish

        Returns:
            True if a game should be triggered
        """
        if random.random() > self.config.encounter_rate:
            return False
        return True

    def _ensure_fish_has_strategy(self, fish: "Fish", game: SkillGame) -> None:
        """Ensure fish has a strategy for the current game.

        Creates default strategy if needed.

        Args:
            fish: The fish
            game: The skill game
        """
        from core.fish.skill_game_component import SkillGameComponent

        # Ensure fish has skill game component
        if not hasattr(fish, "_skill_game_component"):
            fish._skill_game_component = SkillGameComponent()

        # Ensure fish has strategy for this game
        component = fish._skill_game_component
        if component.get_strategy(game.game_type) is None:
            strategy = game.create_default_strategy()
            component.set_strategy(game.game_type, strategy)

    def play_game(
        self,
        fish1: "Fish",
        fish2: Optional["Fish"],
        current_frame: int,
    ) -> Optional[SkillGameEvent]:
        """Play a skill game between fish.

        For two-player games (RPS), both fish compete.
        For single-player games (Number Prediction), fish1 plays alone.

        Args:
            fish1: First player (always plays)
            fish2: Second player (may be None for single-player games)
            current_frame: Current simulation frame

        Returns:
            The game event, or None if game couldn't be played
        """
        game = self.get_active_game()
        if game is None:
            logger.warning("No active skill game configured")
            return None

        # Ensure both fish can play
        if not self.can_play(fish1, current_frame):
            return None
        if fish2 is not None and not self.can_play(fish2, current_frame):
            return None

        # Ensure fish have strategies
        self._ensure_fish_has_strategy(fish1, game)
        if fish2 is not None:
            self._ensure_fish_has_strategy(fish2, game)

        # Get strategies
        strategy1 = fish1._skill_game_component.get_strategy(game.game_type)
        strategy2 = None
        if fish2 is not None:
            strategy2 = fish2._skill_game_component.get_strategy(game.game_type)

        # Play the game
        game_state = {
            "player_id": str(fish1.fish_id),
            "opponent_id": str(fish2.fish_id) if fish2 else None,
        }

        if game.is_zero_sum and fish2 is not None:
            # Two-player game
            result1 = game.play_round(strategy1, strategy2, game_state)

            # Create opposite result for fish2
            result2 = SkillGameResult(
                player_id=str(fish2.fish_id),
                opponent_id=str(fish1.fish_id),
                won=not result1.won and not result1.tied,
                tied=result1.tied,
                score_change=-result1.score_change,
                was_optimal=False,  # Calculate separately if needed
                details=result1.details,
            )
        else:
            # Single-player game
            result1 = game.play_round(strategy1, None, game_state)
            result2 = None

        # Apply energy changes
        energy_transferred = self._apply_energy_changes(fish1, fish2, result1, result2)

        # Update learning
        fish1._skill_game_component.record_game_result(game.game_type, result1)
        if fish2 is not None and result2 is not None:
            fish2._skill_game_component.record_game_result(game.game_type, result2)

        # Set cooldowns
        self._set_cooldown(fish1.fish_id, current_frame)
        if fish2 is not None:
            self._set_cooldown(fish2.fish_id, current_frame)

        # Create and record event
        event = SkillGameEvent(
            frame=current_frame,
            game_type=game.game_type.value,
            player1_id=fish1.fish_id,
            player2_id=fish2.fish_id if fish2 else None,
            winner_id=fish1.fish_id if result1.won else (
                fish2.fish_id if fish2 and result2 and result2.won else None
            ),
            energy_transferred=abs(energy_transferred),
            player1_was_optimal=result1.was_optimal,
            player2_was_optimal=result2.was_optimal if result2 else False,
            details={
                "player1_action": str(result1.actual_action),
                "player2_action": str(result2.actual_action) if result2 else None,
                **result1.details,
            },
        )

        self.events.append(event)
        self._total_games_played += 1
        self._total_energy_transferred += abs(energy_transferred)

        logger.debug(
            f"Skill game: Fish #{fish1.fish_id} vs "
            f"{'Fish #' + str(fish2.fish_id) if fish2 else 'Environment'} - "
            f"{'Win' if result1.won else 'Lose/Tie'} ({energy_transferred:+.1f} energy)"
        )

        return event

    def _apply_energy_changes(
        self,
        fish1: "Fish",
        fish2: Optional["Fish"],
        result1: SkillGameResult,
        result2: Optional[SkillGameResult],
    ) -> float:
        """Apply energy changes from game results.

        For two-player zero-sum games, energy transfers between players.
        For single-player games, energy comes from/goes to environment.

        Args:
            fish1: First player
            fish2: Second player (may be None)
            result1: First player's result
            result2: Second player's result

        Returns:
            Net energy transferred (positive = fish1 gained)
        """
        energy_change = result1.score_change * self.config.stake_multiplier

        if fish2 is not None:
            # Two-player: transfer energy between fish
            if energy_change > 0:
                # Fish1 wins, takes energy from fish2
                capacity = max(0.0, fish1.max_energy - fish1.energy)
                actual_transfer = min(
                    energy_change,
                    fish2.energy * 0.5,  # Cap at 50% of loser's energy
                    capacity,
                )
                fish1.modify_energy(actual_transfer)
                fish2.modify_energy(-actual_transfer)
                return actual_transfer
            elif energy_change < 0:
                # Fish1 loses, gives energy to fish2
                capacity = max(0.0, fish2.max_energy - fish2.energy)
                actual_transfer = min(
                    -energy_change,
                    fish1.energy * 0.5,
                    capacity,
                )
                fish1.modify_energy(-actual_transfer)
                fish2.modify_energy(actual_transfer)
                return -actual_transfer
        else:
            # Single-player: energy from environment
            # Winners gain, losers lose (energy conservation not required)
            fish1.modify_energy(energy_change)

        return energy_change

    def check_and_run_encounters(
        self,
        fish_list: List["Fish"],
        current_frame: int,
        encounter_distance: float = 50.0,
    ) -> List[SkillGameEvent]:
        """Check for and run skill game encounters between nearby fish.

        Args:
            fish_list: List of all fish
            current_frame: Current simulation frame
            encounter_distance: Maximum distance for encounter

        Returns:
            List of game events that occurred
        """
        game = self.get_active_game()
        if game is None:
            return []

        events = []
        processed_pairs = set()

        for i, fish1 in enumerate(fish_list):
            if not self.can_play(fish1, current_frame):
                continue

            if game.is_zero_sum:
                # Two-player game: find opponent
                for j, fish2 in enumerate(fish_list):
                    if i >= j:  # Avoid duplicate pairs
                        continue

                    pair_key = (min(fish1.fish_id, fish2.fish_id),
                                max(fish1.fish_id, fish2.fish_id))
                    if pair_key in processed_pairs:
                        continue

                    if not self.can_play(fish2, current_frame):
                        continue

                    # Check distance (fish position is in pos.x, pos.y)
                    dx = fish1.pos.x - fish2.pos.x
                    dy = fish1.pos.y - fish2.pos.y
                    dist = (dx * dx + dy * dy) ** 0.5

                    if dist <= encounter_distance:
                        if self.should_trigger_game(fish1, fish2):
                            event = self.play_game(fish1, fish2, current_frame)
                            if event:
                                events.append(event)
                                processed_pairs.add(pair_key)
            else:
                # Single-player game: play alone
                if random.random() < self.config.encounter_rate:
                    event = self.play_game(fish1, None, current_frame)
                    if event:
                        events.append(event)

        return events

    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent game events for display.

        Args:
            count: Maximum events to return

        Returns:
            List of event dictionaries
        """
        return [e.to_dict() for e in list(self.events)[-count:]]

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics for observation.

        Returns:
            Dictionary of aggregate stats
        """
        game = self.get_active_game()
        return {
            "active_game": game.name if game else "None",
            "total_games_played": self._total_games_played,
            "total_energy_transferred": self._total_energy_transferred,
            "avg_energy_per_game": (
                self._total_energy_transferred / self._total_games_played
                if self._total_games_played > 0 else 0.0
            ),
            "config": {
                "stake_multiplier": self.config.stake_multiplier,
                "encounter_rate": self.config.encounter_rate,
                "min_energy_to_play": self.config.min_energy_to_play,
            },
        }
