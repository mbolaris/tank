"""Environment module for spatial queries and agent management.

This module provides the Environment class which manages spatial queries
for agents in the simulation. It's designed to work with both pygame-based
sprite agents and pure entity objects.
"""

import warnings
from typing import Iterable, List, Optional, Type

# Avoid importing pygame-dependent Agent during tests
try:
    from agents import Agent
except ImportError:  # pragma: no cover - fallback for environments without pygame
    Agent = object


class Environment:
    """
    The environment in which the agents operate.
    This class provides methods to interact with and query the state of the environment.
    """
    def __init__(self, agents: Optional[Iterable[Agent]] = None):
        """
        Initialize the environment.

        Args:
            agents (Iterable[Agent], optional): A collection of agents. Defaults to None.
        """
        self.agents = agents

        # NEW: Initialize communication system for fish
        from core.fish_communication import FishCommunicationSystem
        self.communication_system = FishCommunicationSystem(
            max_signals=50,
            decay_rate=0.05
        )

    def nearby_agents(self, agent: Agent, radius: int) -> List[Agent]:
        """
        Return a list of agents within a certain radius of the given agent.

        Args:
            agent (Agent): The agent to consider.
            radius (int): The radius to consider.

        Returns:
            List[Agent]: The agents within the radius.
        """
        return [other for other in self.agents 
                if other != agent and (other.pos - agent.pos).length() <= radius]

    def get_agents_of_type(self, agent_class: Type[Agent]) -> List[Agent]:
        """
        Get all agents of the given class.

        Args:
            agent_class (Type[Agent]): The class of the agents to consider.

        Returns:
            List[Agent]: The agents of the given class.
        """
        return [agent for agent in self.agents if isinstance(agent, agent_class)]
    
    def nearby_agents_by_type(self, agent: Agent, radius: int, agent_class: Type[Agent]) -> List[Agent]:
        """
        Return a list of agents of a given type within a certain radius of the given agent.

        Args:
            agent (Agent): The agent to consider.
            radius (int): The radius to consider.
            agent_class (Type[Agent]): The class of the agents to find.

        Returns:
            List[Agent]: The agents of the specified type within the radius.
        """
        return [other for other in self.get_agents_of_type(agent_class)
                if other != agent and (other.pos - agent.pos).length() <= radius]

    # Backward compatibility aliases
    def agents_to_avoid(self, agent: Agent, radius: int, agent_class: Type[Agent]) -> List[Agent]:
        """Deprecated: Use nearby_agents_by_type instead.

        This method is deprecated and will be removed in a future version.
        Use nearby_agents_by_type() instead.
        """
        warnings.warn(
            "agents_to_avoid() is deprecated. Use nearby_agents_by_type() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.nearby_agents_by_type(agent, radius, agent_class)

    def agents_to_align_with(self, agent: Agent, radius: int, agent_class: Type[Agent]) -> List[Agent]:
        """Deprecated: Use nearby_agents_by_type instead.

        This method is deprecated and will be removed in a future version.
        Use nearby_agents_by_type() instead.
        """
        warnings.warn(
            "agents_to_align_with() is deprecated. Use nearby_agents_by_type() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.nearby_agents_by_type(agent, radius, agent_class)
