# ADR-013: Collapse the GenericAgent State Layer

## Status

Accepted (2026-06). Extends [ADR-009](009-generic-agent-model-reconciliation.md)
from the *behavior* layer to the *state* layer. Implemented via **Option A**
(delete the shadowed duplicate). Behavior-neutral: `mypy` clean, `fast_gate`
green (1736 passed), seed-42 headless state byte-identical before/after.

## Context

ADR-009 collapsed a duplicated **behavior** model (the `perceive/decide/act`
loop and the `Perception`/`Locomotion`/`Feeding` components were inert
duplicates of the real `Fish` path). The *same pattern* survived one layer
down, in **state**.

`Fish` is declared (`core/entities/fish.py`):

```python
class Fish(EnergyManagementMixin, MortalityMixin, ReproductionMixin, GenericAgent):
```

Both sides defined the **same members**:

| Member | `GenericAgent` | Mixin (`core/entities/mixins/`) |
|---|---|---|
| `energy` / `max_energy` / `size` | ✓ | ✓ `EnergyManagementMixin` |
| `modify_energy` | ✓ | ✓ `EnergyManagementMixin` |
| `is_dead` | ✓ | ✓ `MortalityMixin` |
| `can_reproduce` | ✓ | ✓ `ReproductionMixin` |

Because the mixins precede `GenericAgent` in the MRO, **the mixins win**, and
`Fish` is the *only* `GenericAgent` subclass. So `GenericAgent`'s versions of
these members **never executed for any real entity**.

This was worse than ordinary dead code, for the reason ADR-009 names:

1. **The component *objects* are shared** (`Fish._create_components()` wraps the
   same `EnergyComponent`/`LifecycleComponent`/`ReproductionComponent` the
   mixins use), so *state values* stayed consistent and nothing visibly broke.
2. **The *logic* had already diverged.** `EnergyManagementMixin.modify_energy`
   routes overflow energy into the reproduction bank and spawns food — this is
   load-bearing ("reproduction is funded by overflow energy"). The shadowed
   `GenericAgent.modify_energy` simply **clamped to `max_energy` and dropped the
   overflow.** `is_dead` and `can_reproduce` were exact duplicates.

The danger is precisely *"fewer bugs as we extend."* The correct path won only
by MRO ordering. Reordering Fish's bases, deleting a "redundant" mixin, adding a
second agent type that forgets a mixin, or a single `super().modify_energy()`
call would silently swap reproduction onto the lossy path — a population/birth
regression that benchmarks would misattribute.

Separately, `GenericAgent.update` was marked `@abstractmethod` but the class did
**not** inherit `ABC`/use `ABCMeta`, so the abstractness was *decorative*:
Python would happily instantiate an incomplete subclass.

> **Principle (restated from ADR-009):** one concept deserves exactly one live
> implementation. A second, authoritative-looking copy that is shadowed and
> silently divergent is a standing invitation for drift and mis-targeted code.

## Decision

Mirror ADR-009 **Option A**: delete the inert, divergent copy and keep the one
that runs.

**Removed from `GenericAgent`:** `energy` (getter/setter), `max_energy`, `size`,
`modify_energy`, `is_dead`, `can_reproduce`; and the now-unread `energy` field on
`AgentComponents` (plus the `EnergyComponent`/`EntityState` imports that only it
needed).

**Kept** as the honest shared surface `Fish` genuinely inherits: identity
(`get_entity_id`, `snapshot_type`), the *non-shadowed* lifecycle accessors
(`life_stage`, `age`), `reproduction_component`, `components`, and the abstract
`update`. `AgentComponents` now declares only `lifecycle` and `reproduction`.

**Made abstractness real:** `class GenericAgent(Agent, ABC)`, so `update` is
enforced at instantiation.

Energy/mortality *policy* is now unambiguously **owned by the subclass** (`Fish`
via its mixins), not the generic base. `Fish` is otherwise unchanged.

### Why this was safe to delete (verification)

- Nothing in `core/`/`backend/` is typed as `GenericAgent`, and it claims no
  energy/mortality protocol — call sites use `Fish` or structural protocols.
- No `super().modify_energy()` / `super().is_dead()` / `super().can_reproduce()`
  calls exist; the three mixins are self-contained.
- `AgentComponents` is never serialized; no reader of `.components.energy`
  exists. (The one `.components.poker_stats` reader is `hasattr`-guarded and
  already always falls through — noted as a separate pre-existing issue.)

## Consequences

**Positive**
- One live implementation per concept. The latent reproduction-break is gone.
- `GenericAgent` is honest and genuinely abstract; the docs (CLAUDE.md,
  ARCHITECTURE.md) already describe this real shape.
- ~90 LOC of inert/divergent code removed; zero runtime behavior change, proven
  by an identical seed-42 headless run and the determinism suite.

**Negative**
- `GenericAgent` no longer offers a default energy implementation for a
  hypothetical non-`Fish` subclass. This is intentional: energy *policy* is a
  subclass concern. A future second agent type adds its own path deliberately
  (see Step 2), rather than silently inheriting a divergent default.

## Follow-up (Step 2 — investigated; layering kept)

The original draft of this ADR proposed a further step: `Fish` also carries the
inheritance **mixins** (`EnergyManagementMixin`, `MortalityMixin`,
`ReproductionMixin`) *and* the **components** they use, so "retire the mixins in
favor of components." Close inspection showed that was the wrong call:

- The two are a **layering, not a duplicate model.** The components are pure
  state + math/rules with no `Fish`/`world` coupling (independently
  unit-testable); the mixins are Fish/world *policy* over them (overflow →
  reproduction bank → food drop, migration, offspring via `ReproductionService`).
  The mixins **delegate** to the components — they do not re-implement them.
- The mixin policy **cannot** move down into the components without coupling
  them to the world (it spawns `Food`), which would defeat their testability.
  And the components are not shared (Plant has its own `Plant*Component` family),
  so there is no reuse pressure forcing a merge.
- "Retiring the mixins" therefore means inlining ~520 lines into an already
  809-line `fish.py` (~1300 lines) — strictly worse, for no dedup.

So Step 2 was reduced to a **targeted cleanup** (done): delete the one genuinely
dead duplicate in the layer — `EnergyManagementMixin._apply_energy_gain_internal`,
an uncalled re-implementation of `modify_energy`'s overflow path — and make the
mixin/component docstrings state the policy-vs-state split and the Fish-only
nature explicitly, so the layer is not mistaken for reusable infrastructure or a
second model. The layering itself is **intentional and retained**.

## Related
- [ADR-009: Reconcile the GenericAgent Component Model](009-generic-agent-model-reconciliation.md) (extended by this ADR)
- [ADR-004: Component Composition](004-component-composition.md)
- [ADR-002: Protocol-Based Design](002-protocol-based-design.md)
