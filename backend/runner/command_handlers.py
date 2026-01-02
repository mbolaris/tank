"""Command handlers for SimulationRunner.

This module contains all command handler methods extracted from SimulationRunner
to reduce class size and improve separation of concerns.

Command handlers are responsible for:
- Adding food/fish entities
- Pause/resume/reset controls
- Human poker game interactions
- Benchmark series execution
"""

import logging
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from core import entities, movement_strategy
from core.auto_evaluate_poker import AutoEvaluatePokerGame
from core.config.display import FILES, SCREEN_HEIGHT, SCREEN_WIDTH
from core.config.ecosystem import SPAWN_MARGIN_PIXELS
from core.entities import Fish
from core.genetics import Genome
from core.human_poker_game import HumanPokerGame

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


class CommandHandlerMixin:
    """Mixin class providing command handler methods for SimulationRunner.

    This separates command handling logic from the core runner lifecycle,
    reducing the main class size by ~350 lines.
    """

    def _cmd_add_food(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'add_food' command."""
        x = self.world.rng.randint(0, SCREEN_WIDTH)
        food = entities.Food(
            self.world.environment,
            x,
            0,
            source_plant=None,
            allow_stationary_types=False,
        )
        food.pos.y = 0
        self.world.add_entity(food)
        self._invalidate_state_cache()
        return None

    def _cmd_spawn_fish(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'spawn_fish' command."""
        try:
            logger.info("Spawn fish command received")
            # Random spawn position (avoid edges)
            x = self.world.rng.randint(SPAWN_MARGIN_PIXELS, SCREEN_WIDTH - SPAWN_MARGIN_PIXELS)
            y = self.world.rng.randint(SPAWN_MARGIN_PIXELS, SCREEN_HEIGHT - SPAWN_MARGIN_PIXELS)

            logger.info(f"Creating fish at position ({x}, {y})")

            # Create new fish with random genome
            genome = Genome.random(use_algorithm=True, rng=self.world.rng)
            new_fish = entities.Fish(
                self.world.environment,
                movement_strategy.AlgorithmicMovement(),
                FILES["schooling_fish"][0],
                x,
                y,
                4,  # Base speed
                genome=genome,
                generation=0,
                ecosystem=self.world.ecosystem,
            )
            self.world.add_entity(new_fish)
            new_fish.register_birth()  # Record in lineage tracker
            self._invalidate_state_cache()
        except Exception as e:
            logger.error(f"Error spawning fish: {e}")
        return None

    def _cmd_pause(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'pause' command."""
        self.world.paused = True
        logger.info("Simulation paused")
        return None

    def _cmd_resume(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'resume' command."""
        self.world.paused = False
        logger.info("Simulation resumed")
        return None

    def _cmd_reset(self: "SimulationRunner", data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle 'reset' command."""
        # Reset the underlying world to a clean frame counter and entities
        if hasattr(self.world, "reset"):
            self.world.reset()
        else:
            self.world.setup()
        self._invalidate_state_cache()
        # Unpause after reset for intuitive behavior
        self.world.paused = False
        self.fast_forward = False
        logger.info("Simulation reset")
        return None

    def _cmd_fast_forward(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'fast_forward' command."""
        enabled = data.get("enabled", False) if data else False
        self.fast_forward = enabled
        logger.info(f"Fast forward {'enabled' if enabled else 'disabled'}")
        return None

    def _cmd_start_poker(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'start_poker' command."""
        logger.info("Starting human poker game...")
        try:
            # Get top 3 fish from leaderboard
            fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

            if len(fish_list) < 3:
                logger.warning(
                    f"Not enough fish to start poker game (need 3, have {len(fish_list)})"
                )
                return self._create_error_response(
                    f"Need at least 3 fish to play poker (currently {len(fish_list)})"
                )

            # Get leaderboard
            leaderboard = self.world.ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=3, sort_by="net_energy"
            )

            # Create AI fish data from top 3
            ai_fish = []
            for entry in leaderboard[:3]:
                # Find the actual fish object
                fish = next((f for f in fish_list if f.fish_id == entry["fish_id"]), None)
                if fish:
                    ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

            # If we don't have 3 fish from leaderboard, fill with random fish
            if len(ai_fish) < 3:
                for fish in fish_list:
                    if len(ai_fish) >= 3:
                        break
                    if fish.fish_id not in [f["fish_id"] for f in ai_fish]:
                        ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

            # Create poker game
            game_id = str(uuid.uuid4())
            human_energy = data.get("energy", 500.0) if data else 500.0

            self.human_poker_game = HumanPokerGame(
                game_id=game_id,
                human_energy=human_energy,
                ai_fish=ai_fish,
                small_blind=5.0,
                big_blind=10.0,
            )

            logger.info(f"Created human poker game {game_id} with {len(ai_fish)} AI opponents")

            # Return the initial game state to the frontend
            return {
                "success": True,
                "state": self.human_poker_game.get_state(),
            }

        except Exception as e:
            logger.error(f"Error starting poker game: {e}", exc_info=True)
            return self._create_error_response(f"Failed to start poker game: {str(e)}")

    def _cmd_poker_action(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'poker_action' command."""
        if not self.human_poker_game:
            logger.warning("Poker action received but no game active")
            return self._create_error_response("No poker game active")

        if not data:
            return self._create_error_response("No action data provided")

        action = data.get("action")
        amount = data.get("amount", 0.0)

        logger.info(f"Processing poker action: {action}, amount: {amount}")

        return self.human_poker_game.handle_action("human", action, amount)

    def _cmd_poker_process_ai_turn(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'poker_process_ai_turn' command."""
        if not self.human_poker_game:
            logger.warning("AI turn processing requested but no game active")
            return self._create_error_response("No poker game active")

        return self.human_poker_game.process_single_ai_turn()

    def _cmd_poker_new_round(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'poker_new_round' command."""
        if not self.human_poker_game:
            logger.warning("New round requested but no game active")
            return self._create_error_response("No poker game active")

        logger.info("Starting new poker hand...")
        return self.human_poker_game.start_new_hand()

    def _cmd_poker_autopilot_action(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'poker_autopilot_action' command."""
        if not self.human_poker_game:
            logger.warning("Autopilot action requested but no game active")
            return self._create_error_response("No poker game active")

        game = self.human_poker_game

        # If game is over, return new_round action
        if game.game_over:
            if game.session_over:
                return {"success": True, "action": "exit", "amount": 0}
            return {"success": True, "action": "new_round", "amount": 0}

        # If not human's turn, wait
        human_player = game.players[0]  # Human is always index 0
        if game.current_player_index != 0:
            return {"success": True, "action": "wait", "amount": 0}

        # Use the same AI logic as fish opponents
        from core.poker.core import decide_action, evaluate_hand

        hand = evaluate_hand(human_player.hole_cards, game.community_cards)
        call_amount = game._get_call_amount(0)
        active_bets = [p.current_bet for p in game.players if not p.folded]
        opponent_bet = max(active_bets) if active_bets else 0.0

        action, bet_amount = decide_action(
            hand=hand,
            current_bet=human_player.current_bet,
            opponent_bet=opponent_bet,
            pot=game.pot,
            player_energy=human_player.energy,
            aggression=0.5,  # Medium aggression for autopilot
            hole_cards=human_player.hole_cards,
            community_cards=game.community_cards,
            position_on_button=(game.current_player_index == game.button_index),
            rng=getattr(self.world, "rng", None),  # Pass world RNG for determinism
        )

        # Convert BettingAction enum to string
        action_str = action.name.lower()

        # Handle check vs call
        if action_str == "check" and call_amount > 0:
            action_str = "call"
            bet_amount = call_amount
        elif action_str == "call":
            bet_amount = call_amount
        elif action_str == "raise":
            # bet_amount is the raise amount on top of call
            pass

        logger.info(f"Autopilot recommends: {action_str}, amount: {bet_amount}")
        return {"success": True, "action": action_str, "amount": bet_amount}

    def _cmd_standard_poker_series(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'standard_poker_series' command."""
        logger.info("Starting standard poker benchmark series...")
        try:
            # Get top fish from leaderboard
            fish_list = [e for e in self.world.entities_list if isinstance(e, Fish)]

            if len(fish_list) < 1:
                logger.warning("No fish available for benchmark series")
                return self._create_error_response("Need at least 1 fish to run benchmark series")

            # Get top 3 fish from leaderboard
            num_fish = min(3, len(fish_list))
            leaderboard = self.world.ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=num_fish, sort_by="net_energy"
            )

            # Build list of fish player data
            fish_players = []
            for i in range(num_fish):
                if i < len(leaderboard):
                    # Use leaderboard entry
                    entry = leaderboard[i]
                    fish = next(
                        (f for f in fish_list if f.fish_id == entry["fish_id"]), fish_list[i]
                    )
                    fish_name = (
                        f"{entry['algorithm'][:15]} (Gen {entry['generation']}) #{entry['fish_id']}"
                    )
                else:
                    # Fallback to fish from list
                    fish = fish_list[i]
                    algo_name = "Unknown"
                    behavior_algorithm = fish.genome.behavioral.behavior_algorithm.value
                    if behavior_algorithm:
                        algo_name = behavior_algorithm.algorithm_id
                    fish_name = f"{algo_name[:15]} (Gen {fish.generation}) #{fish.fish_id}"

                fish_players.append(
                    {
                        "name": fish_name,
                        "fish_id": fish.fish_id,
                        "generation": fish.generation,
                        "poker_strategy": (
                            fish.genome.behavioral.poker_strategy.value
                            if fish.genome.behavioral.poker_strategy
                            else None
                        ),
                    }
                )

            # Create benchmark series with multiple fish
            game_id = str(uuid.uuid4())
            standard_energy = data.get("standard_energy", 500.0) if data else 500.0
            max_hands = data.get("max_hands", 1000) if data else 1000

            self.standard_poker_series = AutoEvaluatePokerGame(
                game_id=game_id,
                player_pool=fish_players,
                standard_energy=standard_energy,
                max_hands=max_hands,
                small_blind=5.0,
                big_blind=10.0,
            )

            logger.info(
                f"Created standard series {game_id} with {len(fish_players)} fish vs Standard"
            )

            # Run the series (this will complete all hands)
            final_stats = self.standard_poker_series.run_evaluation()

            # Convert stats to dict for JSON serialization
            stats_dict = {
                "hands_played": final_stats.hands_played,
                "hands_remaining": final_stats.hands_remaining,
                "game_over": final_stats.game_over,
                "winner": final_stats.winner,
                "reason": final_stats.reason,
                "players": final_stats.players,  # List of all player stats
                "performance_history": final_stats.performance_history,
            }

            logger.info(
                f"Standard series complete: {final_stats.winner} after {final_stats.hands_played} hands!"
            )

            # Return the final stats to the frontend
            return {
                "success": True,
                "stats": stats_dict,
            }

        except Exception as e:
            logger.error(f"Error running benchmark series: {e}", exc_info=True)
            return self._create_error_response(f"Failed to run benchmark series: {str(e)}")

    def _cmd_set_plant_energy_input(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'set_plant_energy_input' command.

        Adjusts the runtime plant energy input rate (minimum energy gain per frame).

        Args:
            data: Dictionary with 'rate' key (float, 0.0-1.0 suggested range)
        """
        if not data or "rate" not in data:
            return self._create_error_response("Missing 'rate' parameter")

        rate = float(data["rate"])

        # Clamp to reasonable range (0.0 to 2.0)
        rate = max(0.0, min(2.0, rate))

        # Access the simulation config through the world's engine
        if hasattr(self.world, "engine") and hasattr(self.world.engine, "config"):
            config = self.world.engine.config
            if hasattr(config, "plant"):
                config.plant.plant_energy_input_rate = rate
                logger.info(f"Plant energy input rate set to {rate:.3f}")
                return {"success": True, "rate": rate}
        elif hasattr(self.world, "simulation_config"):
            config = self.world.simulation_config
            if hasattr(config, "plant"):
                config.plant.plant_energy_input_rate = rate
                logger.info(f"Plant energy input rate set to {rate:.3f}")
                return {"success": True, "rate": rate}

        return self._create_error_response("Could not access plant configuration")
