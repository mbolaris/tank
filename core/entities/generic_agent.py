"""Composable base class for ALife entities."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.entities.base import Agent, EntityState, EntityUpdateResult

if TYPE_CHECKING:
    from core.agents.components.lifecycle_component import LifecycleComponent
    from core.agents.components.reproduction_component import ReproductionComponent
    from core.energy.energy_component import EnergyComponent
    from core.world import World


@dataclass
class AgentComponents:
    """Components a GenericAgent delegates core state to.

    Each field is the single owner of one concern. Subclasses supply the
    components they need via ``GenericAgent._create_components`` (or by
    passing an instance to the constructor); unset concerns stay ``None``.
    """

    energy: EnergyComponent | None = None
    lifecycle: LifecycleComponent | None = None
    reproduction: ReproductionComponent | None = None


class GenericAgent(Agent):
    """Base class for agents composed from reusable components.

    ``GenericAgent`` owns the shared plumbing every agent needs - identity and
    the energy / lifecycle / reproduction wiring - and delegates each concern
    to a component in :class:`AgentComponents`. It deliberately does **not**
    prescribe a behavior loop: subclasses implement :meth:`update` and own how
    they sense and move (e.g. ``Fish`` uses its ``memory_system`` and
    ``BehaviorExecutor``). See ADR-009.
    """

    def __init__(
        self,
        environment: World,
        x: float,
        y: float,
        speed: float,
        components: AgentComponents | None = None,
        agent_id: int | None = None,
    ) -> None:
        """Initialize a generic agent.

        Args:
            environment: The world the agent lives in
            x: Initial x position
            y: Initial y position
            speed: Base movement speed
            components: Component configuration (uses _create_components if None)
            agent_id: Unique identifier (0 if not specified)
        """
        super().__init__(environment, x, y, speed)

        # Agent identity
        self._agent_id: int = agent_id if agent_id is not None else 0

        # Initialize components (subclasses can override _create_components)
        self._components = components if components is not None else self._create_components()

        # Cache for is_dead optimization
        self._cached_is_dead: bool = False

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
    def snapshot_type(self) -> str:
        """Return entity type for snapshot serialization.

        Default implementation uses lowercase class name.
        Subclasses can override for custom type strings.
        """
        return self.__class__.__name__.lower()

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

    @abstractmethod
    def update(
        self, frame_count: int, time_modifier: float = 1.0, time_of_day: float | None = None
    ) -> EntityUpdateResult:
        """Update the agent state for one frame.

        Subclasses must implement this to define their specific update
        behavior (sensing, movement, lifecycle, energy, reproduction).

        Args:
            frame_count: Current frame number
            time_modifier: Time scaling factor
            time_of_day: Normalized time of day (0.0-1.0)

        Returns:
            EntityUpdateResult with any spawned entities or events
        """
        ...
