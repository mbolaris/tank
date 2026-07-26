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

**Last audited against the tree: 2026-07-26** (external review #3 pass — every
number that review cited was re-measured; the stale entries it exposed are
corrected in **2.6** and **7.3**, and its findings became **5.4**, **7.4**,
**7.5**, **9.3**, plus additions to **1.0** and **10.6**).

**Prior audit, 2026-07-25.** That audit found eight proposals
still written as open work whose implementations were already merged (1.4, 1.6,
4.5, 7.2, 10.5, 11.5, 11.7, 12.1), four more that had shipped in part (5.3,
11.6, 12.4, 12.6), and every re-measurable number in Themes 2, 6, and 7 out of
date — one of them by 3x. If you pick
something from here, **verify the premise first** (does the file still have that
many lines? does that tool already exist?) and fix the entry in the same PR if
it has drifted. See the closing rule at the bottom of this file.

**Best current starter picks:**

- **5.4** — fix the README's "50+ behavior algorithms" claim, which names five
  algorithm categories ADR-016 deleted. `S`, Layer 2, and the drift is already
  measured for you below.
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

> **Themes 5.4, 7.4, 7.5, 9.3, and the reframing of 1.0 and 10.6 come from a
> third external review (2026-07-26, overall 91/100)** — up from the two 82s
> above. Its verdict: Tank World "has crossed from 'ambitious personal
> codebase' into a credible research platform," and the missing nine points are
> "about deterministic scientific reproducibility, concentrated complexity, and
> frontend/product maturity — not sloppy fundamentals." Subscores: architecture
> 18/20, correctness & determinism 16/20, **testing & CI 19/20** ("exceptional
> for a project of this size"), maintainability 15/20, research rigor 13/15,
> **product/docs/security/release 10/15**. It executed 70/70 smoke tests and
> 596/596 selected architecture/determinism/genetics/energy tests green, and
> ~1,300 of the non-slow suite before its own sandbox timed out; it could not
> run ruff/black/frontend tests (mirror 503s) and correctly declined to hold
> that against the repo.
>
> Its explicit strategic advice, which is worth more than any single task here:
> **stop proving seriousness by adding subsystems.** "You have enough
> machinery. The next leap comes from making the existing system reproducible
> across environments, easier to modify, empirically convincing, and enjoyable
> to use." Weight new proposals accordingly — a new theme now needs to justify
> itself against that sentence.
>
> Its named path to 95, mapped to tasks in this file: cross-machine
> deterministic replay as a release gate (**1.0**), one real Playwright path
> (**7.4**), finish renderer extraction (**7.3**, **7.5**), a formal evidence
> campaign (**10.6**), generate project claims from code (**5.4**), and an
> authentication boundary (**9.3**). Every number it cited was re-measured
> against the tree on 2026-07-26 before being written in below; two came back
> different (see 2.6 and 7.3).

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

**Review #3 (2026-07-26) made this the single highest-priority item in the
repo** and sharpened the acceptance bar in two ways worth adopting:

1. **Make cross-machine deterministic replay a release gate**, not an
   investigation. The target property it states: given a seed, configuration,
   code SHA, and environment definition, the same result reproduces across
   supported machines — "until then, Tank World cannot honestly claim top-tier
   reproducibility."
2. **The gate must report the earliest divergent frame, phase, entity, RNG
   stream, and state field — not merely a final fingerprint mismatch.** The
   instrumentation above already covers frame, snapshot hash, and entity-type
   component hashes; *phase*, *RNG stream identity*, and *which state field*
   are the gaps. A gate that only says "the digests differ" hands the next
   agent the same multi-day bisect this entry has already cost once.

Its reasoning for the priority is the ALife-specific one, and it is correct:
for an ordinary game, run-to-run float divergence is tolerable; for an
evolutionary framework where small trajectory differences compound across
generations, it is a fundamental scientific concern. Note the interaction with
Theme 11 — ladder metrics are longitudinally comparable *by construction*, so
they partially insulate the skill story from this problem, but champion
trajectories are not insulated at all.

*(1.4 multi-seed agent validation and 1.6 smoke-gate dependency diagnostics both
shipped — see the Shipped section. 1.0 is the only open Theme 1 item.)*

## Theme 2 — Tame the god files

Round 1 shipped (see the Shipped section): the three planned splits plus
`core/ecosystem.py` and `backend/simulation_runner.py`. Future splits should
follow the same pattern: extracted collaborators + thin delegating facades,
verified by the full fast gate and exact champion reproduction.

### 2.6 Round 2: the next worst offenders — `M` each · ★★
Long files are "where AI-agent codebases start to rot": agents over-edit,
duplicate logic, and miss invariants. One file per PR, same discipline as
round 1.

**Read the pins, not this table.** `tests/test_god_class_limits.py` holds
`LEGACY_MAX_LINES`, a machine-enforced ceiling per grandfathered file that CI
keeps honest — it cannot go stale the way a hand-written table can. The
external review's 2026-07-06 numbers here had drifted badly by 2026-07-25 (it
listed `tools/evolution_report.py` at 904 lines; it is 274 and no longer a god
file at all), so the table below is now just *commentary* on entries that live
in `LEGACY_MAX_LINES`. Sorted by size as pinned on 2026-07-25:

| File / item | Pin | Notes |
| --- | ---: | --- |
| `core/poker/human_poker_game.py` | 863 | Now the largest Python file in the repo. Low traffic, so still low priority — but it is no longer "do last" by size. |
| `core/entities/fish.py` | 810 | `Fish.__init__` still dominates; extract construction/wiring helpers. Champions must reproduce exactly. |
| `backend/state_payloads.py` | 812 | **7.1** shipped as a contract test, so the "don't split before deciding" blocker is resolved — the split is now unblocked. Layer 2. |
| `core/transfer/entity_transfer.py` | 800 | Not on the original list; grew into it since. |
| `core/spatial/grid.py` | 795 | Hot path — split only if a clean seam exists; never at a performance cost. |
| `core/mixed_poker/interaction.py::play_poker` | 361-line method (file 728) | Grew from the ~336 the review measured. Extract per-street/settlement helpers; behavior-preserving, verify with champion reproduction. |

**The router factories are back, and this is a cautionary tale.** The
2026-07-25 audit retired `backend/routers/worlds.py` from this list on the
grounds that the file was 356 lines total, so the ~300-line factory function
review #2 described could not exist. Review #3 flagged "router factory
functions exceeding 350 lines" anyway, so it was re-measured on 2026-07-26:

| Item | Measured 2026-07-26 |
| --- | ---: |
| `backend/routers/worlds.py::setup_worlds_router` | ~379 lines (file 432) |
| `backend/routers/solutions.py::create_solutions_router` | ~366 lines (file 418) |

Both are single functions holding the great majority of their file. The
dismissal was correct on the day it was written and wrong three weeks later —
the file grew 76 lines in the interim. **A "no longer qualifies" note is a
measurement with an expiry date, not a permanent verdict**; that is the same
rot mode as rule 2 at the bottom of this file, just inverted. Treat these as
live `S`/`M` targets: an endpoint-per-module split behind the same factory
signature, Layer 2, verified by the backend router tests.

**Still does not qualify:** `core/algorithms/base.py` is 572 and already split;
`tools/evolution_report.py` is 274.

Frontend files are covered by **7.3** and **7.5**.

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

*No open proposals: 4.1–4.5 have all shipped (see the Shipped section). This
theme is a good place to add new ideas — it is the one most directly about
making the project pleasant to use.*

---

## Theme 5 — Documentation that sells the project

### 5.1 Visual assets in the README — `S` · ★★★
The project is *visual* and the README has no visuals. Add a screenshot/GIF of
a running tank, plus the evolution-loop and three-layer diagrams (Mermaid is
already rendered inline — see the README). A reader should *see* the tank in the
first scroll.



### 5.3 Generated docs stay generated — `S` · ★
Anything that mirrors code should be generated by a script run in CI, so docs
can't drift from reality. Two halves have shipped:
`tools/generate_algorithm_catalog.py` → `docs/ALGORITHM_CATALOG.md`, and the
benchmark catalog → `docs/BENCHMARK_CATALOG.md`; the smoke gate fails on stale
output for both.

**Remaining candidate — and the 2026-07-25 audit is the evidence for it.**
Every hand-maintained number in this very file had drifted, one by 3x, and
eight proposals described work that was already merged. The generated-doc
pattern is the fix: a checker that flags prose claims which contradict the
tree. Concretely, the cheapest useful version is a smoke-gate test that parses
the file-size table in **2.6** and the `Any` counts in **6.2** and fails when
they disagree with a fresh measurement — the same contract
`test_docs_agent_onboarding.py` already enforces for benchmark paths. The old
48-vs-58 algorithm-count bug and this audit are the same failure mode.

### 5.4 Generate project claims from the code — `S` (first fix) / `M` (checker) · ★★★
Review #3's "generate project claims from the code" item, and the cheapest
★★★ in this file. It flagged that the README's "50+ behavior algorithms"
language "appears inconsistent with the newer composable-behavior
architecture." Re-measured 2026-07-26 — **it is worse than inconsistent, it is
false, and it advertises deleted code:**

```bash
python -c "from core.algorithms.registry import ALL_ALGORITHMS; print(len(ALL_ALGORITHMS))"
```

- `ALL_ALGORITHMS` is **3** (`OpportunisticFeeder`, `FoodQualityOptimizer`,
  `CooperativeForager`).
- `README.md:94` claims "**50+ behavior algorithms** across food seeking,
  predator avoidance, schooling, energy management, territory, and poker
  strategies." **Five of those six categories were deleted by ADR-016** —
  `predator_avoidance.py`, `schooling.py`, `energy_management.py`,
  `territory.py`, `poker.py`, 44 algorithms, ~3,100 lines. The README is
  selling files that are not in the tree.
- `README.md:393` still says "Foundation (58 algorithms, …)".
- `README.md:57` and the Mermaid node at `README.md:47` say "dozens of
  parametrizable behavior algorithms" — also wrong, though they at least point
  at `ALL_ALGORITHMS` as the source of truth.

This is the most damaging class of drift in the repo, because it is the *first*
thing a new reader or agent sees, and an agent that believes it will go looking
for a `territory.py` that ADR-016 deliberately removed.

**Plan.**
1. *(S, do this first, standalone PR.)* Fix the four README sites to describe
   the composable framework plus three survivor foragers, pointing at
   `docs/ALGORITHM_CATALOG.md` (already generated) as the count of record.
   Check `docs/ROADMAP.md` and `docs/VISION.md` for the same claim while you
   are there.
