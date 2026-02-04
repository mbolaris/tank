"""Environment module for spatial queries and agent management.

This module provides the Environment class which manages spatial queries
for agents in the simulation.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, Iterable

from core.entities import Agent
from core.interfaces import MigrationHandler
from core.spatial.bounds import WorldBounds
from core.spatial.grid import SpatialGrid

# Type alias for energy delta recorder callback
# Signature: (entity, delta, source, metadata) -> None
EnergyDeltaRecorder = Callable[["Agent", float, str, Dict[str, Any]], None]


class Environment:
    """
    The environment in which the agents operate.
    This class provides methods to interact with and query the state of the environment.
    """

    # Class-level cache for issubclass results to avoid repeated checks
    # Key: (type_key, agent_class), Value: bool
    _subclass_cache: dict[tuple[type, type], bool] = {}

    def __init__(
        self,
        agents: Iterable[Agent] | None = None,
        width: int = 800,
        height: int = 600,
        time_system: Any | None = None,
        rng: random.Random | None = None,
        event_bus: Any | None = None,
        simulation_config: Any | None = None,
    ):
        """
        Initialize the environment.

        Args:
            agents (list[Agent] | None): List of agents (stored by reference). Defaults to None.
            width (int): Width of the environment in pixels. Defaults to 800.
            height (int): Height of the environment in pixels. Defaults to 600.
            time_system (TimeSystem, optional): Time system for day/night cycle effects
            rng: Random number generator for deterministic behavior
            event_bus: Optional EventBus for domain event dispatch
            simulation_config: Optional SimulationConfig for runtime parameters
        """
        agents_list: list[Agent] | None
        if agents is None:
            agents_list = None
        elif isinstance(agents, list):
            agents_list = agents
        else:
            agents_list = list(agents)
        self.agents = agents_list
        self.width = width
        self.height = height

        # New components
        self.bounds = WorldBounds(width, height)
        # OPTIMIZATION: Cache bounds as tuple to avoid allocation in hot path
        self._cached_bounds = ((0.0, 0.0), (float(width), float(height)))
        self.spatial_grid = SpatialGrid(width, height, cell_size=150)

        self.time_system = time_system
        self.event_bus = event_bus  # Domain event dispatch
        self.simulation_config = simulation_config  # Runtime config access
        from core.util.rng import require_rng_param

        self._rng = require_rng_param(rng, "__init__")

        # Default to GenomeCodePool with all builtins for better safety + determinism
        from core.code_pool import create_default_genome_code_pool

        self.genome_code_pool = create_default_genome_code_pool()

        # Migration support (injected by backend)
        self.connection_manager: Any = None  # Set by backend if migrations enabled
        self.world_manager: Any = None  # Set by backend if migrations enabled
        self.world_id: str | None = None  # Set by backend if migrations enabled
        self.world_name: str | None = None  # Set by backend for lineage tracking
        self.migration_handler: MigrationHandler | None = (
            None  # Set by backend if migrations enabled
        )

        # World mode identifier (set by mode pack / backend when available)
        self.world_type: str | None = None

        # Optional circular dish geometry for Petri mode (set during mode switching)
        self._dish: Any | None = None

        # Optional soccer components (populated by Soccer mode packs)
        self.ball: Any = None
        self.goal_manager: Any = None

        # Performance: Cache detection range modifier (updated once per frame)
        self._cached_detection_modifier: float = 1.0

        # Optional spawn requester (injected by engine to centralize mutations)
        self._spawn_requester = None
        # Optional remove requester (injected by engine to centralize mutations)
        self._remove_requester = None

        # Build initial spatial grid if agents are provided
        if self.agents is not None:
            self.spatial_grid.rebuild(self.agents)

        self._type_cache: dict[type[Agent], list[Agent]] = {}

        # NEW: Initialize communication system for fish
        from core.agent_signals import AgentSignalSystem

        self.communication_system = AgentSignalSystem(max_signals=50, decay_rate=0.05)

    @property
    def dish(self) -> Any | None:
        return self._dish

    @dish.setter
    def dish(self, value: Any | None):
        self._dish = value
        # Update bounds component
        self.bounds.set_custom_boundary(value)

    def set_spawn_requester(self, requester) -> None:
        """Inject a spawn requester callback from the simulation engine.

        The requester should accept (entity, reason=..., metadata=...) and return bool.
        """
        self._spawn_requester = requester

    def set_remove_requester(self, requester) -> None:
        """Inject a removal requester callback from the simulation engine.

        The requester should accept (entity, reason=..., metadata=...) and return bool.
        """
        self._remove_requester = requester

    def set_energy_delta_recorder(self, recorder: EnergyDeltaRecorder | None) -> None:
        """Inject an energy delta recorder callback from the simulation engine.

        The recorder is called each time an entity's energy changes via modify_energy().
        Set to None to disable recording (done at end of each frame).

        Args:
            recorder: Callback with signature (entity, delta, source, metadata) -> None
        """
        self._energy_delta_recorder = recorder

    def record_energy_delta(
        self,
        entity: Agent,
        delta: float,
        source: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Record an energy change if recorder is active.

        Called by entities during modify_energy() to track energy changes.
        Zero deltas are ignored.

        Args:
            entity: The entity whose energy changed
            delta: The actual energy change applied (may differ from requested amount)
            source: Description of why energy changed (e.g., "metabolism", "poker")
            meta: Optional additional metadata
        """
        if delta == 0:
            return
        recorder = getattr(self, "_energy_delta_recorder", None)
        if recorder is not None:
            recorder(entity, delta, source, meta or {})

    def request_spawn(
        self, entity: Agent, *, reason: str = "", metadata: dict[str, Any] | None = None
    ) -> bool:
        """Request an entity spawn via the engine's mutation queue.

        Prefer core.util.mutations.request_spawn for entity-owned spawn requests.

        Returns False if no requester is configured.
        """
        if self._spawn_requester is None:
            return False
        return bool(self._spawn_requester(entity, reason=reason, metadata=metadata))

    def request_remove(
        self, entity: Agent, *, reason: str = "", metadata: dict[str, Any] | None = None
    ) -> bool:
        """Request an entity removal via the engine's mutation queue.

        Prefer core.util.mutations.request_remove for entity-owned removal requests.

        Returns False if no requester is configured.
        """
        if self._remove_requester is None:
            return False
        return bool(self._remove_requester(entity, reason=reason, metadata=metadata))

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
        if self.agents is None:
            self.spatial_grid.clear()
        else:
            self.spatial_grid.rebuild(self.agents)
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

    def resolve_boundary_collision(self, agent: Agent) -> bool:
        """Resolve collision with custom boundary (e.g., circular dish).

        This method is called by Agent.handle_screen_edges() to allow
        non-rectangular boundaries. When a dish is set (Petri mode),
        uses circular physics. Otherwise returns False to use rectangular bounds.

        Args:
            agent: The agent to check and potentially reposition

        Returns:
            True if collision was resolved (agent should skip rectangular bounds),
            False to fall back to rectangular boundary handling
        """
        return self.bounds.resolve_collision(agent)

    def nearby_agents(self, agent: Agent, radius: float) -> list[Agent]:
        """
        Return a list of agents within a certain radius of the given agent.

        Uses spatial grid partition for O(k) performance.
        """
        return self.spatial_grid.query_radius(agent, float(radius))

    def get_agents_of_type(self, agent_type: type[Agent]) -> list[Agent]:
        """
        Get all agents of the given class.

        Uses caching to avoid re-filtering on repeated calls within the same frame.
        """
        # Check cache first
        if agent_type in self._type_cache:
            return self._type_cache[agent_type]

        # Compute and cache result
        if self.agents is None:
            return []

        result = [agent for agent in self.agents if isinstance(agent, agent_type)]
        self._type_cache[agent_type] = result
        return result

    def closest_fish(self, agent: Agent, radius: float) -> Agent | None:
        """Find closest fish efficiently."""
        return self.spatial_grid.closest_fish(agent, radius)

    def closest_food(self, agent: Agent, radius: float) -> Agent | None:
        """Find closest food efficiently."""
        return self.spatial_grid.closest_food(agent, radius)

    def nearby_agents_by_type(
        self,
        agent: Agent,
        radius: float,
        agent_type: type[Agent] | None = None,
        *,
        agent_class: type[Agent] | None = None,
    ) -> list[Agent]:
        """
        Return a list of agents of a given type within a certain radius of the given agent.
        """
        resolved_type = agent_type if agent_type is not None else agent_class
        if resolved_type is None:
            raise TypeError(
                "nearby_agents_by_type requires 'agent_type' (positional) or 'agent_class' (keyword)"
            )
        return self.spatial_grid.query_type(agent, float(radius), resolved_type)

    def nearby_evolving_agents(self, agent: Agent, radius: float) -> list[Agent]:
        """Get nearby evolving agents (entities that can reproduce)."""
        # Currently just fish
        return self.spatial_grid.query_fish(agent, float(radius))

    def nearby_resources(self, agent: Agent, radius: float) -> list[Agent]:
        """Get nearby consumable resources."""
        # Currently just food
        return self.spatial_grid.query_food(agent, float(radius))

    def nearby_interaction_candidates(
        self, agent: Agent, radius: float, crab_type: type[Agent]
    ) -> list[Agent]:
        """
        Optimized method to get nearby Fish, Food, and Crabs in a single pass.
        """
        return self.spatial_grid.query_interaction_candidates(agent, float(radius), crab_type)

    def nearby_poker_entities(self, agent: Agent, radius: float) -> list[Agent]:
        """
        Optimized method to get nearby fish and Plant entities for poker.
        """
        return self.spatial_grid.query_poker_entities(agent, float(radius))

    # =========================================================================
    # Caching Architecture Note
    # =========================================================================
    #
    # Two separate caches exist for different access patterns:
    #
    # 1. CacheManager (in EntityManager): Caches fish_list and food_list for
    #    engine-level access (systems, stats calculation, etc.)
    #    Access via: engine.get_fish_list(), engine.get_food_list()
    #
    # 2. Environment._type_cache: Caches get_agents_of_type() results for
    #    behavior algorithms that run per-fish per-frame.
    #    Access via: environment.get_agents_of_type(SomeClass)
    #
    # Both caches are invalidated when entities are added/removed.
    # The SpatialGrid provides O(k) proximity queries and is separate.
    # =========================================================================

    # --- World Protocol Implementation ---
    # The following methods/properties implement the World Protocol,
    # making Environment usable as an abstract World in generic simulation code.

    @property
    def dimensions(self) -> tuple[float, ...]:
        """Get environment dimensions (implements World Protocol).

        Returns:
            Tuple of (width, height) for 2D environment
        """
        # OPTIMIZATION: Return from cached bounds if available
        if hasattr(self, "_cached_bounds"):
            return self._cached_bounds[1]
        return self.bounds.get_dimensions()

    def get_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get environment boundaries (implements World Protocol).

        Returns:
            ((min_x, min_y), (max_x, max_y)) for 2D environment
        """
        # OPTIMIZATION: Return cached tuple to avoid allocation
        return self._cached_bounds

    def get_2d_bounds(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get 2D boundaries (implements World2D Protocol).

        Returns:
            ((min_x, min_y), (max_x, max_y))
        """
        return self._cached_bounds

    def is_valid_position(self, position: tuple[float, float]) -> bool:
        """Check if a position is valid within this environment (implements World Protocol).

        Args:
            position: (x, y) tuple to check

        Returns:
            True if position is within bounds [0, width) x [0, height)
        """
        if not isinstance(position, (tuple, list)) or len(position) != 2:
            return False

        x, y = position
        return self.bounds.is_valid_position(x, y)

    @property
    def rng(self) -> random.Random:
        """Get the shared RNG (implements World Protocol).

        Returns:
            Random instance for deterministic simulation
        """
        return self._rng

    def list_policy_component_ids(self, kind: str) -> list[str]:
        """List available policy component IDs for a given policy kind.

        Canonical API for querying available policies. Use this instead of
        probing for code_pool attribute.

        Args:
            kind: Policy kind (e.g., "movement_policy", "soccer_policy")

        Returns:
            List of component IDs, or empty list if no pool configured.
        """
        if self.genome_code_pool is None:
            return []
        return self.genome_code_pool.get_components_by_kind(kind)
