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

Three files carry too much and make safe change hard. Each extraction must keep
determinism (verify with `pytest -m core` + a benchmark re-run).

### 2.1 Split `core/simulation/engine.py` (~950 LOC) — `L` · ★★
Extract `PhaseExecutor` (ordered phase loop + timing), `MutationExecutor`
(drain the mutation queue in its own post-update phase), and `FrameAggregator`
(collect metrics/events at frame end). The public `Engine.update()` becomes a
short orchestration method.

### 2.2 Split `core/genetics/behavioral.py` (~830 LOC) — `M` · ★★
Separate `BehavioralInheritanceLogic`, `MatePreferenceSystem`, and
`BehavioralTraitCodec`. Trait *specs* stay declarative; the *logic* moves into
named, individually-testable units.

### 2.3 Split `core/poker/strategy/composable/strategy.py` (~845 LOC) — `M` · ★
Pull CFR table blending into `CFRInheritance`, validation into
`PokerStrategyValidator`, and (de)serialization into a codec. Document the
blend math and add an explicit `CFRInheritanceMode` enum.

---

## Theme 3 — Consolidate the algorithm library

### 3.1 Decide the fate of the 15 monolithic food-seekers — `M` · ★★
**Problem.** `core/algorithms/food_seeking/` holds 15 standalone strategies that
predate the composable framework. Evolution's search space is now fractured
across two systems, and bug fixes diverge.

**Plan.**
- Benchmark which monoliths are still evolutionary winners.
- Reimplement winners as composable configs; deprecate the rest behind a
  `DEPRECATED_ALGORITHMS` list with a one-release removal window.
- Document the decision in an ADR so the history is legible.

### 3.2 Unify parameter bounds — `M` · ★
Today bounds live in three places (`SUB_BEHAVIOR_PARAMS`,
`ALGORITHM_PARAMETER_BOUNDS`, poker `definitions.py`). Introduce a single
`ParameterRegistry` and add runtime clamping so evolved/mutated parameters can
never silently leave their design range.

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
