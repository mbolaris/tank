## Design Guidelines (concise)

Goal: keep the codebase easy to understand, extend, test, and refactor.

- Single Responsibility: modules should have one clear responsibility.
- Explicit Public API: expose a small surface via `__all__` in packages.
- Small Interfaces: prefer focused Protocols/ABCs over large monoliths.
- Dependency Injection: pass collaborators (rng, world, logger) into constructors.
- Immutability for messages: use dataclasses/frozen for events & payloads.
- Composition over inheritance: prefer small mixins and composition for behavior.
- Type Safety: use Protocols and run mypy on `core/`.
- Tests as safety net: fast unit tests for deterministic parts (seeding, serialization).

Small, safe next steps:
- Introduce explicit `__all__` for major packages (core, core.algorithms, core.entities).
- Add a `mypy.ini` and opt-in strictness for `core/`.
- Add tests for deterministic seeding of `SimulationEngine`.
- Use dependency injection for RNG in simulation constructors.
