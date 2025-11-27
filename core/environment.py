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

        # Grid storage: dict of (col, row) -> dict of type -> list of agents
        # Using list instead of set for faster iteration in tight loops
        self.grid: Dict[Tuple[int, int], Dict[Type[Agent], List[Agent]]] = defaultdict(lambda: defaultdict(list))
        
        # Dedicated grids for high-frequency types to avoid dictionary lookups and issubclass checks
        # These contain the SAME agent objects as self.grid, just indexed differently for speed
        self.fish_grid: Dict[Tuple[int, int], List[Agent]] = defaultdict(list)
        self.food_grid: Dict[Tuple[int, int], List[Agent]] = defaultdict(list)

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
        # Use type(agent) for exact type matching which is faster than isinstance checks later
        # But we need to be careful about inheritance if we query by base class
        # For now, we'll store by exact type
        agent_type = type(agent)
        self.grid[cell][agent_type].append(agent)
        
        # Update dedicated grids
        # We use string names to avoid circular imports or heavy isinstance checks
        type_name = agent_type.__name__
        if type_name == 'Fish':
            self.fish_grid[cell].append(agent)
        elif type_name == 'Food' or type_name == 'LiveFood':
            self.food_grid[cell].append(agent)
            
        self.agent_cells[agent] = cell

    def remove_agent(self, agent: Agent):
        """Remove an agent from the spatial grid."""
        if agent in self.agent_cells:
            cell = self.agent_cells[agent]
            agent_type = type(agent)
            if agent_type in self.grid[cell]:
                try:
                    self.grid[cell][agent_type].remove(agent)
                    # Clean up empty lists to keep iteration fast
                    if not self.grid[cell][agent_type]:
                        del self.grid[cell][agent_type]
                except ValueError:
                    pass  # Agent might not be in the list if something went wrong
            
            # Remove from dedicated grids
            type_name = agent_type.__name__
            if type_name == 'Fish':
                if agent in self.fish_grid[cell]:
                    self.fish_grid[cell].remove(agent)
                    if not self.fish_grid[cell]:
                        del self.fish_grid[cell]
            elif type_name == 'Food' or type_name == 'LiveFood':
                if agent in self.food_grid[cell]:
                    self.food_grid[cell].remove(agent)
                    if not self.food_grid[cell]:
                        del self.food_grid[cell]
                        
            del self.agent_cells[agent]

    def update_agent(self, agent: Agent):
        """Update an agent's position in the grid (call when agent moves)."""
        if not hasattr(agent, "pos"):
            return

        new_cell = self._get_cell(agent.pos.x, agent.pos.y)
        old_cell = self.agent_cells.get(agent)

        # Only update if the agent changed cells
        if old_cell != new_cell:
            agent_type = type(agent)
            # Remove from old cell
            if old_cell is not None:
                if agent_type in self.grid[old_cell]:
                    try:
                        self.grid[old_cell][agent_type].remove(agent)
                        if not self.grid[old_cell][agent_type]:
                            del self.grid[old_cell][agent_type]
                    except ValueError:
                        pass
                
                # Remove from dedicated grids (old cell)
                type_name = agent_type.__name__
                if type_name == 'Fish':
                    if agent in self.fish_grid[old_cell]:
                        self.fish_grid[old_cell].remove(agent)
                        if not self.fish_grid[old_cell]:
                            del self.fish_grid[old_cell]
                elif type_name == 'Food' or type_name == 'LiveFood':
                    if agent in self.food_grid[old_cell]:
                        self.food_grid[old_cell].remove(agent)
                        if not self.food_grid[old_cell]:
                            del self.food_grid[old_cell]
            
            # Add to new cell
            self.grid[new_cell][agent_type].append(agent)
            
            # Add to dedicated grids (new cell)
            type_name = agent_type.__name__
            if type_name == 'Fish':
                self.fish_grid[new_cell].append(agent)
            elif type_name == 'Food' or type_name == 'LiveFood':
                self.food_grid[new_cell].append(agent)
                
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

        # Collect candidates
        candidates = []
        grid = self.grid
        
        # Iterate ranges directly
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                # Get all type buckets in this cell
                cell_agents = grid.get((col, row))
                if cell_agents:
                    for type_list in cell_agents.values():
                        candidates.extend(type_list)
        
        # Filter using list comprehension
        return [
            other
            for other in candidates
            if other is not agent
            and (other.pos.x - agent_pos_x) * (other.pos.x - agent_pos_x) + 
                (other.pos.y - agent_pos_y) * (other.pos.y - agent_pos_y) <= radius_sq
        ]

    def query_fish(self, agent: Agent, radius: float) -> List[Agent]:
        """Optimized query for nearby fish."""
        if not hasattr(agent, "pos"):
            return []

        agent_x = agent.pos.x
        agent_y = agent.pos.y
        radius_sq = radius * radius
        
        cell_size = self.cell_size
        min_col = max(0, int((agent_x - radius) / cell_size))
        max_col = min(self.cols - 1, int((agent_x + radius) / cell_size))
        min_row = max(0, int((agent_y - radius) / cell_size))
        max_row = min(self.rows - 1, int((agent_y + radius) / cell_size))

        candidates = []
        fish_grid = self.fish_grid
        
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_fish = fish_grid.get((col, row))
                if cell_fish:
                    candidates.extend(cell_fish)
                    
        return [
            other
            for other in candidates
            if other is not agent
            and (other.pos.x - agent_x) * (other.pos.x - agent_x) + 
                (other.pos.y - agent_y) * (other.pos.y - agent_y) <= radius_sq
        ]

    def query_food(self, agent: Agent, radius: float) -> List[Agent]:
        """Optimized query for nearby food."""
        if not hasattr(agent, "pos"):
            return []

        agent_x = agent.pos.x
        agent_y = agent.pos.y
        radius_sq = radius * radius
        
        cell_size = self.cell_size
        min_col = max(0, int((agent_x - radius) / cell_size))
        max_col = min(self.cols - 1, int((agent_x + radius) / cell_size))
        min_row = max(0, int((agent_y - radius) / cell_size))
        max_row = min(self.rows - 1, int((agent_y + radius) / cell_size))

        candidates = []
        food_grid = self.food_grid
        
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_food = food_grid.get((col, row))
                if cell_food:
                    candidates.extend(cell_food)
                    
        return [
            other
            for other in candidates
            if other is not agent
            and (other.pos.x - agent_x) * (other.pos.x - agent_x) + 
                (other.pos.y - agent_y) * (other.pos.y - agent_y) <= radius_sq
        ]

    def query_interaction_candidates(self, agent: Agent, radius: float, crab_type: Type[Agent]) -> List[Agent]:
        """
        Optimized query for collision candidates (Fish, Food, Crabs).
        Performs a single grid traversal to collect all relevant entities.
        """
        if not hasattr(agent, "pos"):
            return []

        agent_x = agent.pos.x
        agent_y = agent.pos.y
        radius_sq = radius * radius
        
        cell_size = self.cell_size
        min_col = max(0, int((agent_x - radius) / cell_size))
        max_col = min(self.cols - 1, int((agent_x + radius) / cell_size))
        min_row = max(0, int((agent_y - radius) / cell_size))
        max_row = min(self.rows - 1, int((agent_y + radius) / cell_size))

        candidates = []
        fish_grid = self.fish_grid
        food_grid = self.food_grid
        grid = self.grid
        
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell = (col, row)
                
                # Check Fish
                cell_fish = fish_grid.get(cell)
                if cell_fish:
                    candidates.extend(cell_fish)
                            
                # Check Food
                cell_food = food_grid.get(cell)
                if cell_food:
                    candidates.extend(cell_food)
                            
                # Check Crabs
                cell_agents = grid.get(cell)
                if cell_agents and crab_type in cell_agents:
                    candidates.extend(cell_agents[crab_type])
                            
        return [
            other
            for other in candidates
            if other is not agent
            and (other.pos.x - agent_x) * (other.pos.x - agent_x) + 
                (other.pos.y - agent_y) * (other.pos.y - agent_y) <= radius_sq
        ]

    def clear(self):
        """Clear all agents from the grid."""
        self.grid.clear()
        self.fish_grid.clear()
        self.food_grid.clear()
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
        
        # Migration support (injected by backend)
        self.connection_manager = None  # Set by backend if migrations enabled
        self.tank_registry = None  # Set by backend if migrations enabled
        self.tank_id = None  # Set by backend if migrations enabled
        
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
        # Optimized implementation:
        # 1. Inline spatial grid logic to avoid function call overhead
        # 2. Iterate grid cells directly to avoid creating intermediate candidate list
        # 3. Use type buckets to only iterate relevant agents
        
        if not hasattr(agent, "pos"):
            return []

        # Local variables for speed
        grid = self.spatial_grid
        cell_size = grid.cell_size
        agent_x = agent.pos.x
        agent_y = agent.pos.y
        
        # Calculate cell range
        min_col = max(0, int((agent_x - radius) / cell_size))
        max_col = min(grid.cols - 1, int((agent_x + radius) / cell_size))
        min_row = max(0, int((agent_y - radius) / cell_size))
        max_row = min(grid.rows - 1, int((agent_y + radius) / cell_size))
        
        radius_sq = radius * radius
        result = []
        grid_dict = grid.grid
        
        # Iterate cells
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                # Get type buckets for this cell
                # Use get() to avoid creating empty entries in defaultdict
                cell_buckets = grid_dict.get((col, row))
                if not cell_buckets:
                    continue
                    
                # Iterate over type buckets
                for type_key, agents in cell_buckets.items():
                    # Check if this type is relevant (subclass check)
                    # This handles inheritance (e.g. asking for Fish gets all Fish subclasses)
                    if issubclass(type_key, agent_class):
                        for other in agents:
                            if other is agent:
                                continue
                                
                            # Distance check
                            dx = other.pos.x - agent_x
                            dy = other.pos.y - agent_y
                            if dx*dx + dy*dy <= radius_sq:
                                result.append(other)
                            
        return result

    def nearby_fish(self, agent: Agent, radius: int) -> List[Agent]:
        """
        Optimized method to get nearby fish.
        """
        return self.spatial_grid.query_fish(agent, radius)

    def nearby_food(self, agent: Agent, radius: int) -> List[Agent]:
        """
        Optimized method to get nearby food.
        """
        return self.spatial_grid.query_food(agent, radius)

    def nearby_interaction_candidates(self, agent: Agent, radius: int, crab_type: Type[Agent]) -> List[Agent]:
        """
        Optimized method to get nearby Fish, Food, and Crabs in a single pass.
        """
        return self.spatial_grid.query_interaction_candidates(agent, radius, crab_type)

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
