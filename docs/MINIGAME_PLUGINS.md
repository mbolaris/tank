# Minigames as Plugins, and Making Fun Pay for Itself

> **Status**: Proposal (July 2026). Pre-implementation design. Covers two linked
> ideas: (1) promoting minigames (poker, soccer) from residents of `core/` into a
> first-class **plugin API**, and (2) fixing the energy economy so entertainment is
> **net-positive for evolution** instead of taxing it. Builds on
> [ADR-011](adr/011-minigames-out-of-core.md) and the "Entertainment as Utility"
> principle in [VISION.md](VISION.md).

---

## Why This Matters

Poker and soccer are not decoration and they are not scope creep — they are the
**adoption engine**. The ALife hobbyist community grows through moddability
(NetHack, Dwarf Fortress, and Screeps all prove that a moddable substrate outlives a
finished product), and casual players stay because emergence is *fun to watch*. A
person who would never touch an evolution engine will happily write a new game for
their fish.

But right now the minigames sit in an awkward place:

1. **They live in `core/`** even though ADR-011 says minigames belong outside it. The
   architecture tests (`test_arch_soccer_engine_encapsulation`,
   `test_engine_no_tank_imports`) already push in the right direction — the seam is
   half-built.
2. **They fight evolution instead of feeding it.** Per the project's own guidance in
   `CLAUDE.md`: ball play and poker burn the *overflow* energy that funds
   reproduction. So today, the more fun a fish has, the fewer offspring it leaves —
   and the `ecosystem_health` benchmark punishes exactly that. Every Layer 1 agent
   optimizing benchmarks is therefore being trained to **evolve fish that ignore the
   fun parts.** That is the opposite of what the product needs.

This document proposes fixes for both.

---

## Part 1: The Minigame Plugin API

### Goal

Turn "minigame" into a real extension point so that poker and soccer become the
**first two plugins**, not special cases baked into the engine. A third-party author
should be able to add a new game — races, foraging contests, mazes, mating
displays — without editing `core/`.

### The `MinigameProtocol` seam

Define a protocol (in the spirit of [ADR-002](adr/002-protocol-based-design.md)) that
a minigame implements to participate in a tick:

```python
class MinigameProtocol(Protocol):
    id: str                       # stable, namespaced, e.g. "core.poker"

    def eligible(self, world: WorldView) -> Sequence[ParticipantSet]:
        """Which fish, if any, can start/continue a game this frame."""

    def step(self, session: MinigameSession, rng: Random) -> MinigameOutcome:
        """Advance one session deterministically. No engine mutation here."""

    def settle(self, outcome: MinigameOutcome) -> Sequence[EnergyDeltaRecord]:
        """Translate results into energy deltas routed through the
        existing mutation/energy-delta queues — never direct mutation."""
```

Design rules, all consistent with the current architecture:

- **Registration via entry points**, so plugins are discovered without `core/`
  importing them. This is the natural extension of the `SystemPack` /
  `WorldRegistry` factory pattern.
- **Determinism preserved.** A minigame receives an RNG derived from the engine seed
  and must be reproducible; its conformance test mirrors
  `test_soccer_match_runner_determinism`.
- **No engine mutation inside the game.** Outcomes become `EnergyDeltaRecord` /
  spawn/remove requests routed through the existing central queues — honoring
  Guiding Rule 2 (all spawns/removals go through central queues).
- **Sealed-mode safe.** Minigames run in both Sealed and Open mode (see
  [FEDERATION.md](FEDERATION.md)); nothing about a game may depend on wall-clock or
  network state.

### Migration path (poker & soccer become plugins)

The refactor is mostly *relocation behind a boundary already tested for*:

- [ ] Extract a `minigames/` plugin surface with the protocol + registration.
- [ ] Move `core/algorithms/poker.py` game logic and `core/minigames/soccer/`
      behind the protocol; leave only the thin participant hooks fish need.
- [ ] Convert existing arch tests into **plugin-boundary tests**: `core/` must not
      import any concrete minigame (extends `test_engine_no_tank_imports` and
      `test_no_concrete_entity_imports_in_infra`).
- [ ] Publish a `docs/examples/minigame_plugin/` reference plugin (a trivial game)
      as the copy-paste starting point for contributors.

The result: my earlier "scope sprawl" critique inverts into a **feature**. The
periphery stops diluting the core and becomes the community's contribution surface.

