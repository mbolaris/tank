# Improvement Proposals

> A living, prioritized backlog of high-leverage improvements for Tank World.
> Each proposal names **what's interesting**, **why it matters**, and a concrete
> **implementation plan**. Pick one, open a PR, check it off.

This document complements [ROADMAP.md](ROADMAP.md). The roadmap tracks the
strategic milestones (the Evolution Loop MVP, meta-evolution, etc.);
this file tracks the *engineering* work that makes the codebase more fun to
use and a better example of software design.

**How to use it:** proposals are grouped by theme and tagged with effort
(`S` / `M` / `L`) and impact (`★` low to `★★★` high). Start with
high-impact, low-effort items. When you complete one, move it to the
"Shipped" section at the bottom with the PR link.

**Best current starter picks:**

- **11.3** — the foraging gym with an oracle ceiling: the first absolute
  foraging skill measure, self-contained, and the template for Theme 11's
  remaining rulers.
- **6.2** — retire `Any` in one small core module, after re-running the grep
  and skipping files already checked in the notes below.

For smaller / less expensive agents: pick one `S` task tagged **Layer 2**. Those
changes do not alter simulation results, cannot regress a champion trajectory,
and are usually proven by the normal docs/tooling gates. Follow the recipe in
[AGENT_FIELD_GUIDE.md](AGENT_FIELD_GUIDE.md): one focused change per PR.

> **Themes 6–8 come from an external code review (2026-07, overall 82/100).**
> The review praised the vision, architecture, test discipline, and determinism
> policy, and located the remaining rough edges in *type safety, frontend
> contracts, performance confidence, and product-facing meaning* — which is
> exactly what those themes turn into concrete, pickup-able tasks. Counts cited
> in them (`Any` usage, file lengths, test-file ratio) were re-measured against
> the tree when the tasks were written; re-check before trusting a stale number.

> **Themes 9–10, task 1.7, and the Theme 2 "round 2" list come from a second
> external review (2026-07, also 82/100).** Its verdict: "Tank World is already
> impressive as software. It is not yet defensible as a scientific paper until
> the data pipeline catches up with the vision." It verified the smoke gate,
> agent gate, mypy, black/ruff, frontend build/tests, and soccer benchmark
> determinism all pass, identified one hard defect (wheel packaging, now shipped
> as 9.1), and identified the missing research instrumentation in Theme 10.
> Subscores: architecture 84, test discipline 88, determinism 86,
> maintainability 74, research readiness 72, **packaging 45**. File-size claims
> were re-verified against the tree 2026-07-06 when these tasks were written.

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

**Instrumentation status.** Benchmark fingerprint streams now record exact and
6-decimal-rounded snapshot hashes, entity-type component hashes/counts, and an
environment manifest every 100 frames. Ecosystem champion verification runs
twice, compares the streams within CI, and uploads both streams for comparison
with local runs. Use `tools/compare_fingerprint_streams.py` to report the first
exact and rounded divergent frames.

**Remaining plan.** Use the uploaded fingerprint streams to compare two CI runs
and a local run, find the first divergent frame, inspect that frame's code path,
and eliminate the environment input. Then re-land the food-targeting
improvement (the revert preserved it in git history at `e1fed26`; it beat both
tank champions on every local environment).

### 1.4 Multi-seed validation for the AI agent — `M` · ★★
**Problem.** `scripts/ai_code_evolution_agent.py` validates a proposed change on
a single short run, where natural variance dwarfs the improvement signal.

**Shipped building block.** `tools/run_bench_matrix.py` and
`tools/validate_improvement.py` already understand multi-seed benchmark results
and majority-of-seeds comparison.

**Remaining plan.** Wire `scripts/ai_code_evolution_agent.py` to validate across
≥3 seeds instead of the current hard-coded seed `42`, report mean ± stddev, log
the seed list to the attempt ledger, and require the change to beat the champion
in a majority of seeds. Run `pytest -x` and `mypy` on the edited files *before*
committing so the agent never pushes a syntax/import break.

### 1.6 One health command that works from a clean checkout — `M` · ★★
**Problem (external review, 2026-07).** The review's #1 next move: "make one
clean health command work everywhere" — `tools/smoke_gate.py` should install/
resolve the tools it needs and pass from a fresh checkout, instead of assuming
black/ruff/mypy/node are already present. The reviewer's gate run failed only
because tools weren't installed, not because code was wrong.

**Plan.** Make `tools/smoke_gate.py` (or a thin wrapper it calls) detect missing
dev tools and either install them or print the exact one-liner to do so, so a
green run is achievable from `git clone` + one command. Complements shipped
`scripts/diagnose.py` — diagnose reports, this one repairs. **Layer 2.**



## Theme 2 — Tame the god files

Round 1 shipped (see the Shipped section): the three planned splits plus
`core/ecosystem.py` and `backend/simulation_runner.py`. Future splits should
follow the same pattern: extracted collaborators + thin delegating facades,
verified by the full fast gate and exact champion reproduction.

### 2.6 Round 2: the next worst offenders — `M` each · ★★
**External review #2 (2026-07)** flagged a new crop; line counts below were
re-measured against the tree 2026-07-06 after several follow-up cleanups. Long
files are "where AI-agent codebases start to rot": agents over-edit, duplicate
logic, and miss invariants. One file per PR, same discipline as round 1.
Ordered by leverage (how often agents touch it), not raw size:

