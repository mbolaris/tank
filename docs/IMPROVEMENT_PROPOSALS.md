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

### 4.1 One-command startup — `S` · ★★★
Add `python start.py` (or a `tank` console-script entry point) that launches
backend + frontend together with sane defaults and a single Ctrl-C shutdown.
Two-terminal setup is the #1 onboarding friction point.

### 4.2 `scripts/diagnose.py` health check — `S` · ★★★
One command that verifies the environment and prints a green/red checklist:
Python deps importable, core modules load, a 100-frame sim initializes, frontend
deps installed. Turns "it's broken somewhere" into a precise pointer.

### 4.3 Algorithm catalog doc — `S` · ★★
Generate `docs/ALGORITHM_CATALOG.md` from the registry: each algorithm's file,
tunable parameters, the niche it wins, and its known weakness. This is the map
an AI agent needs to target improvements instead of guessing. Generate it from
code so it never goes stale.

### 4.4 Frontend connection status + FPS counter — `S` · ★★
A small `useWebSocket` hook with exponential-backoff reconnect and a visible
connection indicator, plus an FPS overlay. Makes the live UI trustworthy and
exposes rendering bottlenecks (fractal plants are the prime suspect).

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

## Shipped

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
