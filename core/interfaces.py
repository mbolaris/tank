"""Canonical protocol definitions for the Tank World simulation.

This is the **single source of truth** for all protocol interfaces in the
simulation. Protocols are organized into two categories:

Entity Capability Protocols (structural subtyping for entity features):
    EnergyHolder, Positionable, Movable, Mortal, Reproducible,
    Consumable, Predator, Identifiable, LifecycleAware, Evolvable,
    PokerPlayer, SkillGamePlayer, SkillfulAgent

System Protocols (contracts for simulation subsystems):
    BehaviorStrategy, SimulationStats, EntityManager, FoodSpawner,
    CollisionHandler, PokerCoordinator, TraitContainer, TelemetrySink,
    MigrationHandler, MigrationCapable

Design Philosophy
-----------------
Protocols follow the **Interface Segregation Principle**: each protocol
represents ONE capability. Entities implement only the protocols they need.

    Fish: EnergyHolder + Positionable + Movable + Mortal + Identifiable + ...
    Plant: EnergyHolder + Positionable + Mortal
    Food: Positionable + Consumable

Protocol Composition:
    PokerPlayer = EnergyHolder + Positionable + poker-specific methods

Why Protocols over ABC?
    - Structural subtyping: no explicit inheritance required
    - Duck typing support: third-party classes satisfy protocols automatically
    - Better testability: lightweight mocks satisfy protocols without boilerplate

Runtime Checking:
    Protocols marked with @runtime_checkable can be used with isinstance():

        if isinstance(entity, EnergyHolder):
            entity.modify_energy(-10.0)

Usage
-----
Import protocols for type hints:
    from core.interfaces import EnergyHolder, Movable, Mortal

Use isinstance() checks with @runtime_checkable protocols:
    if isinstance(entity, EnergyHolder):
        entity.modify_energy(-10.0)
"""

from typing import (TYPE_CHECKING, Any, List, Optional, Protocol, Tuple,
                    runtime_checkable)

# Explicit public API for this module
__all__ = [
    # Entity capability protocols
    "EnergyHolder",
    "Positionable",
    "Movable",
    "Mortal",
    "Consumable",
    "Predator",
    "Identifiable",
    "LifecycleAware",
    "Evolvable",
    "Reproducible",
    "PokerPlayer",
    "SkillGamePlayer",
    "SkillfulAgent",
    "TraitContainer",
    # System protocols
    "BehaviorStrategy",
    "SimulationStats",
    "EntityManager",
    "FoodSpawner",
    "CollisionHandler",
    "PokerCoordinator",
    "MigrationHandler",
    "MigrationCapable",
    "TelemetrySink",
]

if TYPE_CHECKING:
    import random as pyrandom

    from core.ecosystem_stats import (MixedPokerOutcomeRecord,
                                      PlantPokerOutcomeRecord,
                                      PokerOutcomeRecord)
    from core.entities import Agent
    from core.entities.base import EntityState, LifeStage
    from core.fish.skill_game_component import SkillGameComponent
    from core.genetics import Genome
    from core.math_utils import Vector2
    from core.poker.core import PokerHand
    from core.skills.base import SkillGameResult, SkillGameType, SkillStrategy
    from core.telemetry.events import TelemetryEvent


@runtime_checkable
class TraitContainer(Protocol):
    """Any object that holds genetic traits.

    This protocol enables generic code to work with any trait container
    (PhysicalTraits, BehavioralTraits, or future trait categories).

    Both PhysicalTraits and BehavioralTraits implement this pattern,
    allowing functions to accept either type while maintaining type safety.

    Example:
        def inherit_all_traits(
            parent1: TraitContainer,
            parent2: TraitContainer,
            rng: random.Random
        ) -> TraitContainer:
            return type(parent1).from_parents(parent1, parent2, rng=rng)
    """

    @classmethod
    def random(cls, rng: "pyrandom.Random") -> "TraitContainer":
        """Generate random traits."""
        ...

    @classmethod
    def from_parents(
        cls,
        parent1: "TraitContainer",
        parent2: "TraitContainer",
        *,
        weight1: float = 0.5,
        mutation_rate: float = 0.1,
        mutation_strength: float = 0.1,
        rng: "pyrandom.Random",
    ) -> "TraitContainer":
        """Inherit traits from two parents with mutation."""
        ...


