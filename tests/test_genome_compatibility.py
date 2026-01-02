import random

from core.genetics import Genome
from core.genetics.trait import GeneticTrait


def test_trait_containers():
    rng = random.Random(42)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Read trait containers
    assert isinstance(g.physical.size_modifier.value, float)
    assert isinstance(g.behavioral.aggression.value, float)
    assert isinstance(g.behavioral.mate_preferences.value, dict)

    # Set values directly on GeneticTrait containers
    g.physical.size_modifier.value = 1.77
    assert abs(g.physical.size_modifier.value - 1.77) < 1e-6

    g.behavioral.aggression.value = 0.12
    assert abs(g.behavioral.aggression.value - 0.12) < 1e-6


def test_cache_invalidation_on_trait_change():
    rng = random.Random(1)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Compute baseline speed
    base_speed = g.speed_modifier

    # Change a trait that affects speed and invalidate caches via API
    g.physical.fin_size.value = g.physical.fin_size.value + 0.5
    g.invalidate_caches()
    new_speed = g.speed_modifier

    assert new_speed != base_speed


# =============================================================================
# Code Policy Tests
# =============================================================================


def test_code_policy_has_defaults():
    """New genomes should have a default movement policy."""
    from core.code_pool import BUILTIN_SEEK_NEAREST_FOOD_ID

    rng = random.Random(42)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Code policy traits exist and have default values
    assert g.behavioral.code_policy_kind is not None
    assert g.behavioral.code_policy_kind.value == "movement_policy"

    assert g.behavioral.code_policy_component_id is not None
    assert g.behavioral.code_policy_component_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID

    # Params should be None by default (no tuning yet)
    assert g.behavioral.code_policy_params is not None
    assert g.behavioral.code_policy_params.value is None


def test_old_genome_loads_without_code_policy():
    """Old genomes (schema v1) without code policy get default policy assigned.
    
    When loading old genomes that don't have code_policy fields, the factory
    creates a new genome with defaults, which includes the default movement policy.
    """
    from core.code_pool import BUILTIN_SEEK_NEAREST_FOOD_ID

    rng = random.Random(123)

    # Simulate an old genome without code policy fields
    old_genome_data = {
        "schema_version": 1,
        "size_modifier": 1.0,
        "color_hue": 0.5,
        "color_saturation": 0.5,
        "color_brightness": 0.5,
        "fin_size": 0.5,
        "tail_size": 0.5,
        "pattern_type": 0,
        "pattern_intensity": 0.5,
        "body_aspect": 0.5,
        "eye_size": 0.5,
        "template_id": 0,
        "aggression": 0.5,
        "social_tendency": 0.5,
        "pursuit_aggression": 0.5,
        "prediction_skill": 0.5,
        "hunting_stamina": 0.5,
        "asexual_reproduction_chance": 0.1,
        # No code_policy_* fields - they get defaults from factory
    }

    # Should load without crashing
    g = Genome.from_dict(old_genome_data, rng=rng, use_algorithm=False)

    # Code policy defaults from factory (not None)
    assert g.behavioral.code_policy_kind.value == "movement_policy"
    assert g.behavioral.code_policy_component_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID
    assert g.behavioral.code_policy_params.value is None

    # Other traits should be loaded
    assert abs(g.physical.size_modifier.value - 1.0) < 1e-6
    assert abs(g.behavioral.aggression.value - 0.5) < 1e-6


def test_genome_with_code_policy_round_trip():
    """Genome with code policy should serialize and deserialize correctly."""
    rng = random.Random(456)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Set code policy fields
    g.behavioral.code_policy_kind = GeneticTrait("movement_policy")
    g.behavioral.code_policy_component_id = GeneticTrait("comp_abc123")
    g.behavioral.code_policy_params = GeneticTrait({"speed_mult": 1.5, "turn_rate": 0.8})

    # Serialize and deserialize
    data = g.to_dict()
    rng2 = random.Random(456)
    g2 = Genome.from_dict(data, rng=rng2, use_algorithm=False)

    # Verify round-trip
    assert g2.behavioral.code_policy_kind.value == "movement_policy"
    assert g2.behavioral.code_policy_component_id.value == "comp_abc123"
    assert g2.behavioral.code_policy_params.value == {"speed_mult": 1.5, "turn_rate": 0.8}


