"""Protocol-based abstractions for simulation entities.

This module defines structural protocols that entities can satisfy without
explicit inheritance. Protocols enable:
- Loose coupling between systems and entities
- Easy addition of new entity types
- Better testability with mock objects
- Clear contracts for entity capabilities

Design Philosophy:
-----------------
Instead of checking `isinstance(entity, Fish)`, systems should check for
capabilities using protocols: `isinstance(entity, EnergyHolder)`.

This allows new entity types to work with existing systems automatically
if they provide the required capabilities.

Example:
    # ❌ Bad - tightly couples system to Fish type
    if isinstance(agent, Fish):
        agent.energy -= 10

    # ✅ Good - works with any entity that has energy
    if isinstance(agent, EnergyHolder):
        agent.modify_energy(-10)

Protocol Hierarchy:
------------------
    EnergyHolder - Has energy that can be modified
    Mortal - Can die and has lifecycle state
    Reproducible - Can reproduce (has reproduction component)
    Movable - Can move with velocity
    Consumable - Can be consumed by other entities
    Predator - Can hunt and eat other entities
    SkillGamePlayer - Can participate in skill games (poker)
    Identifiable - Has a unique ID for tracking

See Also:
    - core/entities/base.py: Base entity classes (Entity, Agent)
    - core/energy/energy_component.py: EnergyComponent implementation
    - core/fish/reproduction_component.py: ReproductionComponent implementation
"""

from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.entities.base import EntityState, LifeStage
    from core.fish.reproduction_component import ReproductionComponent
    from core.fish.skill_game_component import SkillGameComponent
    from core.math_utils import Vector2


