"""Reproduction management component for fish.

This module provides the ReproductionComponent class which handles all reproduction-related
functionality for fish, including mating, pregnancy, and offspring generation.
Separating reproduction logic into its own component improves code organization and testability.
"""

import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.genetics import Genome
    from core.entities import LifeStage


class ReproductionComponent:
    """Manages fish reproduction, pregnancy, and mating mechanics.

    This component encapsulates all reproduction-related logic for a fish, including:
    - Mate compatibility calculation
    - Pregnancy state management
    - Reproduction cooldown tracking
    - Offspring generation

    Attributes:
        is_pregnant: Whether the fish is currently pregnant
        pregnancy_timer: Frames remaining until birth
        reproduction_cooldown: Frames until can reproduce again
        mate_genome: Genome of the mate (stored for offspring generation)
    """

    # Reproduction constants
    REPRODUCTION_ENERGY_THRESHOLD = 25.0  # Minimum energy to reproduce (reduced for more breeding)
    REPRODUCTION_COOLDOWN = 240  # 8 seconds (reduced for better breeding)
    PREGNANCY_DURATION = 300  # 10 seconds
    MATING_DISTANCE = 60.0  # Maximum distance for mating
    REPRODUCTION_ENERGY_COST = 10.0  # Energy cost for initiating mating
    ENERGY_TRANSFER_TO_BABY = 0.30  # Parent transfers 30% of their current energy to baby
    MIN_ACCEPTANCE_THRESHOLD = 0.3  # Minimum chance to accept mate (30%)

    def __init__(self):
        """Initialize the reproduction component."""
        self.is_pregnant: bool = False
        self.pregnancy_timer: int = 0
        self.reproduction_cooldown: int = 0
        self.mate_genome: Optional["Genome"] = None

    def can_reproduce(self, life_stage: "LifeStage", energy: float) -> bool:
        """Check if fish can reproduce.

        Args:
            life_stage: Current life stage of the fish
            energy: Current energy level

        Returns:
            bool: True if fish can reproduce
        """
        from core.entities import LifeStage

        return (
            life_stage == LifeStage.ADULT
            and energy >= self.REPRODUCTION_ENERGY_THRESHOLD
            and self.reproduction_cooldown <= 0
            and not self.is_pregnant
        )

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
        # Check distance
        if distance > self.MATING_DISTANCE:
            return False

        # Calculate mate compatibility (sexual selection)
        total_compatibility = self.calculate_mate_compatibility(
            own_genome, mate_genome, own_energy, own_max_energy, mate_energy, mate_max_energy
        )

        # Mate selection: use compatibility as probability threshold
        # Higher compatibility = higher chance of accepting mate
        # Minimum threshold ensures population doesn't get stuck
        acceptance_threshold = max(self.MIN_ACCEPTANCE_THRESHOLD, total_compatibility)

        if random.random() > acceptance_threshold:
            # Mate rejected based on preferences
            return False

        # Success! Start pregnancy
        self.is_pregnant = True
        self.pregnancy_timer = self.PREGNANCY_DURATION
        self.mate_genome = mate_genome
        self.reproduction_cooldown = self.REPRODUCTION_COOLDOWN

        return True

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
    ) -> tuple["Genome", float]:
        """Generate offspring genome from mating.

        Args:
            own_genome: This fish's genome
            population_stress: Environmental stress factor (0.0-1.0)

        Returns:
            Tuple of (Genome, energy_for_baby): The offspring's genome and energy to transfer
        """
        from core.genetics import Genome

        if self.mate_genome is not None:
            offspring_genome = Genome.from_parents(
                own_genome, self.mate_genome, population_stress=population_stress
            )
        else:
            # Fallback: random genome if no mate stored
            offspring_genome = Genome.random()

        # Clear mate genome after birth
        self.mate_genome = None

        # Calculate energy to transfer to baby (as a fraction, to be calculated by caller)
        # The caller will compute: energy_to_transfer = parent.energy * ENERGY_TRANSFER_TO_BABY
        return offspring_genome, self.ENERGY_TRANSFER_TO_BABY

    def reset_pregnancy(self) -> None:
        """Reset pregnancy state (e.g., due to starvation or death)."""
        self.is_pregnant = False
        self.pregnancy_timer = 0
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