| File / item | Lines | Notes |
| --- | ---: | --- |
| `core/entities/fish.py` | 625 | `Fish.__init__` still dominates the file; extract construction/wiring helpers. Champions must reproduce exactly. |
| `core/mixed_poker/interaction.py::play_poker` | ~336-line method | Extract per-street/settlement helpers; behavior-preserving, verify with champion reproduction. |
| `backend/routers/worlds.py::setup_worlds_router` | ~300-line function | Split endpoint groups into module-level handlers or sub-routers. Layer 2. |
| `core/algorithms/base.py` | 705 | Agents read this constantly when writing behaviors — clarity here compounds. |
| `backend/state_payloads.py` | 741 | Coordinate with 7.1 (contract test / generated types) — don't split before deciding that. |
| `core/spatial/grid.py` | 652 | Hot path — split only if a clean seam exists; never at a performance cost. |
| `tools/evolution_report.py` | 904 | Lowest risk (tooling, no sim impact). Good warm-up split. Layer 2. |
| `core/poker/human_poker_game.py` | 741 | Low traffic; do last. |

Frontend renderers (`renderer.ts` 1,431, etc.) are already covered by **7.3**.

## Theme 3 — Consolidate the algorithm library

Complete. Stage 1 (metadata deprecation) and stage 2 (11 food-seekers removed,
champions re-baselined) shipped under ADR-006; ADR-016 then removed the five
remaining vestigial monolith categories (44 algorithms — predator avoidance,
schooling, energy management, territory, poker interaction), which an
independent reachability audit confirmed no production code path ever
selected. `ALL_ALGORITHMS` is now the three proven foragers; production fish
behavior is the composable framework. The old 3.2 bounds-drift task is
resolved by removal: every algorithm still in `ALGORITHM_PARAMETER_BOUNDS`
has a complete, matching entry. Remaining survivor-bounds gaps (if any
surface) belong to normal maintenance, not a theme.

---

## Theme 4 — Developer & observer experience (the "fun" budget)

This is where "fun to use" and "excellent example of software design" are won.

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



### 5.3 Generated docs stay generated — `S` · ★
Anything that mirrors code should be generated by a script run in CI, so docs
can't drift from reality. The algorithm catalog half is shipped:
`tools/generate_algorithm_catalog.py` regenerates `docs/ALGORITHM_CATALOG.md`,
and the smoke gate checks freshness. Remaining candidates: generate the live
benchmark list/runtime-budget table from benchmark modules, and keep docs that
quote registry counts from hand-maintaining those numbers. The old 48-vs-58
algorithm-count bug is exactly the failure this prevents.

---

## Theme 6 — Type safety as a guardrail (external review, 2026-07)

The reviewer's point is that in a system built for AI agents to *modify* code,
typing is not cosmetic — it is the guardrail that catches a bad edit before CI
does. Current state (measured 2026-07): ~64% of Python functions fully typed;
after several cleanup passes, a quick re-count shows **209 simple `Any`
annotation hits** (`: Any`, `-> Any`, `[Any]`) and **688 plain `Any`
occurrences** across `core/`. Mypy config is deliberately relaxed
(`disallow_untyped_defs = false`, `check_untyped_defs = true`). These tasks
tighten the *core path* first, where a mistake is most expensive.

### 6.1 Tighten mypy on one core package at a time — `M` · ★★
**Do not flip strict mode globally** — it will produce hundreds of errors and no
mergeable PR. Instead, pick **one** package and add a per-module mypy override
that turns on `disallow_untyped_defs = true` for just that path, then fix the
fallout. Shipped so far: `core/simulation/`, `core/worlds/`, `core/genetics/`,
and `core/transfer/`. The next candidate is `backend/state_payloads.py`, but
coordinate it with **7.1** first because the honest types may be generated
payload contracts rather than hand-written annotations. One package per PR,
Layer 2, `pre_pr_gate` green. The `# No overrides` line in `pyproject.toml`'s
mypy section is where the per-module override block goes.

### 6.2 Retire `Any` in the hottest core modules — `S` · ★★
Grep `core/` for `: Any`, `-> Any`, and `[Any]` (209 hits re-measured
2026-07-07; note this pattern misses generic-parameterized forms like
`dict[str, Any]`; a plain `\bAny\b` count is 688) and replace the easy ones
with real types. Each PR: pick one module, remove its `Any`s, keep `mypy core/`
green. Small, safe, and it compounds. **Layer 2.**

**Already checked / completed:** Completed cleanup passes include `core/code_pool/pool.py`,
`core/services/stats/genetic_stats.py`, `core/worlds/petri/backend.py`,
`core/worlds/tank/backend.py`, `core/agents_wrapper.py`, `core/entity_ids.py`,
`core/entities/fish.py`, `core/transfer/entity_transfer.py`,
`core/genetics/sanitization.py`, `core/util/rng.py`, `core/util/mutations.py`,
`core/spatial/bounds.py`, `core/actions/action_registry.py`,
`core/energy/energy_utils.py`, `core/entities/base.py`, `core/modes/tank.py`,
`core/modes/petri.py`, `core/worlds/shared/action_translator.py`,
`core/genetics/mate_preferences.py`, `core/genetics/behavioral_inheritance.py`,
`core/minigames/soccer/seeds.py`, `core/policies/movement_policy_runner.py`,
`core/ecosystem_telemetry.py`, `core/interfaces.py` (all but the legacy
`record_poker_outcome result: Any` param), `core/entities/plant.py`,
`core/plant/poker_component.py`, and `core/plants/plant_strategy_types.py`.