@runtime_checkable
class EnergyHolder(Protocol):
    """Protocol for entities that have energy.

    Entities that implement this protocol can:
    - Store and track energy levels
    - Modify energy (gain/lose energy)
    - Have a maximum energy capacity

    This enables systems to work with any energy-having entity
    without needing to know if it's a Fish, Plant, Crab, etc.

    Examples:
        Fish - has energy from EnergyComponent
        Plant - has energy for growth and nectar production
        Crab - has energy from hunting

    Design Note:
        The modify_energy() method is preferred over direct energy assignment
        as it allows entities to implement validation, logging, or side effects.
    """

    @property
    def energy(self) -> float:
        """Current energy level.

        Returns:
            Current energy as a float. May be negative in edge cases.
        """
        ...

    @energy.setter
    def energy(self, value: float) -> None:
        """Set the energy level directly.

        Args:
            value: New energy level

        Note:
            Prefer modify_energy() for most use cases as it may include
            validation and side effects.
        """
        ...

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity.

        Returns:
            Maximum energy this entity can store.
        """
        ...

    def modify_energy(self, amount: float) -> None:
        """Modify energy by the given amount.

        This is the preferred way to change energy as it allows
        entities to implement validation, bounds checking, or
        trigger side effects (e.g., death on starvation).

        Args:
            amount: Energy delta (positive for gain, negative for loss)
        """
        ...


@runtime_checkable
class Mortal(Protocol):
    """Protocol for entities that can die.

    Entities implementing this protocol have a lifecycle state
    and can transition between states (alive -> dead).

    This enables systems to:
    - Check if entities are dead before processing them
    - Trigger death events and cleanup
    - Track lifecycle states for debugging

    Examples:
        Fish - can die from starvation, predation, old age
        Plant - can die from lack of energy
        Food - transitions to "consumed" state
    """

    @property
    def state(self) -> "EntityState":
        """Current lifecycle state.

        Returns:
            EntityState (ACTIVE, DEAD, REMOVED, etc.)
        """
        ...

    def is_dead(self) -> bool:
        """Check if this entity is dead or removed.

        Returns:
            True if entity should be excluded from processing.
        """
        ...


@runtime_checkable
class Reproducible(Protocol):
    """Protocol for entities that can reproduce.

    Entities implementing this protocol have reproduction capabilities
    including cooldowns, energy requirements, and offspring generation.

    This enables reproduction systems to work with any reproducible
    entity type without coupling to Fish-specific logic.

    Examples:
        Fish - reproduce through poker games or asexually
        Plant - reproduce through nectar consumption
    """

    @property
    def reproduction_component(self) -> "ReproductionComponent":
        """Access to reproduction mechanics.

        Returns:
            ReproductionComponent managing reproduction state.
        """
        ...


@runtime_checkable
class Movable(Protocol):
    """Protocol for entities that can move.

    Entities implementing this protocol have velocity and can
    change position over time.

    This enables movement and collision systems to work with
    any moving entity without needing to know the specific type.

    Examples:
        Fish - move with AI-driven behaviors
        Food - drift with currents
        Crab - patrol and hunt
    """

    @property
    def vel(self) -> "Vector2":
        """Current velocity vector.

        Returns:
            Vector2 representing velocity (pixels per frame).
        """
        ...

    @vel.setter
    def vel(self, value: "Vector2") -> None:
        """Set the velocity vector.

        Args:
            value: New velocity vector
        """
        ...

    @property
    def speed(self) -> float:
        """Base movement speed.

        Returns:
            Maximum speed in pixels per frame.
        """
        ...

    def update_position(self) -> None:
        """Update position based on current velocity.

        This should apply velocity to position and handle
        boundary conditions (screen edges, etc.).
        """
        ...


@runtime_checkable
class Consumable(Protocol):
    """Protocol for entities that can be consumed.

    Entities implementing this protocol can be eaten by other
    entities and track their consumption state.

    This enables collision systems to handle food consumption
    generically without type-specific checks.

    Examples:
        Food - consumed by fish and crabs
        PlantNectar - consumed by fish, triggers plant reproduction
    """

    def is_consumed(self) -> bool:
        """Check if this entity has been consumed.

        Returns:
            True if entity is fully consumed and should be removed.
        """
        ...

    def is_fully_consumed(self) -> bool:
        """Check if this entity is fully consumed.

        Some consumable entities may have multiple "bites" before
        being fully consumed.

        Returns:
            True if entity is completely consumed.
        """
        ...

    def get_eaten(self) -> None:
        """Mark this entity as eaten.

        This may trigger cleanup, events, or state changes.
        """
        ...


@runtime_checkable
class Predator(Protocol):
    """Protocol for entities that can hunt and eat other entities.

    Entities implementing this protocol have predator capabilities
    including hunt cooldowns and consumption logic.

    This enables predation systems to work with any predator type
    without coupling to Crab-specific logic.

    Examples:
        Crab - hunts fish and food
        (Future: Shark, larger fish, etc.)
    """

    @property
    def is_predator(self) -> bool:
        """Check if this is a predator.

        Returns:
            True if entity is a predator.
        """
        ...

    def can_hunt(self) -> bool:
        """Check if this predator can currently hunt.

        May consider cooldowns, energy, or other constraints.

        Returns:
            True if predator can hunt right now.
        """
        ...

    def eat_fish(self, fish: "EnergyHolder") -> None:
        """Consume a fish.

        Args:
            fish: The fish being eaten (requires energy to transfer)
        """
        ...


@runtime_checkable
class SkillGamePlayer(Protocol):
    """Protocol for entities that can play skill games (poker).

    Entities implementing this protocol can participate in
    poker games and other skill-based minigames.

    This enables poker systems to work with any player type
    (Fish, Plant, or future entity types).

    Examples:
        Fish - play poker with evolved strategies
        Plant - can be challenged by fish for energy
    """

    @property
    def skill_game_component(self) -> "SkillGameComponent":
        """Access to skill game state and logic.

        Returns:
            SkillGameComponent managing poker/skill game state.
        """
        ...


@runtime_checkable
class Identifiable(Protocol):
    """Protocol for entities with unique identifiers.

    Entities implementing this protocol have stable IDs that
    can be used for tracking, lineage, and deterministic sorting.

    This enables telemetry and analytics systems to track
    entities across their lifecycle.

    Examples:
        Fish - have fish_id for lineage tracking
        Plant - have plant_id for ecosystem analysis

    Design Note:
        The property name is generic to allow different entity
        types to use their own ID naming (fish_id, plant_id, etc.)
        Systems should use get_entity_id() when they need a stable ID.
    """

    def get_entity_id(self) -> Optional[int]:
        """Get the unique identifier for this entity.

        Returns:
            Unique integer ID, or None if not assigned yet.
        """
        ...


@runtime_checkable
class LifecycleAware(Protocol):
    """Protocol for entities aware of their lifecycle stage.

    Entities implementing this protocol know their current life
    stage (baby, adult, elder) which affects metabolism, behavior,
    and reproduction eligibility.

    This enables systems to apply life-stage-specific logic
    without coupling to specific entity types.

    Examples:
        Fish - transition through baby -> adult -> elder stages
        Plant - may have growth stages
    """

    @property
    def life_stage(self) -> "LifeStage":
        """Current life stage.

        Returns:
            LifeStage enum value (BABY, ADULT, ELDER, etc.)
        """
        ...


# Type aliases for common protocol combinations
#
# These represent common entity archetypes that combine multiple protocols.
# Use these when you need entities with multiple capabilities.
#
# Examples:
#     def handle_living_agent(agent: LivingAgent) -> None:
#         # Agent has energy, can move, and can die
#         agent.modify_energy(-1)
#         agent.update_position()
#         if agent.energy <= 0:
#             agent.is_dead()

# Note: Python's Protocol doesn't support union types directly,
# so these are documentation-only. Use individual protocol checks in code.
#
# LivingAgent = EnergyHolder & Movable & Mortal
# ReproducingAgent = LivingAgent & Reproducible
# PlayableAgent = LivingAgent & SkillGamePlayer & Identifiable
