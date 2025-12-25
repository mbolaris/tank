"""Reproduction management component for fish.

This module provides the ReproductionComponent class which handles reproduction-related
functionality for fish, specifically asexual reproduction and cooldown tracking.

Note on Sexual Reproduction:
    Sexual reproduction occurs ONLY via poker games, not through traditional mating.
    When fish win poker games, they may trigger reproduction with their opponent.
    This design centralizes reproduction logic in PokerSystem.

Note: All reproduction is instant (no pregnancy/gestation period). Asexual reproduction
triggers immediately when conditions are met, and offspring are created in the same frame.
"""

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from core.entities.base import LifeStage
    from core.genetics import Genome


class ReproductionComponent:
    """Manages fish reproduction mechanics.

    This component handles:
    - Asexual reproduction checks and triggers
    - Reproduction cooldown tracking
    - Offspring genome generation
    - Overflow energy banking for reproduction

    Note: Sexual reproduction happens via poker games (see PokerSystem).
    This component does NOT handle mate selection or attraction.

    All reproduction is instant - there is no pregnancy/gestation period.

    Attributes:
        reproduction_cooldown: Frames until can reproduce again.
        overflow_energy_bank: Energy banked for future reproduction.
    """

    # Reproduction constants
    REPRODUCTION_ENERGY_PERCENTAGE = 0.9  # Require ~90% energy before any reproduction path
    ASEXUAL_REPRODUCTION_THRESHOLD = 0.95  # Asexual requires 95% (higher since no mate to help)
    REPRODUCTION_COOLDOWN = 300  # 10 seconds at 30fps - prevents constant reproduction
    MATING_DISTANCE = 60.0  # Maximum distance for poker-triggered reproduction
    REPRODUCTION_ENERGY_COST = 10.0  # Energy cost for reproduction
    ENERGY_TRANSFER_TO_BABY = 0.30  # Parent transfers 30% of their current energy to baby

    __slots__ = (
        "reproduction_cooldown",
        "overflow_energy_bank",
    )

    def __init__(self) -> None:
        """Initialize the reproduction component."""
        self.reproduction_cooldown: int = 0
        self.overflow_energy_bank: float = 0.0

    def bank_overflow_energy(self, amount: float, max_bank: Optional[float] = None) -> float:
        """Bank overflow energy for future reproduction.

        Returns the amount actually banked (may be less than requested if max_bank is provided).
        """
        if amount <= 0:
            return 0.0

        if max_bank is not None:
            available = max(0.0, max_bank - self.overflow_energy_bank)
            banked = min(amount, available)
        else:
            banked = amount

        self.overflow_energy_bank += banked
        return banked

    def consume_overflow_energy_bank(self, max_amount: float) -> float:
        if max_amount <= 0 or self.overflow_energy_bank <= 0:
            return 0.0

        used = min(self.overflow_energy_bank, max_amount)
        self.overflow_energy_bank -= used
        return used

    def can_reproduce(self, life_stage: "LifeStage", energy: float, max_energy: float) -> bool:
        """Check if fish can reproduce.

        Fish must have 90% of their max energy to reproduce - proving they are successful
        at resource acquisition.

        Args:
            life_stage: Current life stage of the fish.
            energy: Current energy level.
            max_energy: Maximum energy capacity.

        Returns:
            True if fish can reproduce.
        """
        from core.entities.base import LifeStage

        min_energy_for_reproduction = max_energy * self.REPRODUCTION_ENERGY_PERCENTAGE
        return (
            life_stage == LifeStage.ADULT
            and energy >= min_energy_for_reproduction
            and self.reproduction_cooldown <= 0
        )

    def can_asexually_reproduce(
        self,
        life_stage: "LifeStage",
        energy: float,
        max_energy: float,
    ) -> bool:
        """Check if the fish can trigger asexual reproduction.
        
        Asexual reproduction requires higher energy than sexual reproduction,
        as the parent must fund the entire offspring alone.
        """
        if not self.can_reproduce(life_stage, energy, max_energy):
            return False

        # Asexual reproduction requires 95% energy (slightly less than 100%)
        return energy >= max_energy * self.ASEXUAL_REPRODUCTION_THRESHOLD

    def trigger_asexual_reproduction(
        self, 
        own_genome: "Genome", 
        rng: Optional["pyrandom.Random"] = None
    ) -> Tuple["Genome", float]:
        """Trigger instant asexual reproduction and return offspring genome.

        This creates a mutated clone of the parent's genome. The reproduction
        happens immediately (no pregnancy period).

        Args:
            own_genome: This fish's genome
            rng: Random number generator for deterministic mutation

        Returns:
            Tuple of (offspring_genome, energy_transfer_fraction)
        """
        from core.genetics import Genome

        # Set cooldown to prevent immediate re-reproduction
        self.reproduction_cooldown = self.REPRODUCTION_COOLDOWN

        # Create mutated clone
        offspring_genome = Genome.clone_with_mutation(own_genome, rng=rng)

        return offspring_genome, self.ENERGY_TRANSFER_TO_BABY

    def update_cooldown(self) -> None:
        """Update reproduction cooldown timer.

        Call this once per frame to decrement the cooldown.
        """
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

    def get_reproduction_state(self) -> str:
        """Get a human-readable description of reproduction state.

        Returns:
            str: Description of reproduction state
        """
        if self.reproduction_cooldown > 0:
            seconds_until_ready = self.reproduction_cooldown / 30.0
            return f"Cooldown ({seconds_until_ready:.1f}s until ready)"
        else:
            return "Ready to reproduce"
