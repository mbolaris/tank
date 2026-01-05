"""Petri dish environment.

Subclass of the standard tank Environment that adds circular boundary physics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core.environment import Environment

if TYPE_CHECKING:
    from core.entities.base import Agent
    from core.worlds.petri.dish import PetriDish


class PetriEnvironment(Environment):
    """Petri dish environment with circular boundary.

    Requires a PetriDish object to define the circular boundary geometry.
    """

    dish: PetriDish

    def __init__(
        self,
        *args: Any,
        dish: PetriDish,
        **kwargs: Any,
    ) -> None:
        """Initialize PetriEnvironment with dish geometry.

        Args:
            dish: The PetriDish object defining boundary geometry
            *args, **kwargs: Passed to parent Environment
        """
        super().__init__(*args, **kwargs)
        self.dish = dish

    def resolve_boundary_collision(self, agent: Agent) -> bool:
        """Resolve collision with the circular dish boundary.

        Args:
            agent: The agent to check

        Returns:
            True if collision was resolved (or agent is safe), False to fallback
        """
        if self.dish is None:
            return False

        if not hasattr(agent, "vel"):
            return False

        # Calculate agent center and radius
        # Use max(width, height) / 2 for proper circular approximation
        agent_r = max(agent.width, getattr(agent, "height", agent.width)) / 2
        agent_cx = agent.pos.x + agent.width / 2
        agent_cy = agent.pos.y + getattr(agent, "height", agent.width) / 2

        # Use dish to clamp and reflect
        new_cx, new_cy, new_vx, new_vy, collided = self.dish.clamp_and_reflect(
            agent_cx,
            agent_cy,
            agent.vel.x,
            agent.vel.y,
            agent_r,
        )

        if collided:
            # Update agent position (convert center back to top-left)
            agent.pos.x = new_cx - agent.width / 2
            agent.pos.y = new_cy - getattr(agent, "height", agent.width) / 2
            if hasattr(agent, "rect"):
                agent.rect.x = agent.pos.x
                agent.rect.y = agent.pos.y

            # Update velocity
            agent.vel.x = new_vx
            agent.vel.y = new_vy

        return True  # Always handled (circular boundary is authoritative)
