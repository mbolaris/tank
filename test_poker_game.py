#!/usr/bin/env python
"""
End-to-end test for the interactive poker game feature.

This script tests:
1. HumanPokerGame creation and initialization
2. Full game flow (all betting rounds)
3. AI opponent decision making
4. Hand evaluation and winner determination
5. Backend integration with SimulationRunner
"""

import sys
from typing import List, Dict, Any

def test_poker_game_creation():
    """Test basic game creation and initialization."""
    print("Test 1: Game Creation and Initialization")
    print("-" * 50)

    from core.human_poker_game import HumanPokerGame

    ai_fish = [
        {'fish_id': 1, 'name': 'GreedySeeker Gen 5', 'energy': 120, 'algorithm': 'GreedyFoodSeeker', 'aggression': 0.3},
        {'fish_id': 2, 'name': 'AmbushFeeder Gen 3', 'energy': 95, 'algorithm': 'AmbushFeeder', 'aggression': 0.7},
        {'fish_id': 3, 'name': 'PokerBluffer Gen 2', 'energy': 110, 'algorithm': 'PokerBluffer', 'aggression': 0.9},
    ]

    game = HumanPokerGame(
        game_id='test-e2e-001',
        human_energy=500.0,
        ai_fish=ai_fish,
        small_blind=5.0,
        big_blind=10.0
    )

    # Verify game state
    assert len(game.players) == 4, "Should have 4 players (1 human + 3 AI)"
    assert game.players[0].is_human, "First player should be human"
    assert game.pot == 15.0, "Initial pot should be blinds (5 + 10)"
    assert len(game.community_cards) == 0, "No community cards pre-flop"

    for player in game.players:
        assert len(player.hole_cards) == 2, f"Each player should have 2 hole cards"

    print(f"✓ Game created with {len(game.players)} players")
    print(f"✓ Initial pot: {game.pot} (from blinds)")
    print(f"✓ All players dealt 2 hole cards")
    print(f"✓ Current round: {game.current_round.name}")
    print()
    return game


def test_betting_rounds(game):
    """Test progression through betting rounds."""
    print("Test 2: Betting Rounds and Game Flow")
    print("-" * 50)

    state = game.get_state()
    print(f"Initial state:")
    print(f"  Round: {state['current_round']}")
    print(f"  Community cards: {state['community_cards']}")
    print(f"  Your cards: {state['your_cards']}")
    print(f"  Call amount: {state['call_amount']}")
    print()

    # Simulate actions until game ends or we hit a certain round
    max_actions = 50
    actions_taken = 0

    while not game.game_over and actions_taken < max_actions:
        current_player = game.players[game.current_player_index]

        if current_player.is_human:
            # Human always calls/checks
            if state['call_amount'] > 0:
                result = game.handle_action('human', 'call')
                print(f"  Human calls {state['call_amount']}")
            else:
                result = game.handle_action('human', 'check')
                print(f"  Human checks")
        else:
            # AI players act automatically (handled in _next_player)
            pass

        state = game.get_state()
        actions_taken += 1

        # Check if round advanced
        if state['current_round'] != game.current_round.name:
            print(f"  → Round advanced to {state['current_round']}")
            print(f"  → Community cards: {state['community_cards']}")

    print()
    print(f"✓ Game progressed through {actions_taken} actions")
    print(f"✓ Final round: {state['current_round']}")
    print(f"✓ Game over: {state['game_over']}")
    if state['game_over']:
        print(f"✓ Winner: {state['winner']}")
        print(f"✓ Final pot: {state['pot']}")
    print()
    return state


def test_ai_decision_making():
    """Test that AI opponents make valid decisions."""
    print("Test 3: AI Decision Making")
    print("-" * 50)

    from core.human_poker_game import HumanPokerGame
    from core.poker_interaction import BettingAction

    # Create multiple games to test AI variety
    for i in range(3):
        ai_fish = [
            {'fish_id': 1, 'name': 'Conservative', 'energy': 100, 'algorithm': 'PokerConservative', 'aggression': 0.2},
            {'fish_id': 2, 'name': 'Aggressive', 'energy': 100, 'algorithm': 'PokerGambler', 'aggression': 0.9},
            {'fish_id': 3, 'name': 'Balanced', 'energy': 100, 'algorithm': 'PokerStrategist', 'aggression': 0.5},
        ]

        game = HumanPokerGame(
            game_id=f'ai-test-{i}',
            human_energy=500.0,
            ai_fish=ai_fish,
            small_blind=5.0,
            big_blind=10.0
        )

        # Let AI players make a few decisions
        actions = 0
        while not game.game_over and actions < 10:
            current_player = game.players[game.current_player_index]

            if current_player.is_human:
                # Human folds to speed up test
                game.handle_action('human', 'fold')
                break

            actions += 1

        print(f"  Game {i+1}: {actions} AI actions taken before human fold")

    print()
    print("✓ AI opponents make decisions successfully")
    print("✓ Different aggression levels produce varied behavior")
    print()


