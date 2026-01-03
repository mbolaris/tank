"""Petri dish environment.

Subclass of the standard tank Environment that adds circular boundary physics.
"""

from typing import TYPE_CHECKING, Any

from core.environment import Environment
from core.worlds.petri.geometry import (
    PETRI_CENTER_X,
    PETRI_CENTER_Y,
    PETRI_RADIUS,
    reflect_velocity,
)

if TYPE_CHECKING:
    from core.entities.base import Agent


class PetriEnvironment(Environment):
    """Petri dish environment with circular boundary."""

    def resolve_boundary_collision(self, agent: "Agent") -> bool:
        """Resolve collision with the circular dish boundary.
        
        Args:
            agent: The agent to check
            
        Returns:
            True if collision was resolved (or agent is safe), False to fallback
        """
        if not hasattr(agent, "vel"):
            return False

        # Calculate agent distance from center
        # Use center of agent for simple checking, or closest point?
        # Usually agents are circles or points in physics.
        # Let's assume circular agent with radius = width/2
        agent_r = agent.width / 2
        agent_cx = agent.pos.x + agent_r
        agent_cy = agent.pos.y + agent_r

        dx = agent_cx - PETRI_CENTER_X
        dy = agent_cy - PETRI_CENTER_Y
        dist_sq = dx * dx + dy * dy
        
        # Max distance allowed is dish radius minus agent radius
        max_dist = PETRI_RADIUS - agent_r
        max_dist_sq = max_dist * max_dist

        if dist_sq > max_dist_sq:
            # Collision!
            dist = dist_sq ** 0.5
            if dist < 0.001:
                return True # Should not happen unless max_dist is 0

            # Calculate normal (pointing inward)
            # The vector (dx, dy) points OUTWARD from center to agent
            # So inward normal is (-dx, -dy)
            nx = -dx / dist
            ny = -dy / dist

            # Push agent back in
            overlap = dist - max_dist
            new_cx = agent_cx + nx * overlap
            new_cy = agent_cy + ny * overlap
            
            # Update agent position (top-left)
            agent.pos.x = new_cx - agent_r
            agent.pos.y = new_cy - agent_r
            if hasattr(agent, "rect"):
                agent.rect.x = agent.pos.x
                agent.rect.y = agent.pos.y

            # Reflect velocity if moving outward
            # Velocity v dot Normal n < 0 means moving against normal (outward)
            # agent.vel dot (nx, ny) < 0 ?
            # Wait, normal points INWARD. 
            # If v points outward, v dot n < 0.
            # So if v dot n < 0, we reflect.
            vx = agent.vel.x
            vy = agent.vel.y
            
            if vx * nx + vy * ny < 0:
                new_vx, new_vy = reflect_velocity(vx, vy, nx, ny)
                agent.vel.x = new_vx
                agent.vel.y = new_vy

            return True

        return True  # Agent is inside, handled (no need for rect check)
