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

**Last audited against the tree: 2026-07-30** (external review #5 pass —
scored the snapshot 95/100 and flagged that this document's own status
entries had drifted; **7.4**, **7.6**, and the leaderboard/ranking half of
**8.1** were marked open after they had already shipped in #911/#912, and are
now corrected. Prior pass 2026-07-28, review #4 — every number that review
cited was re-measured before being written in; all of them checked out. Its
findings became **7.6** and the sharpened acceptance bars in **7.4** and
**8.1**; its verdicts updated **1.0**, **6.2**, **7.3**, and **9.3**. Prior
pass 2026-07-26, review #3 — its stale entries were corrected in **2.6** and
**7.3**, and its findings became **7.4**, **7.5**, **9.3**, plus additions to
**1.0** and **10.6**.)

**Prior audit, 2026-07-25.** That audit found eight proposals
still written as open work whose implementations were already merged (1.4, 1.6,
4.5, 7.2, 10.5, 11.5, 11.7, 12.1), four more that had shipped in part (5.3,
11.6, 12.4, 12.6), and every re-measurable number in Themes 2, 6, and 7 out of
date — one of them by 3x. If you pick
something from here, **verify the premise first** (does the file still have that
many lines? does that tool already exist?) and fix the entry in the same PR if
it has drifted. See the closing rule at the bottom of this file.

**Best current starter picks:**