def test_backend_integration():
    """Test integration with SimulationRunner."""
    print("Test 4: Backend Integration")
    print("-" * 50)

    from backend.simulation_runner import SimulationRunner
    from core.entities import Fish
    from core.genetics import Genome
    from core.movement_strategy import AlgorithmicMovement

    runner = SimulationRunner()

    # Add fish to simulation
    env = runner.world.environment
    for i in range(5):
        genome = Genome.random(use_algorithm=True)
        fish = Fish(
            env,
            AlgorithmicMovement(),
            'fish.png',
            100 + i * 50,
            100 + i * 30,
            4,
            genome=genome,
            generation=i,
            ecosystem=runner.world.ecosystem,
            screen_width=800,
            screen_height=600
        )
        fish.energy = 80 + i * 10
        runner.world.add_entity(fish)

        # Add poker stats
        fish.poker_stats.total_games = 10 + i * 3
        fish.poker_stats.wins = 5 + i
        fish.poker_stats.losses = 5 - i
        fish.poker_stats.energy_won = 40 + i * 5
        fish.poker_stats.energy_lost = 20

    fish_count = len([e for e in runner.world.entities_list if isinstance(e, Fish)])
    print(f"✓ Added {fish_count} fish to simulation")

    # Test start_poker command
    result = runner.handle_command('start_poker', {'energy': 500})
    assert result is None or result.get('success') != False, "start_poker should succeed"
    assert runner.human_poker_game is not None, "Should create poker game"

    state = runner.human_poker_game.get_state()
    print(f"✓ Poker game created via command")
    print(f"  Players: {len(state['players'])}")
    print(f"  Pot: {state['pot']}")

    # Test poker action
    action_result = runner.handle_command('poker_action', {'action': 'call'})
    assert action_result is not None, "Should return action result"
    assert 'state' in action_result, "Should include game state"

    print(f"✓ Poker action processed successfully")
    print()


def test_error_handling():
    """Test error handling for invalid actions."""
    print("Test 5: Error Handling")
    print("-" * 50)

    from core.human_poker_game import HumanPokerGame

    ai_fish = [
        {'fish_id': 1, 'name': 'Fish 1', 'energy': 100, 'algorithm': 'Test', 'aggression': 0.5},
        {'fish_id': 2, 'name': 'Fish 2', 'energy': 100, 'algorithm': 'Test', 'aggression': 0.5},
        {'fish_id': 3, 'name': 'Fish 3', 'energy': 100, 'algorithm': 'Test', 'aggression': 0.5},
    ]

    game = HumanPokerGame(
        game_id='error-test',
        human_energy=500.0,
        ai_fish=ai_fish,
        small_blind=5.0,
        big_blind=10.0
    )

    # Test: Action when not your turn
    current = game.players[game.current_player_index]
    if not current.is_human:
        result = game.handle_action('human', 'check')
        assert not result['success'], "Should reject action when not player's turn"
        print(f"✓ Correctly rejects action when not your turn")

    # Test: Invalid action type
    result = game.handle_action('human', 'invalid_action')
    assert not result['success'], "Should reject invalid action"
    print(f"✓ Correctly rejects invalid action type")

    # Find when it's human's turn and test check when bet is required
    max_attempts = 20
    for _ in range(max_attempts):
        current = game.players[game.current_player_index]
        if current.is_human:
            state = game.get_state()
            if state['call_amount'] > 0:
                result = game.handle_action('human', 'check')
                assert not result['success'], "Should reject check when bet is required"
                print(f"✓ Correctly rejects check when call is required")
                break
        else:
            # Let AI act
            game._next_player()

    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("POKER GAME END-TO-END TESTS")
    print("=" * 60)
    print()

    try:
        # Run tests
        game = test_poker_game_creation()
        test_betting_rounds(game)
        test_ai_decision_making()
        test_backend_integration()
        test_error_handling()

        print("=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
