import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from core.human_poker_game import HumanPokerGame

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)


class PokerCommands:
    def _cmd_start_poker(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'start_poker' command."""
        logger.info("Starting human poker game...")
        try:
            # Get top 3 fish from leaderboard
            # Intentional: poker only applies to fish agents in TankWorld v1
            entities_list = self.world.get_entities_for_snapshot()
            fish_list = [
                e for e in entities_list
                if getattr(e, 'snapshot_type', None) == "fish"
            ]

            if len(fish_list) < 3:
                logger.warning(
                    f"Not enough fish to start poker game (need 3, have {len(fish_list)})"
                )
                return self._create_error_response(
                    f"Need at least 3 fish to play poker (currently {len(fish_list)})"
                )

            # Get leaderboard
            ecosystem = getattr(self.world, "ecosystem", None)
            if not ecosystem:
                return self._create_error_response("Ecosystem not available for poker")

            # Get top 12 fish to provide variety
            leaderboard = ecosystem.get_poker_leaderboard(
                fish_list=fish_list, limit=12, sort_by="net_energy"
            )

            # Shuffle and pick 3
            rng = self.world.rng
            selected_entries = list(leaderboard)
            if rng:
                rng.shuffle(selected_entries)
            else:
                import random

                random.shuffle(selected_entries)

            selected_entries = selected_entries[:3]

            # Create AI fish data from selected entries
            ai_fish = []
            for entry in selected_entries:
                # Find the actual fish object
                fish = next((f for f in fish_list if f.fish_id == entry["fish_id"]), None)
                if fish:
                    ai_fish.append(self._create_fish_player_data(fish, include_aggression=True))

            # If we don't have 3 fish from leaderboard, fill with random fish
            if len(ai_fish) < 3:
                for fish in fish_list:
                    if len(ai_fish) >= 3:
                        break
                    # Avoid duplicates
                    if any(f["fish_id"] == fish.fish_id for f in ai_fish):
                        continue
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

    def _apply_poker_rewards(self: "SimulationRunner", result: Dict[str, Any]) -> None:
        """Apply energy and reproduction rewards to the winner of a poker hand."""
        if not result or not result.get("fish_id"):
            return

        winner_id = result["fish_id"]
        pot = result["pot"]
        is_human = result["is_human"]

        # 1. Apply Energy Reward
        # Find the winning fish entity
        entities_list = getattr(self.world, "get_entities_for_snapshot", lambda: [])()
        if not entities_list:
            # Fallback if get_entities_for_snapshot is not available (e.g. some tests)
            engine = getattr(self.world, "engine", None)
            if engine:
                entities_list = engine.get_all_entities()

        winner_entity = next(
            (e for e in entities_list if getattr(e, "fish_id", None) == winner_id), None
        )

        if winner_entity:
            # Add energy
            winner_entity.energy += pot
            logger.info(f"Poker Reward: Fish #{winner_id} won {pot:.1f} energy")

            # 2. Trigger Reproduction (if AI won)
            # We use the existing ReproductionService to handle genetics, cooldowns, etc.
            if not is_human:
                engine = getattr(self.world, "engine", None)
                reproduction_service = getattr(engine, "reproduction_service", None)

                if reproduction_service:
                    # Construct participating fish list for mate selection
                    game = self.human_poker_game
                    participating_fish = []
                    for p in game.players:
                        if not p.is_human and p.fish_id is not None:
                            fish = next(
                                (
                                    e
                                    for e in entities_list
                                    if getattr(e, "fish_id", None) == p.fish_id
                                ),
                                None,
                            )
                            if fish:
                                participating_fish.append(fish)

                    # Mock the PokerInteraction object expected by reproduction service
                    class MockPokerResult:
                        def __init__(self, w_id, count):
                            self.winner_id = w_id
                            self.fish_count = count
                            self.is_tie = False
                            self.winner_type = "fish"

                    class MockPokerInteraction:
                        def __init__(self, w_id, players):
                            self.result = MockPokerResult(w_id, len(players))
                            self.fish_players = players

                        def _get_player_id(self, player):
                            return player.fish_id

                    mock_poker = MockPokerInteraction(winner_id, participating_fish)

                    # Attempt reproduction
                    try:
                        baby = reproduction_service.handle_post_poker_reproduction(mock_poker)
                        if baby:
                            logger.info(
                                f"Poker Reward: Fish #{winner_id} reproduced after winning!"
                            )
                    except Exception as e:
                        logger.error(f"Error triggering poker reproduction: {e}")

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

        result = self.human_poker_game.handle_action("human", action, amount)

        # Check for game completion and apply rewards
        if result.get("success") and self.human_poker_game.game_over:
            hand_result = self.human_poker_game.get_last_hand_result()
            if hand_result:
                self._apply_poker_rewards(hand_result)

        return result

    def _cmd_poker_process_ai_turn(
        self: "SimulationRunner", data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle 'poker_process_ai_turn' command."""
        if not self.human_poker_game:
            logger.warning("AI turn processing requested but no game active")
            return self._create_error_response("No poker game active")

        result = self.human_poker_game.process_single_ai_turn()

        # Check for game completion and apply rewards
        if result.get("success") and self.human_poker_game.game_over:
            hand_result = self.human_poker_game.get_last_hand_result()
            if hand_result:
                self._apply_poker_rewards(hand_result)

        return result

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
            now = time.monotonic()
            last = getattr(self, "_last_poker_autopilot_no_game_warning", 0.0)
            if now - last >= 5.0:
                logger.warning("Autopilot action requested but no game active")
                self._last_poker_autopilot_no_game_warning = now
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
            rng=self.world.rng,  # Pass world RNG for determinism
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
            if bet_amount <= 0:
                if call_amount > 0:
                    action_str = "call"
                    bet_amount = call_amount
                else:
                    action_str = "check"
                    bet_amount = 0
            # bet_amount is the raise amount on top of call
            pass

        logger.info(f"Autopilot recommends: {action_str}, amount: {bet_amount}")
        return {"success": True, "action": action_str, "amount": bet_amount}
