"""Reproduction management component for fish.

This module provides the ReproductionComponent class which handles all reproduction-related
functionality for fish, including mating, pregnancy, and offspring generation.
Separating reproduction logic into its own component improves code organization and testability.
"""

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from core.entities.base import LifeStage
    from core.genetics import Genome


class ReproductionComponent:
    """Manages fish reproduction, pregnancy, and mating mechanics.

    This component encapsulates all reproduction-related logic for a fish, including:
    - Mate compatibility calculation
    - Pregnancy state management
    - Reproduction cooldown tracking
    - Offspring generation

    Attributes:
        is_pregnant: Whether the fish is currently pregnant.
        pregnancy_timer: Frames remaining until birth.
        reproduction_cooldown: Frames until can reproduce again.
        mate_genome: Genome of the mate (stored for offspring generation).
    """

    # Reproduction constants
    REPRODUCTION_ENERGY_PERCENTAGE = 1.0  # Require full energy before any reproduction path
    REPRODUCTION_COOLDOWN = 180  # 6 seconds (reduced for better breeding and faster generations)
    PREGNANCY_DURATION = 240  # 8 seconds (reduced for faster generations)
    MATING_DISTANCE = 60.0  # Maximum distance for mating
    REPRODUCTION_ENERGY_COST = 10.0  # Energy cost for initiating mating
    ENERGY_TRANSFER_TO_BABY = 0.30  # Parent transfers 30% of their current energy to baby
    MIN_ACCEPTANCE_THRESHOLD = 0.3  # Minimum chance to accept mate (30%)

    __slots__ = (
        "is_pregnant",
        "pregnancy_timer",
        "reproduction_cooldown",
        "mate_genome",
        "_asexual_pregnancy",
        "stored_overflow_energy",
    )

    def __init__(self) -> None:
        """Initialize the reproduction component."""
        self.is_pregnant: bool = False
        self.pregnancy_timer: int = 0
        self.reproduction_cooldown: int = 0
        self.mate_genome: Optional[Genome] = None
        self._asexual_pregnancy: bool = False
        # Overflow energy redirected into reproduction (from capped gains)
        # is stored here until birth so it can be passed to the offspring.
        self.stored_overflow_energy: float = 0.0

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
            and not self.is_pregnant
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

    def calculate_mate_compatibility(
        self,
        own_genome: "Genome",
        mate_genome: "Genome",
        own_energy: float,
        own_max_energy: float,
        mate_energy: float,
        mate_max_energy: float,
    ) -> float:
        """Calculate compatibility with a potential mate.

        Args:
            own_genome: This fish's genome
            mate_genome: Potential mate's genome
            own_energy: This fish's current energy
            own_max_energy: This fish's maximum energy
            mate_energy: Mate's current energy
            mate_max_energy: Mate's maximum energy

        Returns:
            float: Compatibility score (0.0 to 1.0)
        """
        # Base compatibility from genome
        compatibility = own_genome.calculate_mate_compatibility(mate_genome)

        # Add energy consideration (prefer mates with good energy)
        energy_ratio = mate_energy / mate_max_energy if mate_max_energy > 0 else 0.0
        energy_bonus = energy_ratio * 0.2
        total_compatibility = min(compatibility + energy_bonus, 1.0)

        return total_compatibility

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

    def start_asexual_pregnancy(self, overflow_energy: float = 0.0) -> None:
        """Begin asexual reproduction cycle.

        Args:
            overflow_energy: Extra energy redirected into reproduction because
                the parent was already at capacity. This reserve will be
                transferred to the offspring at birth, preserving energy.
        """

        self.is_pregnant = True
        self.pregnancy_timer = self.PREGNANCY_DURATION
        self.reproduction_cooldown = self.REPRODUCTION_COOLDOWN
        self.mate_genome = None
        self._asexual_pregnancy = True
        # Store overflow energy (if any) so it can fuel the baby later.
        self.stored_overflow_energy = max(0.0, overflow_energy)

    def consume_stored_overflow_energy(self, amount: float) -> float:
        """Use stored overflow energy, returning how much was consumed."""

        usable_amount = min(max(amount, 0.0), self.stored_overflow_energy)
        self.stored_overflow_energy -= usable_amount
        return usable_amount

    def clear_stored_overflow_energy(self) -> float:
        """Drain and return any leftover overflow energy reserve."""

        leftover = self.stored_overflow_energy
        self.stored_overflow_energy = 0.0
        return leftover

    def update_state(self) -> bool:
        """Update reproduction state (cooldown and pregnancy timer).

        Returns:
            bool: True if birth should occur this frame
        """
        # Update cooldown
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1

        # Update pregnancy
        if self.is_pregnant:
            self.pregnancy_timer -= 1

            if self.pregnancy_timer <= 0:
                # Time to give birth!
                self.is_pregnant = False
                return True

        return False

    def give_birth(
        self, own_genome: "Genome", population_stress: float = 0.0
    ) -> Tuple["Genome", float]:
        """Generate offspring genome from mating.

        Args:
            own_genome: This fish's genome
            population_stress: Environmental stress factor (0.0-1.0)

        Returns:
            Tuple of (Genome, energy_for_baby): The offspring's genome and energy to transfer
        """
        from core.genetics import Genome

        if self._asexual_pregnancy:
            offspring_genome = Genome.clone_with_mutation(
                own_genome, population_stress=population_stress
            )
        elif self.mate_genome is not None:
            offspring_genome = Genome.from_parents(
                own_genome, self.mate_genome, population_stress=population_stress
            )
        else:
            # Fallback: random genome if no mate stored
            offspring_genome = Genome.random()

        # Clear mate genome after birth
        self.mate_genome = None
        self._asexual_pregnancy = False

        # Calculate energy to transfer to baby (as a fraction, to be calculated by caller)
        # The caller will compute: energy_to_transfer = parent.energy * ENERGY_TRANSFER_TO_BABY
        return offspring_genome, self.ENERGY_TRANSFER_TO_BABY

    def reset_pregnancy(self) -> None:
        """Reset pregnancy state (e.g., due to starvation or death)."""
        self.is_pregnant = False
        self.pregnancy_timer = 0
        self.stored_overflow_energy = 0.0
        self.mate_genome = None

    def get_reproduction_state(self) -> str:
        """Get a human-readable description of reproduction state.

        Returns:
            str: Description of reproduction state
        """
        if self.is_pregnant:
            seconds_until_birth = self.pregnancy_timer / 30.0  # Assuming 30 FPS
            return f"Pregnant ({seconds_until_birth:.1f}s until birth)"
        elif self.reproduction_cooldown > 0:
            seconds_until_ready = self.reproduction_cooldown / 30.0
            return f"Cooldown ({seconds_until_ready:.1f}s until ready)"
        else:
            return "Ready to reproduce"
