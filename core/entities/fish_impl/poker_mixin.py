"""PokerPlayer Protocol implementation mixin for Fish."""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from core.genetics import Genome

class FishPokerMixin:
    """Implement the PokerPlayer protocol for Fish.
    
    Expected attributes on host:
        genome: Genome
        fish_id: int
    """
    
    # Type definition for mixin expectations
    if TYPE_CHECKING:
        genome: "Genome"
        fish_id: int

    def get_poker_aggression(self) -> float:
        """Get poker aggression level (implements PokerPlayer protocol).

        Returns:
            Aggression value for poker decisions (0.0-1.0)
        """
        # Ensure we have the trait before accessing (safety)
        if hasattr(self.genome.behavioral, "aggression"):
            return self.genome.behavioral.aggression.value
        return 0.5

    def get_poker_strategy(self) -> Any:
        """Get poker strategy for this fish (implements PokerPlayer protocol).

        Returns:
            PokerStrategyAlgorithm from genome, or None for aggression-based play
        """
        trait = getattr(self.genome.behavioral, "poker_strategy", None)
        return trait.value if trait else None

    def get_poker_id(self) -> int:
        """Get stable ID for poker tracking (implements PokerPlayer protocol).

        Returns:
            fish_id for consistent identification
        """
        return self.fish_id
