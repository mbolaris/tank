"""RCSSWorld: A World implementation backed by the RoboCup Soccer Simulator.

This module adapts the RCSSServerAdapter to the core World protocol, allowing
the rest of the simulation system (SimulationEngine, WorldRegistry) to interact
with an external rcssserver process (or fake) as just another "World".
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type

from core.entities.base import Agent
from core.interfaces import Positionable
from core.math_utils import Vector2
from core.world import World, World2D
from core.worlds.soccer.rcssserver_adapter import RCSSServerAdapter

if TYPE_CHECKING:
    from core.worlds.soccer.backend import SoccerWorldConfig

logger = logging.getLogger(__name__)


class RCSSWorld:
    """A World implementation backed by rcssserver.
    
    This wrapper translates World protocol calls into RCSS adapter calls.
    It maintains the connection to the server and manages the mapping
    between simulation Agents and RCSS players.
    """

    def __init__(
        self,
        adapter: RCSSServerAdapter,
        rng: Optional[random.Random] = None,
    ) -> None:
        """Initialize RCSSWorld.
        
        Args:
            adapter: The underlying RCSSServerAdapter instance
            rng: Random number generator (optional)
        """
        self._adapter = adapter
        self._rng = rng or random.Random()
        
        # Determine field dimensions from adapter config or defaults
        # Standard RCSS field is ~105m x 68m, but we mapped to "tank units" internally or not?
        # Actually RCSS uses its own coordinate system (-52.5 to 52.5).
        # We should expose these raw dimensions for now.
        config = getattr(adapter, "config", None)
        if config:
            self._width = config.field_width
            self._height = config.field_height
        else:
            # Fallback defaults (standard RCSS)
            self._width = 105.0
            self._height = 68.0

    @property
    def rng(self) -> random.Random:
        return self._rng

    @property
    def dimensions(self) -> Tuple[float, float]:
        return (self._width, self._height)

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    def get_bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Get 2D bounds (min_x, min_y), (max_x, max_y)."""
        half_w = self._width / 2
        half_h = self._height / 2
        return ((-half_w, -half_h), (half_w, half_h))
    
    def get_2d_bounds(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return self.get_bounds()

    def is_valid_position(self, position: Any) -> bool:
        """Check if position is within field bounds."""
        if not hasattr(position, "x") or not hasattr(position, "y"):
            return False
        
        (min_x, min_y), (max_x, max_y) = self.get_bounds()
        return (min_x <= position.x <= max_x) and (min_y <= position.y <= max_y)

    # --- Spatial Queries ---
    
    # Note: RCSS doesn't give us a full "god view" of all agents easily unless we use
    # the online coach or monitor protocol. The adapter currently parses 'see' messages
    # for each agent.
    # For this World implementation, we rely on the adapter's `get_current_snapshot()`
    # which aggregates known state.
    
    def nearby_agents(self, agent: Agent, radius: float) -> List[Agent]:
        # TODO: Implement proper spatial query using snapshot state
        # For now, return empty as this is primarily for interaction which isn't fully 
        # implemented for pure RCSS yet (interactions happen via kicks/tackles in engine)
        return []

    def nearby_agents_by_type(
        self, agent: Agent, radius: float, agent_type: Type[Agent]
    ) -> List[Agent]:
        return []

    def nearby_evolving_agents(self, agent: Agent, radius: float) -> List[Agent]:
        return []

    def nearby_resources(self, agent: Agent, radius: float) -> List[Agent]:
        return []

    def get_agents_of_type(self, agent_type: Type[Agent]) -> List[Agent]:
        # TODO: Return proxy agents representing the players/ball?
        return []

    # --- Lifecycle and Interaction ---

    def start(self) -> None:
        """Start the world (connect to server)."""
        # Adapter connects on first step or explicit init?
        # The adapter.reset() handles connection usually.
        pass

    def step(self, actions_by_agent: Optional[Dict[str, Any]] = None) -> Any:
        """Advance simulation one step."""
        return self._adapter.step(actions_by_agent)

    def close(self) -> None:
        """Clean up."""
        if hasattr(self._adapter, "close"):
            self._adapter.close()