@runtime_checkable
class TelemetrySink(Protocol):
    """Sink for telemetry events emitted by domain entities."""

    def record_event(self, event: "TelemetryEvent") -> None:
        """Record a telemetry event."""
        ...


@runtime_checkable
class EnergyHolder(Protocol):
    """Any entity that holds and manages energy.

    This is the fundamental resource protocol. Energy is the "currency"
    of the simulation - entities need it to survive, move, reproduce,
    and participate in games.

    Design Note:
        Energy modification uses modify_energy() rather than direct
        property assignment to allow implementations to:
        - Clamp values to valid ranges
        - Emit events on energy changes
        - Track energy flow for statistics
    """

    @property
    def energy(self) -> float:
        """Current energy level (always >= 0)."""
        ...

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity (energy is clamped to this)."""
        ...

    def modify_energy(self, amount: float, *, source: str = "unknown") -> float:
        """Add or remove energy (positive = gain, negative = loss).

        The implementation should clamp the result to [0, max_energy].

        Returns:
            The actual delta applied to the entity's energy store.
        """
        ...


@runtime_checkable
class Positionable(Protocol):
    """Any entity with a position in 2D space."""

    @property
    def pos(self) -> Any:
        """Position vector with x and y attributes."""
        ...

    @property
    def width(self) -> float:
        """Entity width."""
        ...

    @property
    def height(self) -> float:
        """Entity height."""
        ...


@runtime_checkable
class Movable(Protocol):
    """Any entity that can move with velocity.

    Enables movement and collision systems to work with any moving entity
    without needing to know the specific type (Fish, Food, Crab, etc.).
    """

    @property
    def vel(self) -> "Vector2":
        """Current velocity vector (pixels per frame)."""
        ...

    @vel.setter
    def vel(self, value: "Vector2") -> None:
        """Set the velocity vector."""
        ...

    @property
    def speed(self) -> float:
        """Base movement speed (pixels per frame)."""
        ...

    def update_position(self) -> None:
        """Update position based on current velocity."""
        ...


@runtime_checkable
class Consumable(Protocol):
    """Any entity that can be consumed by other entities (Food, PlantNectar)."""

    def is_consumed(self) -> bool:
        """Check if this entity has been consumed."""
        ...

    def is_fully_consumed(self) -> bool:
        """Check if this entity is completely consumed (no bites remaining)."""
        ...

    def get_eaten(self) -> None:
        """Mark this entity as eaten, triggering cleanup/state changes."""
        ...


@runtime_checkable
class Predator(Protocol):
    """Any entity that can hunt and consume other entities (Crab, etc.)."""

    @property
    def is_predator(self) -> bool:
        """Whether this entity is a predator."""
        ...

    def can_hunt(self) -> bool:
        """Whether this predator can currently hunt (considering cooldowns, etc.)."""
        ...

    def eat_fish(self, fish: "EnergyHolder") -> None:
        """Consume a fish, transferring its energy."""
        ...


@runtime_checkable
class Identifiable(Protocol):
    """Any entity with a unique identifier for tracking and lineage."""

    def get_entity_id(self) -> Optional[int]:
        """Get the unique identifier for this entity, or None if unassigned."""
        ...


@runtime_checkable
class LifecycleAware(Protocol):
    """Any entity aware of its lifecycle stage (baby, adult, elder)."""

    @property
    def life_stage(self) -> "LifeStage":
        """Current life stage (BABY, ADULT, ELDER, etc.)."""
        ...


@runtime_checkable
class SkillGamePlayer(Protocol):
    """Any entity that can participate in skill games (poker).

    Distinct from SkillfulAgent: this protocol checks for the component-based
    skill game interface, while SkillfulAgent checks for the strategy-based
    interface.
    """

    @property
    def skill_game_component(self) -> "SkillGameComponent":
        """Access to skill game state and logic."""
        ...


@runtime_checkable
class PokerPlayer(EnergyHolder, Positionable, Protocol):
    """Any entity that can participate in poker games.

    This protocol is a composition of EnergyHolder and Positionable,
    as poker players need both to manage bets and proximity.

    Implementations must provide poker-specific attributes and methods
    for aggression, strategy, identification, and cooldown management.
    """

    @property
    def species(self) -> str:
        """Species identifier for same-species reproduction checks."""
        ...

    @property
    def poker_cooldown(self) -> int:
        """Frames until entity can play poker again."""
        ...

    @poker_cooldown.setter
    def poker_cooldown(self, value: int) -> None:
        """Set poker cooldown."""
        ...

    def get_poker_aggression(self) -> float:
        """Get aggression level for poker decisions (0.0-1.0)."""
        ...

    def get_poker_strategy(self) -> Optional[Any]:
        """Get poker strategy algorithm, or None to use aggression-based play."""
        ...

    def get_poker_id(self) -> int:
        """Get stable ID for poker (fish_id or plant_id + offset)."""
        ...


@runtime_checkable
class BehaviorStrategy(Protocol):
    """Contract for behavior algorithm implementation.

    This is the **Strategy Pattern** applied to fish behavior. Each fish
    has a behavior algorithm (strategy) that determines how it moves and
    makes decisions. There are 48+ different behavior algorithms in the
    simulation, each with unique characteristics.

    Design Philosophy:
        - Behaviors are **stateless**: they make decisions based only on
          the current world state and the fish's properties
        - Behaviors are **evolvable**: parameters can mutate during reproduction
        - Behaviors are **composable**: complex behaviors can delegate to simpler ones

    The execute() method returns a direction vector, not a position. This
    allows the fish's movement system to apply speed, energy costs, and
    collision detection uniformly across all behaviors.

    Example Implementation:
        class SeekFoodBehavior:
            def execute(self, fish: Fish) -> Tuple[float, float]:
                nearest_food = fish.environment.nearest_food(fish.pos)
                if nearest_food:
                    return (nearest_food.pos - fish.pos).normalized()
                return (0.0, 0.0)

            def mutate_parameters(self, strength: float = 0.1) -> None:
                pass  # No evolvable parameters
    """

    def execute(self, fish: Any) -> Tuple[float, float]:
        """Execute the behavior and return movement direction.

        Args:
            fish: The fish entity executing this behavior

        Returns:
            Tuple of (direction_x, direction_y) - should be normalized
        """
        ...

    def mutate_parameters(self, strength: float = 0.1) -> None:
        """Apply genetic mutation to the behavior parameters.

        Called during reproduction to evolve behavior parameters.

        Args:
            strength: Mutation strength (0.0-1.0), higher = larger changes
        """
        ...


@runtime_checkable
class SimulationStats(Protocol):
    """Interface for simulation statistics collection.

    Design Philosophy:
        Statistics collection is decoupled from simulation logic via this protocol.
        Implementations can record stats to memory, files, databases, or remote
        services without changing the simulation code.

    Thread Safety:
        Implementations should be thread-safe if used in multi-threaded simulations.

    Extensibility:
        New stats methods can be added by extending this protocol. Use Parameter
        Objects (dataclasses) for methods with many parameters.
    """

    def record_death(
        self,
        fish_id: int,
        generation: int,
        age: int,
        cause: str,
        genome: "Genome",
        algorithm_id: Optional[int] = None,
        remaining_energy: float = 0.0,
    ) -> None:
        """Record a fish death event.

        Args:
            fish_id: Unique identifier of the deceased fish
            generation: Generation number of the fish
            age: Age in frames at time of death
            cause: Death cause ('starvation', 'old_age', 'predation', etc.)
            genome: The fish's genetic information for trait analysis
            algorithm_id: Behavior algorithm ID for performance tracking
            remaining_energy: Energy remaining at death (for debugging)
        """
        ...

    def record_reproduction(self, algorithm_id: int, is_asexual: bool = True) -> None:
        """Record a reproduction event.

        Args:
            algorithm_id: Behavior algorithm ID of the parent
            is_asexual: True for asexual reproduction, False for sexual
        """
        ...

    def record_poker_outcome(
        self,
        winner_id: int,
        loser_id: int,
        winner_algo_id: Optional[int],
        loser_algo_id: Optional[int],
        amount: float,
        winner_hand: Optional["PokerHand"],
        loser_hand: Optional["PokerHand"],
        house_cut: float,
        result: Any,
        player1_algo_id: Optional[int],
        player2_algo_id: Optional[int],
    ) -> None:
        """Record a poker game outcome.

        Note:
            This method has many parameters. For new code,
            consider using PokerOutcomeRecord from ecosystem_stats.py to group
            these parameters into a single object:

                from core.ecosystem_stats import PokerOutcomeRecord
                record = PokerOutcomeRecord(winner_id=1, loser_id=2, amount=10.0)
                # Then pass record fields to this method

        Args:
            winner_id: Fish ID of winner (-1 for ties)
            loser_id: Fish ID of loser
            winner_algo_id: Winner's behavior algorithm ID
            loser_algo_id: Loser's behavior algorithm ID
            amount: Energy transferred from loser to winner
            winner_hand: Winner's poker hand (for hand rank stats)
            loser_hand: Loser's poker hand
            house_cut: Energy removed by house (game fee)
            result: Full PokerResult object for detailed stats
            player1_algo_id: Algorithm ID of player 1 (for position tracking)
            player2_algo_id: Algorithm ID of player 2 (for position tracking)
        """
        ...

    def record_poker_outcome_record(self, record: "PokerOutcomeRecord") -> None:
        """Record a poker outcome using a value object."""
        ...

    def record_plant_poker_game_record(self, record: "PlantPokerOutcomeRecord") -> None:
        """Record a plant poker outcome using a value object."""
        ...

    def record_mixed_poker_outcome_record(self, record: "MixedPokerOutcomeRecord") -> None:
        """Record a mixed poker outcome using a value object."""
        ...


@runtime_checkable
class EntityManager(Protocol):
    """Interface for managing entities in the simulation."""

    def add_entity(self, entity: "Agent") -> None:
        """Add an entity to the simulation."""
        ...

    def remove_entity(self, entity: "Agent") -> None:
        """Remove an entity from the simulation."""
        ...

    def get_all_entities(self) -> List["Agent"]:
        """Get all entities in the simulation."""
        ...


@runtime_checkable
class FoodSpawner(Protocol):
    """Interface for food spawning systems."""

    def spawn(self) -> Optional["Agent"]:
        """
        Spawn food if conditions are met.

        Returns:
            New food entity if spawned, None otherwise
        """
        ...

    def update(self) -> List["Agent"]:
        """
        Update spawner state and return any new food entities.

        Returns:
            List of newly spawned food entities
        """
        ...


@runtime_checkable
class CollisionHandler(Protocol):
    """Interface for collision detection and handling."""

    def check_collision(self, e1: "Agent", e2: "Agent") -> bool:
        """Check if two entities collide."""
        ...

    def handle_collisions(self) -> None:
        """Process all collisions for the current frame."""
        ...


@runtime_checkable
class PokerCoordinator(Protocol):
    """Interface for poker game coordination."""

    def find_poker_groups(self) -> List[List[Any]]:
        """Find groups of entities eligible for poker games."""
        ...

    def play_game(self, players: List[Any]) -> Optional[Any]:
        """
        Play a poker game between the given players.

        Args:
            players: List of poker-eligible entities

        Returns:
            PokerResult if game was played, None otherwise
        """
        ...


class Evolvable(Protocol):
    """Any entity with an evolvable genome."""

    @property
    def genome(self) -> "Genome":
        """The entity's genetic information."""
        ...

    @property
    def generation(self) -> int:
        """The generation number of this entity."""
        ...