2. *(M.)* Then the checker, per **5.3**: a smoke-gate test that fails when a
   prose claim contradicts a fresh measurement. Start with the claims that have
   a machine-readable source of truth — algorithm count (`ALL_ALGORITHMS`),
   benchmark catalog (`docs/BENCHMARK_CATALOG.md`), file sizes
   (`LEGACY_MAX_LINES`), typing coverage (`pyproject.toml` overrides).

**Also stale, same failure mode, cheap to close:** review #3 noted "a stale open
PR still describes startup and diagnostic functionality that appears to have
already landed." Confirmed — that is
[PR #587](https://github.com/mbolaris/tank/pull/587) (`start.py` +
`diagnose.py`, last touched 2026-06-09), and both halves are recorded in the
Shipped section as **4.1** and **4.2**. It is the only open PR on the repo.
Close it with a pointer to the shipped work.

---

## Theme 6 — Type safety as a guardrail (external review, 2026-07)

The reviewer's point is that in a system built for AI agents to *modify* code,
typing is not cosmetic — it is the guardrail that catches a bad edit before CI
does. Re-measured 2026-07-25: **227 simple `Any` annotation hits** (`: Any`,
`-> Any`, `[Any]`) and **760 plain `Any` occurrences** across `core/`. Both
went *up* since the last count (209 / 688) — `core/` grew faster than the
cleanup passes retired `Any`, so treat 6.2 as a treadmill, not a burn-down. The
global mypy config stays deliberately relaxed (`disallow_untyped_defs = false`,
`check_untyped_defs = true`); strictness is applied per package via overrides
(**6.1**), which is the part that has actually ratcheted.

### 6.1 Tighten mypy one core package at a time — `M` · ★★
**Do not flip strict mode globally** — it will produce hundreds of errors and no
mergeable PR. Instead, pick a package, add a per-module override that turns on
`disallow_untyped_defs = true` for just that path, then fix the fallout. The
override blocks live under the `# Overrides` comment in `pyproject.toml`'s mypy
section. Layer 2; `pre_pr_gate` green is the acceptance bar.

**Already strict** (re-verified 2026-07-25): `core.simulation`, `core.worlds`,
`core.genetics`, `core.transfer`, `core.entities`, `core.spatial`,
`core.solutions`, `core.util`, `backend.state_payloads`, plus
`core.algorithms`, `core.behavior`, `core.config`, `core.energy`,
`core.movement`, `core.parameters`, `core.reproduction`, `core.research`, and
`core.skill`.

**Remaining candidates**, roughly by leverage: `core.poker` (52 files — do it in
sub-package slices, not one PR), `core.minigames` (24), `core.services` (8),
`core.mixed_poker` (7), `core.plant` (6), `core.code_pool` (6),
`core.systems` (6), then the small leaves (`core.actions`, `core.agents`,
`core.brains`, `core.contracts`, `core.events`, `core.evolution`, `core.fish`,
`core.foraging`, `core.modes`, `core.plants`, `core.policies`, `core.pursuit`,
`core.replay`, `core.taxonomy`, `core.telemetry`). Probe the fallout before
sizing a PR: add the override, run `mypy core/ backend/`, and count. Several of
the small leaves are already annotation-clean and cost nothing but the config
block.

### 6.2 Retire `Any` in the hottest core modules — `S` · ★★
Grep `core/` for `: Any`, `-> Any`, and `[Any]` (227 hits re-measured
2026-07-25; note this pattern misses generic-parameterized forms like
`dict[str, Any]`; a plain `\bAny\b` count is 760) and replace the easy ones
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
`core/plant/poker_component.py`, `core/plants/plant_strategy_types.py`, and
`core/algorithms/composable/food_selection.py`, `core/brains/contracts.py`,
`core/cache_manager.py`, and `core/behavior/pursuit_nodes.py`.

**Avoid as a small 6.2 pick:** `backend/state_payloads.py`. Checked 2026-07;
nearly every remaining `Any` is either `to_dict() -> dict[str, Any]` or a
heterogeneous wire-payload field. That file belongs under **7.1** unless the
contract strategy changes.

**Next step:** re-run `rg -n "\bAny\b" core/`, pick one small core module with
mechanical annotations, and keep `mypy core/` green.

---

## Theme 7 — Frontend contracts & performance (external review, 2026-07)

The reviewer rated the frontend the weakest surface relative to its size. Both
halves of that judgement have moved since — re-measured 2026-07-26: **32,668
total lines** across **163 `.ts`/`.tsx` files** (29,924 lines excluding tests),
with **28 test files**. So test coverage roughly doubled since the first review
*and* the surface grew; the ratio is about where it was. The 1,000+ line
renderers are still the concrete tractable piece.

**Review #3 escalated this theme, and its argument is the one to act on.** It
judged that "the frontend is clearly behind the backend" and — importantly —
that *for a project whose long-term success depends on people enjoying and
understanding the ecosystem, this is now a more serious limitation than backend
architecture*. That is a genuine reprioritization: Themes 1, 2, and 6 are about
a codebase agents can safely modify; Theme 7 is about whether anyone wants to
look at what evolves. The backend has 19/20 testing; this surface is where the
missing product points live.

