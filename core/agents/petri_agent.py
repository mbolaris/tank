"""Petri dish microbe agent using the GenericAgent abstraction.

This module implements a simple microbe agent for Petri dish mode,
demonstrating proper use of the GenericAgent composition pattern.

The PetriMicrobeAgent serves as a reference implementation showing how to:
1. Extend GenericAgent with appropriate components
2. Implement the sense-think-act loop
3. Add species-specific behavior while reusing core infrastructure
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.agents.components import FeedingComponent, LocomotionComponent, PerceptionComponent
from core.energy.energy_component import EnergyComponent
from core.entities.base import EntityUpdateResult
from core.entities.generic_agent import Action, AgentComponents, GenericAgent, Percept
from core.fish_memory import FishMemorySystem

if TYPE_CHECKING:
    from core.world import World


# Default configuration for microbes
MICROBE_MAX_ENERGY = 100.0
MICROBE_BASE_METABOLISM = 0.05
MICROBE_INITIAL_ENERGY_RATIO = 0.5
MICROBE_MEMORY_MAX = 50
MICROBE_MEMORY_DECAY = 0.02
MICROBE_MEMORY_LEARNING = 0.2
MICROBE_BITE_MULTIPLIER = 10.0


class PetriMicrobeAgent(GenericAgent):
    """Simple microbe agent for Petri dish mode.

    This agent demonstrates the GenericAgent composition pattern with a
    minimal viable configuration:
    - Energy system for metabolism
    - Perception for food/danger memory
    - Locomotion for movement mechanics
    - Feeding for food consumption

    Unlike Fish, microbes have:
    - No lifecycle stages (constant size)
    - No reproduction
    - No poker/skill games
    - Simpler metabolism (constant burn rate)

    Protocol Compliance:
    -------------------
    Through GenericAgent's component composition, PetriMicrobeAgent satisfies:
    - EnergyHolder: Has energy component
    - Mortal: Can die from energy depletion
    - Movable: Inherited from Agent base

    Example:
        microbe = PetriMicrobeAgent(
            environment=world,
            x=100,
            y=200,
            speed=2.0,
            microbe_id=1,
        )
    """

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        speed: float,
        microbe_id: int | None = None,
    ) -> None:
        """Initialize a petri microbe agent.

        Args:
            environment: The world the microbe lives in
            x: Initial x position
            y: Initial y position
            speed: Base movement speed
            microbe_id: Unique identifier (0 if not specified)
        """
        # Create memory system for perception
        self._memory_system = FishMemorySystem(
            max_memories_per_type=MICROBE_MEMORY_MAX,
            decay_rate=MICROBE_MEMORY_DECAY,
            learning_rate=MICROBE_MEMORY_LEARNING,
        )

        # Create components for this microbe
        components = AgentComponents(
            energy=EnergyComponent(
                max_energy=MICROBE_MAX_ENERGY,
                base_metabolism=MICROBE_BASE_METABOLISM,
                initial_energy_ratio=MICROBE_INITIAL_ENERGY_RATIO,
            ),
            perception=PerceptionComponent(self._memory_system),
            locomotion=LocomotionComponent(),
            feeding=FeedingComponent(bite_size_multiplier=MICROBE_BITE_MULTIPLIER),
            # No lifecycle component (microbes don't age)
            # No reproduction component (microbes don't reproduce)
        )

        super().__init__(
            environment=environment,
            x=x,
            y=y,
            speed=speed,
            components=components,
            agent_id=microbe_id,
        )

        # Microbe-specific state
        self.microbe_id = microbe_id if microbe_id is not None else 0
        self._frame_count: int = 0  # Track frames for update frequency

    @property
    def memory_system(self) -> FishMemorySystem:
        """Access the underlying memory system."""
        return self._memory_system

    # =========================================================================
    # Backwards-Compatible Component Access
    # =========================================================================
    # These properties provide backwards compatibility for code that
    # accesses components directly via _perception, _locomotion, _feeding.

    @property
    def _perception(self) -> PerceptionComponent | None:
        """Backwards-compatible access to perception component."""
        return self._components.perception

    @property
    def _locomotion(self) -> LocomotionComponent | None:
        """Backwards-compatible access to locomotion component."""
        return self._components.locomotion

    @property
    def _feeding(self) -> FeedingComponent | None:
        """Backwards-compatible access to feeding component."""
        return self._components.feeding

    # =========================================================================
    # Sense-Think-Act Implementation
    # =========================================================================

    def perceive(self, time_of_day: float | None = None) -> Percept:
        """Collect sensory inputs for the microbe.

        Microbes have simpler perception than fish - primarily food
        location memory without danger awareness.

        Args:
            time_of_day: Normalized time of day (unused for microbes)

        Returns:
            Percept with current sensory data
        """
        # Get base percept from GenericAgent
        percept = super().perceive(time_of_day)

        # Microbes could add custom perception here
        # For now, base perception is sufficient

        return percept

    def decide(self, percept: Percept) -> Action:
        """Decide on an action based on perception.

        Microbes use simple stimulus-response behavior:
        - If low energy and know food locations, move toward nearest
        - Otherwise, continue current movement

        Args:
            percept: Current sensory data

        Returns:
            Action to execute
        """
        # If a decision policy is set, use it
        if self._decision_policy is not None:
            return self._decision_policy.decide(percept, self)

        # Default behavior: simple food seeking when hungry
        action = Action()

        # If we're hungry and remember food locations, move toward nearest
        if percept.energy < percept.max_energy * 0.5 and percept.nearby_food:
            # Find nearest food
            nearest = min(
                percept.nearby_food,
                key=lambda f: (f.x - percept.position.x) ** 2 + (f.y - percept.position.y) ** 2,
            )

            # Calculate direction to food
            from core.math_utils import Vector2

            direction = Vector2(
                nearest.x - percept.position.x,
                nearest.y - percept.position.y,
            )

            if direction.length_squared() > 0:
                direction = direction.normalize() * self.speed
                action.movement = direction

        return action

    def act(self, action: Action) -> None:
        """Execute the decided action.

        Args:
            action: Action to execute
        """
        # Use base implementation for standard actions
        super().act(action)

    # =========================================================================
    # Update Implementation
    # =========================================================================

    def update(
        self,
        frame_count: int,
        time_modifier: float = 1.0,
        time_of_day: float | None = None,
    ) -> EntityUpdateResult:
        """Update the microbe state for one frame.

        Implements the sense-think-act loop:
        1. Perceive the environment
        2. Decide on an action
        3. Act on the decision
        4. Update lifecycle components

        Args:
            frame_count: Current frame number
            time_modifier: Time scaling factor
            time_of_day: Normalized time of day (unused for microbes)

        Returns:
            EntityUpdateResult (empty for microbes - no spawning)
        """
        self._frame_count = frame_count

        # Early exit if dead
        if self.is_dead():
            self.vel.x = 0
            self.vel.y = 0
            return EntityUpdateResult()

        # Sense-Think-Act loop
        percept = self.perceive(time_of_day)
        action = self.decide(percept)
        self.act(action)

        # Common update logic (position, energy burn, perception update)
        return self._update_common(frame_count, time_modifier, time_of_day)

    def _calculate_energy_burn(self, time_modifier: float) -> float:
        """Calculate energy burn for this frame.

        Microbes have simple constant metabolism.

        Args:
            time_modifier: Time scaling factor

        Returns:
            Amount of energy to burn
        """
        if self._components.energy is None:
            return 0.0

        return self._components.energy.base_metabolism * time_modifier

    # =========================================================================
    # Eating (Override for custom behavior)
    # =========================================================================

    def eat(self, food: Any) -> None:
        """Consume food and gain energy.

        Uses the feeding component for proper bite calculations.

        Args:
            food: The food entity to consume
        """
        # Use base implementation which handles feeding component
        self._execute_eat(food)
