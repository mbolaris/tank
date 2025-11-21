"""Environment module for spatial queries and agent management.

This module provides the Environment class which manages spatial queries
for agents in the simulation.
"""

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type

from core.entities import Agent


class SpatialGrid:
    """
    Spatial partitioning grid for efficient proximity queries.

    Divides the environment into a grid of cells. Each cell contains agents
    that are located within that cell's bounds. This allows O(1) lookup of
    which cells to check for proximity queries, drastically reducing the
    number of distance calculations needed.
    """

    def __init__(self, width: int, height: int, cell_size: int = 150):
        """
        Initialize the spatial grid.

        Args:
            width: Width of the environment in pixels
            height: Height of the environment in pixels
            cell_size: Size of each grid cell in pixels (default 150)
        """
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.cols = math.ceil(width / cell_size)
        self.rows = math.ceil(height / cell_size)

        # Grid storage: dict of (col, row) -> set of agents
        self.grid: Dict[Tuple[int, int], Set[Agent]] = defaultdict(set)

        # Agent to cell mapping for quick updates
        self.agent_cells: Dict[Agent, Tuple[int, int]] = {}

    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get the grid cell coordinates for a position."""
        col = max(0, min(self.cols - 1, int(x / self.cell_size)))
        row = max(0, min(self.rows - 1, int(y / self.cell_size)))
        return (col, row)

    def add_agent(self, agent: Agent):
        """Add an agent to the spatial grid."""
        if not hasattr(agent, "pos"):
            return

        cell = self._get_cell(agent.pos.x, agent.pos.y)
        self.grid[cell].add(agent)
        self.agent_cells[agent] = cell

    def remove_agent(self, agent: Agent):
        """Remove an agent from the spatial grid."""
        if agent in self.agent_cells:
            cell = self.agent_cells[agent]
            self.grid[cell].discard(agent)
            del self.agent_cells[agent]

    def update_agent(self, agent: Agent):
        """Update an agent's position in the grid (call when agent moves)."""
        if not hasattr(agent, "pos"):
            return

        new_cell = self._get_cell(agent.pos.x, agent.pos.y)
        old_cell = self.agent_cells.get(agent)

        # Only update if the agent changed cells
        if old_cell != new_cell:
            if old_cell is not None:
                self.grid[old_cell].discard(agent)
            self.grid[new_cell].add(agent)
            self.agent_cells[agent] = new_cell

    def get_cells_in_radius(self, x: float, y: float, radius: float) -> List[Tuple[int, int]]:
        """Get all grid cells that intersect with a circular radius."""
        # Calculate the range of cells to check
        min_col = max(0, int((x - radius) / self.cell_size))
        max_col = min(self.cols - 1, int((x + radius) / self.cell_size))
        min_row = max(0, int((y - radius) / self.cell_size))
        max_row = min(self.rows - 1, int((y + radius) / self.cell_size))

        # Pre-allocate list size if possible or just use list comprehension which is faster than append loop
        return [
            (col, row)
            for col in range(min_col, max_col + 1)
            for row in range(min_row, max_row + 1)
        ]

    def query_radius(self, agent: Agent, radius: float) -> List[Agent]:
        """
        Get all agents within a radius of the given agent.

        This is much faster than checking all agents, as it only checks
        agents in nearby grid cells.
        """
        if not hasattr(agent, "pos"):
            return []

        # Local variable access is faster
        agent_pos_x = agent.pos.x
        agent_pos_y = agent.pos.y
        radius_sq = radius * radius
        
        # Calculate cell range directly
        cell_size = self.cell_size
        min_col = max(0, int((agent_pos_x - radius) / cell_size))
        max_col = min(self.cols - 1, int((agent_pos_x + radius) / cell_size))
        min_row = max(0, int((agent_pos_y - radius) / cell_size))
        max_row = min(self.rows - 1, int((agent_pos_y + radius) / cell_size))

        # Collect candidates using fast C-implemented extend
        candidates = []
        grid = self.grid
        
        # Iterate ranges directly to avoid creating intermediate list of cells
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                # Direct access to defaultdict is faster than checking 'in'
                # accessing missing key creates empty set, extend handles empty set efficiently
                candidates.extend(grid[(col, row)])
        
        # Filter using list comprehension (faster than explicit for loop)
        # and optimized math (multiplication instead of exponentiation)
        return [
            other
            for other in candidates
            if other is not agent
            and (other.pos.x - agent_pos_x) * (other.pos.x - agent_pos_x) + 
                (other.pos.y - agent_pos_y) * (other.pos.y - agent_pos_y) <= radius_sq
        ]

    def clear(self):
        """Clear all agents from the grid."""
        self.grid.clear()
        self.agent_cells.clear()

    def rebuild(self, agents: Iterable[Agent]):
        """Rebuild the entire grid from scratch."""
        self.clear()
        for agent in agents:
            self.add_agent(agent)


