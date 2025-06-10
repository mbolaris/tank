from typing import List, Optional, Type
import pygame
from agents import Agent

class Environment:
    """
    The environment in which the agents operate. 
    This class provides methods to interact with and query the state of the environment.
    """
    def __init__(self, agents: Optional[pygame.sprite.Group] = None):
        """
        Initialize the environment.

        Args:
            agents (pygame.sprite.Group, optional): A group of agents. Defaults to None.
        """
        self.agents = agents

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
        Get all other agent of the given class.

        Args:
            agent_class (Type[Agent]): The class of the agents to consider.

        Returns:
            List[Agent]: The agents of the given class.
        """
        return [agent for agent in self.agents if isinstance(agent, agent_class) and agent != self]
    
    def agents_to_avoid(self, agent: Agent, radius: int, agent_class: Type[Agent]) -> List[Agent]:
        """
        Return a list of agents of a given type within a certain radius of the given agent.

        Args:
            agent (Agent): The agent to consider.
            radius (int): The radius to consider.
            agent_class (Type[Agent]): The class of the agents to avoid.

        Returns:
            List[Agent]: The agents within the radius.
        """
        return [other for other in self.get_agents_of_type(agent_class)
                if other != agent and (other.pos - agent.pos).length() <= radius]

    def agents_to_align_with(self, agent: Agent, radius: int, agent_class: Type[Agent]) -> List[Agent]:
        """
        Return a list of agents of a given type within a certain radius of the given agent.

        Args:
            agent (Agent): The agent to consider.
            radius (int): The radius to consider.
            agent_class (Type[Agent]): The class of the agents to align with.

        Returns:
            List[Agent]: The agents within the radius.
        """
        return [other for other in self.get_agents_of_type(agent_class)
                if other != agent and (other.pos - agent.pos).length() <= radius]