**Avoid as a small 6.2 pick:** `backend/state_payloads.py`. Checked 2026-07;
nearly every remaining `Any` is either `to_dict() -> dict[str, Any]` or a
heterogeneous wire-payload field. That file belongs under **7.1** unless the
contract strategy changes.

**Next step:** re-run `rg -n "\bAny\b" core/`, pick one small core module with
mechanical annotations, and keep `mypy core/` green.

---

## Theme 7 — Frontend contracts & performance (external review, 2026-07)

The reviewer rated the frontend the weakest surface relative to its size:
22,381 source lines re-measured 2026-07-06, thin tests (13 test files vs. 91
source files), and several 1,000+ line renderers/components. These are the
tractable pieces.

### 7.1 Contract test between backend payloads and frontend types — `M` · ★★★
**Problem.** `backend/state_payloads.py` (Python) and
`frontend/src/types/simulation.ts` (TypeScript, 824 lines) describe the same
wire format and can silently drift. The frontend detects *schema version*
mismatch at runtime, and `tests/test_websocket_payload_v1.py` guards the basic
full/delta V1 keys, but nothing checks the field-level Python DTO shape against
the TypeScript interfaces.

**Plan (two options, pick the smaller that fits).** Either (a) generate the TS
types from the Python dataclasses/pydantic models as a build step so they cannot
drift, or (b) add a contract test that serializes a representative payload from
`state_payloads.py` and asserts every key is present in the TS type (a JSON
fixture checked by both sides). Option (b) is the smaller first step. **Layer 2.**

### 7.2 Measure whether delta updates are truly sparse — `M` · ★★
**Problem.** `EntitySnapshot.to_delta_dict()` in `backend/state_payloads.py`
(line ~223) emits only fast-changing fields, and the wire payload already has
`updates`, `added`, and `removed`. `useWebSocket.applyDelta()` patches entities
by id, and `tests/test_delta_identity_is_stable.py` guards stable IDs. The
remaining suspicion is narrower: `backend/runner/state_publisher.py` currently
builds `updates = [e.to_delta_dict() for e in entities]`, which may still send
every existing entity every delta frame.

**Plan.** First *measure*: log delta-frame payload size and the count of
entities sent vs. actually changed at a few population levels. Only if it is
sending unchanged entities, track the last sent per-entity delta state and emit
only changed updates plus the existing `added`/`removed` lists. Land the
measurement as its own small PR first — don't optimize on a hunch. **Layer 2**
(if the wire-format shape changes, bump the schema version and keep the
mismatch detector happy).

### 7.3 Split the 1,000+ line renderers — `M` · ★
`frontend/src/utils/renderer.ts` (1,431),
`frontend/src/renderers/petri/PetriTopDownRenderer.ts` (1,226),
`frontend/src/components/EvolutionBenchmarkDisplay.tsx` (1,203), and
`frontend/src/renderers/tank/TankTopDownRenderer.ts` (1,122) are the top
offenders. Same discipline as Theme 2's Python god-file splits: extract
*obvious* collaborators (e.g. per-entity draw helpers, a legend/HUD module)
behind a thin facade, verified by `npm run build` + existing tests. Split only
where the responsibility boundary is clear — no abstraction for elegance.
**Layer 2.**

---

## Theme 8 — Product-facing meaning (external review, 2026-07)

### 8.1 Decide soccer reward semantics; bury repro-credit bookkeeping — `M` · ★★
**Problem.** The encapsulation half of this review item is shipped: soccer
reward code now uses the public `reproduction_component` accessor. The
remaining smell is semantic: "repro credit" is internal simulation bookkeeping
leaking toward player-facing achievement. The player-facing model should be
goals, assists, wins, tank identity, and net energy.

**Remaining plan.**
- *Semantics (M):* if repro-credit isn't a concept the project wants to keep,
  remove the `repro_reward_mode="credits"` path decisively rather than hiding it
  from the UI. Reconcile the public docs/API at the same time: backend command
  validation currently accepts only `"credits"` for `repro_reward_mode`, while
  product-facing copy should talk in goals, assists, wins, tank identity, and
  net energy. This is a design decision — **confirm with a maintainer before
  deleting**, and keep it a separate PR from the encapsulation fix (Rule 1).

---

## Theme 9 — Packaging & release hygiene (external review #2, 2026-07)

The review's one confirmed hard defect was fixed in **9.1**. No active Theme 9
proposals remain; see the Shipped section for the wheel packaging smoke test.

---

## Theme 10 — Research instrumentation: make the paper defensible (external review #2, 2026-07)

The review's core message: the "AI agents as evolutionary operators" story is
not defensible until the data pipeline is as real as the system design. The
attempt ledger and multi-seed matrix tooling have landed, so accepted and
rejected attempts can now be recorded. Remaining gaps: agents can still edit
every ruler they are scored against, patches are not yet classified into a
mutation taxonomy, and there is no non-AI control arm.

None of these change simulation behavior — all **Layer 2** — but they touch
scoring/CI infrastructure, so keep each one a separate PR (Rule: Layer 2
changes stay separate from Layer 1 improvements).


