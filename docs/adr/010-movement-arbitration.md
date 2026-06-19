# ADR-010: Unify Movement Drive Arbitration

## Status

Accepted (2026-06). Implemented in two commits. Step 1 landed as designed (the
`MovementArbiter` over an ordered consideration list, byte-identical). Step 2's
*implementation* diverged from the original proposal below - see **Outcome**.

## Context

A fish decides where to move by resolving competing *drives* (flee a
predator, chase food, play poker, chase the soccer ball, explore). Today
that arbitration is **split across two stacked priority chains in two
files**, and the seam between them is a documented source of the
worst-class bug in the simulation.

**Outer chain** — `AlgorithmicMovement.move()` (`core/movement_strategy.py:100`):

1. explicit `movement_policy` override (`:110`)
2. **soccer ball pursuit** (`:131` → `_get_ball_pursuit_velocity`, `:267`)
3. genome code policy (`:137`)
4. composable behavior (`:141`)

**Inner chain** — `ComposableBehavior.execute()` (`core/algorithms/composable/behavior.py:91`):

1. threat response (`:113`)
2. food pursuit (`:121`)
3. poker engagement (`:133`)
4. social / exploration (`:139`)

Flattened, the *effective* priority order is:

```
policy override  >  BALL PURSUIT  >  code policy  >  THREAT  >  FOOD  >  poker  >  social
```

