
import pytest
from unittest.mock import Mock, MagicMock
from core.genetics.behavioral import BehavioralTraits, CODE_POLICY_DROP_PROBABILITY
from core.code_pool.pool import BUILTIN_SEEK_NEAREST_FOOD_ID
from core.entities.fish import Fish
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from backend.entity_transfer import _deserialize_fish
import random

def test_legacy_fish_deserialization_assigns_default_policy():
    """Test that deseralizing a legacy fish without code policy assigns the default."""
    
    # Mock world and dependencies
    mock_world = MagicMock()
    mock_world.rng = random.Random(42)
    mock_world.engine.environment = MagicMock()
    mock_world.engine.ecosystem = MagicMock()
    
    # Minimal legacy fish dict (missing code_policy fields in genome)
    # Using a simplified structure that matches what _deserialize_fish expects
    legacy_data = {
        "species": "Betta",
        "x": 100,
        "y": 100,
        "speed": 5.0,
        "generation": 1,
        "energy": 100.0,
        "genome_data": {
            # Minimal genome dict
             "physical": {
                "size_modifier": {"value": 1.0},
                 "tail_size": {"value": 1.0},
                 "fin_size": {"value": 1.0},
                 "body_aspect": {"value": 1.0},
                 "color_hue": {"value": 0.5},
                 "color_saturation": {"value": 0.5},
                 "pattern_type": {"value": 0.0},
                 "eye_size": {"value": 1.0},
            },
            "behavioral": {
                "aggression": {"value": 0.5},
                "social_tendency": {"value": 0.5},
                # code_policy fields missing
            }
        }
    }
    
    fish = _deserialize_fish(legacy_data, mock_world)
    
    assert fish is not None
    assert fish.genome.behavioral.code_policy_component_id is not None
    assert fish.genome.behavioral.code_policy_component_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID
    assert fish.genome.behavioral.code_policy_kind.value == "movement_policy"

def test_behavioral_traits_random_defaults():
    """Test that BehavioralTraits.random() sets the default policy."""
    rng = random.Random(42)
    traits = BehavioralTraits.random(rng)
    
    assert traits.code_policy_component_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID
    assert traits.code_policy_kind.value == "movement_policy"

def test_mutation_can_swap_policy():
    """Test that mutation can swap to a different available policy."""
    rng = random.Random(42)
    
    # Parent with default policy
    parent = BehavioralTraits.random(rng)
    assert parent.code_policy_component_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID
    
    # Force mutation with a new available policy
    # We need to run many trials because swap chance is small (10% of mutation rate)
    swapped = False
    available = ["NEW_POLICY_ID"]
    
    for _ in range(200):
        # High mutation rate to increase chance
        child = BehavioralTraits.from_parents(
            parent, parent, 
            mutation_rate=1.0, 
            mutation_strength=1.0, 
            rng=rng,
            available_policies=available
        )
        if child.code_policy_component_id.value == "NEW_POLICY_ID":
            swapped = True
            break
            
    assert swapped, "Mutation failed to swap policy component ID"

def test_genome_clone_passes_policies():
    """Test that Genome.clone_with_mutation correctly propagates available_policies."""
    rng = random.Random(42)
    # create a random genome
    parent = Genome.random(rng=rng)
    
    # Clone with available policies
    # This previously raised TypeError: Genome.from_parents_weighted() got an unexpected keyword argument 'available_policies'
    child = Genome.clone_with_mutation(
        parent, 
        rng=rng,
        available_policies=["NEW_POLICY"]
    )
    
    assert child is not None

if __name__ == "__main__":
    pytest.main([__file__])