Its specific finding about test *quality* (not quantity) checks out — measured
2026-07-26: **10 of the 28 frontend test files use `renderToString`, and zero
use `@testing-library`.** So the suite asserts on server-rendered strings and
exercises no real interaction, effects, focus behavior, WebSocket recovery,
accessibility, or browser rendering. There is a second, practical reason to
move off that style: React's SSR output interleaves `<!-- -->` marker comments
between adjacent JSX expressions, so a naive `toContain()` spanning two
expressions fails for reasons that have nothing to do with the component. The
assertions are brittle *and* shallow.

### 7.1 Contract test between backend payloads and frontend types — `M` · ★★★ — SHIPPED
Option (b) landed as `tests/test_frontend_payload_contract.py`: it parses the
exported interfaces in `frontend/src/types/simulation.ts` and `payload.ts` and
asserts that every key of a live full/delta payload — and every field of the
twelve backend DTOs — has a frontend declaration. Verified against the tree
2026-07-25; this entry had gone stale, which is exactly the rot the file's
closing rule warns about. Option (a), generating the TS types from the Python
models, remains available if hand-written types become a maintenance burden.

*(7.2 shipped — deltas now emit only changed entities, with wire telemetry to
prove it. See the Shipped section.)*

### 7.3 Split the 1,000+ line renderers — `M` · ★★
Re-measured 2026-07-26 (`wc -l`). Two of the four original targets are done and
two grew. Review #3 named this as step 3 of its path to 95 — "split drawing
primitives, effects, scene objects, and input handling out of the 1,000-line
renderers" — which is a more specific seam list than this entry previously
carried, so it is now the recommended decomposition. Bumped to ★★ on that
basis.

| File | Then | Now |
| --- | ---: | ---: |
| `frontend/src/renderers/petri/PetriTopDownRenderer.ts` | 1,226 | **1,392** |
| `frontend/src/renderers/tank/TankTopDownRenderer.ts` | 1,122 | **1,267** |
| `frontend/src/components/tank_tabs/TankTrendsTab.tsx` | — | **1,203** (new offender) |
| `frontend/src/utils/plants/renderers.ts` | — | **1,042** (new offender) |
| `frontend/src/pages/NetworkDashboard.tsx` | — | **996** (pinned at 1,046) |
| `frontend/src/utils/renderer.ts` | 1,431 | 812 — *split, done* |
| `frontend/src/components/EvolutionBenchmarkDisplay.tsx` | 1,203 | 304 — *split, done* |

Note `NetworkDashboard.tsx` measures 996 against a `LEGACY_MAX_LINES` pin of
1,046 — it has *shrunk* 50 lines since it was pinned. The ratchet permits that
slack silently. If you touch this file, consider re-pinning it down to its
actual size in the same PR so the ceiling keeps ratcheting.

The two petri/tank renderers regrew past where they started, which is the
argument for doing them properly rather than trimming. Same discipline as
Theme 2's Python god-file splits: extract
*obvious* collaborators (e.g. per-entity draw helpers, a legend/HUD module)
behind a thin facade, verified by `npm run build` + existing tests. Split only
where the responsibility boundary is clear — no abstraction for elegance.
**Layer 2.**

### 7.4 One real end-to-end browser path — `M` · ★★★
Step 2 of review #3's path to 95, and the highest-value frontend item in this
file. Confirmed 2026-07-26: **there is no Playwright config, no `e2e/`
directory, and no browser-driven test anywhere in the repo.** Everything the
user actually does — connecting, watching, clicking, building, reconnecting —
is verified by hand or not at all.

**Scope (deliberately one path, not a suite).** The review's proposed
scenario is a good one because it crosses every seam at once: launch a world →
interact with a fish → place an object → switch views → **drop and restore the
WebSocket** → verify persisted state. The reconnect leg is the part worth the
most: `useWebSocket`'s exponential backoff (`computeReconnectDelay`) shipped
under **4.4** and was verified *manually by killing the backend*, which is
exactly the kind of check that silently stops being true.

**Notes for whoever picks this up.**
- Add `@playwright/test` to the frontend only; keep it out of the Python gates.
  Run it in `frontend-ci`, not `smoke-gate` — it is far too slow for a 30s gate.
- Drive a **seeded headless-backed** world so assertions are deterministic;
  reuse the seed discipline the Python side already has. A flaky e2e test will
  get disabled within a month and is worse than none.
- The launch/verify recipe (ports, pause-before-click, the snapshot API for
  reading entity positions, screenshot coordinate scaling) is already worked
  out for manual UI verification — reuse it rather than rediscovering it.
- **Layer 2** — no simulation behavior changes.

### 7.5 De-duplicate shared canvas logic — `M` · ★★
Review #3: "shared canvas logic — color conversion, fish drawing, effects, and
renderer primitives — is still duplicated across the tank, petri, and avatar
renderers." The three consumers are
`frontend/src/renderers/tank/`, `frontend/src/renderers/petri/`, and
`frontend/src/renderers/avatar_renderer.ts`, with candidate shared modules
already sitting adjacent in `frontend/src/utils/`
(`renderer_sprites.ts`, `renderer_effects.ts`, `renderer_background.ts`,
`renderer_svg_fish.ts`).

This is the frontend mirror of Theme 12's insight on the Python side: the same
primitive implemented three times cannot be improved once. It also makes **7.3**
easier — much of what inflates the two big renderers *is* the duplicated
drawing code, so extracting shared primitives and splitting the renderers are
the same PR series approached from opposite ends. Do 7.5 first if you want the
line counts to fall as a side effect. **Layer 2.**

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