- **8.1** — the ranking/leaderboard half is shipped (#912); the remaining
  `repro_reward_mode="credits"` semantics decision needs a maintainer call.
- **1.0** — cross-machine determinism: the genetics mutation path is fixed
  (polar-method `gauss`, #914). A 2026-07-31 investigation narrowed the
  remaining 34 `math.cos` call sites to 8 confirmed score-sensitive ones on
  CI-gated benchmarks (see `docs/CROSS_PLATFORM_DIVERGENCE.md`), but 1.0's
  own CI-run-to-run instability (a separate, unresolved problem) is still the
  higher-priority open half.

**Note the shape of that list.** With **7.3**, **7.4**, and **7.6** all
shipped, what remains here is one item blocked on a maintainer product
decision and one genuinely hard open research problem — there is no longer a
queue of pick-up-and-go infrastructure work. That is the state review #5
(2026-07-30) predicted and prescribed for: *"stop infrastructure work for a
while and run the research campaign."* An agent arriving here looking for the
next task should read that as the instruction it is, and go produce a
documented sequence of attempted ecosystem improvements — **including the
failures** — rather than searching this file for another refactor.

(**7.4** and **7.6**, the Playwright CI gate and the Node runtime pin, shipped
in #911 on 2026-07-29.)

**Explicitly deprioritized:** review #4's closing advice — "do not spend the
next several PRs only retiring more `Any` annotations. That cleanup is healthy
… but it has reached diminishing returns compared with determinism,
browser-level verification, and making the game clearer and more fun." **6.2**
stays open as background maintenance, not a starter pick.

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

> **A fourth external review (2026-07-28) scored the snapshot 93/100** — up
> from 91, and it named the renderer extraction (**7.3**/**7.5**) as the work
> that earned both points: maintainability moved 15/20 → **17/20** ("the plant
> and trends split used sensible responsibility boundaries rather than creating
> dozens of arbitrary fragments"; the canvas-operation trace is "much better
> than merely moving duplicated methods into differently named files"). Every
> other subscore held: architecture 18/20, correctness/reproducibility 16/20
> ("better diagnostics, but cross-machine determinism is still unresolved"),
> testing & CI 19/20 ("Playwright added, but not yet a meaningful CI gate"),
> research rigor 13/15 ("evidence campaign still limited"), product/docs/
> security 10/15. It independently executed the gates: 73/73 curated smoke,
> 596/596 architecture/determinism, 365 worlds, 936 evolution, 222
> backend/tools, 20 core-infrastructure tests, plus compileall and a clean
> wheel build; it could not run ruff/black/mypy/frontend tests (mirror
> failures again) and again declined to hold that against the repo.
>
> Its path to 95, in its own priority order, mapped to tasks here: finish the
> Playwright path and put it in CI (**7.4**), fix the frontend CI Node runtime
> mismatch it found (**7.6**, new), remove reproduction bookkeeping from the
> player leaderboards and settle one soccer ranking formula (**8.1**), solve
> cross-machine divergence (**1.0**), and split `NetworkDashboard.tsx`
> (**7.3**). Its one *negative* instruction is recorded in the starter-picks
> section above: `Any` retirement (**6.2**) has hit diminishing returns.
> Verdict: "93 is deserved. A credible 95 is close, but the unfinished items
> are substantive — not cosmetic."

> **A fifth external review (2026-07-30) scored the snapshot 95/100** — up
> from 93. It confirmed **7.4** and **7.6** shipped (testing & CI moved
> 19/20 → **20/20**) and the **8.1** leaderboard/ranking half shipped
> (correctness/reproducibility 16/20 → **17/20**); architecture 18/20,
> maintainability 17/20, and research rigor 13/15 held; product/docs/security
> held at 10/15. Its stopping point: the polar-method `gauss` fix (**1.0**,
> shipped as #914) removed the worst source of cross-machine divergence but
> not the whole property — it counted ~35 remaining `math.cos` call
> sites in `core/` of unverified impact — and it found this document itself
> had drifted (7.4/7.6 marked open after shipping, the Node version
> mismatched between README/CI/package.json, this file's own status stale).
> Its named path to 95→97: finish the cross-machine `math.cos` investigation
> (**1.0**) rather than blanket-replacing every call site, split
> `NetworkDashboard.tsx` (**7.3**), and — its strongest instruction —
> **stop adding infrastructure and run a research campaign** with the
> platform that already exists, documenting both wins and failures.

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

**Instrumentation status — the five-part identification is now complete.**
Benchmark fingerprint streams (v2) record, every interval: exact and
6-decimal-rounded snapshot hashes, entity-type component hashes/counts, an
environment manifest, **a digest per entity id**, **a digest per (entity type,
state field)**, **a digest of every distinct `random.Random` state**, and **a
digest after every pipeline step** plus one before the first step. Ecosystem
champion verification runs twice, compares the streams within CI, and uploads
both streams for comparison with local runs.
`tools/compare_fingerprint_streams.py` renders the identification review #3
asked for — frame, phase, entity, RNG stream, state field — instead of a digest
mismatch:

```
exact  : diverged at frame 1500
  phase:  environment  [step_digests]
  rng:    verdict=float_drift diverged_streams=none
          RNG states match at this checkpoint, so both runs made the same
          decisions and drew the same numbers; the difference is arithmetic.
  entity: 1 changed: 1
  field:  fish: energy
```

**The RNG verdict is the load-bearing part.** Identical RNG states with
differing snapshots means both runs took the same branches and drew the same
numbers, so the difference is *arithmetic* — a libm question (see
`docs/CROSS_PLATFORM_DIVERGENCE.md`). Differing RNG states means a decision
went the other way and the draw schedules desynchronised, which is a
control-flow question. Those two need entirely different investigations, and
the old report could not tell them apart.

**Two-pass workflow.** Checkpoints every N frames locate the divergence to a
window and name the entity, field and RNG verdict immediately; the phase reads
`carried_in_from_earlier_frame` whenever the difference predates the checkpoint
frame. Re-run both sides with `--fingerprint-every 1` across that window to
land on the exact phase. The report says so itself when it applies.

*Validated by construction, not by assertion:* `survival_5k` was re-run with
(a) a 1e-9 nudge to one fish's energy and (b) one extra draw burned from the
shared RNG. The first is reported as `float_drift`, one changed entity, field
`energy`; the second as `rng_desync` on the `world` stream with 235 entities
changed. `tests/test_fingerprint_stream.py` pins the same behaviour against the
real engine, including that recording does not perturb the run it measures.

**Remaining plan.** The diagnostics are now sufficient; what is left needs
*two differing machines*, which a single dev box cannot supply. Compare the
uploaded CI streams against a local run, read the verdict, and act on it:
`rng_desync` points at a decision that consumed different draws (bisect the
branch), `float_drift` points at arithmetic (bisect the libm call, starting
from the eight score-sensitive `math.cos` sites in
`docs/CROSS_PLATFORM_DIVERGENCE.md`). Narrow the phase with a
`--fingerprint-every 1` re-run over the window, eliminate the environment
input, then re-land the food-targeting improvement (the revert preserved it in
git history at `e1fed26`; it beat both tank champions on every local
environment).

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
   **All three gaps are now closed** (see the instrumentation status above);
   what remains of this item is running the comparison across machines, not
   building the means to.

Its reasoning for the priority is the ALife-specific one, and it is correct:
for an ordinary game, run-to-run float divergence is tolerable; for an
evolutionary framework where small trajectory differences compound across
generations, it is a fundamental scientific concern. Note the interaction with
Theme 11 — ladder metrics are longitudinally comparable *by construction*, so
they partially insulate the skill story from this problem, but champion
trajectories are not insulated at all.

**Review #4 (2026-07-28) held correctness at 16/20 specifically over this
item** and drew the line between diagnostics and a solution: "the new
fingerprint streams and environment manifests make the problem easier to
investigate. They do not solve it." It restated the same five-part
identification requirement (earliest divergent frame, phase, entity, RNG
stream, state field) and kept this "the largest technical issue because
evolutionary trajectories amplify tiny differences." Nothing about the plan
changes — the instrumentation credit is banked; the remaining work is running
the comparison and closing the gaps (*phase*, *RNG stream*, *state field*)
the instrumentation does not yet identify.

**Related but distinct: Windows-vs-Linux divergence is understood, not this
item's CI-run-to-run instability.** `docs/CROSS_PLATFORM_DIVERGENCE.md`
(#913, 2026-07-29) found and #914 partly fixed a *different* determinism gap —
`math.cos`/`math.tan` disagree in the last ulp between Windows and CI's Linux,
which made every genetic mutation platform-dependent via `random.gauss`
(fixed). A 2026-07-31 follow-up investigation (`tools/audit_cos_call_sites.py`)
narrowed the remaining 34 `math.cos` call sites to exactly 8 that are reached
by CI-gated benchmarks (`tank/survival_5k`/`ecosystem_health_10k`,
`soccer/training_5k`/`ladder_5k`) and confirmed all 8 are score-sensitive; the
other 26 are either unreached by any benchmark or only reached by non-gated
research gyms. See that doc's "What remains" section for the full breakdown.
None of that explains *this* item's CI-to-CI (same platform, same code)
instability, which is a separate open investigation.

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
| `core/transfer/entity_transfer.py` | 800 | Not on the original list; grew into it since. |
| `core/spatial/grid.py` | 795 | Hot path — split only if a clean seam exists; never at a performance cost. |
| `core/mixed_poker/interaction.py::play_poker` | 361-line method (file 728) | Grew from the ~336 the review measured. Extract per-street/settlement helpers; behavior-preserving, verify with champion reproduction. |

**The router factories are back, and this was a cautionary tale — now
shipped (2026-07-26).** The 2026-07-25 audit retired `backend/routers/worlds.py`
from this list on the grounds that the file was 356 lines total, so the
~300-line factory function review #2 described could not exist. Review #3
flagged "router factory functions exceeding 350 lines" anyway, and a
2026-07-26 re-measurement found both factories had regrown past the
dismissal: `setup_worlds_router` to ~379 lines (file 432) and
`create_solutions_router` to ~366 lines (file 418), confirming **a "no longer
qualifies" note is a measurement with an expiry date, not a permanent
verdict** (same rot mode as rule 2 at the bottom of this file, just
inverted). Both were split the same day into `backend/routers/worlds/` and
`backend/routers/solutions/` packages (models + one module per endpoint
group + a thin assembling `__init__.py`, largest file 152 lines); see the
Shipped section for the reachability bug the split uncovered.

**Still does not qualify:** `core/algorithms/base.py` is 572 and already split;
`tools/evolution_report.py` is 274; `backend/state_payloads.py` was split into
`backend/state_payloads/` (largest module 310 lines) — see the Shipped section.

Frontend files are covered by **7.3** and **7.5**.

## Theme 3 — Consolidate the algorithm library

Complete. Stage 1 (metadata deprecation) and stage 2 (11 food-seekers removed,
champions re-baselined) shipped under ADR-006; ADR-016 then removed the five
remaining vestigial monolith categories (44 legacy algorithms — predator avoidance,
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

### 5.1 Visual assets in the README — `S` · ★★★ — SHIPPED (2026-07-26)
The README now opens with an original wide ecosystem illustration at
[`docs/assets/tank-world-hero.png`](assets/tank-world-hero.png), making the
project legible before readers reach the explanatory text. The existing Mermaid
diagrams already cover the evolution loop and three-layer model. The image is
deliberately labelled as an illustration, not represented as a product
screenshot; add a live UI capture only when it can be refreshed alongside
meaningful UI changes.



### 5.3 Generated docs stay generated — `S` · ★ — SHIPPED (2026-07-27)
Anything that mirrors code should be generated by a script run in CI, so docs
can't drift from reality. Three parts have shipped:
`tools/generate_algorithm_catalog.py` → `docs/ALGORITHM_CATALOG.md`, the
benchmark catalog → `docs/BENCHMARK_CATALOG.md`, and automated doc freshness checks
in `tests/test_docs_agent_onboarding.py` which verify that the line-count table pins
in **2.6** match `LEGACY_MAX_LINES` and the `Any` count claims in **Theme 6** match
a fresh scan of `core/`. The smoke gate fails on stale output for all three.

### 5.4 Close the stale open PR — `S` · ★ — SHIPPED (2026-07-26)
[PR #587](https://github.com/mbolaris/tank/pull/587) (`start.py` +
`diagnose.py`) was closed without merging at 2026-07-26T17:11:08Z. Its already
shipped functionality remains recorded as **4.1** and **4.2** below. The open
PR query is now empty, so this item is historical context rather than an
actionable starter task.

---

## Theme 6 — Type safety as a guardrail (external review, 2026-07)

The reviewer's point is that in a system built for AI agents to *modify* code,
typing is not cosmetic — it is the guardrail that catches a bad edit before CI
does. Re-measured 2026-07-28: **227 simple `Any` annotation hits** (`: Any`,
`-> Any`, `[Any]`) and **663 plain `Any` occurrences** across `core/`. Both


went *up* since earlier counts — `core/` grew faster than the
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

**Already strict** (re-verified 2026-07-26): `core.simulation`, `core.worlds`,
`core.genetics`, `core.transfer`, `core.entities`, `core.spatial`,
`core.solutions`, `core.util`, `backend.state_payloads`, plus
`core.algorithms`, `core.behavior`, `core.config`, `core.energy`,
`core.movement`, `core.parameters`, `core.reproduction`, `core.research`,
`core.skill`; the small-leaves batch — `core.actions`, `core.agents`,
`core.brains`, `core.contracts`, `core.events`, `core.evolution`, `core.fish`,
`core.foraging`, `core.modes`, `core.plants`, `core.policies`, `core.pursuit`,
`core.replay`, `core.taxonomy`, `core.telemetry` (fallout was exactly two
annotations); the next tier by leverage — `core.services`,
`core.mixed_poker`, `core.plant`, `core.code_pool`, `core.systems` (fallout
was three annotations, all in `core.plant`/`core.systems`; `core.services`,
`core.mixed_poker`, and `core.code_pool` were already fully clean); and,
closing out the last two named candidates, `core.poker` (52 files) and
`core.minigames` (24 files) — fallout was 38 annotations across 13 files,
all missing return types (`-> None` in every case but two), plus two latent
bugs the annotations surfaced: `core/poker/evaluation/auto_evaluate_poker.py`
assigned a raw `int` from `MultiplayerGameState.current_round` into a
`BettingRound`-typed attribute (now wrapped `BettingRound(...)`), and a
nested helper in `core/minigames/soccer/league_runtime.py` was passed
`LeagueTeam` values but had no annotation to catch it (fixed, not
`TeamAvailability` as the dict's declared-`Any` values briefly looked like).
See the Shipped section.

**No remaining candidates.** Every package under `core/` now carries the
`disallow_untyped_defs = true` override; 6.1 is complete as a backlog item.
Future work here is maintenance — new packages should pick up the override
when they're created, not accumulate untyped defs first.

### 6.2 Retire `Any` in the hottest core modules — `S` · ★★
Grep `core/` for `: Any`, `-> Any`, and `[Any]` (227 hits re-measured
2026-07-25; note this pattern misses generic-parameterized forms like
`dict[str, Any]`; a plain `\bAny\b` count is 529) and replace the easy ones
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
`core/cache_manager.py`, `core/behavior/pursuit_nodes.py`,
`core/simulation/debug_trace.py`, `core/services/stats/selection_quality.py`,
`core/genetics/trait.py`, `core/simulation/event_managers.py`,
`core/entities/predators.py`, `core/code_pool/safety.py`,
`core/replay/fingerprint_stream.py`, `core/minigames/soccer/selection.py`,
`core/genetics/genome_codec.py`, `core/util/enum_utils.py`,
`core/simulation/profiler.py`, `core/solutions/config_hash.py`,
`core/statistics_utils.py`, `core/research/skill_ledger.py`,
`core/worlds/interfaces.py`, `core/environment.py`, `core/ecosystem.py`,
`core/solutions/models.py`, `core/code_pool/genome_code_pool.py`,
`core/simulation/engine.py`, `core/policies/interfaces.py`,
`core/code_pool/sandbox.py`, `core/skill/ladder.py`,
`core/worlds/contracts.py`, `core/interfaces.py` (result param → `object`),
`core/replay/jsonl.py`, and `core/worlds/shared/identity.py`.

**Avoid as a small 6.2 pick:** `backend/state_payloads/` (split from the single
file into a package — see the Shipped section). Checked 2026-07; nearly every
remaining `Any` is either `to_dict() -> dict[str, Any]` or a heterogeneous
wire-payload field. That surface belongs under **7.1** unless the contract
strategy changes.

**Next step:** re-run `rg -n "\bAny\b" core/`, pick one small core module with
mechanical annotations, and keep `mypy core/` green.

---

## Theme 7 — Frontend contracts & performance (external review, 2026-07)

The reviewer rated the frontend the weakest surface relative to its size. Both
halves of that judgement have moved since — re-measured 2026-07-26 after the
renderer de-duplication landed: **32,789 total lines** across **173
`.ts`/`.tsx` files**, with **30 test files**. So test coverage roughly doubled
since the first review *and* the surface grew; the ratio is about where it was.
The renderers, the trends tab, the plant drawing library, and (2026-07-31)
`NetworkDashboard.tsx` are all split (see **7.3**/**7.5**); no frontend file
is near 1,000 lines any more. The largest are now `types/simulation.ts` (901,
a type declaration file) and `utils/renderer.ts` (807).

**Review #3 escalated this theme, and its argument is the one to act on.** It
judged that "the frontend is clearly behind the backend" and — importantly —
that *for a project whose long-term success depends on people enjoying and
understanding the ecosystem, this is now a more serious limitation than backend
architecture*. That is a genuine reprioritization: Themes 1, 2, and 6 are about
a codebase agents can safely modify; Theme 7 is about whether anyone wants to
look at what evolves. The backend has 19/20 testing; this surface is where the
missing product points live.

Its specific finding about test *quality* (not quantity) checks out — measured
2026-07-26: **10 of the 30 frontend test files use `renderToString`, and zero
use `@testing-library`.** So the suite asserts on server-rendered strings and
exercises no real interaction, effects, focus behavior, WebSocket recovery,
accessibility, or browser rendering. There is a second, practical reason to
move off that style: React's SSR output interleaves `<!-- -->` marker comments
between adjacent JSX expressions, so a naive `toContain()` spanning two
expressions fails for reasons that have nothing to do with the component. The
assertions are brittle *and* shallow.

**A third style now exists and is worth copying.** The canvas renderers had the
same problem in a worse form — nothing to assert on at all, so their tests
re-derived arithmetic copied out of the renderer, which passes even when the
renderer is deleted. `renderers/testing/canvasTrace.ts` records every canvas
call, state assignment and gradient colour stop a renderer emits, so
`renderers/topDownRenderTrace.test.ts` can pin the *output* of a whole frame.
That is what made the 7.3/7.5 extraction provable rather than eyeballed, and it
is reusable for any future renderer work.

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

### 7.3 Split the 1,000+ line renderers — `M` · ★★ — SHIPPED (2026-07-31)
Re-measured 2026-07-27 (`wc -l`) after splitting the two files this entry had
flagged as "open" (neither is canvas work, so neither used `renderers/shared/`
from **7.5** — each got its own facade):

| File | Original review | Before this PR | Now |
| --- | ---: | ---: | ---: |
| `frontend/src/renderers/petri/PetriTopDownRenderer.ts` | 1,226 | 1,392 | **569** — *done* |
| `frontend/src/renderers/tank/TankTopDownRenderer.ts` | 1,122 | 1,267 | **405** — *done, off the ratchet* |
| `frontend/src/renderers/avatar_renderer.ts` | — | 555 | **300** — *done, off the ratchet* |
| `frontend/src/utils/renderer.ts` | 1,431 | 812 | 807 — *split, done* |
| `frontend/src/components/EvolutionBenchmarkDisplay.tsx` | 1,203 | 304 | 304 — *split, done* |
| `frontend/src/components/tank_tabs/TankTrendsTab.tsx` | — | 1,203 | **700** — *split, off the ratchet at 1,203, re-pinned at 700* |
| `frontend/src/utils/plants/renderers.ts` | — | 1,042 | **10** — *done, off the ratchet entirely* |
| `frontend/src/pages/NetworkDashboard.tsx` | — | 996 | **278** — *done, off the ratchet entirely* |

`TankTrendsTab.tsx` split into `trendUtils.ts` (pure aggregation:
`buildTrendPoints`, `calculateTrend`, trait/threshold constants — 217 lines)
and `TrendUiPrimitives.tsx` (the presentational primitives: `StatTile`,
`Sparkline`, `ChartCard`, `LegendKey`, `ReadoutCard`, `TrendBadge`,
`CustomTooltip` — 342 lines), leaving the component itself as a 700-line facade
over both. Still legacy-pinned (700 > the 500-line new-file limit) because the
render body genuinely has nine distinct chart cards plus a KPI/readout strip —
further extraction would fragment one cohesive view rather than separate
concerns, so 700 is where this entry stops rather than gold-plating.

`plants/renderers.ts` split cleanly because its six plant-model renderers
(`_renderMandelbrotPlant`, `_renderClaudePlant`, `_renderAntigravityPlant`,
`renderGptCodexPlant` + its `drawCodexSegment` helper, `_renderGptPlant`,
`renderSonnetPlant`) shared no logic with each other beyond the common
`helpers`/`textures`/`lsystem` imports — each is now its own module under
`utils/plants/renderers/` (142–211 lines), with `renderers.ts` reduced to a
10-line re-export barrel so `plant.ts`'s existing imports needed no changes.
`sonnetCache`/`gptCodexCache` moved to live beside the renderer that owns
them (`sonnet.ts`/`gptCodex.ts`) rather than in the barrel.

Verified with `npm run build` (tsc -b + vite build, clean), `npx vitest run`
(30 files / 160 tests, all passing — unchanged from before the split, so no
behavior moved), and `npm run lint` (clean, confirming no dead imports from the
extraction). Pure code motion: no JSX, styling, or computation changed, only
which file it lives in. **Layer 2**: frontend only, no simulation behavior, no
champion touched.

**`NetworkDashboard.tsx`, the last one (2026-07-31).** 996 → **278**, and off
`LEGACY_MAX_LINES` entirely. Split into `pages/network/`: `TankCard.tsx` (331 —
one tank's card, owning its own snapshot polling and pause/fast-forward
commands), `ServerCard.tsx` (166 — one server's header plus its tank grid),
`CreateTankForm.tsx` (152), `MiniPerformanceChart.tsx` (124 — the pure poker
SVG chart), and `types.ts` (15 — the two shared auto-eval player aliases). The
page shell keeps server fetching, create/delete, and the loading/error/empty
states.

The seams were not invented for this split: the existing CSS module's class
names already partitioned along exactly these lines (`server*` on one side,
`tank*` on the other, page-shell classes on a third), which is what made four
files the natural answer rather than an arbitrary count. Form field state
deliberately stayed in the page rather than moving into `CreateTankForm` —
the form is conditionally rendered, so owning it locally would silently
discard a half-typed name on cancel-and-reopen. That behavior was verified in
the running UI after the split (typed a name, cancelled, reopened, confirmed
the value survived), along with the server card, tank card, and form all
rendering against live data.

Verified with `npm run build` (clean), `npx vitest run` (30 files / 160 tests,
unchanged), `npm run lint` (clean), and `pytest tests/test_god_class_limits.py`
(both tests, including the `test_legacy_list_is_current` harvest check that
*requires* removing the pin once a file drops under 500). Pure code motion —
no JSX, styling, or computation changed.

**Review #4 (2026-07-28) promoted this remainder to its path-to-95 list**,
naming `NetworkDashboard.tsx` "the final nearly 1,000-line frontend
component" — and credited the completed splits in this entry as the work that
moved maintainability 15/20 → 17/20. The praise is worth keeping because it
names the standard for the last split: "sensible responsibility boundaries
rather than … dozens of arbitrary fragments," with output protected by a
trace or existing tests rather than eyeballed.

Same discipline as Theme 2's Python god-file splits: extract *obvious*
collaborators behind a thin facade, verified by `npm run build` + existing
tests. Split only where the responsibility boundary is clear — no abstraction
for elegance. **Layer 2.**

### 7.4 One real end-to-end browser path — `M` · ★★★ — SHIPPED (2026-07-29, #911)
Step 2 of review #3's path to 95. The first real Chromium path now lives in
`frontend/e2e/tank-flow.spec.ts`, driven by `frontend/playwright.config.ts` and
run with `npm run test:e2e`. It starts the real backend and Vite app, waits for
the live WebSocket connection, enters Build, selects a placement option, and
returns to Watch. That replaces the prior zero browser-driven tests without
putting a browser dependency in the Python smoke gate.

**Remaining — review #4 (2026-07-28) audited the spec and itemized exactly
what it does not yet do.** Its verdict: "legitimate — but incomplete … a
useful foundation," and it withheld a testing point over it. The checklist,
verified against `frontend/e2e/tank-flow.spec.ts` on 2026-07-28 (all six
still true):

1. It does not actually **place** the object (it selects Algae Reef and
   returns to Watch without clicking the canvas).
2. It does not **interact with a fish**.
3. It does not **switch worlds or views**.
4. It does not **break and restore the WebSocket** — still the highest-value
   leg, see below.
5. It does not **verify persistence**.
6. **`.github/workflows/ci.yml` does not run `npm run test:e2e`** (verified
   2026-07-28: no workflow references it), so the test exists but gates
   nothing. Review #4's first path-to-95 step is "finish Playwright *and put
   it in CI*."

Treat items 1, 4, 5, and 6 as this task's definition of done — placement
verified from live world state, a deliberate WebSocket drop/restore, persisted
state checked after reconnect, and the suite wired into `frontend-ci`. Items
2 and 3 are worth having but are not what the review is withholding the point
over.

**Done, #911 (2026-07-29).** `frontend/e2e/tank-flow.spec.ts` now clicks the
canvas to actually place the Algae Reef, confirms it reached backend world
state over a throwaway WebSocket, does a full page reload (new document, new
WebSocket) to verify the object survived, and re-selects it through the UI —
covering items 1, 4, and 5. `frontend-ci` runs `npm run test:e2e`
(`.github/workflows/ci.yml:226`), closing item 6. Writing the test also
surfaced two real bugs, fixed in the same PR: new clients could receive a
cached delta instead of full state, and object placement while paused was
silently dropped. Items 2 (interact with a fish) and 3 (switch worlds/views)
remain open but are not blocking, per the note above.

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

### 7.5 De-duplicate shared canvas logic — `M` · ★★ — SHIPPED (2026-07-26)
Review #3: "shared canvas logic — color conversion, fish drawing, effects, and
renderer primitives — is still duplicated across the tank, petri, and avatar
renderers."

`frontend/src/renderers/shared/` is now the single implementation, consumed by
all three: `canvasPrimitives.ts` (seeded RNG, hue mapping, blob/capsule paths,
`roundRect` fallback), `microbeAvatar.ts` (the gene-driven organism plus the
trait cues), `microbeScenery.ts` (predator, substrate), `topDownHud.ts` (energy
bars, death badges, birth bursts, poker arrows, selection ring) and
`foodAvatar.ts` (the food sprite table that has to track
`core/constants.py`). `avatar_renderer.ts` also stopped carrying its own copy
of `hslToRgb`, which already existed in `utils/renderer_sprites.ts`.

Three findings worth keeping:

- **The duplication was worse than "primitives".** `drawMicrobe` existed three
  times at ~175 lines each and the trait cues twice at ~80; the header comment
  on one copy literally read "(Copied from microbe_renderer.ts)".
- **The copies had silently drifted**, which is the cost this task existed to
  stop. The tank predator grew capsid facet lines and tail rings; the petri one
  grew a core dot and a pulsing tail. Rather than pick a winner behind the
  reader's back, the shared function takes a named style record
  (`TANK_PREDATOR_STYLE` / `PETRI_PREDATOR_STYLE`) that documents the
  difference and can be collapsed deliberately. Same for the food sprite's
  size/glow constants.
- **`utils/renderer_effects.ts` is *not* a fourth copy** and was left alone: it
  is the side view's deliberately chunkier visual language (6px bars, floating
  hearts), not accidental duplication.

Verified by `renderers/topDownRenderTrace.test.ts`, which pins the full canvas
op trace of a fixture world; see the Shipped section for the three reviewed
deltas. **Layer 2.**

### 7.6 Frontend CI runs an unsupported Node runtime — `S` · ★★ — SHIPPED (2026-07-30)
**Found by review #4 (2026-07-28), verified against the tree the same day.**
The lockfile's `react-router` 8.3.0 entry declares `engines: { node:
">=22.22.0" }`, but both frontend workflow jobs pin `node-version: '20'`
(`.github/workflows/ci.yml:173` and `:210`), and `frontend/package.json` has
no `engines` field at all. npm treats an engines mismatch as a warning rather
than a failure by default, so CI is green while exercising an explicitly
unsupported runtime — the review's phrasing. The failure mode this invites is
nasty: a dependency starts using a Node 22 API, local dev (on newer Node)
stays green, and CI either breaks confusingly or — worse — keeps passing
builds that break for users on the documented runtime.

**Plan (one small PR):**
1. Bump both `node-version` pins in `ci.yml` to `'22.22'` or later (a plain
   `'22'` resolves to the latest 22.x, which is ≥22.22 — acceptable, but the
   explicit pin documents *why*).
2. Add `"engines": { "node": ">=22.22.0" }` to `frontend/package.json` so the
   requirement is declared at the project level, not just inherited invisibly
   from a transitive lockfile entry.
3. Note the required Node version wherever local setup is documented
   (README/onboarding), so local and CI run the same major version — the
   review asked for exactly this alignment.

Review #4 suggested folding this into "the same frontend-infrastructure pass"
as **7.4**'s CI wiring; that pairing is sensible if one PR stays reviewable.
**Layer 2** — no simulation behavior, no champion touched.

**Done.** #911 (2026-07-29) bumped both `node-version` pins in `ci.yml` to
`'22.22.0'` (items 1). This doc-consistency pass (2026-07-30) added
`"engines": { "node": ">=22.22.0" }` to `frontend/package.json` (item 2) and
updated the Node requirement in the README quick-start (item 3).

---

## Theme 8 — Product-facing meaning (external review, 2026-07)

### 8.1 Decide soccer reward semantics; bury repro-credit bookkeeping — `M` · ★★★ — PARTLY SHIPPED (2026-07-29, #912)
**Problem.** The encapsulation half of this review item is shipped: soccer
reward code now uses the public `reproduction_component` accessor. The
remaining smell is semantic: "repro credit" is internal simulation bookkeeping
leaking toward player-facing achievement. The player-facing model should be
goals, assists, wins, tank identity, and net energy.

**Review #4 (2026-07-28) escalated this from a smell to a contradiction** —
"the soccer UI still contradicts your product direction" — and put it on the
path to 95 (impact raised ★★ → ★★★ accordingly). Its two findings, both
verified against the tree 2026-07-28:

1. **Reproduction bookkeeping is still on the player leaderboards.**
   `frontend/src/components/MinigameLeaders.tsx` appends `— N offspring` to
   both the poker rows (line 106) and the soccer rows (line 139), despite the
   stated direction that reproduction bookkeeping should not clutter the
   leaderboard. The file's own doc comment already states the right model:
   "winning shows up here as wins, goals, and net energy earned."
2. **The soccer ranking formula buries wins.** `SoccerFishStatsTracker
   ._sort_key` (`core/minigames/soccer/fish_stats.py:114`) ranks by
   goals → assists → net energy → wins → matches. The review's judgement:
   "goals and assists should matter heavily, but wins should not be almost
   irrelevant" — as a near-final tiebreaker, a fish that wins constantly but
   rarely scores can sit below a scorer on losing teams indefinitely.

   For context when deciding: the reward economy already weights these
   (`core/config/soccer.py:47-50` — 25 energy per goal, 15 per assist, 5 per
   team win, capped at 70 per match), which the review called "substantial";
   the open question is only what the *displayed standings* sort by. One
   clean, explicitly chosen formula, written down next to `_sort_key`, is the
   deliverable — not necessarily a different one.

**Done, #912 (2026-07-29).** Both `S` items are shipped: `MinigameLeaders.tsx`
no longer appends an `offspring` suffix to either panel, and
`SoccerFishStatsTracker._sort_key` (`core/minigames/soccer/fish_stats.py:135`)
now ranks by the single published `contribution_score` (goal 3.0 > assist 2.0
> win 1.5 > draw 0.5, energy heavily discounted), replacing the old
lexicographic tuple where `wins` was an almost-never-reached tiebreaker. The
rationale is recorded in a docstring on `_sort_key`.

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

**Review #4 (2026-07-28) re-affirmed both halves of this framing:** "no
authentication or authorization boundary … acceptable for a personal/local
simulation, but not for exposing world mutation, commentary, intervention,
and WebSocket controls as a public multi-user service. The backlog accurately
records that limitation." It did not put auth on its path to 95 — so this
stays a documented posture decision, not urgent engineering, unless the
deployment story changes.

---

## Theme 10 — Research instrumentation: make the paper defensible (external review #2, 2026-07)

The review's core message: the "AI agents as evolutionary operators" story is
not defensible until the data pipeline is as real as the system design.

**Every gap the review named now has tooling** (re-verified 2026-07-25): the
attempt ledger and multi-seed matrix (10.1/10.2), held-out evaluators plus the
locked-path check (10.3), the patch taxonomy classifier (10.4), and the non-AI
random-search control arm (10.5) have all shipped. The *output* was the gap,
and as of 2026-09-10 the control arm has been run and published: forty
candidates, every one committed under `research/control_arm/` with its
mutation plan and per-seed scores. See 10.6 for the numbers, including the
finding that seven eighths of the arm's apparent gain is overfitting to the
benchmark it tuned against.

What remains open in 10.6 is not tooling and not a campaign: it is that the
**AI arm has no denominator**. Its rejected attempts were never logged through
the ledger contract, so an acceptance-rate comparison has nothing to divide
by. Closing that is a discipline change — log agent attempts as they happen —
rather than something a further campaign can supply.

None of these change simulation behavior — all **Layer 2** — but they touch
scoring/CI infrastructure, so keep each one a separate PR (Rule: Layer 2
changes stay separate from Layer 1 improvements).


### 10.6 Run the control-arm comparison — `M` · ★★★ — CAMPAIGN RUN (2026-09-10)

**Layer 2.** 10.5 built the machinery and nobody had run it. It has now been
run, at forty candidates on a three-seed matrix, and the evidence is committed
rather than left in a gitignored ledger. The design was fixed in
[CONTROL_ARM_PREREGISTRATION.md](CONTROL_ARM_PREREGISTRATION.md) **before any
result existed**, as its own commit ahead of the results commit, so the
ordering is checkable in `git log` rather than asserted.

```bash
python tools/run_control_arm_campaign.py benchmarks/tank/survival_5k.py \
    --candidates 40 --seeds 42,7,123 \
    --heldout benchmarks/heldout/survival_heldout_5k.py
```

Evidence: `research/control_arm/` — every candidate with its mutation plan and
per-seed scores, accepted and rejected alike.

#### The headline

| quantity | value |
|---|---|
| candidates | 40 |
| accepted | **12/40 = 30%** (Wilson 95% CI 18.1–45.4%) |
| transferred to held-out | **6/12 = 50%** |
| best achieved | **805.397** vs baseline 687.108 (**+17.2%**) |
| worst candidate | 409.603 (−40.4%) |
| candidates above baseline | 20/40 |
| compute | 162 benchmark runs, 9,032 s (2 h 31 m) |

The reference is the paired local baseline on seeds 42/7/123, which is
bit-identical to the committed champion on every seed — so this is
simultaneously a paired-baseline and a champion comparison.

#### Finding 1 — random parameter search beats the shipped defaults, substantially

Twenty of forty random mutations scored above the champion, and the best of
them by **17.2%**. The shipped `ComposableBehavior` parameters are not near a
local optimum for `survival_5k`. That is not a flattering result for the
project and it is the one the evidence supports.

#### Finding 2 — and roughly seven eighths of that gain is overfitting

This is what the held-out evaluator was for, and it earned its cost:

| | mean delta among the 12 accepted |
|---|---|
| tuning benchmark (`tank/survival_5k`) | **+58.52** (+8.5%) |
| held-out (`heldout/survival_heldout_5k`) | **+6.24** (+1.4%) |

The gain shrinks to about a seventh on an evaluator the search never touched,
and the correlation between a candidate's tuning gain and its held-out gain is
only **+0.266**. Winning on the benchmark you tuned against barely predicts
winning anywhere else. Two of the largest tuning wins go *negative* held-out:
c34 (+80.15 → **−14.27**) and c38 (+63.20 → **−19.83**).

**Any future claim of a parameter improvement on this benchmark that is not
checked against the held-out evaluator should be assumed to be measuring
overfitting until shown otherwise.**

#### Finding 3 — one candidate looked real, and was not — RETRACTED 2026-09-11

**What this entry originally said:** c27 improves both, **+118.29 (+17.2%)** on
the tuning benchmark and **+25.04 (+5.6%)** held-out, passing the majority rule
on each, so it "is a genuine Layer 1 improvement candidate sitting in the
trace", left as a follow-up to adopt.

**That claim was too strong and is withdrawn.** Taking it up as the follow-up
was the right instinct and it did not survive the first honest look.

Re-derived from its recorded seed (9028, matching the committed trace
byte-for-byte) and scored on three seeds it was never selected on:

| benchmark | seeds 1 / 2 / 999 | verdict |
|---|---|---|
| `tank/ecosystem_health_10k` | +5.0% / +23.8% / +24.7% | improves on all three |
| `tank/survival_5k` | +11.6% / **INVALID** / no change | **breaks seed 2** |

On seed 2 the candidate drives the starvation rate from **0.9482 to 0.9778**,
past `MAX_VALID_STARVATION_RATE = 0.95`, and `survival_5k` gates its own score
to zero. That is the benchmark reporting that food-seeking broke, and no mean
improvement buys it back.

It is not a uniformly harmful change, which is what makes it instructive rather
than merely wrong: on seed 42 the same mutation *cuts* starvation from 0.8632 to
**0.6033**, a far healthier ecosystem, and it improved `ecosystem_health_10k` on
all six seeds tried. It has a failure mode, not a defect.

**Two things this leaves behind.**

First, a tooling gap, now closed. Acceptance ranked c27 on the three seeds the
campaign searched; nothing re-checked it anywhere else, and a candidate can win
a three-seed mean and still break a fourth.
`core/research/candidate_confirmation.py` adds that stage, and
`tools/confirm_control_arm_candidate.py` runs it. Its rule is deliberately not
"is the mean higher": **invalidating a run that was valid at baseline is
disqualifying on its own**, because an average is not allowed to outvote a
benchmark declaring the ecosystem broken. The committed result for c27 is
`research/control_arm/candidate_27_confirmation.json`, and the tool re-derives
each plan from its seed and refuses to run if it does not match the trace.

Second, a fact about the tank rather than the candidate. Of six seeds sampled at
**baseline**, `survival_5k` is already invalid on seed 999 (starvation 0.9834)
and within 0.3 percentage points of invalid on seed 2 (0.9482). A third of
sampled seeds sit at or beside the "food-seeking broken" line before anything is
changed, which is worth knowing before reading any survival_5k delta as a
verdict on a controller.

**This is the second time in this theme that a result did not survive wider
checking** — the first being the +8.5% tuning gain that fell to +1.4% held-out.
Both point the same way: on this benchmark, three seeds rank candidates, they do
not confirm them.

#### The preregistered prediction failed

The preregistration recorded, in advance: *"most accepted candidates will fail
to transfer."* Result: exactly **6 of 12** failed the majority rule, and by the
looser test of held-out sign, **8 of 12 were positive**. "Most" was wrong
either way. Recorded as failed rather than reworded, which is the entire point
of writing it down first.

#### Two instrument guards, one of which was my own error

Both are enforced in code (`core/research/control_arm.py`) and both fired
during pre-flight:

- **Sensitivity.** `tank/foraging_gym` absorbed 49 parameter mutations across
  five probes with **zero** score movement, so it is excluded. The gym pins its
  traits at neutral and exercises only food pursuit, while this operator
  mutates flee, cohesion, rest, ambush and poker parameters. A campaign there
  would have reported a 0% acceptance rate describing the instrument and
  reading like a finding about search.
- **Reference validity — and an erratum.** The first version of this work
  claimed the champion did not reproduce here, citing a 15.47-point
  cross-platform drift. **That was wrong.** Matrix champions store the mean
  across their seed matrix as the top-level `score` while `seed` names only the
  primary seed, so the check compared a three-seed mean against a single-seed
  run — the exact trap `tools/validate_reproduction.py` documents in a comment.
  Measured per seed, the champion reproduces **exactly** (max delta 0.0 across
  42/7/123). The check now compares every recorded seed against its own score,
  and a regression test pins the matrix case. No campaign number changed: the
  paired baseline used throughout is bit-identical to the champion.

#### What is still missing, stated plainly

**The head-to-head this entry originally asked for is not fully runnable as
specified, and this campaign does not deliver it.** The control arm has a
denominator because every candidate it draws is logged. The AI arm's rejected
attempts were never systematically logged — they live in unmerged branches and
abandoned diffs — so there is no denominator to compare against. Publishing an
"AI vs random search acceptance rate" table would divide by a number that does
not exist.

What *is* comparable is best-achieved score on the same benchmark and seed
matrix, reported above. Closing the rest requires the AI arm to log its
attempts through the same ledger contract going forward; that is a discipline
change, not a tooling gap, and it is the remaining work on this item.

### 10.7 Answer the starvation question — `S` · ★★★ — SHIPPED (2026-09-12)

Two entries above this one measured the tank's starvation and found only what it
*was not*. 10.6's Finding 3 was retracted because a candidate tipped a
borderline seed over the validity gate; the practice-ball ablation refuted the
one mechanism `CLAUDE.md` nominated and left the cause unfound. This closes it.

#### The answer: fish starved holding savings they were not allowed to spend

A fish banks everything it gains above `max_energy` into an overflow
reproduction bank (`_route_overflow_energy`). Until now
`consume_overflow_energy_bank` had exactly one caller —
`core/reproduction/asexual_factory.py` — so that bank was spendable on
offspring and on nothing else. Nothing drew on it to stay alive.

Measured at the death site rather than inferred from the death mix
(`tools/measure_death_reserves.py`, artifact
`research/starvation/death_reserves_before.json`):

| seed | starvation deaths | died holding reserves | mean bank held | energy foreclosed |
|---|---|---|---|---|
| 42 | 164 | **83 (51%)** | 147 | 12,233 |
| 2 | 311 | 89 (29%) | 32 | 9,895 |
| 999 | 355 | 115 (32%) | 41 | 14,695 |

36,823 energy across three seeds, destroyed by fish at exactly zero energy with
a positive balance. The largest single case: a fish dead at zero holding
**539.94**, three times its own `max_energy` of 179.98. `record_death` sums
`energy + bank` into one `remaining_energy` field, which is why nothing
downstream of it could ever tell a fish that starved empty from one that starved
rich.

**Why the death mix could not show this.** `starvation_rate` is a share of
deaths. A fish that dies rich and a fish that dies poor both increment
`starvation`, so the ratio is blind to exactly the distinction that matters.

#### The fix

`_draw_on_reserves` in `core/entities/mixins/energy_mixin.py`: a fish whose
energy reaches zero tops back up out of its own bank before dying. It restores
**only** the starvation threshold, so a fish living on reserves burns straight
back through it and keeps reading as starving to its own behaviour rather than
coasting. An empty bank dies exactly as before.

| benchmark | seeds | mean before | mean after | |
|---|---|---|---|---|
| `tank/survival_5k` | 42, 2, 999, 7, 123 | 514.96 | 812.37 | +57.8% |
| — the four valid at baseline | 42, 2, 7, 123 | 643.70 | 837.98 | +30.2% |
| `heldout/survival_heldout_5k` | 42, 2, 999 | 417.19 | 522.99 | +25.4% |
| `tank/ecosystem_health_10k` | 42, 7, 123 | 9.369 | 11.665 | +24.5% |

Every seed of every benchmark improves. Starvation falls from 86-97% of deaths
to 41-82%. **Seed 999 of `survival_5k` was already gated invalid at baseline
(0.9834) and is now valid at 0.8214** — a repair, not a score, and the reason
the five-seed mean is quoted alongside the four-seed one.

`avg_pop` is unchanged to four decimals on every `survival_5k` seed, so the
entire delta is the energy term. That is the regulation finding below doing its
work: population is pinned by `max_population` and cannot respond.

#### What it costs, and what it does not fix

- **Generation turnover.** Reserves spent surviving are reserves not spent on
  offspring: `survival_5k` seed 999 loses a generation (5 → 4) and
  `ecosystem_health_10k` seed 42 loses one (8 → 7). The other four seeds hold.
  `ecosystem_health_10k` still rises on all three seeds because its starvation
  penalty recovers by more than the generation term loses.
- **Energy is still destroyed at death, just later.** Seed 42 buries 19,751
  banked units before and 18,024 after; the composition moved from starvation
  (12,233) to old age (17,318). The tank scores better because fish live longer
  and hold more energy while alive, not because less is annihilated. Recovering
  energy from corpses is untouched ground.

#### The context: food supply is a thermostat, not a resource

Found while ruling out the obvious cause, and the reason "tune foraging" was
never going to work. `FoodSpawningSystem._calculate_spawn_rate` is a closed loop
on *total fish energy* — triple rate below `AUTO_FOOD_LOW_ENERGY_THRESHOLD`
(5000), slower above `AUTO_FOOD_HIGH_ENERGY_THRESHOLD_1`. Swept over
`auto_food_spawn_rate` at baseline:

| rate | food supply | pop | total fish energy | per fish | drift over window |
|---|---|---|---|---|---|
| 2 | 4.5× stock | 60 | 5,626.0 | 93.8 | +3.1% |
| 3 | 3× stock | 60 | 5,223.7 | 87.1 | +5.6% |
| **9** | **stock** | 60 | **5,012.8** | **83.5** | **+0.3%** |
| 18 | ½ stock | 60 | 3,527.0 | 58.8 | −9.5% |
| 36 | engine default | 53.8 | 2,244.7 | 41.7 | −21.1% |

Across a **4.5× change in food supply** the regulated quantity moves 12% while
population is pinned at 60 by `max_population`, so per-fish energy is a constant
of the configuration rather than an outcome of behavior: a better forager only
makes the thermostat close the tap. Two qualifications the sweep also settles —
the loop **saturates** at its 3× boost ceiling, so rates 18 and 36 are not lower
set points but collapses still in progress when the run ends (negative drift);
and `survival_5k` sits at the *bottom edge* of the regulated band.

`core/research/regulation.py` and `tools/measure_tank_regulation.py` measure
this for any world-config key, reporting the regulated quantity
(`sum(fish.energy)`, which the controller reads) apart from the banked quantity
(which it does not, and which the score counts). Two incidental findings from
the same sweep, both recorded in
`research/starvation/food_supply_regulation.json`:

- The **population arm** of that controller is dead code in every tank
  benchmark: `AUTO_FOOD_HIGH_POP_THRESHOLD_1 = 80` against caps of 50-60.
- `survival_5k` pins `auto_food_spawn_rate: 9` against an engine default of 36,
  and at the default the benchmark is **invalid** (starvation 0.9528). Its
  validity was being bought by that override.
- The same sweep after the fix shows the loop still regulating (raw energy
  4,805-5,136 over the same 4.5× range) and the population now holding at 60
  even at the engine default, where baseline dropped to 53.8. A tank that can
  spend its reserves stays at carrying capacity through a 4× food cut.

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
suggested — and its acceptance comparison is now measured and recorded below:
the graph's food branch beats `ComposableBehavior` on the foraging gym, but the
flag as wired captures none of that gain. **12.5 is the next real step, and it
is the go/no-go gate for the whole theme.** The ADR (`docs/adr/`) recording the encoding decision is still
unwritten; it belongs with 12.5's result, not before it.

### 12.1 Extract steering/sensor primitives into a shared library — `M` · ★★★ — SHIPPED
`core/behavior/primitives/steering.py` exists and is invoked by
`core/algorithms/composable/actions.py`,
`core/algorithms/composable/food_selection.py`, `core/algorithms/base.py`,
`core/code_pool/pool.py` (soccer's `_steer_action`),
`core/behavior/standard_nodes.py`, and the frozen soccer reference teams —
i.e. all three domains plus the graph node set share one implementation, which
was the point.

### 12.4 Foraging graph that reproduces `ComposableBehavior` — `M` · ★★★ — MEASURED; FLAG STAYS OFF
**Layer 1.** The graph controller exists: `default_foraging_graph()` in
`core/behavior/tank_adapter.py`, installed for founders by
`core/behavior/feature_flags.py` only when `tank.graph_behavior_enabled` is
set, dispatched from `core/movement_strategy.py`, covered by
`tests/core/test_graph_foraging_controller.py`. Two sibling flags,
`target_pursuit_module_enabled` and `target_memory_enabled`, gate the shared
pursuit module and target memory independently so the components can be
ablated separately. `graph_behavior_enabled` and `target_memory_enabled` still
default to `False`. `target_pursuit_module_enabled` defaults to `True` as of
the tank-ball/league-soccer skill-transfer work (see
`core/movement/ball_pursuit.py`, `core/minigames/soccer/policy_adapter.py`):
every fish now steers the practice ball and league soccer through one
inherited/mutated pursuit graph. It has no effect on food pursuit or the
foraging graph controller without `graph_behavior_enabled` also on, so this
does not touch the `12.1`/`12.4` foraging-graph theme.

**Honest note on the default-flip validation:** `ecosystem_health_10k` across
8 seeds (42/7/123/1/2/3/99/555) showed candidate wins on 5/8 with mean delta
-4.6% and per-seed stdev 2.09 - the swing is dominated by measurement noise
(standard error ~0.7), not a resolvable win or loss. Root-caused before
shipping anyway: instrumentation confirmed the module's own ball-handling is
objectively fine-to-better (perfectly-aimed kicks, more goals, fewer wasted
pursuit-frames than the naive fallback it replaces) - the large single-seed
swings (e.g. seed 42: -35%, `unique_algorithms` 22->13) come from this
benchmark's chaotic 10k-frame trajectory sensitivity to ANY behavior change
(same class as the existing seed-42/survival_5k noise gotchas), not a defect
in the module. Shipped on that basis - "does not measurably harm, and gives
every fish the shared skill-transfer substrate" - not on a claimed score win.
Both champions were re-baselined since the tank practice ball is present in
both regardless of `soccer_enabled` (see the `tank_practice_enabled` gotcha).

**The acceptance measurement (recorded).** `tools/compare_graph_arm.py` runs
the arms defined in `core/foraging/arms.py` on the 11.3 foraging gym.
`core/foraging/gym.py` itself is untouched — it is a locked path, so the arms
attach what the production arbiter reads to its fish at evaluation time rather
than growing the ruler to fit a new experiment. Each arm
is scored as gross food energy over the oracle ceiling, averaged over 8 founder
genomes x 8 episode seeds (64 episodes per arm); every arm hands its desired
velocity to the same production kinematics, so no arm wins or loses on output
magnitude. Reproduce with:

```bash
python tools/compare_graph_arm.py                                        # cohort A
python tools/compare_graph_arm.py --arms "composable graph" --urgency-threshold 1.0
python tools/compare_graph_arm.py --genome-seeds "9 10 11 12 13 14 15 16" \
    --episode-seeds "2 3 8 13 17 23 29 37"                               # cohort B
```

| arm | cohort A (genomes 1-8, seeds 42/7/31/38/1/5/0/41) | cohort B (genomes 9-16, seeds 2/3/8/13/17/23/29/37) |
|---|---|---|
| `composable` — `ComposableBehavior` alone | 0.983036 | 0.959093 |
| `graph` — behavior graph alone, default urgency 0.35 | 0.300032 | 0.300232 |
| `graph` — behavior graph alone, urgency pinned to 1.0 | **1.000000** | **1.000000** |
| `production` — full arbiter, flag off | 0.983036 | 0.959093 |
| `production_graph` — full arbiter, flag on | 0.986095 (+0.0031) | 0.953582 (-0.0055) |

Two conclusions, and they point in opposite directions:

1. **The graph's food branch out-forages `ComposableBehavior`.** Pinned on food
   pursuit it collects the oracle's full energy on all 128 episodes across both
   cohorts, with and without the shared pursuit module, while the composable
   behavior falls short of the ceiling on 4/8 and 5/8 founder genomes. That is
   the head-to-head this task asked for, and it replicates.
2. **Flipping `graph_behavior_enabled` today captures almost none of that**:
   +0.0031 on cohort A, -0.0055 on cohort B, with per-genome deltas in both
   directions - noise around zero, not a win. Instrumenting the arbiter says
   why: with the flag on, the graph steers only **11.2%** of frames. Above its
   0.35 urgency threshold the graph selects social cohesion,
   `GraphBehaviorConsideration` classifies that as leisure-tier and yields, and
   the composable behavior drives the other 88.8%.

So the flag stays off, and the blocker is now specific rather than vague: it is
the urgency gate, not the graph's steering. The gym's own geometry is half the
story - it is single-fish, so the cohesion branch is a permanent zero vector,
which is the whole of the 0.300 default-urgency score and is a statement about
the gym rather than about the controller. Before 12.5 spends mutation budget on
this topology, decide whether an energy-gated hand-off to a second controller is
the intended design at all; if it is, the threshold and the cohesion branch need
a multi-fish instrument (the gym cannot see them). `ComposableBehavior` stays
the reference oracle either way; do not delete it here.

**That multi-fish instrument now exists, and it answers the question.**
`core/foraging/school_gym.py` runs `SCHOOL_SIZE` fish that start in one tight
cluster while every wave scatters one food item to each of four stations, with
food that expires. A school that spreads out takes all four; a school that
stays together converges on the nearest and the other three rot. Both travel
about the same distance, so what separates them is distribution — the branch
12.4 could not see. `core/foraging/school_arms.py` runs the *same four arms*,
so the numbers stay comparable. Reproduce with:

```bash
python tools/compare_school_arms.py --urgency-sweep "0.0 0.2 0.35 0.5 0.7 1.0"
python tools/compare_school_arms.py --genome-seeds "9 10 11 12 13 14 15 16" \
    --episode-seeds "2 3 8 13 17 23 29 37" --urgency-sweep "0.35 0.7 1.0"
```

8 genomes x 8 episode seeds; reference arms carry no genome:

| arm | cohort A | cohort B | mean neighbour distance (A) |
|---|---|---|---|
| `oracle` — one fish per station | 1.000000 | 1.000000 | 274px |
| `greedy_shoal` — each fish chases the best item | 0.630125 | 0.661294 | **33px** |
| `random_walk` | 0.112859 | 0.122395 | 249px |
| `composable` | 0.887805 | 0.814420 | 239px |
| `graph` — bare, default urgency 0.35 | 0.391404 | 0.389089 | 163px |
| `production` — arbiter, flag off | 0.887805 | 0.814420 | 239px |
| `production_graph` — arbiter, flag on | 0.895741 (+0.0079) | 0.827928 (+0.0135) | 245px |

**The urgency sweep is the result that matters, and it is monotonic:**

| urgency threshold | 0.00 | 0.20 | 0.35 (default) | 0.50 | 0.70 | 1.00 |
|---|---|---|---|---|---|---|
| cohort A | 0.000000 | 0.249581 | 0.391404 | 0.600279 | 0.677706 | 0.771684 |
| cohort B | — | — | 0.389089 | — | 0.706879 | 0.769648 |

Every step *away* from social cohesion improves the score, with no optimum in
between; at threshold 0.0 the graph never forages at all and collects nothing.
So on foraging, the cohesion branch does not earn its place, and the shipped
0.35 default sits near the bad end of its own range.

**Read that with its boundary, though.** This gym rewards dispersal by
construction and contains no predator, which is the thing schooling is
actually for. What is shown is narrow and solid: cohesion is a *foraging*
cost, monotonically. Whether it pays for itself in survival needed a predator
instrument — **which now exists, and closes the question; see below**. The `greedy_shoal` row is the same point from the other side: at 33px mean
separation it is the clumping failure mode made visible, and it scores 0.63
against an attainable 1.0.

**The arbiter's yield-on-cohesion is doing real work.** `production_graph`
beats `production` on both cohorts (+0.0079 / +0.0135), while the bare `graph`
scores half of either. The difference is entirely
`GraphBehaviorConsideration` refusing the graph's leisure-tier output and
handing back to the composable behavior — the design 12.4 flagged as the
bottleneck is also what keeps the flag from being harmful.

#### The predator half: cohesion has no constituency, but the threat branch does

`core/foraging/predator_gym.py` is the instrument the school gym said it
needed. Food spawns *inside* a patrolling crab's lane and fish burn energy
every frame, so hiding starves and feeding without looking down gets you
eaten — `reference_pressures()` asserts both before any arm is scored,
because an instrument with an inert pressure reports confident numbers about
nothing. The predator is not invented for the occasion: `_GymCrab` subclasses
the production `Crab` (the adapters find threats by `isinstance`, so only a
real subclass is visible to the branch under test) and imports
`CRAB_ATTACK_COOLDOWN`. That cooldown *is* dilution — a crab that takes one
fish cannot take another for 15 frames — which is precisely the mechanism by
which grouping could have paid off.

```bash
python tools/compare_predator_arms.py --urgency-sweep "0.0 0.2 0.35 0.5 0.7 1.0"
```

8 genomes x 8 episode seeds; deaths are per 4-fish school:

| arm | survival A / B | eaten A / B | starved A / B |
|---|---|---|---|
| `hide` | 0.8471 / 0.8471 | 0.00 | 4.00 |
| `feed_ignoring_predator` | 0.3601 / 0.3530 | 4.00 | 0.00 |
| `feed_and_flee` | 0.9034 / 0.9139 | 0.00 / 0.25 | 1.50 / 1.25 |
| `composable` = `production` | 0.6938 / 0.7877 | **1.94 / 1.39** | 0.27 / 0.56 |
| `graph` | 0.9114 / 0.8876 | **0.25 / 0.00** | 2.00 / 3.12 |
| `production_graph` | **0.9137 / 0.9134** | 0.17 / 0.06 | 1.73 / 2.12 |

**Two findings, and the second is the new one.**

1. **Cohesion still earns nothing.** The urgency sweep is *flat* from 0.20 to
   1.00 (0.9114 throughout on cohort A), which is exactly what the topology
   predicts: `priority` picks threat whenever the threat vector is nonzero,
   *before* `urgency` is consulted, so the threshold only decides what happens
   when nothing is hunting you. The one apparent exception is a trap worth
   naming — threshold 0.00 scores *highest* (0.9409) while starving all four
   fish and eating none. That is `hide` with extra steps: survival-frames
   reward starving slowly over being eaten quickly. It is not evidence that
   cohesion protects. Taken with the foraging result, **cohesion is a cost in
   one gym and neutral in the other, so it has no constituency in this tank.**

2. **The graph's *threat* branch is excellent, and had never been measured.**
   No previous instrument contained a predator, so `threat_away_vector` was
   always zero and the branch that dominates the entire topology was untested.
   Under predation it cuts deaths-by-predation from **1.94 to 0.25** against
   `ComposableBehavior`, and `production_graph` beats `production` by **+0.22
   survival** — two orders of magnitude more than the +0.003 the foraging gym
   measured. Instrumenting why: with a crab within 200px, the composable
   behavior moves away on only **48%** of frames while the graph does on
   **89%**. The graph gives threat absolute priority; the composable blends it
   with food and loses.

**The pressure caveat, which decides how much of this to bank.** This gym puts
food inside the hazard on purpose, so its predation pressure is far above the
tank's: `survival_5k` on master records 164 starvation deaths, 25 old-age and
**1 predation**. So finding 2 does not overturn 12.4's verdict on the flag —
at the tank's actual predation rate the foraging result dominates. What it
changes is that the flag's value is now a *quantified trade-off against
predation pressure* rather than an unknown, and a tank tuned for more
predation would flip the sign.

### 12.5 Graph mutation + type-safe subgraph crossover — `L` · ★★★
**Layer 1.** Add param mutation (gauss, as today), node-swap mutation (like the
enum switch / policy-ID swap), and low-probability *structural* mutation
(add/remove/rewire an edge, splice a subgraph) behind a heritable
`structural_mutation_rate` meta-gene (reuse `core/genetics/trait.py`).

*Before spending mutation budget on this topology:* the cohesion branch is now
measured on both axes and earns nothing on either — a monotonic foraging cost
in the school gym, and flat under predation, where `priority` pre-empts the
urgency gate entirely. The predator instrument that was the outstanding
prerequisite has been built and reported (see 12.4), so this is no longer
blocked on evidence. Either let mutation reach the threshold (it is already an
evolvable `NodeParameterSpec`, so selection can find this itself — the more
interesting experiment), or simplify the topology first and say why. What the
same instrument *does* argue for keeping is the **threat** branch: it cuts
predation deaths from 1.94 to 0.25 per school against `ComposableBehavior`.

Add
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

- **7.3 Split `TankTrendsTab.tsx` and `plants/renderers.ts` — the last two
  non-canvas god files from this entry.** `TankTrendsTab.tsx` (1,203 lines)
  split into `trendUtils.ts` (pure aggregation — `buildTrendPoints`,
  `calculateTrend`, trait/threshold constants) and `TrendUiPrimitives.tsx`
  (presentational primitives — `StatTile`, `Sparkline`, `ChartCard`,
  `LegendKey`, `ReadoutCard`, `TrendBadge`, `CustomTooltip`), leaving a
  700-line component facade (re-pinned in `LEGACY_MAX_LINES`; still over the
  500-line new-file limit because nine distinct chart cards plus a
  KPI/readout strip is genuine render complexity, not god-class bloat).
  `plants/renderers.ts` (1,042 lines) split into six one-per-plant-model
  files under `utils/plants/renderers/` (142–211 lines each — mandelbrot,
  claude, antigravity, gpt, gptCodex, sonnet), since the six render
  functions shared no logic beyond the common `helpers`/`textures`/`lsystem`
  imports; `renderers.ts` is now a 10-line re-export barrel, dropped from
  `LEGACY_MAX_LINES` entirely, and `plant.ts`'s existing imports needed no
  changes. Verified with `npm run build` (clean), `npx vitest run` (30 files
  / 160 tests, unchanged pass count), and `npm run lint` (clean) — pure code
  motion, no JSX/styling/computation changed. `NetworkDashboard.tsx` is the
  one file this entry's table still lists as open. **Layer 2**: frontend
  only, no simulation behavior, no champion touched.
- **6.1 Strict typing for `core.poker` and `core.minigames` — the last two
  named candidates, closing out the task.** Probing fallout (`mypy core/
  backend/` with both overrides added) found 38 missing-annotation errors
  across 13 files, all mechanical — every `random_instance`/`__post_init__`/
  helper needed only a return type (`-> None` in all but a few cases) or a
  parameter type already implied by its caller
  (`_make_pokerhand_from_ints`'s `hand_type`/`rank_value`/`card_ints` in
  `core/poker/evaluation/hand_evaluator.py`; `game_state:
  MultiplayerGameState` in `core/poker/evaluation/auto_evaluate_poker.py`;
  `fish`/`opponent`/`parent` typed as the project's existing `"Fish"`
  forward-ref pattern, matching `core/mixed_poker/utils.py`, in
  `core/poker/integration/poker_interaction.py`).

  Annotating two functions surfaced real (if harmless) latent type
  mismatches that `disallow_untyped_defs = false` had been hiding by
  skipping body checking entirely: `_apply_hand_result` assigned
  `MultiplayerGameState.current_round` (declared `int` on that dataclass)
  straight into `self.current_round` (inferred `BettingRound` from its two
  other assignment sites) — fixed by wrapping `BettingRound(...)`, a no-op
  on the actual value since `BettingRound` is an `IntEnum`. Separately, a
  nested helper in `core/minigames/soccer/league_runtime.py` receives
  `LeagueTeam` values through a `dict[str, Any]`, and my first annotation
  attempt (`TeamAvailability`, a same-module dataclass with a superficially
  similar name) failed with `attr-defined` on `.source`/`.team_id`/
  `.roster` — corrected to `LeagueTeam`, which the day trip through the
  wrong type happened to have. No other core package remains uncovered:
  every `core/` subpackage with actual source (35 with `__init__.py`, plus
  the namespace packages `core.movement`, `core.transfer`,
  `core.telemetry`) now carries the `disallow_untyped_defs = true`
  override; `core/parameters`, `core/experiments`, and `core/skills`
  contain only stale `__pycache__` directories and no source, so they were
  not candidates. Verified via `mypy core/ backend/` (456 files, clean),
  `ruff`/`black` clean, `agent_gate.py` green (667 tests), and the full
  poker/soccer/league suite (354 tests) green. Confirmed the champion
  reproduction failures already present in `test_benchmark_integrity.py`
  (`training_3k/5k`, `ecosystem_health_10k`, `survival_5k`) reproduce
  identically on unmodified `master` — pre-existing local-Windows
  nondeterminism tracked by **1.0**, not a regression from this change.
  Annotation-only (plus the two behavior-preserving fixes above): no RNG

  **Corrected in CI review:** the initial fallout fix annotated
  `standard.py` and `expert.py` in `core/poker/strategy/implementations/`,
  both frozen benchmark rulers under `tools/check_locked_paths.py`
  `DEFAULT_LOCKED_PATHS` (11.7) — CI's locked-paths job correctly rejected
  the PR even though the edit was typing-only. Reverted both files and
  instead added explicit per-module mypy overrides
  (`disallow_untyped_defs = false`) for all three locked poker strategy
  files plus `core/minigames/soccer/reference_teams.py` (also locked, now
  under this PR's `core.minigames.*` override), so a future 6.1/6.2 pass
  can't hit the same wall: typing fallout in `core.poker.*` or
  `core.minigames.*` can no longer force an edit to a locked ruler.
  draw, no champion re-baseline.
- **7.5 + 7.3 De-duplicated the canvas renderers onto `renderers/shared/`.**
  The tank top-down, petri and avatar renderers carried three near-verbatim
  copies of the gene-driven microbe avatar (~175 lines each), two of the trait
  cues, the predator, the substrate, the whole top-down HUD, the food sprite
  table and the seeded-RNG/path primitives. All of it now lives once in
  `frontend/src/renderers/shared/` (five modules, largest 350 lines).
  **`TankTopDownRenderer.ts` 1,267 → 405, `PetriTopDownRenderer.ts` 1,392 →
  569, `avatar_renderer.ts` 555 → 300**; the first and third dropped out of
  `LEGACY_MAX_LINES` entirely and the second was re-pinned.

  *Proving it changed nothing.* `renderers/testing/canvasTrace.ts` is a
  recording `CanvasRenderingContext2D` that logs every call, state assignment
  and gradient colour stop; `renderers/topDownRenderTrace.test.ts` renders a
  fixture world covering every entity kind and effect branch and snapshots the
  result. The baseline was captured from the pre-refactor renderers, so the
  ~3,400-line trace diff *is* the review. It came out at exactly three deltas,
  all no-ops for drawing, all listed in the test's header comment: 16 dropped
  state assignments left over from a commented-out debug label, four redundant
  `setLineDash([])` calls in the petri path, and two `restore()` calls that
  moved — the last of which is a **bug fix**: the heading whisker for crabs,
  balls and castles was emitted *outside* the entity's transform, pinning every
  whisker to the world origin instead of its entity. No coordinate, colour or
  gradient stop moved.

  `renderers/shared/shared.test.ts` adds 19 unit tests, including the
  structural invariants the modules rely on but nothing enforced: an organism's
  appearance is a pure function of its genome, an unknown generation renders
  identically to generation zero, and the optional layers (trait cues,
  substrate crystals) are strictly *additive* — enabling one cannot disturb the
  drawing underneath, which is what keeps the seeded RNG sequence stable.
  **Layer 2**: frontend only, no simulation behavior, no champion touched.
- **6.1 Strict typing for `core.services`/`core.mixed_poker`/`core.plant`/
  `core.code_pool`/`core.systems`.** The next tier of 6.1's "remaining
  candidates by leverage" list after the small-leaves batch. Probing fallout
  (`mypy core/ backend/` with all five overrides added) found
  `core.services`, `core.mixed_poker`, and `core.code_pool` already fully
  annotation-clean; `core.plant` and `core.systems` needed three annotations
  total. `core/plant/nectar_component.py`'s `_NectarCreationData.__init__`
  now takes `environment: World` and `parent_genome: PlantGenome` (both
  already imported under the file's existing `TYPE_CHECKING` block).
  `core/plant/migration_component.py`'s `execute_migration` now takes
  `plant: Plant` (a new `TYPE_CHECKING`-only import — safe since
  `core.entities.plant` already imports `core.plant`, so a runtime import
  the other way would cycle). `core/systems/soccer_system.py`'s
  `_handle_goal_scored` now takes `goal_event: GoalEvent` (added to the
  file's existing `TYPE_CHECKING` import from `core.entities.goal_zone`).
  Grouped into one PR since each override plus its fallout was too small to
  justify five separate reviews. Annotation-only: no runtime behavior, no
  RNG draw, no champion re-baseline.
- **6.1 Strict typing for fifteen small core leaf packages.** Added mypy
  overrides for `core.actions`, `core.agents`, `core.brains`,
  `core.contracts`, `core.events`, `core.evolution`, `core.fish`,
  `core.foraging`, `core.modes`, `core.plants`, `core.policies`,
  `core.pursuit`, `core.replay`, `core.taxonomy`, and `core.telemetry` — the
  full "small leaves" list 6.1 named as annotation-clean candidates. Probing
  fallout (`mypy core/ backend/` with all fifteen overrides added) confirmed
  it: exactly two functions needed annotations. `extract_traits_from_genome`
  in `core/fish/visual_geometry.py` now takes `genome: object | None` (the
  function is deliberately duck-typed via `getattr` and never checks
  `isinstance`, so `object | None` states its actual contract rather than
  overclaiming a `Genome` type). `JsonlReplayWriter.__exit__` in
  `core/replay/jsonl.py` gained the standard
  `type[BaseException] | None, BaseException | None, TracebackType | None`
  signature. Grouped into one PR since each override plus its fallout was too
  small to justify fifteen separate reviews. Annotation-only: no runtime
  behavior, no RNG draw, no champion re-baseline.
- **2.6 (round 2): split `backend/state_payloads.py` into a package.** The
  812-line module (previously blocked pending **7.1**, which now shipped a
  contract test guarding the wire schema) is now `backend/state_payloads/`:
  `_common.py` (the shared `to_dict`/`serialize` helpers — `orjson` fallback
  to `json`), `entities.py` (`EntitySnapshot`), `metrics.py` (the four
  `Metrics*Payload` trend classes), `poker.py` (`PokerStatsPayload`,
  `PokerEventPayload`, `PokerLeaderboardEntryPayload`,
  `AutoEvaluateStatsPayload`), `soccer.py` (`SoccerEventPayload`), `stats.py`
  (`StatsPayload`, the largest module at 310 lines), and `frames.py`
  (`FullStatePayload`, `DeltaStatePayload`, `STATE_SCHEMA_VERSION`). A thin
  `__init__.py` re-exports the full public surface, so every one of the 18
  existing `from backend.state_payloads import X` call sites across
  `backend/` and `tests/` needed no changes. Also dropped `_compact_dict`, a
  private helper with zero callers anywhere in the tree. Updated the
  `pyproject.toml` mypy override from `backend.state_payloads` to
  `backend.state_payloads.*` so strict typing still covers every submodule,
  and removed the file's `LEGACY_MAX_LINES` pin (no module in the new package
  exceeds 500 lines). Verified with `pytest backend/ tests/test_frontend_payload_contract.py
  tests/test_god_class_limits.py`, `mypy backend/state_payloads`, and
  `agent_gate.py`; no runtime behavior changed (pure dataclass reorganization,
  no simulation code touched — Layer 2).
- **2.6 (round 2): split the `worlds`/`solutions` router factories, and fix a
  route-shadowing bug found along the way.** `backend/routers/worlds.py`
  (`setup_worlds_router`, ~379-line factory) and `backend/routers/solutions.py`
  (`create_solutions_router`, ~366-line factory) are now packages —
  `backend/routers/worlds/` and `backend/routers/solutions/` — with one
  module per endpoint group (`collection`/`instance`/`runtime`/`telemetry`/
  `mode`, and `catalog`/`detail`/`reports`/`capture`/`lifecycle` respectively),
  a `models.py` for the request/response schemas, and a thin `__init__.py`
  that only assembles the sub-routers in the order route-matching requires
  (largest file: 152 lines). Public import paths (`setup_worlds_router`,
  `create_solutions_router`) are unchanged.
  **Bug found and fixed in the process:** in the original `solutions.py`,
  `GET /{solution_id}` was registered *before* `GET /leaderboard`, `GET
  /compare`, and `GET /report`. Starlette matches routes in registration
  order, and `/{solution_id}` is a same-segment-count catch-all, so all three
  were silently shadowed and always returned `404 Solution not found: <name>`
  — confirmed with a `TestClient` probe against the pre-split router before
  touching any code. These three endpoints are documented as working in
  `solutions/README.md` but had never been reachable. Fixed by registering
  the literal-path `reports` module before the catch-all `detail` module;
  added `tests/test_solutions_api.py` to lock in the fix (previously nothing
  exercised these routes at the HTTP layer). Also updated the two other
  places that referenced the old file paths directly:
  `tools/check_wheel.py`'s wheel-contents check and the `INFRA_FILES` list in
  `tests/test_no_concrete_entity_imports_in_infra.py` (now lists every new
  module instead of the two old ones, so the entity-decoupling guard covers
  the same surface it did before, not less). Verified via `agent_gate.py`,
  `pre_pr_gate.py`, and `tools/check_wheel.py` all green; no simulation code
  touched (Layer 2).
- **Documentation claim-drift correction and checker.**
  `ALL_ALGORITHMS` is 3 (`OpportunisticFeeder`, `FoodQualityOptimizer`,
  `CooperativeForager`) after ADR-016, but `README.md` (lines 47, 57, 94, 393)
  and `CLAUDE.md` still advertised "50+ behavior algorithms" / "58 algorithms"
  / "dozens of parametrizable behavior algorithms" — five of the six
  categories the README named (`predator_avoidance.py`, `schooling.py`,
  `energy_management.py`, `territory.py`, `poker.py`) no longer exist. Reworded
  all five sites to describe the composable behavior framework plus the three
  survivor foragers, pointing at `docs/ALGORITHM_CATALOG.md` as the count of
  record. Added `test_public_docs_do_not_overstate_algorithm_count` to
  `tests/test_docs_agent_onboarding.py` (part of the smoke gate): it re-derives
  the count from `core.algorithms.registry.ALL_ALGORITHMS` at test time and
  fails on any numeric or "dozens of" algorithm-count claim in the public agent
  docs that disagrees with it, so this drift mode can't return silently.
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
   The shipped documentation claim-drift checker is the concrete first fix;
   **5.3** remains the candidate for broadening that protection to this file's
   other hand-maintained measurements.
3. **A "no longer qualifies" dismissal expires too.** The 2026-07-26 pass found
   that the previous audit had correctly retired `backend/routers/worlds.py`
   from Theme 2.6 — and the file then grew 76 lines and its factory function is
   ~379 lines today (see 2.6). Removing an entry is itself a measurement with a
   date on it. When you retire something, say what you measured and when, so
   the next reader knows whether to re-check rather than trusting it forever.
