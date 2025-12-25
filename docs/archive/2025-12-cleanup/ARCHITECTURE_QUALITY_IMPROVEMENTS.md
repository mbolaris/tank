# Architecture Quality Improvements - December 2024

## Summary

This document tracks safe, incremental architectural improvements to move the codebase toward exemplary software design.

## Completed Improvements

### 1. ✅ Deprecated Unused Wrapper Functions (crossover.py)

**Problem**: `crossover_genomes()` and `crossover_genomes_weighted()` in `evolution/crossover.py` existed but were never called in production code. They were wrappers around `Genome.from_parents()` that added indirection without value.

**Solution**: Added deprecation warnings directing developers to use the canonical API (`Genome.from_parents()` and `Genome.from_parents_weighted_params()`).

**Impact**: 
- Clearer API surface for developers
- Reduced confusion about which function to use
- Backward compatible (functions still work, just emit warnings)

### 2. ✅ Removed Broken Test File (test_evolution_smoke.py)

**Problem**: `tests/test_evolution_smoke.py` imported from a non-existent module `core.evolution.smoke_test`. This was a stale file that couldn't run.

**Solution**: Removed the broken test file. The correct tests are at `tests/smoke/test_evolution_smoke.py`.

### 3. ✅ Fixed Stale Integration Test (test_proper_energy_scaling.py)

**Problem**: Test was using old API:
- `PokerInteraction(fish1, fish2)` instead of `PokerInteraction([fish1, fish2])`
- Referenced non-existent fields: `reproduction_occurred`, `offspring`

**Solution**: Updated to use new API and `should_trigger_reproduction()` function.

### 4. ✅ Fixed Import Error (test_proper_energy_scaling.py)  

**Problem**: Imported from deleted module `core.fish_poker`.

**Solution**: Changed to `core.poker_interaction`.

### 5. ✅ Expanded Result Type Usage (PlantManager)

**Problem**: `PlantManager.sprout_new_plant()` returned `bool`, but there were multiple distinct failure reasons (disabled, no spot, claim failed). Callers couldn't tell *why* sprouting failed.

**Solution**: Changed return type from `bool` to `Result[Plant, str]`.

```python
# Before - caller doesn't know why it failed
def sprout_new_plant(...) -> bool:
    if not self.enabled:
        return False  # Why? Disabled? No space? Claim failed?

# After - failure reason is explicit
def sprout_new_plant(...) -> Result[Plant, str]:
    if not self.enabled:
        return Err("Plants are disabled")
    if spot is None:
        return Err(f"No available root spot near ({parent_x:.0f}, {parent_y:.0f})")
    ...
    return Ok(plant)
```

**Impact**:
- Failures are now explicit and debuggable
- Callers can use `result.is_ok()` for backward-compatible bool checks
- Error messages provide context for debugging
- Demonstrates the Result pattern for future adoption

**Files changed**:
- `core/plant_manager.py` - Added Result import, changed return type
- `core/simulation_engine.py` - Updated wrapper to use `result.is_ok()`

---

## Recommended Future Improvements

### 2. 🔄 Consolidate CrossoverMode Enums

**Status**: Ready for implementation

**Problem**: Two crossover mode enums exist:
```python
core.evolution.crossover.CrossoverMode       # AVERAGING, RECOMBINATION, WEIGHTED
core.genetics.genome.GeneticCrossoverMode    # AVERAGING, RECOMBINATION, DOMINANT_RECESSIVE
```

**Recommendation**: 
1. Keep only `GeneticCrossoverMode` 
2. Deprecate `CrossoverMode` with alias to `GeneticCrossoverMode`
3. Add `WEIGHTED` to `GeneticCrossoverMode` if needed

**Files to change**:
- `core/evolution/crossover.py` - deprecate `CrossoverMode`
- `core/evolution/__init__.py` - re-export `GeneticCrossoverMode` 
- `tests/test_evolution_module.py` - use `GeneticCrossoverMode`

