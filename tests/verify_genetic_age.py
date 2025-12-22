import sys
import os
import random

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.genetics.genome import Genome
from core.genetics.physical import PhysicalTraits
from core.entities.fish import Fish
from core.config.fish import LIFE_STAGE_MATURE_MAX

def verify_genetic_age():
    print("Verifying Genetic Age Implementation...")
    
    # 1. Verify Trait Existence and Random Generation
    print("\n1. Testing Genome Generation...")
    genome = Genome.random()
    if hasattr(genome.physical, "lifespan_modifier"):
        print(f"PASS: Genome has lifespan_modifier: {genome.physical.lifespan_modifier.value:.2f}")
    else:
        print("FAIL: Genome missing lifespan_modifier trait!")
        return

    # 2. Verify Max Age Calculation
    print("\n2. Testing Max Age Calculation...")
    
    # Create a dummy class to mock what Fish needs
    class MockMovement:
        def __init__(self): 
            self.velocity = type('obj', (object,), {'length': lambda: 0})()
        
    class MockEnv:
        def __init__(self): 
            self.width = 1000
            self.height = 1000
            self.agents = []
        def add_agent(self, agent): pass
            
    # Manually modify genome for test cases
    # We must set the .value of the GeneticTrait
    
    # Case A: Normal lifespan (1.0)
    # Physical traits store their values inside GeneticTrait wrappers.
    genome.physical.size_modifier.value = 1.0
    genome.physical.lifespan_modifier.value = 1.0
    
    try:
        fish = Fish(
            environment=MockEnv(),
            movement_strategy=MockMovement(),
            species="TestSpecies",
            x=0, y=0,
            speed=5.0,
            genome=genome,
            ecosystem=None
        )
        
        expected_age = int(LIFE_STAGE_MATURE_MAX * 1.0 * 1.0)
        print(
            f"Test A (1.0, 1.0): Max Age: {fish._lifecycle_component.max_age} (Expected: {expected_age})"
        )
        # Allow small rounding errors if any, but int cast should match exact logic
        if fish._lifecycle_component.max_age == expected_age:
            print("PASS: Calculation correct for base values.")
        else:
            print(f"FAIL: Calculation incorrect. Got {fish._lifecycle_component.max_age}")

        # Case B: Long lifespan (1.4)
        genome.physical.lifespan_modifier.value = 1.4
        fish_long = Fish(
            environment=MockEnv(),
            movement_strategy=MockMovement(),
            species="TestSpecies",
            x=0, y=0,
            speed=5.0,
            genome=genome,
            ecosystem=None
        )
        expected_age_long = int(LIFE_STAGE_MATURE_MAX * 1.0 * 1.4)
        print(
            f"Test B (1.0, 1.4): Max Age: {fish_long._lifecycle_component.max_age} (Expected: {expected_age_long})"
        )
        
        # Case C: Short lifespan (0.6)
        genome.physical.lifespan_modifier.value = 0.6
        fish_short = Fish(
            environment=MockEnv(),
            movement_strategy=MockMovement(),
            species="TestSpecies",
            x=0, y=0,
            speed=5.0,
            genome=genome,
            ecosystem=None
        )
        expected_age_short = int(LIFE_STAGE_MATURE_MAX * 1.0 * 0.6)
        print(
            f"Test C (1.0, 0.6): Max Age: {fish_short._lifecycle_component.max_age} (Expected: {expected_age_short})"
        )
        
        if (
            fish_long._lifecycle_component.max_age
            > fish._lifecycle_component.max_age
            > fish_short._lifecycle_component.max_age
        ):
            print("PASS: Variance working correctly (Long > Normal > Short).")
        else:
            print("FAIL: Variance logic failed.")
            
    except Exception as e:
        print(f"FAIL: Error initializing Fish: {e}")
        import traceback
        traceback.print_exc()

    # 3. Verify Inheritance/Mutation
    print("\n3. Testing Inheritance...")
    parent1 = Genome.random()
    parent1.physical.lifespan_modifier.value = 1.4
    
    parent2 = Genome.random()
    parent2.physical.lifespan_modifier.value = 1.4
    
    # With two high-lifespan parents, offspring should be high (around 1.4)
    offspring = Genome.from_parents(parent1, parent2)
    print(f"Parent1: 1.4, Parent2: 1.4 -> Offspring: {offspring.physical.lifespan_modifier.value:.2f}")
    
    if offspring.physical.lifespan_modifier.value > 1.2: 
        print("PASS: Inheritance preserves high lifespan.")
    else:
        print("FAIL: Offspring lifespan drifted too far or reset to default.")

if __name__ == "__main__":
    verify_genetic_age()
