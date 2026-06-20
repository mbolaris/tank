"""Composable base class for ALife entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.entities.base import Agent, EntityUpdateResult

if TYPE_CHECKING:
    from core.agents.components.lifecycle_component import LifecycleComponent
    from core.agents.components.reproduction_component import ReproductionComponent
    from core.world import World


@dataclass
class AgentComponents:
    """Components a GenericAgent delegates core state to.

    Each field is the single owner of one concern. Subclasses supply the
    components they need via ``GenericAgent._create_components`` (or by
    passing an instance to the constructor); unset concerns stay ``None``.

    Energy is intentionally absent here: ``GenericAgent`` exposes lifecycle
    and reproduction accessors, but an agent's energy *policy* (overflow
    routing, metabolism, death-on-depletion) is owned by the subclass.
    ``Fish`` supplies it via ``EnergyManagementMixin`` over its own
    ``EnergyComponent``. See ADR-013.
    """

    lifecycle: LifecycleComponent | None = None
    reproduction: ReproductionComponent | None = None


class GenericAgent(Agent, ABC):
    """Abstract base for agents composed from reusable components.

    ``GenericAgent`` owns only the *shared* plumbing: stable identity and
    read accessors over the lifecycle / reproduction components in
    :class:`AgentComponents`. It deliberately does **not** prescribe a
    behavior loop or an energy/mortality policy - subclasses implement
    :meth:`update` and own how they sense, move, burn energy, and die
    (e.g. ``Fish`` uses its ``memory_system`` + ``BehaviorExecutor`` for
    behavior and the energy/mortality/reproduction mixins for state policy).

    It is abstract - :meth:`update` is required - and inherits ``ABC`` so
    that is enforced at instantiation rather than being decorative. See
    ADR-009 and ADR-013.
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

        # Death cache shared with subclass mortality logic (e.g. Fish's
        # MortalityMixin reads/sets this on the hot path).
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
    def reproduction_component(self):
        """Access to reproduction mechanics.

        Returns None if no reproduction component is present.
        """
        return self._components.reproduction

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