---

## Part 2: Make Fun Net-Positive (the Energy Economy Fix)

### The problem, precisely

Reproduction is funded by *overflow* energy — energy banked above `max_energy`
(`CLAUDE.md`, "Reproduction is funded by overflow energy"). Minigames currently
*spend* that surplus:

- Soccer/ball play burns energy for movement with no reward path back into the bank.
- Poker redistributes energy between players but is, in aggregate, a drain relative
  to foraging time.

So a fish optimizing for offspring should **avoid minigames entirely**, and any
benchmark that rewards generation turnover will select for exactly that avoidance.
Entertainment and fitness are pulling in opposite directions.

### The fix: positive-sum games with rewards routed to the reproduction bank

Redesign each minigame so that *participation and skill are, on average, energy
non-negative and can be net-positive*, with winnings routed into the overflow bank
that funds reproduction:

1. **Poker already has settlement.** Keep the redistribution, but make the *pot*
   partially funded by an ecosystem source (e.g. a "table rake in reverse" — a small
   energy subsidy for playing well) so that skilled play grows the reproductive
   surplus rather than merely shuffling it. Losers should not be driven below the
   safe threshold by a single hand.
2. **Soccer needs a reward path.** Goals, assists, and possession translate to
   shaped rewards (the `test_soccer_shaped_rewards` scaffolding already exists) that
   settle as `EnergyDeltaRecord`s into the winner's bank. Winning a match should be a
   *reproductive advantage*, not an energy tax.
3. **Skill becomes heritable fitness.** Because `poker_engagement` and the relevant
   traits are in the genome, positive-sum games mean natural selection can actually
   favor *good players* — which is far more entertaining to watch than selection
   favoring players who abstain.

### Guardrails so the fix doesn't wreck the ecosystem

- **Conservation by default.** The ecosystem's total energy budget must remain
  bounded; minigame subsidies draw from a defined source (e.g. a portion of plant
  nectar / a capped per-frame pool), not from nothing. A test asserts the global
  energy ledger stays within bounds (extends `test_energy_accounting`).
- **No starvation spiral.** A fish cannot be pushed below the safe threshold purely
  by losing minigames; losses are capped relative to current energy.
- **Tune against multiple seeds.** Per `CLAUDE.md`, `ecosystem_health` is
  trajectory-sensitive on a single seed — validate any reward change on seeds 42, 7,
  and 123 before trusting it.

### A benchmark that rewards fun *and* health

The core mechanism keeping this honest is measurement. Add an **engagement × health**
benchmark so the Layer 1 loop can no longer improve fitness by making fish boring:

- **Health component**: existing `ecosystem_health` signals (max_generation,
  population stability, diversity).
- **Engagement component**: minigame participation rate, decisiveness (games reach
  outcomes rather than stalling), and skill spread across the population.
- **Scored jointly** so a candidate that boosts generation turnover by killing all
  play *loses*. This directly encodes "Entertainment as Utility" from
  [VISION.md](VISION.md) into the selection pressure itself.

Record its champion in `champions/tank/` once the reward economy stabilizes.

---

## Sequencing

Ordered by urgency and by what unblocks what:

1. **Energy economy fix + engagement×health benchmark** — *do this first.* It is
   cheap and it is actively distorting evolution right now; every day it waits, the
   benchmark trains fish to be duller.
2. **Minigame plugin API** — unlocks community contribution and completes ADR-011.
3. **Reference plugin + docs** — lowers the barrier for the hobbyist audience.
4. **Federated minigame highlights** — poker/soccer results become shareable lineage
   stories across tanks (see [FEDERATION.md](FEDERATION.md)).

None of this sacrifices the discipline that makes Tank World credible: the plugin
boundary and the reward ledger get the same **enforced-by-test** treatment as the
import rules and phase order do today.

---

## Relationship to Existing Docs

- [ADR-011](adr/011-minigames-out-of-core.md) — the decision this implements.
- [VISION.md](VISION.md) — "Entertainment as Utility" and "Evolving Visualization".
- [FEDERATION.md](FEDERATION.md) — how game results travel across tanks.
- [SOCCER_INTEGRATION_GUIDE.md](SOCCER_INTEGRATION_GUIDE.md) — current soccer wiring.
- `CLAUDE.md` — the overflow-energy and single-seed-noise gotchas this must respect.

---

*Last updated: July 2026*