@runtime_checkable
class Mortal(Protocol):
    """Any entity that can die and has a lifecycle state.

    Enables systems to check entity liveness without coupling to
    concrete entity types (Fish, Plant, etc.).
    """

    @property
    def state(self) -> "EntityState":
        """Current lifecycle state (ACTIVE, DEAD, REMOVED, etc.)."""
        ...

    def is_dead(self) -> bool:
        """Check if this entity is dead or removed."""
        ...


class Reproducible(Protocol):
    """Any entity that can reproduce.

    Note: Reproduction is now instant (no pregnancy timer). Offspring are
    created immediately when conditions are met.
    """

    def can_reproduce(self) -> bool:
        """Check if the entity can currently reproduce."""
        ...

    def try_mate(self, partner: Any) -> bool:
        """Attempt to mate with a partner.

        Returns:
            True if mating was successful
        """
        ...

    @property
    def reproduction_cooldown(self) -> int:
        """Frames until entity can reproduce again."""
        ...


@runtime_checkable
class SkillfulAgent(Protocol):
    """Any agent that can participate in skill games.

    This Protocol defines the contract for agents that can play skill games
    (poker, rock-paper-scissors, etc.). It separates the skill game system
    from the core entity system, allowing any agent type to participate.

    Design Philosophy:
    - Skill games are optional capabilities, not core to being an Agent
    - Agents can have multiple strategies (one per game type)
    - Learning happens both within lifetime and across generations
    - Strategies are stored/inherited through the genome
    """

    def get_strategy(self, game_type: "SkillGameType") -> Optional["SkillStrategy"]:
        """Get the agent's strategy for a specific skill game.

        Args:
            game_type: The type of skill game

        Returns:
            The agent's strategy for that game, or None if not available
        """
        ...

    def set_strategy(self, game_type: "SkillGameType", strategy: "SkillStrategy") -> None:
        """Set the agent's strategy for a specific skill game.

        Args:
            game_type: The type of skill game
            strategy: The strategy to use for that game
        """
        ...

    def learn_from_game(self, game_type: "SkillGameType", result: "SkillGameResult") -> None:
        """Update strategy based on game outcome.

        This is how agents learn within their lifetime. The strategy
        should be updated based on the result (win/loss/tie).

        Args:
            game_type: The type of skill game that was played
            result: The outcome of the game
        """
        ...

    @property
    def can_play_skill_games(self) -> bool:
        """Whether this agent is currently able to play skill games.

        Returns:
            True if agent has sufficient energy, isn't on cooldown, etc.
        """
        ...


