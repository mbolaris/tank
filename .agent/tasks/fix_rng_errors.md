# Fix RNG Errors in Evolution Tests

## Objective
Fix `MissingRNGError` and assert failures in evolution-related tests by ensuring consistent RNG injection and updating configuration expectations.

## Changes Implemented

1.  **`tests/test_evolution_comprehensive.py`**:
    *   Injected `rng=random.Random(42)` into `GreedyFoodSeeker` constructor, `PlantGenome` variant creation methods (`create_claude_variant`, `create_cosmic_fern_variant`), `Genome.random`, `Genome.from_parents`, and other calls.
    *   Updated `test_algorithm_switch_probability` to expect `0.08` switch rate (matching `DEFAULT_MUTATION_CONFIG`) instead of `0.04`.

2.  **`tests/test_poker_evolution_fixes.py`**:
    *   Updated all test methods to instantiate seeded `random.Random(42)`.
    *   Passed `rng` to Poker Strategy constructors (`TightAggressiveStrategy`, etc.) which now strictly require it.
    *   Passed `rng` to `crossover_poker_strategies`, `Genome.random`, and `Genome.from_winner_choice`.

3.  **`core/algorithms/registry.py`**:
    *   Fixed `_crossover_algorithms_base` fallback logic. When `random_instance(rng)` fails, it now attempts `cls(rng=rng)` before falling back to `cls()`. This allows algorithms like `EnergyConserver` (which require RNG in `__init__`) to be instantiated correctly during crossover fallbacks.

4.  **`tests/test_evolution_module.py`**:
    *   Updated `test_mutation_rate_clamps_to_max` to expect `0.35` (rate) and `0.25` (strength) matching default config, instead of outdated `0.25` and `0.15`.

5.  **`tests/test_genetics_refactor.py`**:
    *   Injected seeded `rng` into `Genome.random()`, `Genome.from_parents()`, and `Genome.from_parents_weighted()` calls.
    *   Updated `test_fish_integration` to initialize `Environment` with a seeded `rng`, allowing `Fish` to successfully retrieve it via `require_rng`.

## Validation
All tests in the following files pass:
*   `tests/test_evolution_comprehensive.py`
*   `tests/test_poker_evolution_fixes.py`
*   `tests/test_evolution_module.py`
*   `tests/test_genetics_refactor.py`
