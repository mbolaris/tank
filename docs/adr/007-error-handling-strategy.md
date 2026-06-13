# ADR-007: Error Handling Strategy

## Status
Accepted (2026-06)

## Context

The codebase accumulated **three overlapping error-handling styles with no
written rule** for choosing between them:

- `core/result.py` — a `Result`/`Ok`/`Err` type, used in only 2 modules
  (`state_machine.py`, `plant_manager.py`).
- `core/exceptions.py` — a `TankError` hierarchy, of which only
  `TransferError` was ever adopted (7 of 8 classes had zero usages).
- ~92 bare `raise ValueError` / `raise RuntimeError` sites doing the actual
  work of signalling domain failures.

Without a documented convention, contributors (human and AI agents) cannot
tell which mechanism to reach for. The result is inconsistent failure modes,
`except`-clauses that are either too broad (`except Exception`) or wrong, and
error handling that drifts with every change. That directly undermines the
project goal of **fewer bugs as the system is extended**.

## Decision

Use **two complementary mechanisms, each with a defined job**, plus a simple
deciding question.

### 1. Exceptions (`TankError` hierarchy) — for *exceptional* failures

Raise a narrow `TankError` subclass when continuing would be wrong and the
failure should **propagate up the stack**:

| Situation | Exception |
|---|---|
| Invalid configuration at startup (fail fast) | `ConfigurationError` |
| Invariant / precondition violation, "this should never happen" | `SimulationError` (or narrowest subclass) |
| Entity-level lifecycle/energy/movement failure | `EntityError` |
| Genome encode/decode/mutation failure | `GeneticsError` |
| Poker subsystem failure | `PokerError` |
| Cross-world transfer failure | `TransferError` |
| Save/load/snapshot failure | `PersistenceError` |

Rules:
- Prefer the **narrowest** subclass; never `raise Exception`.
- Use the hierarchy for **domain** errors so callers can `except TankError`
  (or one branch of it) precisely instead of guessing.
- Plain `ValueError`/`TypeError` remain appropriate for genuinely generic
  *argument* misuse (e.g. a helper handed the wrong type), not for domain
  conditions.

### 2. `Result[T, E]` — for *expected, recoverable* outcomes

Return `Ok`/`Err` when failure is a **normal, anticipated branch that the
immediate caller handles inline** — not something to bubble up:

- State-machine transitions (`StateMachine.transition` → already returns `Result`).
- Resource acquisition that routinely fails (`PlantManager.try_sprout`, e.g.
  no free root spot → already returns `Result`).
- Operations called in a hot loop where raising-and-catching would be costly
  or noisy.

### 3. `None` / empty — for trivial lookups

Idiomatic "not found" where the caller simply skips
(`get_system(name) -> System | None`). Do **not** wrap these in `Result`.

### The deciding question

> **Will the immediate caller almost always branch on the outcome right here?**
> → return a `Result`.
>
> **Does failure mean "stop and propagate up the stack"?**
> → raise a `TankError` subclass.

## Consequences

### Positive
- One written rule. Failure modes become predictable and greppable
  (`except TankError`).
- The exception hierarchy now has a defined purpose, so it gets adopted
  instead of decaying into unused classes.
- `Result` stays where it earns its keep (inline-handled, hot-path failures)
  rather than spreading everywhere or being abandoned.

### Negative
- ~91 existing generic `raise` sites need migration. This is done
  **incrementally and opportunistically** (when you touch a module), not as a
  big-bang rewrite.
- Two mechanisms means contributors must internalise the deciding question
  (mitigated by this ADR and the worked example below).

## Implementation notes

- **Reference example:** `SimulationConfig.validate()` now raises
  `ConfigurationError` instead of `ValueError`. Invalid config is a fail-fast
  startup condition — the canonical exception case.
- **Migration policy:** when editing a module, convert its *domain*
  `raise ValueError`/`raise RuntimeError` calls to the appropriate `TankError`
  subclass. No mass rewrite; no separate "fix all errors" PR.
- Do **not** delete the currently-unused `TankError` subclasses — this ADR
  gives them a job, and adoption is incremental.

## Related
- ADR-002: Protocol-Based Design
- `core/result.py` — the `Result`/`Ok`/`Err` implementation
- `core/exceptions.py` — the `TankError` hierarchy
