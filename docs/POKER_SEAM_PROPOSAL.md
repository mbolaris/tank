# Design Note: A Clean Seam for Poker

> **Status:** Proposal / design note (not yet an accepted ADR). Captures the
> architecture follow-up from the 2026-06 review. Poker is treated here as a
> **retained research pillar** — the goal is a better boundary, **not** less
> poker.

## The observation

Poker is the largest subsystem in the engine:

| Subsystem | LOC | Notes |
|-----------|-----|-------|
| `core/poker/` | ~11,350 | hand engine, betting, strategy, evaluation, human game |
| `core/mixed_poker/` | ~1,490 | plant-vs-fish poker |
| `core/algorithms/` (whole library) | ~7,355 | for comparison |
| `core/genetics/` | ~4,612 | for comparison |
| `core/simulation/` (the engine itself) | ~2,480 | for comparison |

More telling than the size is the **coupling**: outside `core/poker` and
`core/mixed_poker`, roughly **85 files** in `core/` mention poker — including
`core/genetics/*`, `core/evolution/*`, `core/config/poker.py`, the telemetry
layer, and the *generic* `SimulationEngine` constructor itself
(`enable_poker_benchmarks`, `benchmark_evaluator`, `poker_system`,
`poker_proximity_system`).

Contrast with **soccer**, which ADR-011 ("minigames out of core") already
disentangled: soccer logic lives in `core/minigames/soccer/`, and the tank
`SystemPack` *registers* a `SoccerSystem` and injects the ball/goals
(`core/worlds/tank/pack.py`). The generic engine knows almost nothing about
soccer. Poker never got this treatment — it predates the minigame seam and grew
inward.

## Why this matters (even though poker stays)

A pillar earns a *clean* boundary, not a free pass on entanglement. Today:

- **The generic engine is not generic.** `SimulationEngine.__init__` hard-codes
  poker benchmark wiring. A second world that doesn't play poker still drags it
  along, and anyone reading the engine must understand poker to understand the
  engine.
- **"Fewer bugs as we extend" is undercut.** Poker touches genetics, evolution,
  telemetry, reproduction, and movement. A change in any of those must reason
  about poker; a poker change can perturb all of them. The 2026-06 skills
  removal hit this directly — the post-poker reproduction path had drawn from
  the shared simulation RNG purely to feed a now-deleted cosmetic decision, so
  the removal had to *retain* that otherwise-vestigial draw as a determinism
  anchor to stay byte-identical (`reproduction_service._create_post_poker_offspring`).
  A minigame's cosmetic state should never have been coupled to the core RNG
  stream; the seam below is how it stops being.
- **It blocks the ADR-011 vision.** The codebase already decided minigames live
  outside core. Poker is the large exception that keeps that principle
  aspirational rather than true.

## The key tension: poker is *heritable*

Soccer was separable because it is pure mechanics — no soccer state lives in the
genome. Poker is different: **poker strategy is encoded in the genome and
evolves** (`core/genetics/behavioral.py`, `genome_codec.py`, the poker
sub-behavior params, `core/algorithms/poker.py`). That part is genuinely
core-domain — it is *what evolves*, the same way food-seeking behavior is.

So the seam is not "move `core/poker` to `core/minigames/poker`." It is a
**split** along the real fault line:

| Concern | Belongs | Today |
|---------|---------|-------|
| Heritable poker *strategy* (genes, params, mutation) | **Core domain** (near the genome) | scattered: genetics + `algorithms/poker.py` + `poker/strategy` |
| Poker *eligibility & interaction trigger* (proximity, cooldown) | **Core** (a thin port) | `systems/poker_proximity.py`, `Fish.can_play_poker` ✓ (already clean) |
| Poker *game engine* (hand engine, betting, showdown) | **Minigame** (behind a port) | `core/poker/simulation`, `core/poker/core` |
| Poker *evaluation/benchmark/human game/UI* | **Minigame / tooling** (out of core) | `core/poker/evaluation`, `human_poker_game.py` |

## Target shape

Introduce a single **`PokerInteraction` port** in `core/interfaces.py`: the
engine/sim depends only on "given N eligible agents, resolve a game and return
energy deltas + an outcome record." The implementation (hand engine, betting,
evaluation) lives behind that port and is *registered by the tank SystemPack*,
exactly as `SoccerSystem` is. Then:

```
core/
  interfaces.py            # PokerInteraction port (the only thing core knows)
  genetics/, algorithms/   # heritable poker STRATEGY stays here (it's what evolves)
  minigames/
    poker/                 # hand engine, betting, evaluation, human game (the MECHANICS)
worlds/tank/pack.py        # registers the poker system + injects config (like soccer)
```

The generic `SimulationEngine` loses its poker attributes and
`enable_poker_benchmarks` arg; a non-poker world is then genuinely poker-free.

## Incremental path (no big-bang, determinism-preserving)

Order matters — start where there is **no genome entanglement**, so each step is
byte-identical against the champions:

1. **Lift benchmark wiring out of the generic engine.** Move
   `benchmark_evaluator` / `enable_poker_benchmarks` from `SimulationEngine.__init__`
   into the tank `SystemPack` (pure infra; champions run poker-off, so this is
   byte-identical for them). *This is the cleanest first cut and proves the
   pattern.*
2. **Define the `PokerInteraction` port** and make `PokerSystem` /
   `PokerProximitySystem` depend on the port, not concretions.
3. **Relocate the mechanics** (`core/poker/simulation`, `core/poker/core`,
   `evaluation`, `human_poker_game.py`) under `core/minigames/poker/`, leaving
   the heritable strategy where the genome can reach it.
4. **Register via SystemPack**; delete the engine's residual poker attributes.

Each step is independently shippable and guarded by champion reproduction
(`tools/verify_all_champions.py`) — note that both tank champions set
`poker_activity_enabled: False`, so the *evolution-of-strategy* path is **not**
exercised by the champions. Add a poker-on benchmark before step 3 if you want
the relocation covered by reproduction, not just unit tests.

## What NOT to do

- **Don't shrink poker.** The user affirmed it as a research pillar; this note
  is about boundaries, not scope.
- **Don't move the heritable strategy out of core.** It is domain, not minigame.
- **Don't big-bang it.** The coupling took a long time to grow; unwinding it is
  opportunistic and test-backed, like the in-function-import and `getattr` debt
  in `ARCHITECTURE_REVIEW.md`.

## Related
- ADR-011 — minigames out of core (the precedent, applied to soccer)
- `docs/ARCHITECTURE_REVIEW.md` — Finding: poker altitude
- `docs/WORLDS.md` — SystemPack registration model
