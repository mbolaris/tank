"""Protocol interfaces for type safety and better IDE support.

This module defines formal interfaces (Protocols) for the key abstractions
in the simulation. These provide:
- Better IDE autocomplete and type checking
- Documentation of expected interfaces
- Decoupling between components
"""

from typing import TYPE_CHECKING, Any, List, Optional, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:
    from core.entities import Agent
    from core.genetics import Genome
    from core.poker.core import PokerHand
    from core.skills.base import SkillGameResult, SkillGameType, SkillStrategy


@runtime_checkable
class EnergyHolder(Protocol):
    """Any entity that holds and manages energy."""

    @property
    def energy(self) -> float:
        """Current energy level."""
        ...

    @property
    def max_energy(self) -> float:
        """Maximum energy capacity."""
        ...

    def modify_energy(self, amount: float) -> None:
        """Add or remove energy (positive = gain, negative = loss)."""
        ...


@runtime_checkable
class PokerPlayer(Protocol):
    """Any entity that can participate in poker games."""

    @property
    def energy(self) -> float:
        """Current energy level."""
        ...

    def modify_energy(self, amount: float) -> None:
        """Modify the entity's energy."""
        ...

    @property
    def pos(self) -> Any:
        """Position vector with x and y attributes."""
        ...

    @property
    def width(self) -> float:
        """Entity width for collision/proximity detection."""
        ...

    @property
    def height(self) -> float:
        """Entity height for collision/proximity detection."""
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
class BehaviorStrategy(Protocol):
    """Contract for behavior algorithm implementation."""

    def execute(self, fish: Any) -> Tuple[float, float]:
        """
        Execute the behavior and return movement direction.

        Args:
            fish: The fish entity executing this behavior

        Returns:
            Tuple of (direction_x, direction_y) normalized direction vector
        """
        ...

    def mutate_parameters(self, strength: float = 0.1) -> None:
        """
        Apply genetic mutation to the behavior parameters.

        Args:
            strength: Mutation strength (0.0-1.0)
        """
        ...


class SimulationStats(Protocol):
    """Interface for simulation statistics collection."""

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
        """Record a fish death event."""
        ...

    def record_reproduction(self, algorithm_id: int, is_asexual: bool = True) -> None:
        """Record a reproduction event."""
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
        """Record a poker game outcome."""
        ...


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


class SpatialQuery(Protocol):
    """Interface for spatial queries in the environment."""

    def nearby_agents(self, entity: "Agent", radius: float) -> List["Agent"]:
        """Find agents within radius of entity."""
        ...

    def nearby_fish(self, entity: "Agent", radius: float) -> List[Any]:
        """Find fish within radius of entity."""
        ...

    def nearby_food(self, entity: "Agent", radius: float) -> List[Any]:
        """Find food within radius of entity."""
        ...


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


class CollisionHandler(Protocol):
    """Interface for collision detection and handling."""

    def check_collision(self, e1: "Agent", e2: "Agent") -> bool:
        """Check if two entities collide."""
        ...

    def handle_collisions(self) -> None:
        """Process all collisions for the current frame."""
        ...


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


class Mortal(Protocol):
    """Any entity that can die."""

    def is_dead(self) -> bool:
        """Check if the entity is dead."""
        ...

    def get_death_cause(self) -> str:
        """Get the cause of death."""
        ...


class Reproducible(Protocol):
    """Any entity that can reproduce."""

    def can_reproduce(self) -> bool:
        """Check if the entity can currently reproduce."""
        ...

    def try_mate(self, partner: Any) -> bool:
        """
        Attempt to mate with a partner.

        Args:
            partner: Potential mating partner

        Returns:
            True if mating was successful
        """
        ...

    @property
    def is_pregnant(self) -> bool:
        """Whether the entity is currently pregnant."""
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