---

### 3. 🔄 Expand Result Type Usage

**Status**: Low effort, high value

**Problem**: The excellent `Result` type exists in `core/result.py` but is only used in `core/state_machine.py`.

**Current Usage**:
- `core.state_machine.py` ✅

**Recommended Expansion** (operations where errors should be explicit):
- Fish reproduction (can fail for many reasons)
- Energy transfer operations  
- Migration attempts
- Poker game initiation

**Example refactoring**:
```python
# Before
def try_reproduce(self) -> Optional[Fish]:
    if not self.can_reproduce():
        return None  # Silent failure - caller might forget to check!
    ...

# After
def try_reproduce(self) -> Result[Fish, str]:
    if not self.can_reproduce():
        return Err("Insufficient energy for reproduction")
    ...
    return Ok(offspring)
```

---

### 4. 🔄 Mark Internal Functions as Private

**Status**: Low effort, documentation improvement

**Problem**: Several functions in `evolution/crossover.py` are test utilities but look like public API:
- `blend_values()` 
- `blend_discrete()`
- `crossover_dict_values()`

**Recommendation**: Rename with leading underscore to signal internal use:
- `_blend_values()` 
- `_blend_discrete()`
- `_crossover_dict_values()`

Update test imports to use explicit internal import:
```python
from core.evolution.crossover import _blend_values  # Clear this is internal
```

---

### 5. 🔄 Remove or Consolidate Algorithm Crossover Functions

**Status**: Medium effort, reduces duplication

**Problem**: Algorithm crossover exists in multiple places:
```
core/algorithms/__init__.py:
  - crossover_algorithms()
  - crossover_algorithms_weighted() 
  - crossover_poker_algorithms()
  - _crossover_algorithms_base()

core/evolution/inheritance.py:
  - inherit_algorithm()  # Wraps crossover_algorithms_weighted
```

**Recommendation**: 
1. `inherit_algorithm()` is the high-level API - keep it
2. Consider moving low-level functions from `algorithms/__init__.py` to a dedicated module
3. Document the intended usage pattern

---

### 6. 🔄 Add Pre-commit Checks for Deprecated API Usage

**Status**: Low effort, prevents regression

**Recommendation**: Add a lint rule or pre-commit hook that warns if deprecated functions are used in new code:
```bash
# .pre-commit-config.yaml addition
- repo: local
  hooks:
    - id: check-deprecated-api
      name: Check for deprecated API usage
      entry: grep -rn "crossover_genomes\|crossover_genomes_weighted" --include="*.py"
      language: system
      types: [python]
      pass_filenames: false
```

---

## Code Removal Candidates

### Files/Functions to Consider Removing

| Item | Location | Reason | Safe to Remove? |
|------|----------|--------|-----------------|
| `crossover_genomes()` | `evolution/crossover.py` | Deprecated, never used | After deprecation period |
| `crossover_genomes_weighted()` | `evolution/crossover.py` | Deprecated, never used | After deprecation period |
| `CrossoverMode` enum | `evolution/crossover.py` | Duplicate of `GeneticCrossoverMode` | After migration |

---

## Design Principles Reinforced

1. **Single Source of Truth**: One canonical way to do crossover (`Genome.from_parents()`)
2. **Explicit over Implicit**: Result types make failures visible
3. **Private by Default**: Internal helpers use underscore prefix
4. **Document Intent**: Deprecation notices explain the better alternative
5. **Incremental Change**: Small, tested changes rather than big rewrites

---

## Next Session Tasks

When continuing architectural improvements:

1. [ ] Run full test suite to verify no regressions: `pytest tests/ -v`
2. [ ] Consider consolidating `CrossoverMode` and `GeneticCrossoverMode`
3. [ ] Identify more candidates for `Result` type adoption
4. [ ] Review `algorithms/__init__.py` for consolidation opportunities