### 10.5 A non-AI baseline search method — `L` · ★★
The paper's claim "AI agents are effective evolutionary operators" needs a
control arm. Implement a dumb-but-honest baseline that proposes parameter
perturbations within `ALGORITHM_PARAMETER_BOUNDS` (random search or a simple
evolutionary strategy over `core/config/` + composable parameters). Build on
`tools/param_mutator.py`, which already creates deterministic mutation plans
for composable and per-algorithm parameter bounds. Run the baseline through the
*same* validation pipeline, log it to the *same* attempt ledger with an explicit
non-AI `agent_id`, and compare against agent attempts under the same benchmark
and seed budget. The comparison "agent attempts vs. random-search attempts,
same budget" is the paper's headline figure. Depends on shipped **10.1** and
**10.2**.

---

## Theme 11 — Skill measurement & visualization: frozen rulers (2026-07)

How well do the agents actually play poker, forage, and play soccer — in
absolute terms, over time, and relative to state of the art? Today the answer
is mostly unknowable, for structural reasons:

1. **Champion scores are not comparable over time.** Every determinism fix or
   scoring change re-baselines the registry; `survival_5k`'s history reads
   1161 → 1299 → 127 → 68 → 512 → 388 — a log of re-baselining events, not a
   skill trajectory. Five of its six retirements say "re-baselined", not
   "superseded by better".
2. **Self-play measures nothing absolute.** In-sim poker stats are fish vs
   fish (zero-sum, aggregate win rate ≈ 50% by definition); the soccer score
   is one evolving population playing itself; foraging is only visible through
   ecosystem composites (`avg_energy × avg_pop × penalties`) that conflate
   skill with config and trajectory noise.
3. **Nothing defines a ceiling.** There is no reference anywhere for "how good
   could this possibly be", so "how close are we to SOTA" has no answer.

The design principle that fixes all three: **measure against frozen rulers**.
For each domain, commit a ladder of immutable reference opponents/oracles —
a floor (random/trivial), intermediate rungs (scripted heuristics), and a
ceiling (oracle or strongest scripted opponent) — and express skill as
position on that ladder. Rulers never change (append new rungs, never edit
existing ones), so ladder metrics stay comparable across re-baselines and
config changes. This also directly answers Theme 10's critique that "agents
can edit every ruler they are scored against".

All tasks are **Layer 2** (benchmark/CI/tooling only; no simulation behavior).
Keep each a separate PR.

### 11.1 Fix soccer benchmark insensitivity — `S` · ★★★ — SHIPPED (PR #759)
The training benchmarks pinned every genome to the parameterless default
soccer policy (`soccer_policy_params=None`), so seeds 42/43/44 and the
side-swapped lineup produced byte-identical matches — the multi-seed and
side-swap machinery were no-ops and the benchmark had zero sensitivity to the
evolvable param substrate. Fixed by seeding jitter-0.5 founding-population
params per genome (matching `assign_random_policy`); both champions
re-baselined.

