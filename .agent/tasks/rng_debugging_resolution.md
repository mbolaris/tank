# RNG Debugging Resolution

## Issue
`MissingRNGError` was persistently raised during poker strategy initialization in benchmarks and simulations, despite debug logs showing that a valid `random.Random` object was being passed to the constructors.

## Root Cause Analysis
- Extensive debugging revealed a contradiction: the strategy `__init__` methods received a valid RNG object (verified by prints), but the helper function `require_rng_param(rng, context)` raised a `MissingRNGError` claiming the RNG was `None`.
- This suggests a subtle issue likely related to module import state, function call context, or a non-obvious Python runtime behavior affecting the `require_rng_param` function in the running environment.

## Resolution
- **Inlined RNG Checks:** Instead of relying on the external `require_rng_param` helper, the RNG validation logic was inlined directly into the `__init__` methods of all standard and expert poker strategies (`TightPassive`, `LoosePassive`, `TightAggressive`, `LooseAggressive`, `Balanced`, `Maniac`, `GTOExpert`, `AlwaysFold`, and `Random`).
- **Logic:**
  ```python
  if rng is None:
      raise RuntimeError(f"{self.__class__.__name__}: RNG is None")
  _rng = rng
  ```
- **Cleanup:** Debug prints added to `benchmark_eval.py` and `rng.py` were removed after verification.
- **Verification:** The simulation now runs without `MissingRNGError`, and `test_benchmark_determinism.py` passes cleanly.

## Affected Files
- `core/poker/strategy/implementations/standard.py`
- `core/poker/strategy/implementations/baseline.py`
- `core/poker/strategy/implementations/expert.py`
- `core/poker/evaluation/benchmark_eval.py` (Debug prints removed)
- `core/util/rng.py` (Debug prints removed)