Review #2's one confirmed hard defect was fixed in **9.1**; see the Shipped
section for the wheel packaging smoke test. Review #3 (2026-07-26) reopened the
theme with one item — **9.3**, the authentication boundary.

### 9.3 An auth boundary before this is a public multi-user service — `M` · ★★
Step 6 of review #3's path to 95, phrased as a **precondition, not a feature**:
"add an authentication boundary before treating it as a public multi-user
service." Measured 2026-07-26 — the backend's only origin control is
`CORSMiddleware` in `backend/app_factory.py:299`, which is `allow_origins=["*"]`
outside production mode. There is no `HTTPBearer`, no API-key dependency, no
per-request identity anywhere in `backend/`.

That is entirely fine today: the intended deployment is local (`start.py`,
`localhost:8000` + `localhost:3000`). **The risk is drift, not the current
state.** The project has been growing outward-facing surfaces — the Discussion
Board with multi-agent posting and reactions, federation
(`docs/FEDERATION.md`), the network dashboard, world persistence, transfers —
and any one of them being exposed to a network turns "no auth" from a
reasonable default into a real hole. Note the shape of what is already
writable without identity: board posts, world commands, build-mode object
placement, and saved world state.

**Plan.** Do *not* build a user system. The proportionate move is:
1. Decide and write down the deployment posture in `docs/ARCHITECTURE.md` —
   "single-tenant, loopback-only, not hardened for hostile networks" is a
   perfectly good documented answer, and stating it is most of the value.
2. Make the unsafe default hard to reach by accident: bind loopback unless
   explicitly told otherwise, and make non-loopback binding require an
   explicit flag that also demands a shared secret.
3. Only if a genuinely multi-user deployment is wanted, add a single shared
   token dependency in front of the mutating routes and the WebSocket. Read
   routes can stay open.

**Confirm the posture with a maintainer before building anything** — this is a
product decision about what Tank World is meant to be, and step 1 alone may be
the correct and complete answer. **Layer 2.**

---

## Theme 10 — Research instrumentation: make the paper defensible (external review #2, 2026-07)

The review's core message: the "AI agents as evolutionary operators" story is
not defensible until the data pipeline is as real as the system design.

**Every gap the review named now has tooling** (re-verified 2026-07-25): the
attempt ledger and multi-seed matrix (10.1/10.2), held-out evaluators plus the
locked-path check (10.3), the patch taxonomy classifier (10.4), and the non-AI
random-search control arm (10.5) have all shipped. What is still missing is
the *output*: nobody has run the arms against each other and published the
comparison. That is 10.6, and it is now the only open item in this theme.

None of these change simulation behavior — all **Layer 2** — but they touch
scoring/CI infrastructure, so keep each one a separate PR (Rule: Layer 2
changes stay separate from Layer 1 improvements).


### 10.6 Actually run the control-arm comparison — `M` · ★★★
**10.5 built the machinery; nobody has run it.** `tools/non_ai_baseline.py`
proposes deterministic parameter mutations, evaluates them across a seed
matrix through the normal benchmark contract, and logs them to
`research/attempts.jsonl` under the `non-ai-random-search` agent id. The
headline figure the paper needs — "agent attempts vs. random-search attempts,
same benchmark, same seed budget" — is a *result*, not a tool, and it does not
exist yet.

**Plan.** Fix a budget (say N proposals on `ecosystem_health_10k`, seeds
42/7/123), run the baseline arm to completion, and summarise both arms out of
the shared ledger with `tools/summarize_attempts.py`. Report acceptance rate
and score delta per arm. This is the one Theme 10 item whose output is
evidence rather than infrastructure — which is exactly what review #2 said was
missing. **Layer 2** (no simulation change; it only reads the pipeline).

**Review #3 independently reached the same conclusion and quantified it.** Its
finding: "the platform is stronger than the scientific evidence." It credits
the infrastructure by name — frozen poker opponents, frozen soccer teams, the
foraging gym, replay fingerprints, champion provenance, transfer studies, skill
ledgers, validation tooling — and then observes that "the evidence base remains
comparatively small," and that the target-memory transfer result is "promising,
not yet a compelling general demonstration."

The measurement that makes this undeniable, taken 2026-07-26:

```bash
wc -l research/attempts.jsonl   # 16
```

**Sixteen rows.** Theme 10 built an attempt ledger designed to hold hundreds of
logged attempts including failures, and it currently holds sixteen. That single
number is the gap between "credible research platform" (91) and a defensible
paper.

**What review #3 says a defensible claim requires**, which is a stricter and
more useful acceptance bar than the N-proposal budget above — treat it as 10.6's
real definition of done:

- many attempted improvements, not a handful;
- multiple seeds (already supported — `tools/run_bench_matrix.py`, default
  42/7/123);
- held-out evaluators (already shipped — **10.3**);
- **negative results published, not discarded** — the ledger already records
  rejected and errored attempts, so this costs nothing but the discipline of
  running them;
- compute accounting;
- **preregistered success criteria** — decide the bar before running the arm,
  not after seeing the numbers.

Two of those six are pure discipline rather than engineering, which is the
encouraging read: the remaining work here is mostly *running the machine that
already exists* and refusing to file the failures in a drawer.

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

