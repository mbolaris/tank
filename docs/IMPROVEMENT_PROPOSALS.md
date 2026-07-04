# Improvement Proposals

> A living, prioritized backlog of high-leverage improvements for Tank World.
> Each proposal names **what's interesting**, **why it matters**, and a concrete
> **implementation plan**. Pick one, open a PR, check it off.

This document complements [ROADMAP.md](ROADMAP.md). The roadmap tracks the
strategic milestones (the Evolution Loop MVP, meta-evolution, etc.);
this file tracks the *engineering* work that makes the codebase more fun to
use and a better example of software design.

**How to use it:** proposals are grouped by theme and tagged with effort
(S / M / L) and impact (★ low → ★★★ high). Start with high-impact, low-effort
items. When you complete one, move it to the "Shipped" section at the bottom
with the PR link.

**For smaller / less expensive agents:** every proposal below names the exact
files to touch and a step-by-step plan, so you can pick one and follow it
literally without holding the whole codebase in your head. Prefer the `S`
(small) items tagged **Layer 2** — they don't change simulation results, so
they can't regress a champion, and `pre_pr_gate` is enough to prove them safe.
Good first picks right now: **4.2** (`scripts/diagnose.py`), **4.3** (algorithm
catalog), **1.5** (benchmark budgets), **6.2** (retire `Any` in one module).
Follow the recipe in [AGENT_FIELD_GUIDE.md](AGENT_FIELD_GUIDE.md) — one focused
change per PR.

> **Themes 6–8 come from an external code review (2026-07, overall 82/100).**
> The review praised the vision, architecture, test discipline, and determinism
> policy, and located the remaining rough edges in *type safety, frontend
> contracts, performance confidence, and product-facing meaning* — which is
> exactly what those themes turn into concrete, pickup-able tasks. Counts cited
> in them (`Any` usage, file lengths, test-file ratio) were re-measured against
> the tree when the tasks were written; re-check before trusting a stale number.

---

## The Crown Jewels (what makes this project special)

Before changing anything, it's worth naming what is genuinely novel here, so we
protect it while we improve everything around it.

1. **Git as the heredity mechanism.** PRs are mutations, CI is natural
   selection, merged commits are offspring. The evolutionary validation loop
   (`benchmarks/` → `champions/` → `tools/validate_improvement.py` → CI) is the
   single most important asset in the repo. Every other improvement should make
   this loop *easier to trust and faster to run*, never weaker.

2. **Composable behaviors over black boxes.** `ComposableBehavior`
   (`core/algorithms/composable/`) factors fish behavior into four orthogonal,
   genetically-tuned dimensions — threat response, food approach, social mode,
   poker engagement. It is interpretable, debuggable, and evolvable. This is a
   far more elegant design than a neural-network policy soup, and it is the
   reason an AI agent can reason about *why* a strategy wins.

3. **Determinism as a first-class invariant.** Seeded RNG threaded through every
   system, a record/replay harness (`--record` / `--replay`), and
   double-run determinism checks in CI. Reproducibility is what turns "the
   number went up" into a scientific claim.

4. **A full Texas Hold'em engine with CFR learning inside an ALife sim.** Fish
   play poker for energy and inherit learned regret tables
   (`core/poker/strategy/composable/`). This is a wild, delightful idea that
   doubles as a second evolutionary substrate.

5. **Multi-world backend.** The same genetics and agents render as a fish tank,
   a petri dish, or a soccer pitch (`core/worlds/`, `core/modes/`). One
   evolutionary core, many selection pressures.

Keep these legible and they remain the project's best advertisement.

---

## Theme 1 — Make the evolution loop bulletproof

The loop is the crown jewel; these harden it.

### 1.0 Cross-machine trajectory divergence in ecosystem_health_10k — `M` · ★★★
**The most important open determinism problem.** A reverted improvement
(quality-weighted food targeting, see PR #589) produced trajectories that were
bit-stable locally but diverged on CI - and CI diverged run-to-run (9.098252
locally on Python 3.10 AND 3.11 and under both glibc SIMD/non-SIMD libm
variants; 8.977621 and 8.850779 on two consecutive CI runs of identical code).
Current master's trajectories are robust (champions reproduce exactly locally
under both libm variants and on CI repeatedly), so the registry is safe today -
but the property is fragile: some trajectories sit near knife-edges that
machine-dependent float details flip.