class Environment:
    """
    The environment in which the agents operate.
    This class provides methods to interact with and query the state of the environment.
    """

    def __init__(
        self, agents: Optional[Iterable[Agent]] = None, width: int = 800, height: int = 600, time_system: Optional[Any] = None
    ):
        """
        Initialize the environment.

        Args:
            agents (Iterable[Agent], optional): A collection of agents. Defaults to None.
            width (int): Width of the environment in pixels. Defaults to 800.
            height (int): Height of the environment in pixels. Defaults to 600.
            time_system (TimeSystem, optional): Time system for day/night cycle effects
        """
        self.agents = agents
        self.width = width
        self.height = height
        self.time_system = time_system
        
        # Performance: Cache detection range modifier (updated once per frame)
        self._cached_detection_modifier: float = 1.0

        # Initialize spatial grid for fast proximity queries
        self.spatial_grid = SpatialGrid(width, height, cell_size=150)

        # Build initial spatial grid if agents are provided
        if agents:
            self.spatial_grid.rebuild(agents)

        # Query cache to avoid redundant searches within the same frame
        # Cache is cleared when rebuild_spatial_grid() is called
        self._query_cache: Dict[Tuple, List[Agent]] = {}
        self._type_cache: Dict[Type[Agent], List[Agent]] = {}

        # NEW: Initialize communication system for fish
        from core.fish_communication import FishCommunicationSystem

        self.communication_system = FishCommunicationSystem(max_signals=50, decay_rate=0.05)
    
    def update_detection_modifier(self) -> None:
        """Update cached detection range modifier from time system.
        
        Should be called once per frame to avoid repeated time_system calls.
        """
        if self.time_system is not None:
            self._cached_detection_modifier = self.time_system.get_detection_range_modifier()
        else:
            self._cached_detection_modifier = 1.0
    
    def get_detection_modifier(self) -> float:
        """Get cached detection range modifier.
        
        Returns:
            Float multiplier for detection range (0.25-1.0)
        """
        return self._cached_detection_modifier

    def rebuild_spatial_grid(self):
        """Rebuild the spatial grid from scratch. Call when agents are added/removed."""
        if self.agents:
            self.spatial_grid.rebuild(self.agents)
        # Clear query caches when grid is rebuilt
        self._query_cache.clear()
        # Note: Type cache is NOT cleared here - it's only cleared on entity add/remove

    def invalidate_type_cache(self):
        """Invalidate the type cache when entities are added or removed."""
        self._type_cache.clear()

    def add_agent_to_grid(self, agent: Agent):
        """Add a new agent to the spatial grid and invalidate caches."""
        self.spatial_grid.add_agent(agent)
        self.invalidate_type_cache()

    def remove_agent_from_grid(self, agent: Agent):
        """Remove an agent from the spatial grid and invalidate caches."""
        self.spatial_grid.remove_agent(agent)
        self.invalidate_type_cache()

    def update_agent_position(self, agent: Agent):
        """Update an agent's position in the spatial grid. Call when agent moves."""
        self.spatial_grid.update_agent(agent)

    def nearby_agents(self, agent: Agent, radius: int) -> List[Agent]:
        """
        Return a list of agents within a certain radius of the given agent.

        Uses spatial grid partitioning for O(k) performance instead of O(n),
        where k is the number of agents in nearby cells.

        Args:
            agent (Agent): The agent to consider.
            radius (int): The radius to consider.

        Returns:
            List[Agent]: The agents within the radius.
        """
        # Use spatial grid for fast lookup
        return self.spatial_grid.query_radius(agent, radius)

    def get_agents_of_type(self, agent_class: Type[Agent]) -> List[Agent]:
        """
        Get all agents of the given class.

        Uses caching to avoid re-filtering on repeated calls within the same frame.

        Args:
            agent_class (Type[Agent]): The class of the agents to consider.

        Returns:
            List[Agent]: The agents of the given class.
        """
        # Check cache first
        if agent_class in self._type_cache:
            return self._type_cache[agent_class]

        # Compute and cache result
        result = [agent for agent in self.agents if isinstance(agent, agent_class)]
        self._type_cache[agent_class] = result
        return result

    def nearby_agents_by_type(
        self, agent: Agent, radius: int, agent_class: Type[Agent]
    ) -> List[Agent]:
        """
        Return a list of agents of a given type within a certain radius of the given agent.

        Uses spatial grid partitioning for O(k) performance instead of O(n),
        where k is the number of agents in nearby cells.

        Args:
            agent (Agent): The agent to consider.
            radius (int): The radius to consider.
            agent_class (Type[Agent]): The class of the agents to find.

        Returns:
            List[Agent]: The agents of the specified type within the radius.
        """
        # Use spatial grid for fast lookup, then filter by type
        nearby = self.spatial_grid.query_radius(agent, radius)
        return [other for other in nearby if isinstance(other, agent_class)]

    # Convenient entity filtering helpers for improved code clarity
    def get_all_fish(self) -> List[Agent]:
        """Get all fish agents in the environment.

        Returns:
            List[Agent]: All fish in the environment
        """
        from core.entities import Fish

        return [agent for agent in self.agents if isinstance(agent, Fish)]

    def get_all_food(self) -> List[Agent]:
        """Get all food entities in the environment.

        Returns:
            List[Agent]: All food items in the environment
        """
        from core.entities import Food

        return [agent for agent in self.agents if isinstance(agent, Food)]

    def get_all_plants(self) -> List[Agent]:
        """Get all plant entities in the environment.

        Returns:
            List[Agent]: All plants in the environment
        """
        from core.entities import Plant

        return [agent for agent in self.agents if isinstance(agent, Plant)]

    def get_all_crabs(self) -> List[Agent]:
        """Get all crab (predator) entities in the environment.

        Returns:
            List[Agent]: All crabs in the environment
        """
        from core.entities import Crab

        return [agent for agent in self.agents if isinstance(agent, Crab)]

    def count_fish(self) -> int:
        """Count the number of fish in the environment.

        Returns:
            int: Number of fish
        """
        return len(self.get_all_fish())

    def count_food(self) -> int:
        """Count the number of food items in the environment.

        Returns:
            int: Number of food items
        """
        return len(self.get_all_food())

    def count_entities_by_type(self, agent_class: Type[Agent]) -> int:
        """Count entities of a specific type in the environment.

        Args:
            agent_class: The class of entities to count

        Returns:
            int: Number of entities of the specified type
        """
        return len(self.get_agents_of_type(agent_class))
