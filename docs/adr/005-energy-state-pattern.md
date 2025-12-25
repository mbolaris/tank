# ADR-005: Energy State Pattern

## Status
Accepted (2024-12)

## Context

Energy checking was scattered across the codebase with inconsistent patterns:

```python
# In algorithms/base.py
if fish.energy / fish.max_energy < 0.15:
    # critical behavior

# In fish.py  
if self.energy < self.max_energy * 0.10:
    # starvation check

# In reproduction_component.py
min_energy = max_energy * 0.9
if energy >= min_energy:
    # can reproduce
```

Problems:
1. **Inconsistent thresholds**: Is critical 10%, 15%, or something else?
2. **Magic numbers**: Thresholds scattered without explanation
3. **Duplicate logic**: Same calculations repeated everywhere
4. **Testing difficulty**: Hard to test threshold behavior

## Decision

Introduce an **`EnergyState` value object** that encapsulates all energy thresholds:

```python
@dataclass(frozen=True)
class EnergyState:
    """Immutable snapshot of energy state."""
    
    current_energy: float
    max_energy: float
    
    @property
    def percentage(self) -> float:
        """Energy as 0.0-1.0 ratio."""
        return self.current_energy / self.max_energy
    
    @property
    def is_critical(self) -> bool:
        """Below 10% - emergency survival mode."""
        return self.percentage < CRITICAL_ENERGY_THRESHOLD_RATIO
    
    @property
    def is_hungry(self) -> bool:
        """Below 20% - should prioritize food."""
        return self.percentage < LOW_ENERGY_THRESHOLD_RATIO
    
    @property
    def can_reproduce(self) -> bool:
        """Has enough energy for reproduction."""
        return self.current_energy >= REPRODUCTION_MIN_ENERGY
    
    @property
    def is_saturated(self) -> bool:
        """At or above max capacity."""
        return self.current_energy >= self.max_energy
```

Usage:

```python
# Get snapshot once
state = fish.get_energy_state()

# Use semantic methods
if state.is_critical:
    self._enter_survival_mode()
elif state.is_hungry:
    self._seek_food()
elif state.can_reproduce:
    self._attempt_reproduction()
```

## Consequences

### Positive
- **Single source of truth**: All thresholds defined in one place
- **Semantic naming**: `is_critical` is clearer than `< 0.15`
- **Testable**: Can unit test threshold logic directly
- **Immutable**: Safe to pass around without defensive copying
- **Configurable**: Thresholds come from config constants

### Negative
- **Object allocation**: Creates new object each call (mitigated by caching if needed)
- **Migration effort**: Must update all energy checks to use pattern

## Migration Path

1. Create `EnergyState` with all threshold properties ✅
2. Add `get_energy_state()` to Fish ✅
3. Gradually migrate energy checks to use `EnergyState`
4. Remove deprecated inline calculations

## Related
- ADR-004: Component Composition (EnergyState is a value object)
- `core/config/fish.py` - Contains threshold constants
