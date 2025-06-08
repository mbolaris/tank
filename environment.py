class Environment:
    def __init__(self, agents=None):
        self.agents = agents     

    def nearby_agents(self, agent, radius):
        """Return a list of agents within a certain radius of the given agent."""
        nearby = []
        for other in self.agents:
            if other == agent:  # Skip the agent itself
                continue
            distance = (other.pos - agent.pos).length()  # Calculate the distance
            if distance <= radius:
                nearby.append(other)
        return nearby
    
    
    def get_agents_of_type(self, agent_class):
        """Get all other agent of the given class."""
        return [agent for agent in self.agents if isinstance(agent, agent_class) and agent != self]    
