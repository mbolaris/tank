# ADR-002: Protocol-Based Design

## Status
Accepted (2024-12)

## Context

Traditional inheritance hierarchies create tight coupling:
- Changes to base classes ripple through all subclasses
- Diamond inheritance problems
- Difficult to compose behaviors from multiple sources
- Hard to test components in isolation

Python's duck typing helps, but lacks:
- IDE autocomplete support
- Static type checking
- Documentation of expected interfaces

## Decision

Use **Protocol classes with `@runtime_checkable`** for all major interfaces:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class EnergyHolder(Protocol):
    """Entity that has and consumes energy."""

    @property
    def energy(self) -> float: ...

    @property
    def max_energy(self) -> float: ...

    def consume_energy(self, amount: float) -> None: ...
```

Key protocols in the codebase:
- `World` - Environment providing bounds and entity access
- `EnergyHolder` - Entities with energy systems
- `MigrationCapable` - Entities that can migrate between tanks
- `PokerPlayer` - Entities that can play poker
- `SkillfullAgent` - Entities with skill game capabilities
- `System` - Simulation systems interface

## Consequences

### Positive
- **Structural subtyping**: Any class matching the protocol works
- **Runtime checks**: `isinstance(obj, Protocol)` works with `@runtime_checkable`
- **IDE support**: Full autocomplete and type checking
- **Composition**: Classes can implement multiple protocols
- **Testability**: Easy to create mock implementations

### Negative
- **Runtime overhead**: `@runtime_checkable` adds small isinstance cost
- **Documentation**: Must maintain protocol docstrings separately
- **Partial compliance**: Easy to miss a method if not using type checker

## Implementation Notes

```python
# Good: Check protocol compliance
if isinstance(entity, EnergyHolder):
    entity.consume_energy(10)

# Good: Type hints for function parameters
def process_entity(entity: EnergyHolder) -> None:
    ...

# Avoid: Checking for specific class types
if isinstance(entity, Fish):  # Couples to implementation
    ...
```

## Related
- ADR-001: Systems Architecture (systems use protocols)
- ADR-004: Component Composition (components implement protocols)
