# Plant Genetics Refactoring and Cleanup

## Summary
Successfully refactored `PlantGenome.fractal_type` to `PlantGenome.type` and renamed `core/genetics/plant.py` to `core/genetics/plant_genome.py`. Additionally, cleaned up remaining references to `poker_strategy_algorithm` in favor of `poker_strategy`.

## Changes Implemented

1.  **Renamed Attribute**: `PlantGenome.fractal_type` -> `PlantGenome.type`.
    *   Updated `core/genetics/plant_genome.py`.
    *   Updated `core/entities/plant.py`.
    *   Updated `core/simulation_engine.py`.
    *   Updated `backend/entity_transfer.py`.
    *   Updated frontend types and utilities (`frontend/src/types/simulation.ts`, `frontend/src/utils/plant.ts`).

2.  **Renamed File**: `core/genetics/plant.py` -> `core/genetics/plant_genome.py`.
    *   Updated imports in `core/genetics/__init__.py`.
    *   Checked for other imports (none found directly referencing `core.genetics.plant` outside of `__init__.py`).

3.  **Renamed Behavioral Trait**: `poker_strategy_algorithm` -> `poker_strategy`.
    *   Updated `backend/entity_transfer.py`.
    *   Updated `backend/simulation_runner.py`.
    *   Updated `backend/services/auto_eval_service.py`.
    *   Updated `tests/test_poker_evolution_fixes.py`.
    *   Updated log messages in `core/genetics/genome_codec.py`.

4.  **Updated Documentation**:
    *   `docs/LLM_FRACTAL_PLANT_CONTEST.md` updated to use `type` instead of `fractal_type`.

## Verification
*   Ran 56 tests across `tests/test_entity_transfer_codecs.py`, `tests/test_evolution_comprehensive.py`, `tests/test_evolution_module.py`, and `tests/test_poker_evolution_fixes.py`.
*   **Result**: All 56 tests PASSED.

## Next Steps
*   Restart the simulation (`python main.py`) to load the changes.
*   Monitor the frontend to ensure plants render correctly.
*   Verify that `auto_eval_service` runs correctly without errors (it was touched).
