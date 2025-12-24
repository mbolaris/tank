"""Reproduction management component for fish.

This module provides the ReproductionComponent class which handles all reproduction-related
functionality for fish, including mating and offspring generation.
Separating reproduction logic into its own component improves code organization and testability.

Note: All reproduction is now instant (no pregnancy/gestation period). Asexual reproduction
triggers immediately when conditions are met, and offspring are created in the same frame.
"""

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from core.entities.base import LifeStage
    from core.genetics import Genome


class ReproductionComponent:
    """Manages fish reproduction and mating mechanics.

    This component encapsulates all reproduction-related logic for a fish, including:
    - Mate compatibility calculation
    - Reproduction cooldown tracking
    - Offspring genome generation

    All reproduction is instant - there is no pregnancy/gestation period.

    Attributes:
        reproduction_cooldown: Frames until can reproduce again.
        overflow_energy_bank: Energy banked for future reproduction.
    """

    # Reproduction constants
    REPRODUCTION_ENERGY_PERCENTAGE = 0.9  # Require ~90% energy before any reproduction path
    REPRODUCTION_COOLDOWN = 300  # 10 seconds at 30fps - prevents constant reproduction
    MATING_DISTANCE = 60.0  # Maximum distance for mating
    REPRODUCTION_ENERGY_COST = 10.0  # Energy cost for initiating mating
    ENERGY_TRANSFER_TO_BABY = 0.30  # Parent transfers 30% of their current energy to baby
    MIN_ACCEPTANCE_THRESHOLD = 0.3  # Minimum chance to accept mate (30%)

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
        """Check if the fish can trigger asexual reproduction."""

        if not self.can_reproduce(life_stage, energy, max_energy):
            return False

        # Asexual reproduction only triggers when fully energized
        return energy >= max_energy

    def calculate_mate_attraction(
        self,
        own_genome: "Genome",
        mate_genome: "Genome",
        own_energy: float,
        own_max_energy: float,
        mate_energy: float,
        mate_max_energy: float,
    ) -> float:
        """Calculate attraction to a potential mate.

        Args:
            own_genome: This fish's genome
            mate_genome: Potential mate's genome
            own_energy: This fish's current energy
            own_max_energy: This fish's maximum energy
            mate_energy: Mate's current energy
            mate_max_energy: Mate's maximum energy

        Returns:
            float: Attraction score (0.0 to 1.0)
        """
        # Base attraction from genome
        attraction = own_genome.calculate_mate_attraction(mate_genome)

        # Add energy consideration (prefer mates with good energy)
        energy_ratio = mate_energy / mate_max_energy if mate_max_energy > 0 else 0.0
        energy_bonus = energy_ratio * 0.2
        total_attraction = min(attraction + energy_bonus, 1.0)

        return total_attraction

    def attempt_mating(
        self,
        own_genome: "Genome",
        mate_genome: "Genome",
        own_energy: float,
        own_max_energy: float,
        mate_energy: float,
        mate_max_energy: float,
        distance: float,
    ) -> bool:
        """Attempt to mate with another fish.

        Args:
            own_genome: This fish's genome
            mate_genome: Potential mate's genome
            own_energy: This fish's current energy
            own_max_energy: This fish's maximum energy
            mate_energy: Mate's current energy
            mate_max_energy: Mate's maximum energy
            distance: Distance to potential mate

        Returns:
            bool: True if mating was successful
        """
        # Standard mating is disabled; sexual reproduction now occurs only via poker.
        return False

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
