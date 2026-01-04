"""
Script to update poker imports after consolidation into core/poker/ package.

This script updates all imports from the old scattered poker modules to the new
organized poker package structure.
"""

from pathlib import Path

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # poker_interaction.py -> core.poker.core
    "from core.poker_interaction import": "from core.poker.core import",
    "from core.poker_interaction import BettingAction": "from core.poker.betting.actions import BettingAction",
    "from core.poker_interaction import BettingRound": "from core.poker.betting.actions import BettingRound",
    "from core.poker_interaction import Card": "from core.poker.core.cards import Card",
    "from core.poker_interaction import Deck": "from core.poker.core.cards import Deck",
    "from core.poker_interaction import Rank": "from core.poker.core.cards import Rank",
    "from core.poker_interaction import Suit": "from core.poker.core.cards import Suit",
    "from core.poker_interaction import HandRank": "from core.poker.core.hand import HandRank",
    "from core.poker_interaction import PokerHand": "from core.poker.core.hand import PokerHand",
    "from core.poker_interaction import PokerGameState": "from core.poker.core.game_state import PokerGameState",
    # poker_hand_strength.py -> core.poker.evaluation.strength
    "from core.poker_hand_strength import": "from core.poker.evaluation.strength import",
    # poker_strategy.py -> core.poker.strategy.base
    "from core.poker_strategy import HandStrength": "from core.poker.strategy.base import HandStrength",
    "from core.poker_strategy import OpponentModel": "from core.poker.strategy.base import OpponentModel",
    "from core.poker_strategy import PokerStrategyEngine": "from core.poker.strategy.base import PokerStrategyEngine",
    # poker_strategy_algorithms.py -> core.poker.strategy.implementations
    "from core.poker_strategy_algorithms import": "from core.poker.strategy.implementations import",
    "from core.poker_strategy_algorithms import PokerStrategyAlgorithm": "from core.poker.strategy.implementations import PokerStrategyAlgorithm",
    "from core.poker_strategy_algorithms import get_random_poker_strategy": "from core.poker.strategy.implementations import get_random_poker_strategy",
    "from core.poker_strategy_algorithms import crossover_poker_strategies": "from core.poker.strategy.implementations import crossover_poker_strategies",
    "from core.poker_strategy_algorithms import ALL_POKER_STRATEGIES": "from core.poker.strategy.implementations import ALL_POKER_STRATEGIES",
}


def update_file_imports(file_path: Path) -> bool:
    """Update imports in a single file. Returns True if file was modified."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Apply all import mappings
        for old_import, new_import in IMPORT_MAPPINGS.items():
            content = content.replace(old_import, new_import)

        # Check if file was modified
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to update all poker imports."""
    repo_root = Path(__file__).parent
    python_files = []

    # Find all Python files (excluding the new poker package)
    for pattern in ["core/**/*.py", "tests/**/*.py", "*.py"]:
        python_files.extend(repo_root.glob(pattern))

    # Exclude files in the new poker package
    python_files = [f for f in python_files if "core/poker/" not in str(f)]

    modified_files = []
    for file_path in python_files:
        if file_path.name == "update_poker_imports.py":
            continue

        if update_file_imports(file_path):
            modified_files.append(file_path)
            print(f"✓ Updated: {file_path.relative_to(repo_root)}")

    print(f"\n{'='*60}")
    print(f"Modified {len(modified_files)} files")
    print(f"{'='*60}")

    if modified_files:
        print("\nModified files:")
        for f in modified_files:
            print(f"  - {f.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