Note what straddles the seam: **ball pursuit (outer #2) outranks threat and
food (inner #1/#2).** A leisure minigame structurally outranks *survival*.

### The bug, and the tell

`CLAUDE.md` documents that this exact ordering drove **98% starvation
deaths** — the whole population converged on the ball at tank center and
starved beside uneaten food. The "fix" lives inside
`_get_ball_pursuit_velocity` (`movement_strategy.py:305`): an energy gate
that returns `None` unless `energy_ratio > 0.90`. That is not a fix of the
ordering; it is a **workaround** that smuggles "don't pre-empt food" into
the ball drive's activation condition. The mis-ordering is still there; it
has just been defanged for the specific case someone noticed.

This is the structural smell:

- **No single place answers "what does this fish want most?"** The order is
  encoded as control flow (statement/`if` order) split across two files.
- **Adding a drive means choosing a layer** and then reasoning about every
  cross-seam interaction by hand.
- **Workarounds accrete** at the seam (the energy gate) instead of fixes at
  the model.

> **Principle:** make the thing that varies *data, not control flow.* The
> set of drives and their priority should be a list you can read, reorder,
> and test in one place — not the order of `if` statements spread across
> modules.

## Decision

Introduce a single **Consideration**-based arbiter as the one place drives
compete. Each drive becomes a self-contained `Consideration` that knows its
own activation condition and desired velocity; one ordered registry selects
among them.

```python
# core/movement/considerations.py
from typing import Protocol
from core.math_utils import Vector2

class MoveContext:
    """Per-frame inputs an arbiter passes to each consideration."""
    is_critical: bool
    is_low: bool
    energy_ratio: float
    # ...resolved once per fish per frame

class Consideration(Protocol):
    name: str
    def desired_velocity(self, fish, ctx: MoveContext) -> tuple[float, float] | None:
        """Return a desired (vx, vy) if this drive is active, else None."""
        ...

class ThreatConsideration:
    name = "threat"
    def desired_velocity(self, fish, ctx):
        vx, vy, active = execute_threat_response(fish)
        if not active:
            return None
        m = energy_speed_modifier(fish, ctx)
        return (vx * m, vy * m)

class BallConsideration:
    name = "ball"
    # The 0.90 energy gate becomes an explicit, named precondition of the
    # drive — not a workaround buried in a velocity helper.
    def desired_velocity(self, fish, ctx):
        if ctx.energy_ratio <= PLAY_ENERGY_THRESHOLD_RATIO:
            return None
        return ball_pursuit_velocity(fish)
```

The arbiter is a thin, readable, ordered loop — the canonical priority list
lives in exactly one place:

```python
class PriorityArbiter:
    def __init__(self, considerations: list[Consideration]):
        self._considerations = considerations  # priority = order, as DATA

    def decide(self, fish, ctx) -> tuple[float, float] | None:
        for c in self._considerations:
            v = c.desired_velocity(fish, ctx)
            if v is not None:
                return v
        return None

# The corrected canonical order — survival before leisure:
DEFAULT_ORDER = [
    PolicyOverrideConsideration(),
    ThreatConsideration(),
    FoodConsideration(),
    BallConsideration(),       # now BELOW food, where it belongs
    PokerConsideration(),
    CodePolicyConsideration(),
    SocialConsideration(),
]
```

`AlgorithmicMovement.move()` collapses to: build `MoveContext`, call
`arbiter.decide()`, then the existing velocity smoothing / clamping /
anti-stuck tail (`movement_strategy.py:178-214`) unchanged.

### Arbitration semantics — two sub-options

- **Option 1 — priority-ordered, first-active-wins (recommended).** This is
  exactly today's semantics, just made explicit and data-driven. Low risk,
  fully deterministic, trivial to unit-test ("ball never pre-empts food":
  one assertion on the ordered list). Adopt this now.
- **Option 2 — utility-based scoring.** Each consideration returns a score
  in `[0,1]`; highest wins, with optional blending. More flexible and
  emergent, but a larger behavior change, harder to keep deterministic and
  tuned. **Defer** until there is a concrete need; the Consideration
  interface above can later return `(score, velocity)` without disturbing
  call sites.

## The critical constraint: determinism

Benchmarks are seeded and reproducible (a non-negotiable per `CLAUDE.md`),
and `ComposableBehavior` **consumes the RNG** (e.g. `poker_priority` draw at
`behavior.py:135`, exploration). **Any change to the order in which drives
are evaluated changes the order of RNG draws, which changes seeded
trajectories** — even when the logic is "equivalent." `CLAUDE.md` further
warns that `ecosystem_health` is trajectory-sensitive on a single seed.

This forces a **two-step migration that separates refactor from behavior
change** (also satisfying the repo rule to keep Layer-1 behavior changes
isolated):

1. **Behavior-preserving extraction.** Introduce the arbiter and
   considerations wired to reproduce *today's exact order*, including the
   ball-above-food ordering and the same RNG draw sequence. Acceptance:
   `benchmarks/` champions and determinism tests are **byte-identical**.
   This is pure structure — no scoreboard movement.
2. **The actual fix, measured.** As a *separate* commit, move
   `BallConsideration` below `FoodConsideration` and delete the `0.90`
   energy-gate workaround (its intent is now expressed by ordering).
   This *is* a behavior change: validate with `tools/validate_improvement.py`
   against the champion and run extra seeds (7, 123) per the
   `CLAUDE.md` seed-sensitivity guidance, not seed 42 alone.

## Consequences

**Positive**
- One readable, testable priority list; "survival outranks leisure" becomes
  a unit test, not a 30k-frame archaeology dig.
- Adding drive *N+1* = appending a `Consideration` at the right index — no
  cross-file reasoning, no new `if` in a hot method.
- Ball/soccer logic moves out of core movement into a soccer-owned
  consideration, reducing the minigame coupling flagged in the broader
  review.
- The energy-gate workaround disappears; intent lives in the ordering.

**Negative**
- A small per-frame indirection (iterate considerations vs inline `if`s).
  *Mitigation:* the list is short and fixed; keep `MoveContext` resolved
  once per frame as today.
- Step 2 reorders RNG consumption → seeded trajectories shift. This is
  expected and is the reason for the two-step split and multi-seed
  validation; it is a feature (the bug fix), not a regression, but it must
  be reported with reproduction command + seeds per project rules.

## Outcome (what actually shipped)

**Step 1** shipped as proposed: the `MovementArbiter` + considerations,
byte-identical to the historical if-chain (proven by an identical seed-42
headless run across all behavioral stat fields).

**Step 2** did *not* ship the "run the composable behavior first and reorder
ball below food" design above. That version was implemented and measured, and
it **regressed the canonical `ecosystem_health_10k` benchmark on seed 42**
(2.38 → 1.89) while improving seeds 7 and 123. The cause was exactly the
determinism risk this ADR flagged: forcing the composable behavior to run for
*every* fish every frame (to read its intent before deciding the ball) shifted
the global RNG stream far more than the logic change warranted, and seed 42 -
the champion seed - landed unlucky. Per the project bar ("wins or stays neutral
across seeds"), that is not a pass.

The shipped step 2 is a **more surgical** expression of the same intent: the
ball drive *yields* to survival instead of being reordered beneath it. A new
RNG-free predicate `ComposableBehavior.has_survival_priority(fish)` mirrors the
threat/food activation conditions, and `_get_ball_pursuit_velocity` returns
`None` when it is true. Crucially the check runs **after** the ball's existing
RNG draw, so the random stream is unchanged from step 1 - only the *outcome*
changes, and only for the small subset of fish that both rolled "play" and have
a live survival drive. The arbiter order (step 1) is untouched, so the
`execute_with_intent` / `MoveContext` machinery proved unnecessary and was not
shipped.

Result on `ecosystem_health_10k` (vs the step-1 baseline; reproduce with
`python tools/run_bench.py benchmarks/tank/ecosystem_health_10k.py --seed <s>`):

| seed | baseline | shipped | Δ score | max_gen |
|------|----------|---------|---------|---------|
| 42   | 2.377    | 4.792   | +2.42   | 4 → 6   |
| 7    | 2.011    | 5.666   | +3.66   | 3 → 7   |
| 123  | 2.506    | 3.087   | +0.58   | 4 → 4   |

All seeds improve, none regress; determinism verified (`--verify-determinism`).
The energy gate was **retained** (not deleted as the proposal suggested): with
ordering no longer the starvation safeguard, the gate's remaining job is a
legitimate one - keeping fish from burning reproduction-funding surplus on play.

**Lesson:** when a change's effect is small but it perturbs a determinism-
sensitive global RNG stream, prefer the implementation that minimizes the
perturbation (yield-after-draw) over the "cleaner-looking" one that reshuffles
evaluation order. Correctness of intent is necessary but not sufficient; the
seed-stability of the measurement is part of the design.

## Related
- [ADR-003: Phase-Based Execution](003-phase-based-execution.md)
- [ADR-007: Error-Handling Strategy](007-error-handling-strategy.md)
  (the silent `except` fallback at `movement_strategy.py:174` is in scope
  for the same cleanup)
- `CLAUDE.md` → "Ball pursuit pre-empts food seeking" and "ecosystem_health
  scores are trajectory-sensitive" gotchas
