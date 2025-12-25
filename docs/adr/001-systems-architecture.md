# ADR-001: Systems Architecture

## Status
Accepted (2024-12)

## Context

The simulation originally used a monolithic `BaseSimulator` class that handled:
- Collision detection and response
- Entity lifecycle (birth, death)
- Reproduction logic
- Post-poker interactions
- Utility functions

This created several problems:
1. **High coupling**: Changes to one feature risked breaking others
2. **Poor testability**: Difficult to test individual behaviors in isolation
3. **Unclear responsibilities**: New developers couldn't easily understand what went where
4. **850+ lines** in a single file

## Decision

Adopt a **Systems Architecture** where:

1. Each system has ONE clear responsibility (Single Responsibility Principle)
2. Systems extend `BaseSystem` and implement `_do_update(frame)`
3. Systems declare which `UpdatePhase` they belong to
4. `SimulationEngine` orchestrates systems but doesn't implement game logic
5. Systems access shared state through the engine reference

**Current Systems:**
- `CollisionSystem` - Handles all collision detection and response
- `PokerSystem` - Manages poker games and post-poker reproduction
- `EntityLifecycleSystem` - Tracks births, deaths, entity cleanup
- `ReproductionSystem` - Manages asexual reproduction eligibility
- `SkillGameSystem` - Handles skill-based mini-games

## Consequences

### Positive
- **Testability**: Each system can be unit tested independently
- **Clarity**: New developers know exactly where to add new features
- **Flexibility**: Systems can be enabled/disabled without code changes
- **Maintainability**: Changes are localized to relevant systems

### Negative
- **Indirection**: Logic is spread across multiple files
- **Coordination**: Systems must coordinate through engine, adding some complexity
- **Learning curve**: Must understand the systems pattern to contribute

## Related
- ADR-003: Phase-Based Execution (how systems are ordered)
- ADR-004: Component Composition (how entities are structured)
