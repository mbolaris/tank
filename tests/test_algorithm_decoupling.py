
import pytest
from unittest.mock import MagicMock
from typing import List, Type, Tuple, Any

from core.math_utils import Vector2
from core.world import World
from core.entities import Fish, Food, Agent
from core.algorithms.food_seeking import GreedyFoodSeeker
from core.algorithms.base import BehaviorAlgorithm

class MockWorld:
    """A minimal World implementation for testing algorithm decoupling."""
    
    def __init__(self):
        self.agents = []
        self.bounds = ((0, 0), (1000, 1000))
        
    def nearby_agents(self, agent: "Agent", radius: float) -> List["Agent"]:
        return [a for a in self.agents if a is not agent]
        
    def nearby_agents_by_type(self, agent: "Agent", radius: float, agent_type: Type["Agent"]) -> List["Agent"]:
        return [a for a in self.agents if isinstance(a, agent_type) and a is not agent]
        
    def get_agents_of_type(self, agent_type: Type["Agent"]) -> List["Agent"]:
        return [a for a in self.agents if isinstance(a, agent_type)]
        
    def get_bounds(self) -> Tuple[Any, Any]:
        return self.bounds
        
    def is_valid_position(self, position: Any) -> bool:
        x, y = position.x, position.y
        return 0 <= x <= 1000 and 0 <= y <= 1000
        
    @property
    def dimensions(self) -> Tuple[float, ...]:
        return (1000, 1000)
    
    # Generic methods
    def nearby_resources(self, agent: "Agent", radius: float) -> List["Agent"]:
        return self.nearby_agents_by_type(agent, radius, Food)

    # Note: domain-specific methods like nearby_fish are NOT implemented
    # to prove algorithms use the generic/protocol methods (or handle missing ones gracefully)

def test_algorithm_works_with_mock_world():
    """Test that a behavior algorithm works with a generic World implementation."""
    
    # Setup
    world = MockWorld()
    
    # Create agents with minimal attributes needed for algorithms
    fish = MagicMock(spec=Fish)
    fish.pos = Vector2(500, 500)
    fish.speed = 5.0
    fish.direction = Vector2(1, 0)
    fish.energy = 100
    fish.max_energy = 100
    # Important: fish.environment is the MockWorld, NOT Environment class
    fish.environment = world 
    
    # Mock specific fish methods used by algorithms
    fish.is_critical_energy.return_value = False
    fish.is_low_energy.return_value = False
    fish.get_energy_ratio.return_value = 1.0
    fish.genome = MagicMock()
    fish.genome.behavioral = MagicMock()
    fish.genome.behavioral.pursuit_aggression.value = 0.5
    fish.genome.behavioral.prediction_skill.value = 0.5
    
    # Add food to world
    food = MagicMock(spec=Food)
    food.pos = Vector2(510, 510) # Nearby
    food.vel = Vector2(0, 0)
    food.get_energy_value.return_value = 10
    world.agents.append(food)
    
    # Execute Algorithm
    algorithm = GreedyFoodSeeker()
    
    # This should work without error and return a steering vector
    # internally it calls _find_nearest_food -> nearby_resources (on MockWorld)
    vx, vy = algorithm.execute(fish)
    
    # Verify result
    assert vx != 0 or vy != 0, "Algorithm should return a movement vector toward food"
    
    # Verify interaction
    # The algorithm should have queried the world
    # (Implicitly verified by getting a result, as it needs food to move)

def test_find_nearest_helper_works_with_mock_world():
    """Test the base helper method with MockWorld."""
    world = MockWorld()
    fish = MagicMock(spec=Fish)
    fish.pos = Vector2(0, 0)
    fish.environment = world
    
    target = MagicMock(spec=Agent)
    target.pos = Vector2(10, 10)
    # Hack: make isinstance(target, Agent) work or use side_effect
    # but for simple mock, we simulate list return
    world.agents.append(target)
    
    # We rely on base.py behavior injected into a dummy class
    class TestAlgo(BehaviorAlgorithm):
        def execute(self, f): return 0,0
        def random_instance(cls): return cls()
        
    algo = TestAlgo("test_id")
    
    # This calls _find_nearest -> world.nearby_agents_by_type
    result = algo._find_nearest(fish, Agent, max_distance=100)
    
    assert result == target