def test_code_policy_validation():
    """Code policy validation should catch invalid configurations."""
    rng = random.Random(789)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Valid: all None
    result = g.validate()
    assert result["ok"], f"Unexpected issues: {result['issues']}"

    # Invalid: component_id set but kind is None
    g.behavioral.code_policy_component_id = GeneticTrait("comp_xyz")
    g.behavioral.code_policy_kind = GeneticTrait(None)
    result = g.validate()
    assert not result["ok"]
    assert any(
        "code_policy_component_id is set but code_policy_kind is not" in i for i in result["issues"]
    )

    # Valid: both set
    g.behavioral.code_policy_kind = GeneticTrait("foraging_policy")
    result = g.validate()
    assert result["ok"], f"Unexpected issues: {result['issues']}"

    # Invalid: param out of range
    g.behavioral.code_policy_params = GeneticTrait({"bad_param": 999.0})
    result = g.validate()
    assert not result["ok"]
    assert any("out of range" in i for i in result["issues"])

    # Invalid: param is NaN
    import math

    g.behavioral.code_policy_params = GeneticTrait({"nan_param": math.nan})
    result = g.validate()
    assert not result["ok"]
    assert any("must be finite" in i for i in result["issues"])


def test_code_policy_inheritance_deterministic():
    """Code policy inheritance should be deterministic under fixed RNG."""
    rng1 = random.Random(111)
    rng2 = random.Random(111)

    # Create parents with code policies
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(1))
    parent1.behavioral.code_policy_kind = GeneticTrait("movement_policy")
    parent1.behavioral.code_policy_component_id = GeneticTrait("parent1_comp")
    parent1.behavioral.code_policy_params = GeneticTrait({"x": 1.0})

    parent2 = Genome.random(use_algorithm=False, rng=random.Random(2))
    parent2.behavioral.code_policy_kind = GeneticTrait("foraging_policy")
    parent2.behavioral.code_policy_component_id = GeneticTrait("parent2_comp")
    parent2.behavioral.code_policy_params = GeneticTrait({"y": 2.0})

    # Create offspring twice with same RNG seed
    child1 = Genome.from_parents_weighted(parent1, parent2, rng=rng1)
    child2 = Genome.from_parents_weighted(parent1, parent2, rng=rng2)

    # Should be identical
    assert child1.behavioral.code_policy_kind.value == child2.behavioral.code_policy_kind.value
    assert (
        child1.behavioral.code_policy_component_id.value
        == child2.behavioral.code_policy_component_id.value
    )
    # Params may have been mutated, but deterministically
    assert child1.behavioral.code_policy_params.value == child2.behavioral.code_policy_params.value


def test_code_policy_inheritance_from_single_parent():
    """Code policy inheritance when one parent has custom policy, other has default."""
    from core.code_pool import BUILTIN_SEEK_NEAREST_FOOD_ID

    # Parent with custom code policy
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(10))
    parent1.behavioral.code_policy_kind = GeneticTrait("movement_policy")
    parent1.behavioral.code_policy_component_id = GeneticTrait("custom_parent_comp")
    parent1.behavioral.code_policy_params = GeneticTrait({"z": 3.0})

    # Parent with default code policy (from Genome.random)
    parent2 = Genome.random(use_algorithm=False, rng=random.Random(20))
    # parent2 has default: movement_policy + BUILTIN_SEEK_NEAREST_FOOD_ID

    # Create multiple offspring to check probability distribution
    custom_count = 0
    default_count = 0
    total = 100
    for i in range(total):
        rng = random.Random(1000 + i)
        child = Genome.from_parents_weighted(parent1, parent2, parent1_weight=0.5, rng=rng)
        if child.behavioral.code_policy_component_id.value is not None:
            if child.behavioral.code_policy_component_id.value == "custom_parent_comp":
                custom_count += 1
            elif child.behavioral.code_policy_component_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID:
                default_count += 1

    # Both policies should be inherited sometimes (probabilistic)
    assert custom_count > 10, f"Custom policy inherited only {custom_count} times"
    assert default_count > 10, f"Default policy inherited only {default_count} times"


def test_code_policy_params_mutation():
    """Code policy params should mutate slightly during inheritance."""
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(30))
    parent1.behavioral.code_policy_kind = GeneticTrait("test_policy")
    parent1.behavioral.code_policy_component_id = GeneticTrait("test_comp")
    parent1.behavioral.code_policy_params = GeneticTrait({"a": 5.0, "b": -2.0})

    parent2 = Genome.random(use_algorithm=False, rng=random.Random(40))
    parent2.behavioral.code_policy_kind = GeneticTrait("test_policy")
    parent2.behavioral.code_policy_component_id = GeneticTrait("test_comp")
    parent2.behavioral.code_policy_params = GeneticTrait({"a": 5.0, "b": -2.0})

    # Check if any mutations occur over many offspring
    mutated = False
    for i in range(100):
        rng = random.Random(2000 + i)
        child = Genome.from_parents_weighted(parent1, parent2, rng=rng)
        if child.behavioral.code_policy_params.value is not None:
            params = child.behavioral.code_policy_params.value
            if params.get("a") != 5.0 or params.get("b") != -2.0:
                mutated = True
                break

    # At least some mutations should occur
    assert mutated, "No param mutations detected over 100 offspring"
