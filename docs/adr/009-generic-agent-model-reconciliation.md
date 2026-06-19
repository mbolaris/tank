# ADR-009: Reconcile the GenericAgent Component Model

## Status

Accepted (2026-06) — supersedes part of [ADR-004](004-component-composition.md).
Implemented via **Option A** (delete the inert loop): the `perceive/decide/act`
scaffolding and the Perception/Locomotion/Feeding components were removed and
the docs amended. Behavior-neutral; `fast_gate` green.

## Context

ADR-004 established **component composition** as a core architecture
principle, and `CLAUDE.md` advertises agents as "built from reusable
components (perception, locomotion, feeding)." `GenericAgent`
(`core/entities/generic_agent.py`) presents a clean **sense → think → act**
loop backed by swappable components:

- `perceive()` (`generic_agent.py:260`) → builds a `Percept`
- `decide()` (`generic_agent.py:294`) → delegates to a `DecisionPolicy`
- `act()` (`generic_agent.py:314`) → applies the resulting `Action`
- `_update_common()` (`generic_agent.py:379`) → standard lifecycle tick
- components: `PerceptionComponent`, `LocomotionComponent`,
  `FeedingComponent` (plus `EnergyComponent`, `LifecycleComponent`,
  `ReproductionComponent`)

**The problem: the real entity uses almost none of this.** `Fish` is the
*only* subclass of `GenericAgent` (`fish.py:52`), and `Fish.update()`
(`fish.py:703`) reimplements the tick from scratch. It never calls
`perceive`, `decide`, `act`, or `_update_common`. Concretely:

| `GenericAgent` offers | What `Fish` actually uses instead |
|---|---|
| `perceive()` → `Percept` → `decide()` → `act()` | `BehaviorExecutor` → `AlgorithmicMovement` → `ComposableBehavior` |
| `PerceptionComponent` (wraps `AgentMemorySystem`) | `self.memory_system` directly (`fish.py:730`) |
| `FeedingComponent.consume_food()` / `can_eat()` | `Fish.eat()` (`fish.py:757`) with its own bite logic |
| `LocomotionComponent` direction/turn tracking | `BehaviorExecutor._last_direction` + `_apply_turn_energy_cost` |
| `_update_common()` energy/age/perception tick | bespoke body inside `Fish.update()` |

Two consequences make this worse than ordinary dead code:

1. **`PerceptionComponent`, `LocomotionComponent`, and `FeedingComponent`
   are never instantiated anywhere** in `core/` or `backend/`. Every call
   site in `GenericAgent` is guarded `if self._components.<x> is not None:`,
   and for the only real subclass they are always `None`.
2. **They are not just unused — they are divergent duplicates.** Each
   re-implements logic that already lives (and is maintained) on the Fish
   path. `FeedingComponent.can_eat()` uses a hardcoded `threshold=0.95`
   (`feeding_component.py:70`) that has no reason to match `Fish.can_eat()`,
   and nothing keeps them in sync.

### Why this matters (the architectural risk)

This is two parallel agent architectures wearing one name. The danger is
precisely the project's stated goal — *"fewer bugs as we extend."* A
contributor (human or AI) reads `GenericAgent`, sees an elegant
`perceive/decide/act` loop with a `FeedingComponent`, and writes a feature
against it. The feature type-checks, imports cleanly, has unit tests in
isolation… and never executes, because the real `Fish` path bypasses it.
The abstraction looks authoritative (it is the documented one, enshrined in
ADR-004) while being inert.

> **Principle:** an abstraction must have a real consumer. One concept
> deserves exactly one implementation; "two ways to be an agent" is a
> standing invitation for drift and mis-targeted code.

## Decision

Collapse to a single agent model. Two options are viable; **Option A is
recommended.**

### Option A — Delete the unused loop (recommended)

Make the documentation match reality and remove the inert layer.

**Remove:**
- `GenericAgent.perceive()`, `decide()`, `act()`, `_execute_eat()`
- The `DecisionPolicy` indirection (`_decision_policy`, `decision_policy`
  property) and the `Percept` / `Action` dataclasses in
  `generic_agent_types.py`
- `PerceptionComponent`, `LocomotionComponent`, `FeedingComponent` and
  their fields/accessors on `AgentComponents` and `GenericAgent`

