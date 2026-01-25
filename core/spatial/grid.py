"""Spatial indexing for efficient proximity queries."""

import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Type

from core.entities import Agent, Food


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

        # Base type used to identify all food-like agents (covers subclasses
        # like LiveFood and PlantNectar without needing explicit name checks)
        self._food_base_type = Food

        # Grid storage: dict of (col, row) -> dict of type -> list of agents
        # Using list instead of set for faster iteration in tight loops
        self.grid: Dict[Tuple[int, int], Dict[Type[Agent], List[Agent]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Cache deterministic per-cell type order to avoid sorting on every query.
        # Key: cell tuple, Value: list of types sorted by __name__.
        self._cell_type_order: Dict[Tuple[int, int], List[Type[Agent]]] = {}

        # Dedicated grids for high-frequency types to avoid dictionary lookups and issubclass checks
        # These contain the SAME agent objects as self.grid, just indexed differently for speed
        self.fish_grid: Dict[Tuple[int, int], List[Agent]] = defaultdict(list)
        self.food_grid: Dict[Tuple[int, int], List[Agent]] = defaultdict(list)

        # Agent to cell mapping for quick updates
        self.agent_cells: Dict[Agent, Tuple[int, int]] = {}

    def _insert_type_order(self, cell: Tuple[int, int], agent_type: Type[Agent]) -> None:
        """Insert a type into the cached order list for a cell."""
        order = self._cell_type_order.get(cell)
        if order is None:
            self._cell_type_order[cell] = [agent_type]
            return

        type_name = agent_type.__name__
        # Insert into sorted position by name (small list; linear insert is fine).
        for index, existing in enumerate(order):
            if type_name < existing.__name__:
                order.insert(index, agent_type)
                return
        order.append(agent_type)

    def _remove_type_order(self, cell: Tuple[int, int], agent_type: Type[Agent]) -> None:
        """Remove a type from the cached order list for a cell if present."""
        order = self._cell_type_order.get(cell)
        if not order:
            return

        try:
            order.remove(agent_type)
        except ValueError:
            return

        if not order:
            del self._cell_type_order[cell]

    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get the grid cell coordinates for a position."""
        col = max(0, min(self.cols - 1, int(x / self.cell_size)))
        row = max(0, min(self.rows - 1, int(y / self.cell_size)))
        return (col, row)

    def _get_cell_range(self, x: float, y: float, radius: float) -> Tuple[int, int, int, int]:
        """Get the cell range for a radius query (reduces repeated min/max calls).

        Returns:
            Tuple of (min_col, max_col, min_row, max_row)
        """
        cs = self.cell_size
        cols_m1 = self.cols - 1
        rows_m1 = self.rows - 1
        min_col = max(0, int((x - radius) / cs))
        max_col = min(cols_m1, int((x + radius) / cs))
        min_row = max(0, int((y - radius) / cs))
        max_row = min(rows_m1, int((y + radius) / cs))
        return (min_col, max_col, min_row, max_row)

    def add_agent(self, agent: Agent):
        """Add an agent to the spatial grid."""
        if not hasattr(agent, "pos"):
            return

        cell = self._get_cell(agent.pos.x, agent.pos.y)
        # Use type(agent) for exact type matching which is faster than isinstance checks later
        # But we need to be careful about inheritance if we query by base class
        # For now, we'll store by exact type
        agent_type = type(agent)
        cell_map = self.grid[cell]
        is_new_type = agent_type not in cell_map
        cell_map[agent_type].append(agent)
        if is_new_type:
            self._insert_type_order(cell, agent_type)

        # Update dedicated grids
        # We use string names to avoid circular imports or heavy isinstance checks
        type_name = agent_type.__name__
        if type_name == "Fish":
            self.fish_grid[cell].append(agent)
        elif issubclass(agent_type, self._food_base_type):
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
                        self._remove_type_order(cell, agent_type)
                except ValueError:
                    pass  # Agent might not be in the list if something went wrong

            # Remove from dedicated grids
            type_name = agent_type.__name__
            if type_name == "Fish":
                if agent in self.fish_grid[cell]:
                    self.fish_grid[cell].remove(agent)
                    if not self.fish_grid[cell]:
                        del self.fish_grid[cell]
            elif issubclass(agent_type, self._food_base_type):
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
                            self._remove_type_order(old_cell, agent_type)
                    except ValueError:
                        pass

                # Remove from dedicated grids (old cell)
                type_name = agent_type.__name__
                if type_name == "Fish":
                    if agent in self.fish_grid[old_cell]:
                        self.fish_grid[old_cell].remove(agent)
                        if not self.fish_grid[old_cell]:
                            del self.fish_grid[old_cell]
                elif issubclass(agent_type, self._food_base_type):
                    if agent in self.food_grid[old_cell]:
                        self.food_grid[old_cell].remove(agent)
                        if not self.food_grid[old_cell]:
                            del self.food_grid[old_cell]

            # Add to new cell
            new_cell_map = self.grid[new_cell]
            is_new_type = agent_type not in new_cell_map
            new_cell_map[agent_type].append(agent)
            if is_new_type:
                self._insert_type_order(new_cell, agent_type)

            # Add to dedicated grids (new cell)
            type_name = agent_type.__name__
            if type_name == "Fish":
                self.fish_grid[new_cell].append(agent)
            elif issubclass(agent_type, self._food_base_type):
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
            (col, row) for col in range(min_col, max_col + 1) for row in range(min_row, max_row + 1)
        ]

    def query_radius(self, agent: Agent, radius: float) -> List[Agent]:
        """
        Get all agents within a radius of the given agent.

        This is much faster than checking all agents, as it only checks
        agents in nearby grid cells.

        PERFORMANCE: Avoids intermediate list creation by directly filtering
        during iteration. Uses local variables for faster attribute access.
        """
        # OPTIMIZATION: Assume agent has pos (skip hasattr check in hot path)
        pos = agent.pos
        agent_pos_x = pos.x
        agent_pos_y = pos.y
        radius_sq = radius * radius

        # Calculate cell range directly
        cell_size = self.cell_size
        cols = self.cols
        rows = self.rows
        min_col = max(0, int((agent_pos_x - radius) / cell_size))
        max_col = min(cols - 1, int((agent_pos_x + radius) / cell_size))
        min_row = max(0, int((agent_pos_y - radius) / cell_size))
        max_row = min(rows - 1, int((agent_pos_y + radius) / cell_size))

        result: list[Agent] = []
        result_append = result.append  # OPTIMIZATION: Local reference to append
        grid = self.grid

        # Iterate ranges directly - OPTIMIZATION: Filter inline
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell = (col, row)
                cell_agents = grid.get(cell)
                if cell_agents:
                    for type_key, type_list in cell_agents.items():
                        for other in type_list:
                            if other is not agent:
                                other_pos = other.pos
                                dx = other_pos.x - agent_pos_x
                                dy = other_pos.y - agent_pos_y
                                if dx * dx + dy * dy <= radius_sq:
                                    result_append(other)

        return result

    def query_fish(self, agent: Agent, radius: float) -> List[Agent]:
        """Optimized query for nearby fish.

        PERFORMANCE: Avoids intermediate list creation by directly filtering
        during iteration. Uses local variables for faster attribute access.

        NOTE: Filters out dead/migrated fish to prevent "ghost attraction"
        where live fish are attracted to positions of fish that have died
        but haven't been removed from the grid yet.
        """
        # OPTIMIZATION: Assume agent has pos (skip hasattr check in hot path)
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        # Use helper to consolidate min/max calculations (INLINED)
        cs = self.cell_size
        cols_m1 = self.cols - 1
        rows_m1 = self.rows - 1
        min_col = max(0, int((agent_x - radius) / cs))
        max_col = min(cols_m1, int((agent_x + radius) / cs))
        min_row = max(0, int((agent_y - radius) / cs))
        max_row = min(rows_m1, int((agent_y + radius) / cs))

        result: list[Agent] = []
        result_append = result.append  # OPTIMIZATION: Local reference
        fish_grid = self.fish_grid

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_fish = fish_grid.get((col, row))
                if cell_fish:
                    # OPTIMIZATION: Filter directly during iteration
                    for other in cell_fish:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

        return result

    def query_food(self, agent: Agent, radius: float) -> List[Agent]:
        """Optimized query for nearby food.

        PERFORMANCE: Avoids intermediate list creation by directly filtering
        during iteration. Uses local variables for faster attribute access.
        """
        # OPTIMIZATION: Assume agent has pos (skip hasattr check in hot path)
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        # Use helper to consolidate min/max calculations (INLINED)
        cs = self.cell_size
        cols_m1 = self.cols - 1
        rows_m1 = self.rows - 1
        min_col = max(0, int((agent_x - radius) / cs))
        max_col = min(cols_m1, int((agent_x + radius) / cs))
        min_row = max(0, int((agent_y - radius) / cs))
        max_row = min(rows_m1, int((agent_y + radius) / cs))

        result: list[Agent] = []
        result_append = result.append  # OPTIMIZATION: Local reference
        food_grid = self.food_grid

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_food = food_grid.get((col, row))
                if cell_food:
                    # OPTIMIZATION: Filter directly during iteration
                    for other in cell_food:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

        return result

    def closest_fish(self, agent: Agent, radius: float) -> Optional[Agent]:
        """Find the single closest fish within radius.

        PERFORMANCE: Avoids list allocation by tracking best match during iteration.
        """
        # OPTIMIZATION: Assume agent has pos
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        # Use helper to consolidate min/max calculations (INLINED)
        cs = self.cell_size
        cols_m1 = self.cols - 1
        rows_m1 = self.rows - 1
        min_col = max(0, int((agent_x - radius) / cs))
        max_col = min(cols_m1, int((agent_x + radius) / cs))
        min_row = max(0, int((agent_y - radius) / cs))
        max_row = min(rows_m1, int((agent_y + radius) / cs))

        fish_grid = self.fish_grid

        nearest_agent = None
        nearest_dist_sq = float("inf")

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_fish = fish_grid.get((col, row))
                if cell_fish:
                    for other in cell_fish:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            dist_sq = dx * dx + dy * dy
                            if dist_sq <= radius_sq and dist_sq < nearest_dist_sq:
                                nearest_dist_sq = dist_sq
                                nearest_agent = other

        return nearest_agent

    def closest_food(self, agent: Agent, radius: float) -> Optional[Agent]:
        """Find the single closest food within radius.

        PERFORMANCE: Avoids list allocation by tracking best match during iteration.
        """
        # OPTIMIZATION: Assume agent has pos
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        # Use helper to consolidate min/max calculations (INLINED)
        cs = self.cell_size
        cols_m1 = self.cols - 1
        rows_m1 = self.rows - 1
        min_col = max(0, int((agent_x - radius) / cs))
        max_col = min(cols_m1, int((agent_x + radius) / cs))
        min_row = max(0, int((agent_y - radius) / cs))
        max_row = min(rows_m1, int((agent_y + radius) / cs))

        food_grid = self.food_grid

        nearest_agent = None
        nearest_dist_sq = float("inf")

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell_food = food_grid.get((col, row))
                if cell_food:
                    for other in cell_food:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            dist_sq = dx * dx + dy * dy
                            if dist_sq <= radius_sq and dist_sq < nearest_dist_sq:
                                nearest_dist_sq = dist_sq
                                nearest_agent = other

        return nearest_agent

    def query_interaction_candidates(
        self, agent: Agent, radius: float, crab_type: Type[Agent]
    ) -> List[Agent]:
        """
        Optimized query for collision candidates (Fish, Food, Crabs).
        Performs a single grid traversal to collect all relevant entities.

        PERFORMANCE: Avoids intermediate list creation by directly filtering
        during iteration. Uses local variables for faster attribute access.
        """
        # OPTIMIZATION: Assume agent has pos (skip hasattr check in hot path)
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        cell_size = self.cell_size
        cols = self.cols
        rows = self.rows
        min_col = max(0, int((agent_x - radius) / cell_size))
        max_col = min(cols - 1, int((agent_x + radius) / cell_size))
        min_row = max(0, int((agent_y - radius) / cell_size))
        max_row = min(rows - 1, int((agent_y + radius) / cell_size))

        result: list[Agent] = []
        result_append = result.append  # OPTIMIZATION: Local reference
        fish_grid = self.fish_grid
        food_grid = self.food_grid
        grid = self.grid

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell = (col, row)

                # Check Fish - OPTIMIZATION: Filter inline
                cell_fish = fish_grid.get(cell)
                if cell_fish:
                    for other in cell_fish:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

                # Check Food - OPTIMIZATION: Filter inline
                cell_food = food_grid.get(cell)
                if cell_food:
                    for other in cell_food:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

                # Check Crabs - OPTIMIZATION: Filter inline
                cell_agents = grid.get(cell)
                if cell_agents and crab_type in cell_agents:
                    for other in cell_agents[crab_type]:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

        return result

    def query_poker_entities(self, agent: Agent, radius: float) -> List[Agent]:
        """
        Optimized query for poker-eligible entities (Fish and Plant).

        PERFORMANCE: Single pass through spatial grid for both fish and plants.
        Uses dedicated fish_grid and type-specific plant lookup.
        Filters inline during iteration to avoid intermediate list.
        """
        from core.entities.plant import Plant

        # OPTIMIZATION: Assume agent has pos (skip hasattr check in hot path)
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        cell_size = self.cell_size
        min_col = max(0, int((agent_x - radius) / cell_size))
        max_col = min(self.cols - 1, int((agent_x + radius) / cell_size))
        min_row = max(0, int((agent_y - radius) / cell_size))
        max_row = min(self.rows - 1, int((agent_y + radius) / cell_size))

        result: list[Agent] = []
        result_append = result.append  # OPTIMIZATION: Local reference
        fish_grid = self.fish_grid
        grid = self.grid

        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                cell = (col, row)

                # Get fish from dedicated grid (fast) - inline filter
                cell_fish = fish_grid.get(cell)
                if cell_fish:
                    for other in cell_fish:
                        if other is not agent:
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

                # Get plants from type-specific bucket - inline filter
                cell_agents = grid.get(cell)
                if cell_agents:
                    cell_plants = cell_agents.get(Plant)
                    if cell_plants:
                        for other in cell_plants:
                            if other is not agent:
                                other_pos = other.pos
                                dx = other_pos.x - agent_x
                                dy = other_pos.y - agent_y
                                if dx * dx + dy * dy <= radius_sq:
                                    result_append(other)

        return result

    def clear(self):
        """Clear all agents from the grid."""
        self.grid.clear()
        self.fish_grid.clear()
        self.food_grid.clear()
        self.agent_cells.clear()

    def rebuild(self, agents: List[Agent]):
        """Rebuild the entire grid from scratch."""
        self.clear()
        for agent in agents:
            self.add_agent(agent)

    # Cache for issubclass results to avoid repeated checks
    # Key: (type_key, agent_class), Value: bool
    _subclass_cache: Dict[Tuple[Type, Type], bool] = {}

    def query_type(self, agent: Agent, radius: float, agent_class: Type[Agent]) -> List[Agent]:
        """
        Return a list of agents of a given type within a certain radius of the given agent.

        Optimized to use dedicated grids for common types (Fish, Food) and
        cached type-buckets for others.
        """
        # OPTIMIZATION: Fast-path for common types using dedicated grids
        agent_class_name = agent_class.__name__
        if agent_class_name == "Fish":
            return self.query_fish(agent, radius)
        if agent_class_name == "Food" or issubclass(agent_class, Food):
            return self.query_food(agent, radius)

        # Generic path for other types:
        # 1. Inline spatial grid logic to avoid function call overhead
        # 2. Iterate grid cells directly to avoid creating intermediate candidate list
        # 3. Use type buckets to only iterate relevant agents

        # OPTIMIZATION: Assume agent has pos (skip hasattr check in hot path)
        pos = agent.pos
        agent_x = pos.x
        agent_y = pos.y
        radius_sq = radius * radius

        # Calculate cell range
        min_col = max(0, int((agent_x - radius) / self.cell_size))
        max_col = min(self.cols - 1, int((agent_x + radius) / self.cell_size))
        min_row = max(0, int((agent_y - radius) / self.cell_size))
        max_row = min(self.rows - 1, int((agent_y + radius) / self.cell_size))

        result = []
        result_append = result.append
        grid_dict = self.grid
        subclass_cache = self._subclass_cache

        # Iterate cells
        for col in range(min_col, max_col + 1):
            for row in range(min_row, max_row + 1):
                # Get type buckets for this cell
                cell_buckets = grid_dict.get((col, row))
                if not cell_buckets:
                    continue

                # Iterate over type buckets
                for type_key, agents in cell_buckets.items():
                    # OPTIMIZATION: Use cached issubclass check
                    cache_key = (type_key, agent_class)
                    is_match = subclass_cache.get(cache_key)
                    if is_match is None:
                        is_match = issubclass(type_key, agent_class)
                        subclass_cache[cache_key] = is_match

                    if is_match:
                        for other in agents:
                            if other is agent:
                                continue

                            # Distance check
                            other_pos = other.pos
                            dx = other_pos.x - agent_x
                            dy = other_pos.y - agent_y
                            if dx * dx + dy * dy <= radius_sq:
                                result_append(other)

        return result