### 11.2 Poker ladder benchmark — `M` · ★★★ — SHIPPED (PR #760)
The `poker/ladder_20k` benchmark (PR #760): the evolvable poker substrate
(`ComposablePokerStrategy` neutral defaults) plays duplicate-deal heads-up
matches against a frozen ladder — L0 `random`, L1 `loose_passive`,
L2 `tight_aggressive`, L3 `gto_expert` (all from `BASELINE_STRATEGIES`).
Metric: bb/100 per rung with 95% CIs; score = mean bb/100 across rungs.
First absolute, longitudinally comparable poker skill measure. Seed-42
baseline: 676.15 mean bb/100, all four rungs beaten — including the
non-monotonic finding that the default hero wins more from `gto_expert`
(+589) than from `tight_aggressive` (+385), which the ladder makes visible
for the first time.

### 11.3 Foraging gym with an oracle ceiling — `M` · ★★★
An isolated foraging benchmark: one fish (later a small cohort variant), no
reproduction/poker/ball, a fixed scripted food-spawn schedule per seed.
Compute the **oracle ceiling** on the same spawn script (full-knowledge
greedy planner with energy accounting) and a random-walk floor. Metric:
`energy_collected / oracle_energy_collected` ∈ [0, 1] — pure food-seeking
competence with SOTA = 1.0 by construction, independent of ecosystem config.
The existing ecosystem benchmarks keep measuring the ecosystem; this measures
the skill. Start from `scripts/diagnose_food_seeking.py` for the isolation
setup.

### 11.4 Soccer reference-team ladder — `M` · ★★
After 11.1, self-play soccer scores are sensitive but still relative. Add
frozen reference teams: L0 stationary, L1 random walkers, L2 scripted
chase-and-shoot, L3 a committed snapshot of the best evolved team (fixture,
e.g. `fixtures/soccer/champion_team_2026_07.json`). Metric: goal difference
per 5k frames vs each rung, side-swapped and multi-seed. Skill = highest rung
beaten + margin.

### 11.5 Longitudinal skill ledger + nightly CI append — `M` · ★★★
`research/skill_history.jsonl`: one row per
`(timestamp, git_sha, config_hash, domain, rung, metric, seeds, skill_index)`
appended by the nightly benchmark job and by `tools/run_bench.py
--record-skill`. Sits beside `research/attempts.jsonl`; purely observational,
so it never needs re-baselining. This is the dataset every trend
visualization reads. Policy: rulers are immutable — changing one mints a new
rung ID; old rows stay valid.

### 11.6 Skill dashboards: static report + UI panel — `M` · ★★
Three views over `skill_history.jsonl`:
(a) **skill trajectory** per domain — x = date/commit, y = normalized skill,
horizontal bands per ladder rung, config-hash changes as vertical markers;
(b) **ladder matrix** — domains × rungs heatmap (loses / competitive /
beats); (c) **domain radar** — the three skill indices, current vs 30 days
ago. Deliver as `tools/skill_report.py` (self-contained HTML for PRs and
nightly artifacts) first, then a "Skill Trends" panel in the web UI next to
`EvolutionBenchmarkDisplay`. Depends on 11.5.

### 11.7 Freeze the rulers in CI — `S` · ★★
Add the reference-opponent implementations
(`core/poker/strategy/implementations/baseline.py`, `standard.py`,
`expert.py`, and future soccer reference teams / foraging oracles) to the
locked-paths check (`tools/check_locked_paths.py`) so a PR that edits a ruler
fails loudly unless explicitly acknowledged. Complements Theme 10's
ruler-integrity goals.

---

## Theme 12 — A shared behavioral substrate for cross-domain reuse (2026-07)

A major project goal is **multi-goal evolution**: a capability evolved for one
problem should be reusable or adaptable in another. Today it structurally
cannot be. The genome carries **three disjoint behavior encodings**, one per
domain, with their own vocabularies, parameter dicts, mutation/crossover code,
and inheritance paths:

| Domain | Substrate | Discrete part | Continuous part | Learned part |
| --- | --- | --- | --- | --- |
| Foraging | `ComposableBehavior` (`core/algorithms/composable/`) | 4 enums (threat/food/social/poker-engage) | ~40 keys (`SUB_BEHAVIOR_PARAMS`) | — |
| Poker | `ComposablePokerStrategy` (`core/poker/strategy/composable/`) | 5 enums (hand/bet/bluff/position/showdown) | ~14 keys | CFR regret table |
| Soccer | `soccer_policy_id` + params (`core/code_pool/pool.py`) | policy-ID swap (chaser/striker/defender) | 8 keys (`SOCCER_POLICY_PARAM_KEYS`) | — |

The "pursue a target" concept is `pursuit_speed`/`pursuit_aggression` in
foraging, `pursuit_commit`/`approach_precision` in soccer, and `risk_tolerance`
+ the aggression trait in poker — different keys, different dicts, different
code. There is no gene a genome could carry that means "how hard I chase"
*across* domains, so selection cannot transfer a good subcomponent from one
problem to another. Meanwhile the underlying computations are the same
primitives, and several are **already pure functions**: `select_food_target`
and `predict_food_target` (`core/algorithms/composable/food_selection.py`) are
a target selector + intercept predictor; `_boids_behavior`/`_safe_normalize`
(`actions.py`) and soccer's `_steer_action` (`pool.py`) are steering; the
`MovementArbiter` (`core/movement/considerations.py`) is a priority action
selector. They are just not lifted into a shared library or exposed to the
genome.

**The bet.** Lift those primitives into a shared, typed library
(`sensors → target selectors → steering/decision → arbiter`), and let a genome
wire them into an evolvable **behavior graph** where only the first hop
(sensor binding) and last hop (actuator) are domain-specific. The middle is
domain-agnostic: a "seek the highest-value target and intercept it" subgraph is
the same nodes in foraging (target = food) and soccer (target = ball). This is
the modular/subtree-crossover lever (EVOLVABILITY §3.2) and the
genotype→phenotype encoding lever (§3.5) made concrete.

**The guardrails (do not violate these):**
- **Interpretability is a Crown Jewel.** Keep the node set small, typed, and
  human-named; cap graph size; keep a `short_description`/render. If you can't
  read a champion graph and say what it does, the change is a regression even if
  a number went up.
- **Determinism is non-negotiable.** Introduce every step behind neutral
  defaults so the baseline stays byte-identical and champions reproduce exactly
  (the pattern soccer params and the two-resource-food flag already use).
  Decouple the gene set from RNG draw order — iterate nodes/ports in a stable
  topological + id-sorted order, never dict/hash order (the `SUB_BEHAVIOR_PARAMS`
  "dict-order = RNG schedule" coupling is the anti-pattern to escape; ADR-012 is
  the precedent). No wall-clock (see Theme 1.0).
- **Layer 1 vs Layer 2 stay separate.** The representation change alters
  simulation results (**Layer 1**) — its own PRs, validated against champions.
  Module-lineage / benchmark-schema additions are **Layer 2** — separate PRs.

**Recommended direction.** Do the low-risk half first — **Option B**: extract
the primitives (12.1) and add a shared gene namespace so one evolved
modulator feeds all three domains. Treat the full evolvable graph — **Option
A** (12.5–12.6) — as *earned* by a falsifiable evolvability result on
`benchmarks/tank/selection_response_10k.py` across seeds 42/7/123, with a kill
criterion. A universal policy net is **Option C** and is rejected: it destroys
the interpretability that is the project's best advertisement.

**Best starter pick: 12.1** — a byte-identical refactor that makes the shared
primitives real without touching the genome. The ADR (`docs/adr/`) recording
the encoding decision is written when **12.3/12.4** commit, not before.

### 12.1 Extract steering/sensor primitives into a shared library — `M` · ★★★
**Layer 1 (byte-identical refactor).** Create `core/behavior/primitives/`
(`steering.py`: seek/flee/arrive/wander/intercept/boids/turn-then-dash) and move
the math out of `actions.py`, `food_selection.py`, and `_steer_action` into
shared pure functions that the existing call sites invoke for *identical*
output. Acceptance: all four champions reproduce bit-exactly. Highest
value-per-risk — it makes the "reusable primitive" story real with zero
behavior change. Keep every new file under the god-class ceiling from the start.

### 12.2 Typed node interfaces + registry — `S` · ★★
**Layer 2 (no sim change).** Define the shared type vocabulary (`Scalar`,
`Vector`/`UnitVector` in a normalized frame, `EntityRef`, `Bool`) and the
`Sensor`/`Selector`/`Steering`/`Memory`/`Arbiter` node Protocols in
`core/behavior/nodes.py`, plus a registry. Interfaces + unit tests only; no
genome wiring yet. This is the type discipline that prevents "graph soup": a
domain pulls in only the node *types* it needs (poker never grows steering;
soccer never grows a poker branch), and the registry treats every node
uniformly for serialization/mutation/crossover.

### 12.3 Dormant `behavior_graph` genome field + interpreter — `M` · ★★
**Layer 1.** Add an optional `behavior_graph` trait to `BehavioralTraits`
(default `None`) with serialization (bump `GENOME_SCHEMA_VERSION` in
`genome_codec.py`), validation, and a graph interpreter that **no fish selects
yet**. Baseline byte-identical (field absent = today's path). Ship a golden
replay fixture that exercises the interpreter in isolation. The interpreter must
compile each genome's graph to a flat callable *once* (not per tick) — the move
loop and `core/spatial/grid.py` are hot paths.

### 12.4 Foraging graph that reproduces `ComposableBehavior` — `M` · ★★★
**Layer 1 (the risky step — isolate it).** Build a graph over the 12.1
primitives that reproduces `ComposableBehavior.execute()` for foraging
(priority arbiter: threat > food > social > explore). Validate on the **Theme
11.3 foraging gym** (absolute skill, not ecosystem noise). Aim for
bit-identical; if impossible, re-baseline the foraging champions **once**,
atomically, with a documented `retired_reason`, and lean on the Theme 11 frozen
rulers, which survive re-baselines by design. Keep `ComposableBehavior` as the
reference oracle throughout — do not delete it here.

### 12.5 Graph mutation + type-safe subgraph crossover — `L` · ★★★
**Layer 1.** Add param mutation (gauss, as today), node-swap mutation (like the
enum switch / policy-ID swap), and low-probability *structural* mutation
(add/remove/rewire an edge, splice a subgraph) behind a heritable
`structural_mutation_rate` meta-gene (reuse `core/genetics/trait.py`). Add
type-safe subgraph crossover — spliceable only where port types match, which
avoids the classic GP nonsensical-recombination failure. **Go/no-go gate:** does
the graph encoding raise directional trait drift on
`benchmarks/tank/selection_response_10k.py` (seeds 42/7/123) vs. the flat
encoding, with a pre-registered kill criterion? The graveyard is full of
plausible ideas that landed flat — prove this one before Theme 12.6.

### 12.6 Cross-domain binding: soccer + poker share the middle — `L` · ★★
**Layer 1.** Add a soccer actuator adapter and bind the *same* interception
subgraph to the ball (first genuine cross-domain reuse) → measure on the Theme
11.4 soccer ladder. Add a poker decision-selector + memory node and bind
hand/pot sensors → measure on `benchmarks/poker/ladder_20k.py`. Make a single
`aggression`/`commit` modulator node feed `InterceptMoving.speed`,
`ScoredOptionSelector.raise_bias`, and `TurnThenDash.commit_dist` so one evolved
gene means the same thing in all three domains (pleiotropy = the transfer we
want). Retire the old per-domain substrates only after graphs demonstrably
dominate every domain and champions are re-baselined (mirror ADR-006/016: prove
no production path selects the old thing, then delete).

### 12.7 Module lineage + cross-domain skill matrix — `M` · ★★
**Layer 2 (observational).** Tag each behavioral module with a provenance id and
record, per champion, which modules it carries and where they came from —
"this interception module descends from the foraging champion and now appears in
the soccer champion" is the headline figure for the transfer story. Score a
shared module on multiple ladders (foraging gym / soccer / poker) to produce a
**module skill matrix** (which modules are good where). Sits beside
`research/skill_history.jsonl` (Theme 11.5); never needs re-baselining.

---

## Shipped

- **6.2 Retired `Any` in composable food selection.** Replaced the broad food
  target and selection annotations in
  `core/algorithms/composable/food_selection.py` with the concrete `Food`
  entity type, preserving the selector's existing runtime behavior while making
  the composable foraging contract visible to static analysis.
- **ADR-016: removed the five vestigial monolith algorithm categories.**
  Deleted `predator_avoidance.py`, `schooling.py`, `energy_management.py`,
  `territory.py`, and `poker.py` from `core/algorithms/` (44 algorithms,
  ~3,100 lines) after a reachability audit confirmed no production path ever
  selects a monolith: `Fish.movement_policy` is never set outside
  tooling/tests, the genome carries only `ComposableBehavior` +
  `PokerStrategyAlgorithm`, and `inherit_algorithm` had zero production
  callers. `ALL_ALGORITHMS` is now the three ADR-006 survivor foragers;
  their `ALGORITHM_PARAMETER_BOUNDS` entries are complete (resolving 3.2).
  Acceptance: all four champions reproduce bit-exactly at their recorded
  seeds before and after removal — no re-baseline.
- **1.8 Align `survival_5k` benchmark scoring with healthy ecosystem indicators.**
  Refactored the score formula in `benchmarks/tank/survival_5k.py` to apply a
  starvation penalty when the starvation rate exceeds 95% (scaling down the score
  linearly to 0.5 at 1.0 starvation rate) and a bonus multiplier for achieving a
  higher max generation (`1.0 + max_generation * 0.05`). Re-baselined the
  champion to version 6 with the new scoring structure under seed 42.
- **1.7 Optimize `survival_5k` runtime & reliability.** Solved the benchmark
  execution performance cliff. Replaced the expensive frame-by-frame
  `world.get_stats()` calculator with direct, cheap list comprehensions over
  `world.entities_list` to aggregate fish count, total fish energy (including
  reproduction overflow bank), and max generation. Achieved a 2x speedup (down
  to ~24 seconds per run), resolving constraints while retaining exact score
  determinism.
- **10.3 Held-out evaluators agents cannot edit.** Created the
  [benchmarks/heldout/](../benchmarks/heldout) directory with a held-out
  evaluation module ([survival_heldout_5k.py](../benchmarks/heldout/survival_heldout_5k.py))
  carrying altered parameters. Implemented
  [check_locked_paths.py](../tools/check_locked_paths.py) to parse git changes
  against origin branch/local workspace and fail if any locked paths (such as the
  held-out suite) were modified. Added comprehensive mock test suite coverage
  in [test_check_locked_paths.py](../tests/test_check_locked_paths.py).
- **10.4 Patch taxonomy refinements.** Upgraded the rule-based patch classifier in
  [classify_patch.py](../tools/classify_patch.py) to exclude active backend code
  from `benchmark-or-meta` category and analyze them for diff hunks. Also removed
  the blind configuration file bypass to allow precise, line-level literal vs.
  dynamic expression checks inside parameters/config files. Added five new
  tests inside [test_classify_patch.py](../tests/test_classify_patch.py).
- **2.7 Extend god-class limits ratchet beyond `core/`.** Expanded the architectural
  line-limit enforcement in [test_god_class_limits.py](../tests/test_god_class_limits.py)
  to monitor `backend/`, `tools/`, and `frontend/src/` files. Existing legacy files
  exceeding the 500-line limit were grandfathered in `LEGACY_MAX_LINES` at their
  current line counts.
- **5.2 Enforce the archive deprecation policy.** Mechanical pass over all 44
  archived Markdown files to prepend the required one-line header banner, e.g.
  `> Archived YYYY-MM. Superseded by [docs/FILENAME](RELATIVE_PATH).` where a
  direct current counterpart exists (mapping `ROADMAP.md`, `AI_QUICK_START.md`,
  `ARCHITECTURE` reviews, etc. to active docs) and falling back to a general
  date-stamped banner otherwise.
- **10.1 Attempt ledger: log every attempt, not just wins.** Created
  [attempt_ledger.py](../core/research/attempt_ledger.py), which appends
  accepted, rejected, and errored evaluations to `research/attempts.jsonl` with
  benchmark id, seed(s), candidate/champion scores, config hash, verdict,
  agent/model metadata, git branch/commit/diff stat, changed files, command,
  duration, and gate/champion-update flags. Wired logging into
  [validate_improvement.py](../tools/validate_improvement.py),
  [run_bench_matrix.py](../tools/run_bench_matrix.py), and
  [ai_code_evolution_agent.py](../scripts/ai_code_evolution_agent.py). Added
  [summarize_attempts.py](../tools/summarize_attempts.py) for ledger reporting
  and [test_attempt_ledger.py](../tests/test_attempt_ledger.py) coverage.
- **1.7 phase profiling instrumentation.** Added `main.py --profile-phases` and
  `TANK_PROFILE_PHASES=1` support backed by
  [profiler.py](../core/simulation/profiler.py). Headless runs print cumulative
  phase timings and include `phase_profiling` in `--export-stats`; coverage in
  [test_phase_profiling.py](../tests/test_phase_profiling.py) verifies default
  off behavior, config/env enablement, and phase bucket accounting.
- **9.1 Fix broken wheel packaging + add a clean-install smoke test.** Switched to package discovery in `pyproject.toml` (`[tool.setuptools.packages.find]`) to recursively package all subpackages of `core` and `backend`. Created `tools/check_wheel.py` to build the wheel, programmatically check the zip contents for correct package structure/exclusions, and verify representative imports inside a clean temporary virtual environment. Added this wheel packaging check as a step in the CI workflow's smoke-gate job.
- **4.3 Algorithm catalog doc.** `tools/generate_algorithm_catalog.py`
  introspects `ALL_ALGORITHMS`/`ALGORITHM_PARAMETER_BOUNDS` and regenerates
  `docs/ALGORITHM_CATALOG.md` (file, tunable parameters + bounds coverage,
  deprecation status). A freshness test in `test_docs_agent_onboarding.py`
  (part of the smoke gate) fails if the checked-in doc drifts from the
  generator's output.
- **1.5 Benchmark runtime budgets.** Every live benchmark declares
  `EXPECTED_RUNTIME_SECONDS`; `tools/run_bench.py` prints `Runtime: <elapsed>s
  (budget ~<budget>s)` after each run, and `benchmarks/README.md` documents the
  budget table with reference champion runtimes. Pure visibility — no scoring
  change.
- **4.2 `scripts/diagnose.py` health check.** A setup-oriented diagnosis command
  now checks core/backend imports, NumPy/FastAPI availability, a deterministic
  100-frame headless sim, black/ruff/mypy resolution, and frontend dependencies.
  It prints independent pass/fail rows with one-line remedies, so missing setup
  is easier to distinguish from broken simulation code.
- **4.1 One-command startup.** `start.py` launches backend + frontend together
  with sane defaults and a single Ctrl-C shutdown; the two-terminal onboarding
  friction is gone.
- **4.4 Frontend connection status + FPS counter.** `useWebSocket` exposes a
  `connectionStatus` of `'connecting' | 'live' | 'reconnecting'` (alongside the
  existing `isConnected` boolean) and reconnects with real exponential backoff
  (`computeReconnectDelay`, 3s/6s/12s/24s capped at 30s) instead of a fixed
  3s retry. `Canvas` tracks its own render-loop FPS independent of simulation
  data and reports it via `onRenderFps`. `TankView` wires both into the
  `canvas-hud`/`hud-group`/`hud-item` CSS in `App.css`, which already existed
  but had no consumer. Manually verified: killing the backend flips the
  indicator to RECONNECTING (pulsing) and disables controls; the FPS badge
  measurably dropped when the browser tab lost focus (rAF throttling) and
  recovered on refocus, confirming it reflects real render health.
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

- **6.1 Strict type checking for core/simulation, core/worlds, and core/genetics.** Enabled mypy strictness overrides (`disallow_untyped_defs = true`, `disallow_incomplete_defs = true`) for the `core/simulation`, `core/worlds` (excluding internal tests), and `core/genetics` packages. Resolved untyped functions, arguments, and annotations across these packages, keeping all CI gates green.
- **1.2 Score decomposition in benchmark output.** Verified that benchmarks (`survival_5k`, `ecosystem_health_10k`, `selection_response_10k`, and `training_3k/5k`) emit a `score_breakdown` dict, and `validate_improvement.py` dynamically extracts it, displays side-by-side comparison, and reports the weakest component.
- **6.2 Retired Any in core/transfer/entity_transfer.py and core/genetics/sanitization.py.** Tightened typing by removing generic `Any` annotations, introducing concrete entity classes, parameterizing generic `TransferOutcome[T]`, and utilizing generic `object` types for external untrusted inputs. Enabled strict typing checks override in `pyproject.toml` for `core/transfer/`.
- **10.2 Multi-seed benchmark matrix tooling.** Created
  [run_bench_matrix.py](../tools/run_bench_matrix.py) to run a benchmark across
  a seed list (default `42, 7, 123`), compute statistics (mean, min, max, stdev,
  n), support seed-by-seed comparison, and exit nonzero if the candidate doesn't
  beat the champion on a majority of seeds. Updated
  [validate_improvement.py](../tools/validate_improvement.py) to support
  matrix-seed results and champion updates.
- **Fix benchmark and gate process hangs.** Optimized clean-exit checks to use a lightweight 1-frame real-world benchmark in `tests/test_run_bench.py` to prevent CI timeouts. Changed validation gates in `tools/gate_common.py` to use `os._exit()` to prevent parent process hangs. Created `tests/test_watchdog_survival.py` to verify the real `survival_5k` benchmark running to 3200 frames exits cleanly, and wired a CI smoke check step verifying `pre_pr_gate.py` exit cleanliness.
- **CI / Formatting hardening.** Configured Ruff/Black checks to cover `benchmarks/` in `tools/smoke_gate.py`. Swapped parallel pytest-xdist execution for serial by default in the pre-PR gate. Added held-out benchmarks path checker to PR workflows. Cleaned up unused config values in benchmarks.

- **Docs: fixed stale algorithm count (48 → 58) and completed the docs index.**
  Verified the count against `core/algorithms/registry.py` and added the missing
  `REPLAY.md` / `UI_SPEC.md` entries. (commit `380a6c0`)
- **Docs: refreshed ROADMAP status** — marked `validate_improvement.py` and
  `bench.yml` as shipped, clarified which tank benchmarks actually exist.
- **6.3 Tightened type safety on core packages.** Enabled mypy strictness overrides
  (`disallow_untyped_defs = true`, `disallow_incomplete_defs = true`) for `core.spatial.*`,
  `core.solutions.*`, and `core.util.*`. Resolved all missing type annotations, returning
  types, and generic function signatures in these packages, maintaining fully green type checks.
- **9.2 Repo Hygiene and Package Versioning.** Bumped project version in `pyproject.toml`
  from `0.1.0` to `1.0.0` after 1,800+ commits. Cleaned up and deleted stray runtime results
  and profile stats (`results.json`, `improved_results.json`, `profile_stats.txt`) from the
  workspace root.

---

*Keep this list honest. If a proposal is no longer worth doing, delete it with a
one-line note rather than letting it rot.*
