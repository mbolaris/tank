"""Abstract World interface for environment-agnostic simulation code.

This module defines the World Protocol - an abstract interface that any
simulation environment must implement. This allows core simulation logic
to work with different environment types (2D tank, 3D aquarium, graph-based
habitat, etc.) without coupling to specific implementation details.

Design Philosophy:
- World is about SPATIAL QUERIES and BOUNDARIES
- It doesn't care about rendering, physics details, or domain specifics
- Implementations can be 2D, 3D, graph-based, or anything else
- Core simulation code depends on World, not concrete implementations

Example Usage:
    # Core simulation code can work with any World implementation
    def find_nearby_targets(agent: Agent, world: World, radius: float):
        return world.nearby_agents(agent, radius)

    # Works with 2D tank
    tank_env = Environment(width=800, height=600)
    targets = find_nearby_targets(my_fish, tank_env, 100.0)

    # Would also work with 3D aquarium (future)
    aquarium = Aquarium3D(width=800, height=600, depth=400)
    targets = find_nearby_targets(my_fish, aquarium, 100.0)
"""

import random
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from core.entities.base import Agent


@runtime_checkable
class World(Protocol):
    """Abstract interface for simulation environments.

    This Protocol defines what any simulation environment must provide
    for core simulation logic to work. Implementations can use any
    spatial representation (2D grid, 3D octree, graph, etc.).

    The World abstraction focuses on:
    1. Spatial queries (finding nearby entities)
    2. Boundary checking (valid positions)
    3. Environment properties (bounds, dimensions)

    It explicitly does NOT define:
    - Rendering/visualization details
    - Physics simulation specifics
    - Domain-specific concepts (water, temperature, etc.)
    """

    # --- Spatial Queries ---

    def nearby_agents(self, agent: "Agent", radius: float) -> list["Agent"]:
        """Find all agents within a radius of the given agent.

        This is the most fundamental spatial query. Implementations should
        optimize this heavily as it's called frequently.

        Args:
            agent: The agent to search around
            radius: Search radius (units depend on implementation)

        Returns:
            List of agents within radius (may include agent itself)
        """
        ...

    def nearby_agents_by_type(
        self, agent: "Agent", radius: float, agent_type: type["Agent"]
    ) -> list["Agent"]:
        """Find agents of a specific type within radius.

        Optimized query for type-specific searches (e.g., find nearby food).

        Args:
            agent: The agent to search around
            radius: Search radius
            agent_type: Type of agents to find (e.g., Food, Fish)

        Returns:
            List of agents of the specified type within radius
        """
        ...

    def nearby_evolving_agents(self, agent: "Agent", radius: float) -> list["Agent"]:
        """Find evolving agents (entities that can reproduce) within radius.

        This is a generic query for primary simulation entities.
        In the fish tank domain, this returns Fish.

        Args:
            agent: The agent to search around
            radius: Search radius

        Returns:
            List of evolving agents within radius
        """
        ...

    def nearby_resources(self, agent: "Agent", radius: float) -> list["Agent"]:
        """Find consumable resources within radius.

        This is a generic query for resource entities.
        In the fish tank domain, this returns Food.

        Args:
            agent: The agent to search around
            radius: Search radius

        Returns:
            List of resource agents within radius
        """
        ...

    def update_agent_position(self, agent: "Agent") -> None:
        """Update an agent's position in any spatial index.

        Implementations that maintain a spatial grid should update the agent's
        cell membership here. Worlds without a spatial index may implement this
        as a no-op.
        """
        ...

    def get_agents_of_type(self, agent_type: type["Agent"]) -> list["Agent"]:
        """Get all agents of a specific type in the environment.

        This is a global query (not spatial). Use for iteration over
        all entities of a type when spatial filtering isn't needed.

        Args:
            agent_type: Type of agents to retrieve

        Returns:
            List of all agents of the specified type
        """
        ...

    def list_policy_component_ids(self, kind: str) -> list[str]:
        """List available policy component IDs for a given kind.

        This is used by reproduction/mutation code to discover policy components
        (e.g., movement policies) that can be assigned to offspring.
        """
        ...

    # --- Boundary/Position Validation ---

    def get_bounds(self) -> tuple[Any, Any]:
        """Get the environment's boundaries.

        Return type is intentionally flexible to support different
        coordinate systems:
        - 2D: ((min_x, min_y), (max_x, max_y))
        - 3D: ((min_x, min_y, min_z), (max_x, max_y, max_z))
        - Graph: (node_set, edge_set)

        Returns:
            Environment-specific boundary representation
        """
        ...

    def is_valid_position(self, position: Any) -> bool:
        """Check if a position is valid within this environment.

        Args:
            position: Position to check (type depends on implementation)

        Returns:
            True if position is within valid bounds
        """
        ...

    # --- Environment Properties ---

    @property
    def dimensions(self) -> tuple[float, ...]:
        """Get environment dimensions.

        Returns:
            Tuple of dimensions (e.g., (width, height) for 2D,
            (width, height, depth) for 3D)
        """
        ...

    @property
    def rng(self) -> random.Random:
        """The shared random number generator for this world.

        All simulation code should use this RNG for deterministic behavior.
        When a simulation is seeded, this RNG will be seeded accordingly,
        ensuring reproducible results across runs.

        Returns:
            The Random instance used for all stochastic decisions in this world
        """
        ...


@runtime_checkable
class World2D(World, Protocol):
    """Specialized World interface for 2D environments.

    Extends World with 2D-specific conveniences. This is optional -
    code that only needs World can work with any implementation.
    """

    @property
    def width(self) -> float:
        """Width of the 2D environment."""
        ...

    @property
    def height(self) -> float:
        """Height of the 2D environment."""
        ...

    def get_2d_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get 2D boundaries as ((min_x, min_y), (max_x, max_y))."""
        ...


# Helpers for world inspection
def is_2d_world(world: World) -> bool:
    """Check if a World implementation is 2D.

    Args:
        world: World instance to check

    Returns:
        True if world implements World2D interface
    """
    return isinstance(world, World2D)


def get_2d_dimensions(world: World) -> tuple[float, float]:
    """Get dimensions as (width, height) for 2D worlds.

    Args:
        world: World instance (should be 2D)

    Returns:
        (width, height) tuple

    Raises:
        ValueError: If world is not 2D
    """
    if not is_2d_world(world):
        raise ValueError("World is not 2D - cannot get 2D dimensions")

    dims = world.dimensions
    if len(dims) != 2:
        raise ValueError(f"Expected 2 dimensions, got {len(dims)}")

    return (dims[0], dims[1])
