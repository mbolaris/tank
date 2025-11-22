"""Table orchestration for poker games between fish players."""
from typing import Iterable, Optional, TYPE_CHECKING

from core.entities import Fish

if TYPE_CHECKING:
    from core.fish_poker import PokerResult


class PokerTable:
    """Run poker hands for a collection of fish without mixing concerns."""

    def __init__(self, players: Iterable[Fish]):
        self.players = list(players)
        if len(self.players) < 2:
            raise ValueError("PokerTable requires at least two players")

    def play_hand(self, bet_amount: Optional[float] = None) -> Optional["PokerResult"]:
        """Play a poker hand among the configured players."""

        from core.fish_poker import PokerInteraction

        interaction = PokerInteraction(*self.players)
        if not interaction.can_play_poker():
            return None

        interaction.play_poker(bet_amount=bet_amount)
        return interaction.result