### 11.3 Foraging gym with an oracle ceiling — `M` · ★★★ — SHIPPED
An isolated foraging benchmark: one fish (later a small cohort variant), no
reproduction/poker/ball, a fixed scripted food-spawn schedule per seed.
Compute the **oracle ceiling** on the same spawn script (full-knowledge
greedy planner with energy accounting) and a random-walk floor. Metric:
`energy_collected / oracle_energy_collected` ∈ [0, 1] — pure food-seeking
competence with SOTA = 1.0 by construction, independent of ecosystem config.
The existing ecosystem benchmarks keep measuring the ecosystem; this measures
the skill. Start from `scripts/diagnose_food_seeking.py` for the isolation
setup.

### 11.4 Soccer reference-team ladder — `M` · ★★ — SHIPPED
`benchmarks/soccer/ladder_5k.py` plays the neutral-default soccer substrate
against four frozen teams in `core/minigames/soccer/reference_teams.py`: L0
`stationary_v1`, L1 `random_walk_v1`, L2 `chase_shoot_v1`, L3 `formation_v1`.
Metric is goal difference per 5k-frame match, side-swapped on the same engine
seed and averaged over 3 seeds. Seed-42 baseline: **+58.0 / +48.2 / 0.0 /
-9.5**, skill index 50 (2 of 4 rungs beaten).

Two design notes worth keeping: L2 is a frozen snapshot of the neutral
substrate chaser, so its measured 0.00 both proves the side-swap cancels the
kickoff/formation advantage exactly and makes "goal diff vs L2" read as
"improvement since the freeze". L3 is a scripted role formation rather than
the proposed evolved-team fixture — it beats the all-chase substrate by 9.5
goals a match, so it is a real unbeaten ceiling, and an evolved-team snapshot
can be appended later as L4 without touching L0-L3.

### 11.5 Longitudinal skill ledger + nightly CI append — `M` · ★★★ — SHIPPED
`core/research/skill_ledger.py` + `tools/run_bench.py --record-skill`.
`research/skill_history.jsonl`: one row per
`(timestamp, git_sha, config_hash, domain, rung, metric, seeds, skill_index)`
appended by the nightly benchmark job and by `tools/run_bench.py
--record-skill`. Sits beside `research/attempts.jsonl`; purely observational,
so it never needs re-baselining. This is the dataset every trend
visualization reads. Policy: rulers are immutable — changing one mints a new
rung ID; old rows stay valid.

### 11.6 Skill dashboards: static report + UI panel — `M` · ★★ — PARTLY SHIPPED
`tools/skill_report.py` ships the static text/JSON/HTML report. **The web-UI
"Skill Trends" panel is the open half.** Three views over
`skill_history.jsonl`:
(a) **skill trajectory** per domain — x = date/commit, y = normalized skill,
horizontal bands per ladder rung, config-hash changes as vertical markers;
(b) **ladder matrix** — domains × rungs heatmap (loses / competitive /
beats); (c) **domain radar** — the three skill indices, current vs 30 days
ago. Deliver as `tools/skill_report.py` (self-contained HTML for PRs and
nightly artifacts) first, then a "Skill Trends" panel in the web UI next to
`EvolutionBenchmarkDisplay`. Depends on 11.5.

### 11.7 Freeze the rulers in CI — `S` · ★★ — SHIPPED
`tools/check_locked_paths.py` now covers the poker ladder, foraging gym, and
soccer ladder; read the bootstrap note in the Shipped section before adding a
new ruler. Original scope:
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

**Status as of the 2026-07-25 audit.** 12.1, 12.2, and 12.3 have shipped, and
12.4 has landed behind a default-off flag — further than this section's prose
suggested. **12.5 is the next real step, and it is the go/no-go gate for the
whole theme.** The ADR (`docs/adr/`) recording the encoding decision is still
unwritten; it belongs with 12.5's result, not before it.