**Evidence gathered so far** (PR #589 investigation):
- Not interpreter version (3.10 == 3.11 locally, bit-exact).
- Not numpy (core/ uses no numpy at all).
- Not glibc ifunc/SIMD libm dispatch alone (GLIBC_TUNABLES hwcaps off:
  raw sin/cos/exp digests change, but the benchmark score does not).
- CI run-to-run instability on identical code means a per-machine or
  per-run environment input reaches the trajectory. Suspects to bisect:
  wall-clock leakage (e.g. core/minigames/soccer/league/provider.py caches
  by time.time(); engine.start_time), runner CPU model differences, glibc
  version differences between runner images.

**Plan.** Add a fingerprint-dump mode to the replay harness that records a
per-frame (or every-100-frames) fingerprint stream as a CI artifact; run it on
CI twice and locally, diff to find the first divergent frame, inspect that
frame's code path, eliminate the environment input. Then re-land the
food-targeting improvement (the revert preserved it in git history at
e1fed26; it beat both tank champions on every local environment).

**Instrumentation status.** Benchmark fingerprint streams now record exact and
6-decimal-rounded snapshot hashes, entity-type component hashes/counts, and an
environment manifest every 100 frames. Ecosystem champion verification runs
twice, compares the streams within CI, and uploads both streams for comparison
with local runs. Use `tools/compare_fingerprint_streams.py` to report the first
exact and rounded divergent frames.


### 1.2 Score decomposition in benchmark output — `S` · ★★
**Problem.** `survival_5k` reports a single opaque scalar
(`avg_energy * avg_pop / 1000`). Agents can't tell whether to optimize energy or
population.

**Plan.** Have benchmarks emit a `score_breakdown` dict alongside the scalar
(e.g. `{"energy": ..., "population": ..., "stability": ...}`), and surface the
weakest component in `validate_improvement.py` output. No scoring change — just
visibility.

### 1.4 Multi-seed validation for the AI agent — `M` · ★★
**Problem.** `scripts/ai_code_evolution_agent.py` validates a proposed change on
a single short run, where natural variance dwarfs the improvement signal.

**Plan.** Validate across ≥3 seeds, report mean ± stddev, and require the change
to beat the champion in a majority of seeds. Run `pytest -x` and `mypy` on the
edited files *before* committing so the agent never pushes a syntax/import
break.

### 1.5 Publish benchmark runtime budgets — `S` · ★★
**Problem (external review, 2026-07).** A reviewer could not tell whether a
benchmark was hanging or just slow: "could not complete the 5k survival
benchmark in this sandbox, and the full suite timed out." For an evolution
platform, benchmark reproducibility needs to be *boringly obvious*.

**Plan.** Record an expected wall-clock budget for each live benchmark (short /
medium / 5k) and surface it. Concretely: add a `expected_runtime_s` field (or a
short table in `benchmarks/README.md`) for `survival_5k`,
`ecosystem_health_10k`, and the soccer trainings, measured on a known machine,
and have `tools/run_bench.py` print `elapsed 41.2s (budget ~45s)` when it
finishes. No scoring change — pure "is this normal?" visibility. **Layer 2.**

### 1.6 One health command that works from a clean checkout — `M` · ★★
**Problem (external review, 2026-07).** The review's #1 next move: "make one
clean health command work everywhere" — `tools/smoke_gate.py` should install/
resolve the tools it needs and pass from a fresh checkout, instead of assuming
black/ruff/mypy/node are already present. The reviewer's gate run failed only
because tools weren't installed, not because code was wrong.

**Plan.** Make `tools/smoke_gate.py` (or a thin wrapper it calls) detect missing
dev tools and either install them or print the exact one-liner to do so, so a
green run is achievable from `git clone` + one command. Pairs naturally with
4.2 (`scripts/diagnose.py`) — diagnose reports, this one repairs. **Layer 2.**

---

## Theme 2 — Tame the god files

All three planned splits shipped (see the Shipped section), plus two more that
turned out to be the worst offenders: `core/ecosystem.py` and
`backend/simulation_runner.py`. Future splits should follow the same pattern:
extracted collaborators + thin delegating facades, verified by the full fast
gate and exact champion reproduction.

## Theme 3 — Consolidate the algorithm library

### 3.1 Stage 2: remove deprecated food-seekers + re-baseline — `M` · ★★
Stage 1 shipped (see Shipped + ADR-006): benchmark data collected, KEEP/
DEPRECATE decided, `DEPRECATED_ALGORITHMS` metadata added. Stage 2, one
bundled change: port the three winners' tactics (quality-weighted targeting,
opportunistic switching, shared-target avoidance) into the composable
framework, remove the 11 deprecated modules, drop monoliths from
`ALL_ALGORITHMS`, fix the 3.2 bounds-table drift for survivors, and
re-baseline all champions in the same PR.

