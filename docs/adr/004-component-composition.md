# ADR-004: Component Composition

## Status
Accepted (2024-12)

## Context

The `Fish` entity originally had all logic in one class:
- Energy management
- Lifecycle (aging, life stages)
- Reproduction
- Memory systems
- Skill games
- Visual effects

This led to:
- 800+ line class
- Difficult to test individual behaviors
- Hard to reuse logic for other entity types
- Merge conflicts when multiple developers worked on Fish

## Decision

Use **Component Composition** to break entity logic into focused components:

```python
class Fish(Agent):
    def __init__(self, ...):
        # Components handle specific concerns
        self._energy_component = EnergyComponent(max_energy, metabolism)
        self._lifecycle_component = LifecycleComponent()
        self._reproduction_component = ReproductionComponent()
        self._skill_game_component = SkillGameComponent()

        # Visual state is separate from domain logic
        self.visual_state = FishVisualState()
```

### Current Components

| Component | Responsibility |
|-----------|---------------|
| `EnergyComponent` | Energy storage, consumption, overflow |
| `LifecycleComponent` | Age tracking, life stages, death |
| `ReproductionComponent` | Mating, offspring creation |
| `SkillGameComponent` | Skill game strategies, stats |
| `FishVisualState` | Rendering effects (poker, birth, death) |

### Mixins for Protocol Implementation

For cleaner code organization, protocol implementations use mixins:

```python
class Fish(FishEnergyMixin, FishSkillsMixin, FishPokerMixin, Agent):
    ...
```

## Consequences

### Positive
- **Testability**: Components can be unit tested in isolation
- **Reusability**: Components can be shared (e.g., plants could use EnergyComponent)
- **Separation of concerns**: Visual state separated from domain logic
- **Smaller files**: Each component is <200 lines

### Negative
- **Indirection**: Must navigate to component to find logic
- **State synchronization**: Components must stay in sync with entity
- **Memory**: Each component is a separate object allocation

## Value Objects

For immutable snapshots, use frozen dataclasses:

```python
@dataclass(frozen=True)
class EnergyState:
    """Immutable snapshot of energy state."""
    current_energy: float
    max_energy: float

    @property
    def is_critical(self) -> bool:
        return self.percentage < 0.10
```

This pattern:
- Provides consistent energy thresholds across the codebase
- Enables safe sharing without defensive copying
- Documents the energy checking interface

## Related
- ADR-002: Protocol-Based Design (components implement protocols)
- ADR-005: Energy State Pattern (example value object)