@runtime_checkable
class MigrationHandler(Protocol):
    """Handles entity migration between connected tanks.

    This protocol abstracts the migration system, allowing entities to
    migrate without depending on backend implementation details.

    Design Note:
        Using a Protocol instead of getattr() provides:
        - Type safety and IDE support
        - Clear documentation of the interface
        - Easier testing (mock implementations)
        - Explicit dependency injection

    Example:
        # In entity code:
        if isinstance(self.environment, MigrationCapable):
            handler = self.environment.migration_handler
            if handler is not None:
                handler.attempt_entity_migration(self, "left", world_id)
    """

    def attempt_entity_migration(
        self,
        entity: Any,
        direction: str,
        source_world_id: str,
    ) -> bool:
        """Attempt to migrate an entity to a connected world.

        Args:
            entity: The entity attempting to migrate
            direction: "left" or "right" - which boundary was hit
            source_world_id: ID of the world the entity is leaving

        Returns:
            True if migration successful, False otherwise
        """
        ...


@runtime_checkable
class MigrationCapable(Protocol):
    """An environment that supports entity migration.

    Environments implementing this protocol can have entities migrate
    to connected tanks when they hit boundaries.
    """

    @property
    def migration_handler(self) -> Optional[MigrationHandler]:
        """Get the migration handler if available."""
        ...

    @property
    def world_id(self) -> Optional[str]:
        """Get the world identifier for migration tracking."""
        ...