### 3.2 Bounds-table drift: 11 algorithms mutate unbounded parameters — `S` · ★★
**Found while shipping the ParameterRegistry** (see Shipped): 11 algorithms have
runtime parameters with no (or mismatched) entries in
`ALGORITHM_PARAMETER_BOUNDS`, so those parameters mutate via the unbounded
fallback (floor 0.0 only) and have no design range to clamp to. Worst cases:
`AggressiveHunter` and `SpiralForager` (no table entry at all),
`CircularHunter` (table names don't match its actual params). Partial misses:
CooperativeForager, EnergyConserver, FreezeResponse, OpportunisticFeeder,
OpportunisticRester, PerpendicularEscape, SurfaceSkimmer, VerticalEscaper.

**Decision needed**: declaring bounds changes the mutation math (span-based vs
scale-based) and therefore seed-42 trajectories - champions must be
re-baselined in the same change. Bundle this with 3.1's algorithm
consolidation so the ecosystem only pays the re-baseline cost once.

---

## Theme 4 — Developer & observer experience (the "fun" budget)

This is where "fun to use" and "excellent example of software design" are won.

### 4.2 `scripts/diagnose.py` health check — `S` · ★★★
One command that verifies the environment and prints a green/red checklist:
Python deps importable, core modules load, a 100-frame sim initializes, frontend
deps installed. Turns "it's broken somewhere" into a precise pointer.

**Concrete steps for a small agent.** Create `scripts/diagnose.py` that runs an
ordered list of independent checks, each printing `✅`/`❌` plus a one-line
remedy on failure, and exits non-zero if any check fails:
1. `import core`, `import backend`, `import numpy`, `import fastapi` succeed.
2. `from core.simulation.engine import ...` and a 100-frame headless sim
   (`python main.py --headless --max-frames 100 --seed 42`) initialize and run.
3. `black --version`, `ruff --version`, `mypy --version` resolve (the exact
   gap the reviewer hit: "Ruff/black/mypy gate could not run — tools not
   installed").
4. `frontend/node_modules` exists (else print `cd frontend && npm install`).
Model it on the existing gate scripts in `tools/` (they already shell out and
aggregate pass/fail). **Layer 2, no simulation impact — pure ergonomics.**

### 4.3 Algorithm catalog doc — `S` · ★★
Generate `docs/ALGORITHM_CATALOG.md` from the registry: each algorithm's file,
tunable parameters, the niche it wins, and its known weakness. This is the map
an AI agent needs to target improvements instead of guessing. Generate it from
code so it never goes stale.

### 4.4 Frontend connection status + FPS counter — `S` · ★★
`frontend/src/hooks/useWebSocket.ts` already reconnects on drop; what's still
missing is the *visible* half. Add (a) a small connection-status indicator
driven by the hook's state (connecting / live / reconnecting), and (b) an FPS
overlay on the render loop. Makes the live UI trustworthy and exposes rendering
bottlenecks (fractal plants are the prime suspect). Upgrade the reconnect to
true exponential backoff if it isn't already. **Layer 2.**

### 4.5 Debug-frame / debug-entity tracing — `M` · ★★
Add `--debug-frame N` and `--debug-entity ID` flags to the headless runner that
dump every energy delta and event for the targeted frame/entity. Cuts
regression hunts from hours to minutes.

---

## Theme 5 — Documentation that sells the project

### 5.1 Visual assets in the README — `S` · ★★★
The project is *visual* and the README has no visuals. Add a screenshot/GIF of
a running tank, plus the evolution-loop and three-layer diagrams (Mermaid is
already rendered inline — see the README). A reader should *see* the tank in the
first scroll.

### 5.2 Archive deprecation policy — `S` · ★★
43 archived docs sit beside active ones with no retention rule. Adopt a short
policy (see [archive/README.md](archive/README.md)): archived docs get a header
banner linking to their current replacement; the index never links stale docs as
if current.

### 5.3 Generated docs stay generated — `S` · ★
Anything that mirrors code (algorithm count, catalog, benchmark list) should be
generated by a script run in CI, so docs can't drift from reality. The 48-vs-58
algorithm-count bug is exactly the failure this prevents.

---

## Theme 6 — Type safety as a guardrail (external review, 2026-07)

The reviewer's point is that in a system built for AI agents to *modify* code,
typing is not cosmetic — it is the guardrail that catches a bad edit before CI
does. Current state (measured 2026-07): ~64% of Python functions fully typed;
**306 `Any` annotations in `core/`**; mypy config is deliberately relaxed
(`disallow_untyped_defs = false`, `check_untyped_defs = true`). These tasks
tighten the *core path* first, where a mistake is most expensive.

### 6.1 Tighten mypy on one core package at a time — `M` · ★★
**Do not flip strict mode globally** — it will produce hundreds of errors and no
mergeable PR. Instead, pick **one** package and add a per-module mypy override
that turns on `disallow_untyped_defs = true` for just that path, then fix the
fallout. Suggested order (highest leverage first):
`core/simulation/`, `core/worlds/`, `core/genetics/`, then
`backend/state_payloads.py`. One package per PR, Layer 2, `pre_pr_gate` green.
The `# No overrides` line in `pyproject.toml`'s mypy section is where the
per-module override block goes.

### 6.2 Retire `Any` in the hottest core modules — `S` · ★★
Grep `core/` for `: Any`, `-> Any`, and `[Any]` (306 hits today) and replace
the easy ones with real types — start with the entity/state modules a benchmark
touches every frame (`core/entities/fish.py`, `backend/state_payloads.py`).
Each PR: pick one module, remove its `Any`s, keep `mypy core/` green. Small,
safe, and it compounds. **Layer 2.**

---

## Theme 7 — Frontend contracts & performance (external review, 2026-07)

The reviewer rated the frontend the weakest surface relative to its ~26k LOC:
thin tests (13 test files vs. 91 source files) and several 1,000+ line
renderers/components. These are the tractable pieces.

### 7.1 Contract test between backend payloads and frontend types — `M` · ★★★
**Problem.** `backend/state_payloads.py` (Python) and
`frontend/src/types/simulation.ts` (TypeScript, ~876 lines) describe the same
wire format and can silently drift. The frontend already detects *schema
version* mismatch at runtime, but nothing checks field-level shape.

**Plan (two options, pick the smaller that fits).** Either (a) generate the TS
types from the Python dataclasses/pydantic models as a build step so they cannot
drift, or (b) add a contract test that serializes a representative payload from
`state_payloads.py` and asserts every key is present in the TS type (a JSON
fixture checked by both sides). Option (b) is the smaller first step. **Layer 2.**

### 7.2 Make the delta state path actually delta — `M` · ★★
**Problem.** `StateSnapshot.to_delta_dict()` in `backend/state_payloads.py`
(line ~223) exists, but the reviewer notes the path "appears not truly delta in
spirit — the backend can send updates for every entity, and the frontend applies
maps/filtering over the full entity list." Fine at today's entity counts, a
likely future bottleneck.

**Plan.** First *measure*: log delta-frame payload size and the count of entities
sent vs. changed at a few population levels. Only if it's actually sending
unchanged entities, make `to_delta_dict()` emit changed entities plus a removal
list, and have the frontend patch its entity map instead of rebuilding it. Land
the measurement as its own small PR first — don't optimize on a hunch. **Layer 2**
(wire-format change — bump the schema version and keep the mismatch detector
happy).

### 7.3 Split the 1,000+ line renderers — `M` · ★
`frontend/src/utils/renderer.ts` (1,658), `PetriTopDownRenderer.ts` (1,392),
`EvolutionBenchmarkDisplay.tsx` (1,297), and `TankTopDownRenderer.ts` (1,263)
are the top offenders. Same discipline as Theme 2's Python god-file splits:
extract *obvious* collaborators (e.g. per-entity draw helpers, a legend/HUD
module) behind a thin facade, verified by `npm run build` + existing tests.
Split only where the responsibility boundary is clear — no abstraction for
elegance. **Layer 2.**

---

## Theme 8 — Product-facing meaning (external review, 2026-07)

### 8.1 Decide soccer reward semantics; bury repro-credit bookkeeping — `M` · ★★
**Problem.** The reviewer flagged two related smells: (1) soccer reward code
reaches into a private-ish component —
`core/minigames/soccer/rewards.py:apply_soccer_repro_rewards` reads
`entity._reproduction_component` and calls `add_repro_credits`; (2) "repro
credit" is internal simulation bookkeeping leaking toward player-facing
achievement. The player-facing model should be goals, assists, wins, tank
identity, and net energy.

**Plan (two separable steps).**
- *Encapsulation (S):* give `ReproductionComponent` a public accessor so
  `rewards.py` stops touching the underscore-prefixed attribute directly. Behavior
  identical; champions must still reproduce exactly. Search first —
  `_reproduction_component` and `repro_credit` appear in ~20 files, so scope the
  rename carefully.
- *Semantics (M):* if repro-credit isn't a concept the project wants to keep,
  remove the `reward_mode="credits"` path decisively rather than hiding it from
  the UI. This is a design decision — **confirm with a maintainer before
  deleting**, and keep it a separate PR from the encapsulation fix (Rule 1).

---

## Shipped

- **4.1 One-command startup.** `start.py` launches backend + frontend together
  with sane defaults and a single Ctrl-C shutdown; the two-terminal onboarding
  friction is gone.
- **3.1 stage 1: monolithic food-seekers benchmarked and triaged (ADR-006).**
  `tools/benchmark_algorithms.py` pins every fish to one algorithm and runs
  seeded headless worlds; 14 monoliths + composable baseline x 3 seeds.
  Headline findings: the live sim never selects monoliths for movement (they
  are vestigial), and only food_quality_optimizer (+23%), opportunistic_feeder
  (+11%), and cooperative_forager (+8%) beat the composable baseline on every
  seed - the best concrete lead on the chronic starvation rate. KEEP those
  three (port to composable); DEPRECATE the other 11 via metadata-only
  `DEPRECATED_ALGORITHMS` (selection untouched; champions still reproduce).

- **3.2 Unified ParameterRegistry with runtime clamping.**
  `core/parameters/registry.py` composes the three existing bounds tables
  (behavior sub-params, poker sub-params, per-algorithm bounds - source
  modules stay authoritative). Closed a real enforcement gap: out-of-range
  values entering via crossover blending or from_dict deserialization could
  persist indefinitely (mutation only clamped keys whose mutation roll fired);
  every mutate path now ends with an RNG-free full clamp over declared keys.
  All four champions reproduce exactly (clamping is a no-op on their
  trajectories). 25 new tests in tests/core/test_parameter_registry.py.

- **Theme 2 (all): god files split into focused collaborators.** Five splits,
  each behavior-preserving (full pre-PR gate matches baseline; champions
  reproduce exactly): `core/simulation/engine.py` 951→~700 (PhaseExecutor,
  MutationExecutor, FrameAggregator, engine_setup, headless_runner);
  `core/ecosystem.py` 995→622 (telemetry router, poker outcome recorder,
  diversity tracker, reporting); `backend/simulation_runner.py` 1020→577
  (loop, world_switch, evolution_benchmark, stats_collector);
  `core/genetics/behavioral.py` 830→270 (behavioral_inheritance,
  mate_preferences, policy_inheritance); poker `strategy.py` 846→770
  (CFRInheritance with documented blend math + CFRInheritanceMode enum,
  PokerStrategyValidator, PokerStrategyCodec).
- **Pause actually pauses now.** The paused flag was set/saved/restored but
  never gated stepping, so "paused" worlds simulated at ~30fps since the repo
  import. Fixed in the runner loop; also fixed petri restore validation
  (demanded a tank-only Castle) and the restore-failure fallback (`_seed`
  AttributeError on petri).

- **1.1 Config-hash guarding for champions.** `run_bench.py` stamps every result
  with a stable hash of (seed, benchmark id, benchmark CONFIG, core config) via
  `core/solutions/config_hash.py`; `validate_improvement.py` and
  `validate_reproduction.py` refuse to compare scores across mismatched hashes
  with a "config changed — re-baseline" message. Existing champions backfilled
  with `tools/backfill_config_hash.py`.
- **1.3 Benchmark-harness integrity test.** `tests/test_benchmark_integrity.py`
  re-runs every champion at its recorded seed (marked `slow`); wired into the
  nightly gate, and the CI `schedule` trigger that nightly-full expected now
  actually exists.

- **Docs: fixed stale algorithm count (48 → 58) and completed the docs index.**
  Verified the count against `core/algorithms/registry.py` and added the missing
  `REPLAY.md` / `UI_SPEC.md` entries. (commit `380a6c0`)
- **Docs: refreshed ROADMAP status** — marked `validate_improvement.py` and
  `bench.yml` as shipped, clarified which tank benchmarks actually exist.

---

*Keep this list honest. If a proposal is no longer worth doing, delete it with a
one-line note rather than letting it rot.*
