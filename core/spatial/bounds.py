"""World boundary management and collision resolution."""

from typing import Any, Tuple

from core.entities import Agent


class WorldBounds:
    """
    Manages the geometry and boundary behavior of the world.

    Handles rectangular bounds by default and supports optional custom
    boundary shapes (e.g., circular for Petri dish mode).
    """

    def __init__(self, width: int, height: int):
        """
        Initialize the world bounds.

        Args:
            width: Width of the environment in pixels
            height: Height of the environment in pixels
        """
        self.width = width
        self.height = height
        # Optional custom boundary handler (e.g., PetriDish)
        self._custom_boundary: Any = None

    def set_custom_boundary(self, boundary_handler: Any) -> None:
        """Set a custom boundary handler (e.g. for Petri Dish mode)."""
        self._custom_boundary = boundary_handler

    def get_dimensions(self) -> Tuple[float, float]:
        """Get the world dimensions (width, height)."""
        return (float(self.width), float(self.height))

    def is_valid_position(self, x: float, y: float) -> bool:
        """Check if a position is within the rectangular bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def resolve_collision(self, agent: Agent) -> bool:
        """
        Resolve collision with custom boundary.

        This method is called by Agent.handle_screen_edges() to allow
        non-rectangular boundaries.

        Returns:
            True if collision was resolved (agent should skip rectangular bounds),
            False to fall back to rectangular boundary handling.
        """
        if self._custom_boundary is None:
            return False

        if not hasattr(agent, "vel"):
            return False

        # Calculate agent center and radius
        # Use max(width, height) / 2 for proper circular approximation
        agent_r = max(agent.width, getattr(agent, "height", agent.width)) / 2
        agent_width = agent.width
        agent_height = getattr(agent, "height", agent.width)

        agent_cx = agent.pos.x + agent_width / 2
        agent_cy = agent.pos.y + agent_height / 2

        # Use custom boundary to clamp and reflect
        # The handler is expected to implement clamp_and_reflect compatible with PetriDish
        new_cx, new_cy, new_vx, new_vy, collided = self._custom_boundary.clamp_and_reflect(
            agent_cx,
            agent_cy,
            agent.vel.x,
            agent.vel.y,
            agent_r,
        )

        if collided:
            # Update agent position (convert center back to top-left)
            agent.pos.x = new_cx - agent_width / 2
            agent.pos.y = new_cy - agent_height / 2

            # Update rect if present
            if hasattr(agent, "rect"):
                agent.rect.x = agent.pos.x
                agent.rect.y = agent.pos.y

            # Update velocity
            agent.vel.x = new_vx
            agent.vel.y = new_vy

        # Always return True when custom boundary is active,
        # meaning "I handled (or checked) it, don't do default rect logic"
        return True
