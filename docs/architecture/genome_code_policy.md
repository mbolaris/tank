# Genome Code Policy

This document describes the code policy trait system, which allows fish genomes to carry references to the CodePool.

## Overview

The code policy trait block enables a genome to reference executable code components stored in the CodePool. This is a **data plumbing** layer only - the genetics system does not generate or execute code, it only manages references to code that exists elsewhere.

## Fields

The following fields are added to `BehavioralTraits`:

### `code_policy_kind`
- **Type**: `GeneticTrait[Optional[str]]`
- **Default**: `None`
- **Description**: The kind/category of policy this genome references (e.g., `"movement_policy"`, `"foraging_policy"`)
- **Validation**: Must be set if `code_policy_component_id` is set

### `code_policy_component_id`
- **Type**: `GeneticTrait[Optional[str]]`
- **Default**: `None`
- **Description**: The component ID from the CodePool that this genome references
- **Validation**: Must be a valid string if set

### `code_policy_params`
- **Type**: `GeneticTrait[Optional[Dict[str, float]]]`
- **Default**: `None`
- **Description**: Optional tuning parameters for the code policy
- **Validation**:
  - All values must be finite numbers (no NaN or Infinity)
  - All values must be in the range `[-10.0, 10.0]`

## Why Genetics Shouldn't Generate New Code

The genetics system is designed to **select from existing code**, not to generate new code. This separation exists for several reasons:

1. **Separation of Concerns**: Code generation is a complex task that belongs in the CodePool/training environment, not in the genetics layer.

2. **Safety**: Allowing genetics to generate arbitrary code would create security and stability risks.

3. **Evolvability**: By keeping genetics focused on selection and parameter tuning, we maintain a clean interface between evolution (which selects) and training (which creates).

4. **Debuggability**: When code references are explicit IDs, it's easier to trace which code a fish is using.

## Inheritance Rules

When two parents reproduce, the offspring's code policy is determined as follows:

1. **Both parents have code policies**: The child inherits one of them based on weighted probability (favoring the "winner" parent in winner-biased inheritance).

2. **Only one parent has a code policy**: The child may inherit it with probability proportional to that parent's weight, plus a small "gene flow" chance (30%) even if the other parent would normally dominate.

3. **Neither parent has a code policy**: The child has no code policy.

### Mutation

- **Drop probability**: 2% chance (scaled by mutation rate) to drop the code policy entirely, setting all fields to `None`.
- **Parameter mutation**: Each parameter in `code_policy_params` has a 15% chance (scaled by mutation rate) to be mutated with Gaussian noise.

### Constants

```python
CODE_POLICY_DROP_PROBABILITY = 0.02      # 2% base drop rate
CODE_POLICY_PARAM_MUTATION_RATE = 0.15   # 15% per-param mutation rate
CODE_POLICY_PARAM_MUTATION_STRENGTH = 0.1  # Gaussian sigma
CODE_POLICY_PARAM_MIN = -10.0            # Minimum param value
CODE_POLICY_PARAM_MAX = 10.0             # Maximum param value
```

## Serialization

Code policy fields are serialized in the genome's JSON representation:

```json
{
  "schema_version": 2,
  "code_policy_kind": "movement_policy",
  "code_policy_component_id": "comp_abc123",
  "code_policy_params": {
    "speed_mult": 1.5,
    "turn_rate": 0.8
  }
}
```

Old genomes (schema version 1) without these fields will load correctly, with code policy defaulting to `None`.

## Forward Path: Training Environment Integration

The planned integration with the training environment works as follows:

1. **CodePool creates components**: The training environment generates new code components and registers them in the CodePool with unique IDs.

2. **Genomes reference components**: When a fish is born or "upgraded" by the training system, its genome can be given a reference to a CodePool component.

3. **Evolution selects**: Over generations, natural selection will favor fish with beneficial code policies. The genetics system propagates and mutates these references without understanding what they do.

4. **Pool pruning**: Components that are never referenced by surviving fish can be garbage collected from the CodePool.

This creates a two-layer evolution system:
- **Layer 1 (Population)**: Genomes evolve, selecting from available code components
- **Layer 2 (Algorithm)**: The training environment creates new code components based on performance data

## Usage Example

```python
from core.genetics import Genome
from core.genetics.trait import GeneticTrait

# Create a genome
genome = Genome.random(use_algorithm=True, rng=rng)

# Assign a code policy
genome.behavioral.code_policy_kind = GeneticTrait("movement_policy")
genome.behavioral.code_policy_component_id = GeneticTrait("fast_swimmer_v1")
genome.behavioral.code_policy_params = GeneticTrait({
    "speed_multiplier": 1.5,
    "energy_cost": 0.8
})

# Validate
result = genome.validate()
assert result["ok"]

# Serialize
data = genome.to_dict()

# Deserialize
genome2 = Genome.from_dict(data, rng=rng)
assert genome2.behavioral.code_policy_component_id.value == "fast_swimmer_v1"
```

## Testing

The test suite (`tests/test_genome_compatibility.py`) verifies:

- New genomes default to no code policy
- Old genomes (schema v1) load correctly without code policy
- Code policy round-trips through serialization
- Validation catches invalid configurations
- Inheritance is deterministic under fixed RNG
- Parameter mutation occurs as expected