### 12.1 Extract steering/sensor primitives into a shared library — `M` · ★★★ — SHIPPED
`core/behavior/primitives/steering.py` exists and is invoked by
`core/algorithms/composable/actions.py`,
`core/algorithms/composable/food_selection.py`, `core/algorithms/base.py`,
`core/code_pool/pool.py` (soccer's `_steer_action`),
`core/behavior/standard_nodes.py`, and the frozen soccer reference teams —
i.e. all three domains plus the graph node set share one implementation, which
was the point.

### 12.4 Foraging graph that reproduces `ComposableBehavior` — `M` · ★★★ — LANDED, UNPROVEN
**Layer 1.** The graph controller exists: `default_foraging_graph()` in
`core/behavior/tank_adapter.py`, installed for founders by
`core/behavior/feature_flags.py` only when `tank.graph_behavior_enabled` is
set, dispatched from `core/movement_strategy.py`, covered by
`tests/core/test_graph_foraging_controller.py`. Two sibling flags,
`target_pursuit_module_enabled` and `target_memory_enabled`, gate the shared
pursuit module and target memory independently so the components can be
ablated separately. All three default to `False`, so the baseline is
byte-identical and no champion moved.

**What is not done:** the flag is off, so nothing selects the graph in
production, and there is no recorded **11.3 foraging-gym** score for the graph
arm vs. the `ComposableBehavior` arm. That comparison is the acceptance
criterion this task was written around — run it and record the result before
treating 12.4 as finished. `ComposableBehavior` stays the reference oracle
either way; do not delete it here.

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

### 12.6 Cross-domain binding: soccer + poker share the middle — `L` · ★★ — SOCCER HALF LANDED
**Layer 1.** The soccer half exists: `core/behavior/soccer_adapter.py` plus
`core/minigames/soccer/policy_adapter.py` bind the shared pursuit module, and
`core/movement/ball_pursuit.py` drives ball pursuit through the same target
memory used for food — the first genuine cross-domain reuse. Transfer is being
measured by `core/pursuit/transfer_gym.py` and the
`core/behavior/target_memory_transfer_*` study modules. **The poker half is
untouched**, and neither half has a recorded **11.4 soccer ladder** delta.

Original scope: add a soccer actuator adapter and bind the *same* interception
subgraph to the ball → measure on the Theme
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

- **6.1 Strict typing for nine more core packages.** `disallow_untyped_defs` /
  `disallow_incomplete_defs` now cover `core.algorithms`, `core.behavior`,
  `core.config`, `core.energy`, `core.movement`, `core.parameters`,
  `core.reproduction`, `core.research`, and `core.skill` — including the two
  packages agents edit most often when proposing Layer 1 improvements. Total
  fallout was seven unannotated functions; `core/behavior/target_memory.py`
  gained a structural `TargetMemoryHolder` Protocol so the module keeps its
  deliberate freedom from entity imports. Annotation-only: no runtime behavior,
  no RNG draw, no champion re-baseline.
- **11.4 Soccer reference-team ladder.** Added
  [`benchmarks/soccer/ladder_5k.py`](../benchmarks/soccer/ladder_5k.py) and the
  frozen rulers in
  [`core/minigames/soccer/reference_teams.py`](../core/minigames/soccer/reference_teams.py)
  (stationary / random-walk / chase-and-shoot / role formation). The rulers are
  self-contained by construction — they never read `soccer_policy_params`, never
  call the shared steering primitives, and register under their own
  `soccer_reference_policy` kind so mutation can never draw a genome onto the
  opponent it is scored against. Wired into the locked-path check, nightly
  determinism + skill-ledger recording, and the champion registry
  (`champions/soccer/ladder_5k.json`, seed 42, score 24.17).
- **11.5 Longitudinal skill ledger.** Added
  `core/research/skill_ledger.py` and `tools/run_bench.py --record-skill`.
  Frozen-ruler benchmarks now emit append-only per-rung rows containing the
  commit, config hash, seed set, metric, and normalized skill index.
- **11.6 Static skill report.** Added `tools/skill_report.py`, which renders
  the current skill index, first-to-latest change, config transitions, and
  latest rung standings as text, JSON, or dependency-free HTML.
- **11.7 Frozen-ruler CI protection.** The poker ladder, foraging gym, and
  soccer ladder are now included in the CI locked-path invocation; nightly
  benchmark CI records the histories and uploads the ledger plus HTML report
  as an artifact.

  **Bootstrap note for whoever adds the next ruler.** The PR that *introduces*
  a ruler necessarily trips `check-locked-paths`: it adds the ruler file and
  edits `tools/check_locked_paths.py`, which is itself permanently locked. So
  is the benchmark, once you add it to the workflow's `--locked` list. There is
  no diff ordering that avoids this — deferring the registration to a follow-up
  PR just moves the failure, because editing the locked list always trips it.
  Apply the `override-locked-paths` label to that one PR; the job's `if:`
  condition then skips it. Note that labeling does **not** re-trigger CI
  (`on: pull_request` defaults to opened/synchronize/reopened) and re-running
  the failed job replays the original event payload without the label — you
  need a fresh push after labeling.
- **4.5 Headless debug-frame/entity tracing.** Added opt-in
  `main.py --debug-frame N` and `--debug-entity ID` tracing. The observable
  path records energy deltas, lifecycle mutations, current-frame events, and
  matching entity snapshots as a versioned JSON document, while ordinary
  headless runs retain the cheap update path.
- **10.5 Non-AI baseline search control arm.** Added
  `tools/non_ai_baseline.py`, which evaluates deterministic parameter mutation
  proposals across a seed matrix using the normal benchmark contract, applies
  mean-plus-majority-of-seeds acceptance, and logs baseline/candidate attempts
  as `non-ai-random-search` without editing source or ruler files.

- **1.4 Multi-seed AI-agent validation.** The code-evolution agent now runs a
  fresh baseline and candidate validation on at least three unique deterministic
  seeds, reports per-seed results plus mean and standard deviation, requires a
  majority of seeds to pass, and records the complete seed list in the attempt
  ledger. The seed matrix is configurable through `--validation-seeds`.
- **7.2 Sparse websocket deltas and wire telemetry.** Delta frames now emit
  only entities whose delta-visible fields changed; newly added entities are
  sent once through their full payload. `StatePublisher.delta_metrics()` and
  debug logging expose total/changed/added/removed entity counts and serialized
  bytes, making the bandwidth win measurable without changing the wire schema.
- **1.6 Smoke-gate dependency diagnostics.** A clean checkout now reports the
  missing development modules and the exact `pip install -e ".[dev]"` command
  needed to make the health check runnable.
- **5.3 Generated benchmark catalog.** Benchmark IDs, module paths, and runtime
  budgets are now extracted from live benchmark modules into
  `docs/BENCHMARK_CATALOG.md`; docs tests fail when the generated catalog is
  stale, and public onboarding points to the generated source of truth.

- **12.3 Dormant `behavior_graph` genome field + interpreter.** Added
  [`core/behavior/graph.py`](../core/behavior/graph.py), an immutable acyclic
  graph format with typed registry validation and a compiler that binds a flat
  execution plan once, outside the per-tick path. `BehavioralTraits` now carries
  an optional graph trait, persisted under schema version 3 only when present
  and inherited without consuming extra RNG for graph-free genomes. The golden
  replay fixture ([`scalar_threshold_v1.json`](../tests/fixtures/behavior_graphs/scalar_threshold_v1.json))
  proves deterministic isolated graph execution. No production fish selects the
  graph yet; existing `ComposableBehavior` remains the live path.
- **12.2 Typed node interfaces + registry.** Added
  [`core/behavior/nodes.py`](../core/behavior/nodes.py), defining the closed
  `Scalar`/`Vector`/`UnitVector`/`EntityRef`/`Bool` vocabulary; the five
  readable node-role Protocols; and a deterministic `NodeRegistry`. The
  registry stores immutable port contracts, validates exact type-compatible
  connections, and serializes every node through one stable envelope. No
  production node, genome, or simulation path is wired yet; focused unit tests
  cover metadata, factory validation, serialization, and connection rejection.
- **11.3 Foraging gym with an oracle ceiling.** Added
  [`benchmarks/tank/foraging_gym.py`](../benchmarks/tank/foraging_gym.py), a
  deterministic single-fish ruler that runs the production neutral
  `ComposableBehavior` food path against a fixed seeded food schedule. It
  reports gross energy collected / attainable oracle energy, plus the frozen
  `random_walk_v1` floor and `full_information_greedy_v1` ceiling in standard
  skill-ladder metadata. The oracle collects every scripted food item under the
  same speed, bounds, and capture rules, so the score's 1.0 ceiling is real.
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
  hard validity gate at 95% starvation mortality, so a starvation-dominated
  ecology cannot become a champion, plus a bonus multiplier for achieving a
  higher max generation (`1.0 + max_generation * 0.05`). The scoring version is
  included in `CONFIG`, forcing an explicit re-baseline instead of silently
  comparing old champion scores. The stale seed-42 champion was retired from
  the active registry because its reproduced result is intentionally invalid
  under this ruler (`starvation_rate=1.0`, score `0.0`); a new active champion
  must come from an eligible result.
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
- **CI: de-duplicated the pre-PR gate.** The old `pre-pr-gate` job ran the smoke
  gate up to three times (a standalone job, embedded in `pre_pr_gate.py`, and
  again via a dedicated smoke-check step), the `worlds` shard at least twice,
  and the full non-slow suite a third time just for coverage (`-n auto`) —
  serialized behind `needs: smoke-gate` so nothing started until smoke
  finished. Replaced with a `pre-pr-shard` matrix job (4 shards, `--xdist
  --workers 2` each, coverage collected inline via `pre_pr_gate.py --coverage`
  honoring `COVERAGE_FILE`) that runs concurrently with `smoke-gate` and a
  standalone `mypy` job; a thin `pre-pr-gate` job (same name, kept for
  branch-protection compatibility) just combines the per-shard coverage data
  and enforces the 70% floor. The CI step that re-ran smoke + `worlds` solely
  to sanity-check `pre_pr_gate.py`'s process-exit cleanliness is now
  `tests/test_gate_common.py::test_exit_for_gate_hard_exits_despite_lingering_non_daemon_thread`,
  a subprocess-based regression test for the same property that runs in
  milliseconds. Also added `concurrency: cancel-in-progress` and pip caching
  across the Python jobs.

---

*Keep this list honest. If a proposal is no longer worth doing, delete it with a
one-line note rather than letting it rot.*

**How this file rots, and the two rules that stop it.** The 2026-07-25 audit
found eight proposals still written as open work whose implementations were
already merged, plus stale numbers throughout. The cause was mechanical: PRs
appended to **Shipped** without deleting the matching body entry, so the file
grew two contradictory accounts of the same task and the body — the half agents
actually read to pick work — silently became fiction.

1. **Shipping a proposal means deleting or marking its body entry in the same
   PR**, not only adding a Shipped bullet. If the entry carries design notes
   worth keeping (Theme 11's rulers are the good example), mark it `— SHIPPED`
   in the heading and keep the prose; otherwise delete it and leave a one-line
   pointer.
2. **Never cite a number you did not just measure.** Every count here is a
   claim about the tree, and the tree moves. Quote the command, or point at a
   machine-enforced source of truth — `LEGACY_MAX_LINES` in
   `tests/test_god_class_limits.py` for file sizes, `pyproject.toml`'s mypy
   overrides for typing coverage, `docs/BENCHMARK_CATALOG.md` for benchmarks.
   **5.3** proposes automating exactly this check, and **5.4** is the concrete
   first fix.
3. **A "no longer qualifies" dismissal expires too.** The 2026-07-26 pass found
   that the previous audit had correctly retired `backend/routers/worlds.py`
   from Theme 2.6 — and the file then grew 76 lines and its factory function is
   ~379 lines today (see 2.6). Removing an entry is itself a measurement with a
   date on it. When you retire something, say what you measured and when, so
   the next reader knows whether to re-check rather than trusting it forever.
