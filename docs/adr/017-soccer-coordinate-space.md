# ADR-017: Canonical Soccer Coordinate Space

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08 |
| **Context** | [SOCCER_ARENA_DESIGN.md](../SOCCER_ARENA_DESIGN.md) §6.2, §10.4 |

## Context

Soccer match positions currently exist in whatever convention each consumer
finds convenient. The frontend renderer treats the field as metres centred at
the origin with `+y` pointing **down**, because that is what an HTML canvas
wants. Nothing states this anywhere; it is inferred from
`SoccerTopDownRenderer.buildSoccerScene`, which maps field metres straight into
scene pixels with no sign change.

That works exactly as long as there is one producer and one consumer. We are
about to have neither:

- The Soccer Arena adds a second, layered render path.
- Matches may be driven by tank policies, frozen reference policies, or
  **external RCSS clients** (see <https://github.com/rcsoccersim>).
- Replay and benchmark tooling read the same positions offline, where "down"
  is meaningless.

RCSS's own monitor protocol uses a field-centred metre space with its own
axis and angle conventions. If we adopt the canvas convention as the domain
truth, then every RCSS import must silently absorb a sign flip somewhere, and
the natural place for it to end up is scattered across the adapter, the policy
observation builder, and the renderer — three places that must agree and have
no test forcing them to.

The failure mode is specific and expensive: an imported team attacks its own
goal, turns the wrong way, or kicks with a mirrored angle. None of that is
visible in a static screenshot. It is visible only in motion, intermittently,
and it looks like a policy bug rather than a coordinate bug.

## Decision

**Define one canonical coordinate space for soccer, independent of any
rendering surface, and convert at explicit boundaries.**

### Canonical space

| Property | Value |
|---|---|
| Units | metres |
| Origin | field centre |
| `+x` | toward the **right** side's goal |
| `+y` | **north** (up, in the conventional mathematical sense) |
| Angles | radians, `0` along `+x`, increasing **counter-clockwise** |
| Range | `x ∈ [−length/2, +length/2]`, `y ∈ [−width/2, +width/2]` |

Canonical space is the domain truth. Match state, policy observations, replay
records, and benchmark output all use it.

### Boundaries

```
RCSS monitor/protocol ──[ RcssMonitorAdapter ]──┐
                                                 ├──▶  CANONICAL  ──[ renderFromCanonical ]──▶ render space
Tank match engine ─────[ TankMatchAdapter ]─────┘         ▲                                     (+y down, CW angles)
                                                          │                                              │
                                          replay, benchmarks, policy observations          [ fitTransform ] ──▶ css px
```

Three rules:

1. **Production adapters convert *to* canonical, never to render space.** An
   adapter that knows about pixels is a bug.
2. **`renderFromCanonical` is the only place the `y` sign flips**, and the only
   place angle handedness changes. It is one function, in one file.
3. **Pure coordinate utilities may be bidirectional** —
   `legacy_to_canonical()` / `canonical_to_legacy()` — for validation and for
   the render boundary. They know about coordinates and nothing else: no
   pixels, no canvas dimensions, no DPR, no layout. The round-trip test applies
   to these utilities, not to the one-way production adapter.

Below that boundary, all drawing code continues to assume `+y = down` exactly
as it does today. The render path pays nothing for this decision.

### Migration

`SoccerMatchState` carries `coord_space?: 'canonical' | 'legacy_render'`. When
absent, consumers assume `'legacy_render'` — the current implicit convention —
so nothing breaks on day one. The backend starts emitting `'canonical'` when
the adapter lands; the existing panel keeps working throughout.

## Consequences

**Positive**

- An RCSS-driven match becomes a data-source swap. The adapter is the only new
  code; render, layout, scoreboard, and lineup are untouched.
- The convention is stated once, testably, instead of being inferred from a
  renderer.
- Offline consumers (replay, benchmarks, `scripts/`) get a convention that
  makes sense without a canvas in the picture.
- Sign errors become test failures rather than intermittent visual weirdness.

**Negative**

- One extra transform step, and a period where both conventions exist on the
  wire behind `coord_space`.
- Contributors must know which side of the boundary they are on. Mitigated by
  naming: anything in canonical space is typed `CanonicalPoint`, anything below
  the boundary is `RenderPoint`.

**Neutral**

- No change to stored data or to any champion. This is a wire and module-graph
  decision, not a simulation one; match results are unaffected.

## Verification

Required by [SOCCER_ARENA_DESIGN.md](../SOCCER_ARENA_DESIGN.md) §10.5:

- Golden **engine** fixture tests — hand-checked deterministic engine snapshots
  adapted through `tank_adapter.py`, asserting canonical positions, headings,
  and ball velocity. Monitor-protocol `(show ...)` fixtures belong with the
  RCSS adapter, not here: `core/minigames/soccer/fake_server.py` emits
  player-facing `(see ...)` / `(sense_body ...)`, not monitor frames.
- Attack-direction test per side, surviving the half swap.
- Round-trip on the pure utilities:
  `canonical_to_legacy(legacy_to_canonical(p)) ≈ p`.
- Handedness test asserting counter-clockwise in canonical and clockwise on
  screen, named so the two cannot be confused.

## Alternatives Considered

**Adopt `+y = down` as canonical.** Simplest today — zero conversion for the
existing renderer. Rejected: it bakes a canvas convention into the domain
model, forces every non-render consumer to reason in screen terms, and pushes
the RCSS sign flip into adapters where no single test can pin it down.

**Convert inside each adapter to render space directly.** Fewer hops.
Rejected: it multiplies the number of places that know the flip by the number
of adapters, which is precisely the failure this ADR exists to prevent.

**Defer until RCSS integration actually starts.** Rejected: the arena's render
path, event contracts, and fixture tests are being written now. Retrofitting a
coordinate boundary through them later costs far more than declaring it first.
