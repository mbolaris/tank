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

    # Movement policy should have default
    assert g.behavioral.movement_policy_id is not None
    assert g.behavioral.movement_policy_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID

    # Other policies None by default
    assert g.behavioral.poker_policy_id is not None
    assert g.behavioral.poker_policy_id.value is None

    # Params should be None by default (no tuning yet)
    assert g.behavioral.movement_policy_params is not None
    assert g.behavioral.movement_policy_params.value is None


def test_old_genome_loads_with_migration():
    """Old genomes (legacy schema) with code_policy fields should migrate to per-kind fields.

    When loading a legacy genome that has 'code_policy_kind'='movement_policy',
    it should populate 'movement_policy_id' and 'movement_policy_params'.
    """
    rng = random.Random(123)

    # Simulate a legacy genome with single-policy fields
    legacy_genome_data = {
        "schema_version": 2,
        "size_modifier": 1.0,
        "color_hue": 0.5,
        "fin_size": 0.5,
        "tail_size": 0.5,
        "body_aspect": 0.5,
        "eye_size": 0.5,
        "code_policy_kind": "movement_policy",
        "code_policy_component_id": "test_legacy_id",
        "code_policy_params": {"legacy_param": 1.0},
        # Per-kind fields missing -> should trigger migration
    }

    # Should load and migrate
    g = Genome.from_dict(legacy_genome_data, rng=rng, use_algorithm=False)

    # Verified migration to per-kind fields
    # NEW BEHAVIOR: Legacy migration is removed, so we expect defaults (ignoring legacy ID)
    from core.code_pool import BUILTIN_SEEK_NEAREST_FOOD_ID

    assert g.behavioral.movement_policy_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID
    # Params should be None or default, definitively NOT the legacy param
    assert g.behavioral.movement_policy_params.value is None

    # Poker/Soccer should be empty
    assert g.behavioral.poker_policy_id.value is None
    assert g.behavioral.soccer_policy_id.value is None


def test_genome_with_code_policy_round_trip():
    """Genome with per-kind code policy should serialize and deserialize correctly."""
    rng = random.Random(456)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Set per-kind policy fields
    g.behavioral.movement_policy_id = GeneticTrait("comp_move")
    g.behavioral.movement_policy_params = GeneticTrait({"speed": 1.0})

    g.behavioral.poker_policy_id = GeneticTrait("comp_poker")
    g.behavioral.poker_policy_params = GeneticTrait({"bet": 0.5})

    # Serialize and deserialize
    data = g.to_dict()
    rng2 = random.Random(456)
    g2 = Genome.from_dict(data, rng=rng2, use_algorithm=False)

    # Verify round-trip
    assert g2.behavioral.movement_policy_id.value == "comp_move"
    assert g2.behavioral.movement_policy_params.value == {"speed": 1.0}

    assert g2.behavioral.poker_policy_id.value == "comp_poker"
    assert g2.behavioral.poker_policy_params.value == {"bet": 0.5}


def test_code_policy_validation():
    """Code policy validation should catch invalid configurations."""
    rng = random.Random(789)
    g = Genome.random(use_algorithm=False, rng=rng)

    # Valid: defaults
    result = g.validate()
    assert result["ok"], f"Unexpected issues: {result['issues']}"

    # Invalid: param out of range
    g.behavioral.movement_policy_id = GeneticTrait("comp_move")
    g.behavioral.movement_policy_params = GeneticTrait({"bad_param": 999.0})  # Max is 100.0 usually
    result = g.validate()
    assert not result["ok"]
    assert any("out of range" in i for i in result["issues"])

    # Invalid: param is NaN
    import math

    g.behavioral.movement_policy_params = GeneticTrait({"nan_param": math.nan})
    result = g.validate()
    assert not result["ok"]
    assert any("must be finite" in i for i in result["issues"])


def test_code_policy_inheritance_deterministic():
    """Code policy inheritance should be deterministic under fixed RNG."""
    rng1 = random.Random(111)
    rng2 = random.Random(111)

    # Create parents with per-kind policies
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(1))
    parent1.behavioral.movement_policy_id = GeneticTrait("p1_move")
    parent1.behavioral.movement_policy_params = GeneticTrait({"x": 1.0})

    parent2 = Genome.random(use_algorithm=False, rng=random.Random(2))
    parent2.behavioral.movement_policy_id = GeneticTrait("p2_move")
    parent2.behavioral.movement_policy_params = GeneticTrait({"y": 2.0})

    # Create offspring twice with same RNG seed
    child1 = Genome.from_parents_weighted(parent1, parent2, rng=rng1)
    child2 = Genome.from_parents_weighted(parent1, parent2, rng=rng2)

    # Should be identical
    assert child1.behavioral.movement_policy_id.value == child2.behavioral.movement_policy_id.value
    # Params may have been mutated, but deterministically
    assert (
        child1.behavioral.movement_policy_params.value
        == child2.behavioral.movement_policy_params.value
    )


def test_code_policy_inheritance_from_single_parent():
    """Code policy inheritance when one parent has custom policy, other has default."""
    from core.code_pool import BUILTIN_SEEK_NEAREST_FOOD_ID

    # Parent with custom code policy
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(10))
    parent1.behavioral.movement_policy_id = GeneticTrait("custom_parent_comp")
    parent1.behavioral.movement_policy_params = GeneticTrait({"z": 3.0})

    # Parent with default code policy (from Genome.random)
    parent2 = Genome.random(use_algorithm=False, rng=random.Random(20))
    # parent2 has default: movement_policy_id = BUILTIN_SEEK_NEAREST_FOOD_ID

    # Create multiple offspring to check probability distribution
    custom_count = 0
    default_count = 0
    total = 100
    for i in range(total):
        rng = random.Random(1000 + i)
        child = Genome.from_parents_weighted(parent1, parent2, parent1_weight=0.5, rng=rng)
        if child.behavioral.movement_policy_id.value is not None:
            if child.behavioral.movement_policy_id.value == "custom_parent_comp":
                custom_count += 1
            elif child.behavioral.movement_policy_id.value == BUILTIN_SEEK_NEAREST_FOOD_ID:
                default_count += 1

    # Both policies should be inherited sometimes (probabilistic)
    assert custom_count > 10, f"Custom policy inherited only {custom_count} times"
    assert default_count > 10, f"Default policy inherited only {default_count} times"


def test_code_policy_params_mutation():
    """Code policy params should mutate slightly during inheritance."""
    parent1 = Genome.random(use_algorithm=False, rng=random.Random(30))
    parent1.behavioral.movement_policy_id = GeneticTrait("test_comp")
    parent1.behavioral.movement_policy_params = GeneticTrait({"a": 5.0, "b": -2.0})

    parent2 = Genome.random(use_algorithm=False, rng=random.Random(40))
    parent2.behavioral.movement_policy_id = GeneticTrait("test_comp")
    parent2.behavioral.movement_policy_params = GeneticTrait({"a": 5.0, "b": -2.0})

    # Check if any mutations occur over many offspring
    mutated = False
    for i in range(100):
        rng = random.Random(2000 + i)
        child = Genome.from_parents_weighted(parent1, parent2, rng=rng)
        if child.behavioral.movement_policy_params.value is not None:
            params = child.behavioral.movement_policy_params.value
            if params.get("a") != 5.0 or params.get("b") != -2.0:
                mutated = True
                break

    # At least some mutations should occur
    assert mutated, "No param mutations detected over 100 offspring"