**Keep** `GenericAgent` as an honest shared base: identity (`_agent_id`,
`get_entity_id`), and the energy / lifecycle / reproduction wiring that
`Fish` genuinely delegates to (`energy`, `modify_energy`, `is_dead`,
`can_reproduce`, `size`, `age`, `life_stage`).

Target shape of the slimmed container:

```python
@dataclass
class AgentComponents:
    """Components a GenericAgent delegates core state to."""
    energy: EnergyComponent | None = None
    lifecycle: LifecycleComponent | None = None
    reproduction: ReproductionComponent | None = None
    # perception / locomotion / feeding removed:
    # Fish owns memory_system, BehaviorExecutor, and eat() directly.
```

`GenericAgent` keeps `update()` abstract (it already is, `generic_agent.py:359`)
and drops the unused `perceive/decide/act` scaffolding. `Fish` is unchanged.

Then **amend ADR-004 and `CLAUDE.md`** to describe the architecture that
actually runs: Fish composes `EnergyComponent` + `LifecycleComponent` +
`ReproductionComponent` + `SkillGameComponent`, and delegates *behavior* to
`BehaviorExecutor` → `MovementStrategy` → `ComposableBehavior`. That is a
genuinely good design — it just isn't the `perceive/decide/act` one the
docs imply.

### Option B — Wire Fish through the components

Make the documented model real: route `Fish` perception through
`PerceptionComponent` (backed by its `memory_system`), eating through
`FeedingComponent`, and turn costs through `LocomotionComponent`; have
`Fish.update()` call the `perceive/decide/act` cycle.

This is the larger, riskier change:
- It touches the **per-frame hot path**. Building a `Percept` object every
  frame for every fish (allocating lists of `Vector2`) is almost certainly
  why the loop was bypassed originally; reintroducing it has a real
  performance cost in a simulation that runs tens of thousands of frames.
- The `ComposableBehavior` (384+ evolvable combinations) does not fit the
  `DecisionPolicy.decide(percept) -> Action` shape without adapter work —
  it reads rich fish/environment state, not a flattened `Percept`.
- It is behavior-affecting and must clear the determinism + champion
  benchmarks (see ADR-010 for the same RNG-ordering caveat).

## Consequences

### Option A (recommended)
**Positive**
- One agent model; the docs become true. New code can only target the path
  that runs.
- Removes ~3 divergent duplicate components (~380 LOC) and the
  `Percept`/`Action`/`DecisionPolicy` indirection.
- Zero runtime behavior change (deleting never-executed code) → provable by
  the existing determinism/champion suite staying green.

**Negative**
- Loses a speculative extension point. *Mitigation:* it can be reintroduced
  deliberately, with a real second agent type to justify it, instead of
  living unused. Git history preserves the design.
- Requires updating ADR-004 (a previously "Accepted" decision). That is
  healthy — an ADR superseded by reality is the system working.

### Option B
**Positive**
- The "component composition for behavior" principle becomes literally true
  and uniformly applied.

**Negative**
- Hot-path performance regression risk; larger surface; behavior-affecting
  (benchmark + determinism risk). High effort, uncertain payoff.

## Migration plan (Option A)

1. Delete the three unused components and their `AgentComponents` /
   `GenericAgent` accessors; delete `Percept`, `Action`, `DecisionPolicy`,
   and the `perceive/decide/act/_execute_eat` methods.
2. Drop the now-dead exports from `core/agents/__init__.py` and
   `core/agents/components/__init__.py`.
3. Grep-verify no remaining references (production or test).
4. Amend ADR-004 and the `CLAUDE.md` "component composition" line to
   describe the real Fish composition + `BehaviorExecutor` path.
5. **Verification:** `python tools/fast_gate.py` (full broad suite + mypy)
   must stay green. Because nothing deleted ever executed in the Fish path,
   `benchmarks/` champions and determinism tests must be byte-identical.

## Related
- [ADR-004: Component Composition](004-component-composition.md) (amended by this ADR)
- [ADR-002: Protocol-Based Design](002-protocol-based-design.md)
- [ADR-010: Unify Movement Drive Arbitration](010-movement-arbitration.md)
