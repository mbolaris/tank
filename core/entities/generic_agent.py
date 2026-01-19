"""Composable base class for ALife entities."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from core.entities.base import Agent, EntityState, EntityUpdateResult
from core.entities.generic_agent_types import Action, AgentComponents, DecisionPolicy, Percept
from core.math_utils import Vector2

if TYPE_CHECKING:
    from core.agents.components import FeedingComponent, LocomotionComponent, PerceptionComponent
    from core.world import World


class GenericAgent(Agent):
    """Base class for agents composed from reusable components."""

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        speed: float,
        components: AgentComponents | None = None,
        decision_policy: DecisionPolicy | None = None,
        agent_id: int | None = None,
    ) -> None:
        """Initialize a generic agent.

        Args:
            environment: The world the agent lives in
            x: Initial x position
            y: Initial y position
            speed: Base movement speed
            components: Component configuration (uses _create_components if None)
            decision_policy: Policy for deciding actions (uses default if None)
            agent_id: Unique identifier (0 if not specified)
        """
        super().__init__(environment, x, y, speed)

        # Agent identity
        self._agent_id: int = agent_id if agent_id is not None else 0

        # Initialize components (subclasses can override _create_components)
        self._components = components if components is not None else self._create_components()

        # Decision policy (can be swapped at runtime)
        self._decision_policy = decision_policy

        # Cache for is_dead optimization
        self._cached_is_dead: bool = False

        # Initialize direction tracking if locomotion component exists
        if self._components.locomotion is not None:
            self._components.locomotion.update_direction(self.vel)

    def _create_components(self) -> AgentComponents:
        """Create default components for this agent type.

        Subclasses should override this to supply appropriate components.
        The default implementation returns empty components.

        Returns:
            AgentComponents with appropriate components for this agent type
        """
        return AgentComponents()

    def get_entity_id(self) -> int | None:
        """Get the unique identifier for this agent.

        Returns:
            Agent ID, or None if not assigned
        """
        return self._agent_id if self._agent_id != 0 else None

    @property
    def energy(self) -> float:
        """Current energy level.

        Returns 0.0 if no energy component is present.
        """
        if self._components.energy is not None:
            return self._components.energy.energy
        return 0.0

    @energy.setter
    def energy(self, value: float) -> None:
        """Set energy level."""
        if self._components.energy is not None:
            self._components.energy.energy = value
            # Update death cache if energy depleted
            if value <= 0:
                self._cached_is_dead = True

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity.

        Returns 0.0 if no energy component is present.
        """
        if self._components.energy is not None:
            return self._components.energy.max_energy
        return 0.0

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Modify energy by the given amount.

        Args:
            amount: Energy delta (positive for gain, negative for loss)
            source: Source of energy change for tracking

        Returns:
            Actual energy change applied
        """
        if self._components.energy is None:
            return 0.0

        old_energy = self._components.energy.energy
        new_energy = max(0.0, old_energy + amount)

        # Clamp to max
        if new_energy > self.max_energy:
            new_energy = self.max_energy

        self._components.energy.energy = new_energy

        # Update death cache
        if new_energy <= 0:
            self._cached_is_dead = True
        elif self.state.state == EntityState.ACTIVE:
            self._cached_is_dead = False

        return new_energy - old_energy

    @property
    def life_stage(self):
        """Current life stage.

        Returns None if no lifecycle component is present.
        """
        if self._components.lifecycle is not None:
            return self._components.lifecycle.life_stage
        return None

    @property
    def age(self) -> int:
        """Current age in frames.

        Returns 0 if no lifecycle component is present.
        """
        if self._components.lifecycle is not None:
            return self._components.lifecycle.age
        return 0

    @property
    def size(self) -> float:
        """Current size multiplier.

        Combines lifecycle stage and genetics if available.
        Returns 1.0 if no lifecycle component is present.
        """
        if self._components.lifecycle is not None:
            return self._components.lifecycle.size
        return 1.0

    def is_dead(self) -> bool:
        """Check if this agent is dead.

        Uses cached value when possible for performance.
        """
        if self._cached_is_dead:
            return True

        # Check state machine
        if self.state.state in (EntityState.DEAD, EntityState.REMOVED):
            self._cached_is_dead = True
            return True

        # Check energy depletion
        if self._components.energy is not None and self._components.energy.energy <= 0:
            self.state.transition(EntityState.DEAD, reason="starvation")
            self._cached_is_dead = True
            return True

        # Check old age
        if self._components.lifecycle is not None:
            lc = self._components.lifecycle
            if lc.age >= lc.max_age:
                self.state.transition(EntityState.DEAD, reason="old_age")
                self._cached_is_dead = True
                return True

        return False

    @property
    def reproduction_component(self):
        """Access to reproduction mechanics.

        Returns None if no reproduction component is present.
        """
        return self._components.reproduction

    def can_reproduce(self) -> bool:
        """Check if this agent can reproduce.

        Returns False if no reproduction component is present.
        """
        if self._components.reproduction is None:
            return False
        if self._components.lifecycle is None:
            return False

        return self._components.reproduction.can_reproduce(
            self._components.lifecycle.life_stage,
            self.energy,
            self.max_energy,
        )

    @property
    def components(self) -> AgentComponents:
        """Access to all components."""
        return self._components

    @property
    def perception(self) -> PerceptionComponent | None:
        """Access to perception component."""
        return self._components.perception

    @property
    def locomotion(self) -> LocomotionComponent | None:
        """Access to locomotion component."""
        return self._components.locomotion

    @property
    def feeding(self) -> FeedingComponent | None:
        """Access to feeding component."""
        return self._components.feeding

    @property
    def decision_policy(self) -> DecisionPolicy | None:
        """Get the current decision policy."""
        return self._decision_policy

    @decision_policy.setter
    def decision_policy(self, policy: DecisionPolicy | None) -> None:
        """Set the decision policy."""
        self._decision_policy = policy

    def perceive(self, time_of_day: float | None = None) -> Percept:
        """Collect sensory inputs into a Percept.

        This method gathers all available sensory information into a
        single Percept object for decision-making.

        Subclasses can override to add species-specific perception.

        Args:
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            Percept containing all sensory data
        """
        nearby_food: list[Vector2] = []
        nearby_danger: list[Vector2] = []

        # Query perception component if available
        if self._components.perception is not None:
            nearby_food = self._components.perception.get_food_locations()
            nearby_danger = self._components.perception.get_danger_zones()

        return Percept(
            position=Vector2(self.pos.x, self.pos.y),
            velocity=Vector2(self.vel.x, self.vel.y),
            energy=self.energy,
            max_energy=self.max_energy,
            age=self.age,
            size=self.size,
            nearby_food=nearby_food,
            nearby_danger=nearby_danger,
            time_of_day=time_of_day,
        )

    def decide(self, percept: Percept) -> Action:
        """Decide on an action based on perception.

        If a decision policy is set, delegates to it. Otherwise,
        returns a default action (no movement change).

        Subclasses can override for species-specific decision logic.

        Args:
            percept: Current sensory data

        Returns:
            Action to execute
        """
        if self._decision_policy is not None:
            return self._decision_policy.decide(percept, self)

        # Default: no action
        return Action()

    def act(self, action: Action) -> None:
        """Execute an action.

        Applies the action's effects:
        - Movement changes
        - Eating
        - Interaction with other entities

        Subclasses can override for species-specific actions.

        Args:
            action: Action to execute
        """
        # Apply movement if specified
        if action.movement is not None:
            self.vel = action.movement

        # Handle eating if specified
        if action.eat_target is not None:
            self._execute_eat(action.eat_target)

    def _execute_eat(self, food: Any) -> None:
        """Execute eating action.

        Subclasses can override for species-specific eating behavior.

        Args:
            food: Food entity to consume
        """
        if self._components.feeding is None:
            return

        if not self._components.feeding.can_eat(self.energy, self.max_energy):
            return

        bite_size = self._components.feeding.calculate_effective_bite(
            self.size, self.energy, self.max_energy
        )
        gained = self._components.feeding.consume_food(food, bite_size)
        self.modify_energy(gained, source="ate_food")

        # Record in memory
        if self._components.perception is not None:
            self._components.perception.record_food_discovery(food.pos)

    @abstractmethod
    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: float | None = None
    ) -> EntityUpdateResult:
        """Update the agent state for one frame.

        This method orchestrates the sense-think-act loop and updates
        all lifecycle components. Subclasses must implement this to
        define their specific update behavior.

        Args:
            frame_count: Current frame number
            time_modifier: Time scaling factor
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            EntityUpdateResult with any spawned entities or events
        """
        ...

    def _update_common(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: float | None = None
    ) -> EntityUpdateResult:
        """Common update logic for all agent types.

        Subclasses should call this from their update() implementation
        to handle standard lifecycle operations.

        Args:
            frame_count: Current frame number
            time_modifier: Time scaling factor
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            EntityUpdateResult (empty unless death occurred)
        """
        # Update position from Agent base
        self.update_position()

        # Age increment
        if self._components.lifecycle is not None:
            self._components.lifecycle.increment_age()

        # Memory/perception update (every 10 frames for performance)
        if self._components.perception is not None:
            if self.age % 10 == 0:
                self._components.perception.update(self.age)

        # Energy metabolism
        if self._components.energy is not None:
            burn = self._calculate_energy_burn(time_modifier)
            self.modify_energy(-burn, source="metabolism")

        # Direction tracking for turn costs
        if self._components.locomotion is not None:
            self._components.locomotion.update_direction(self.vel)

        # Check for death
        if self.is_dead():
            # Stop movement for dying agent
            self.vel = Vector2(0, 0)

        return EntityUpdateResult()

    def _calculate_energy_burn(self, time_modifier: float) -> float:
        """Calculate energy burn for this frame.

        Subclasses can override for species-specific metabolism.

        Args:
            time_modifier: Time scaling factor

        Returns:
            Amount of energy to burn
        """
        if self._components.energy is None:
            return 0.0

        # Default: simple constant burn rate
        base_burn = self._components.energy.base_metabolism
        return base_burn * time_modifier

    def eat(self, food: Any) -> None:
        """Consume food and gain energy.

        This is the public API for eating, used by collision systems.

        Args:
            food: The food entity to consume
        """
        self._execute_eat(food)

    def get_remembered_food_locations(self) -> list[Vector2]:
        """Get list of remembered food locations.

        Returns empty list if no perception component.
        """
        if self._components.perception is not None:
            return self._components.perception.get_food_locations()
        return []
