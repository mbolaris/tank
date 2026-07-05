# Multi-Problem-Space Search — assessment and a plan to make transfer real

> **Status:** proposal / design note (Layer 2). No behavior, config, benchmark,
> or scoring change is made by this document. It records what the "search many
> problem spaces at once" idea actually buys us, where the current codebase
> already supports it, where it falls short, and a sequence of small, testable
> changes that would let us *demonstrate* cross-domain transfer instead of
> hoping for it.
>
> Read alongside [EVOLVABILITY.md](EVOLVABILITY.md) (the levers and the
> anti-Goodhart discipline), [VISION.md](VISION.md) (the three layers), and
> [MULTILEVEL_EVOLUTION_STRATEGY.md](MULTILEVEL_EVOLUTION_STRATEGY.md).

---

## 1. The idea, stated precisely

The pitch: our fish are not solving one problem, they are solving several at
once — foraging, predator evasion, schooling, poker, soccer, energy budgeting,
territory. The hope is that **progress on one problem carries over to another**,
and that this coupling lets a population **climb out of a local optimum** in one
domain by riding a fitness gradient supplied by a different domain.

This is a real and well-founded idea, not wishful thinking. It has two names in
the literature:

- **Exaptation / pleiotropy** (biology): a trait selected for one function is
  co-opted for another (feathers for thermoregulation → flight). One gene,
  several phenotypic consequences, several selective handles.
- **Multi-task learning / transfer** (ML): training on related tasks
  regularizes a shared representation and often beats single-task training,
  because each task constrains the shared parameters differently.

### Why it can escape local optima — the load-bearing argument

A point is a **local optimum of problem A** if no small genetic change improves
A. The population gets stuck there because every direction is flat-or-worse *for
A*. Now add problem B, sharing some of the same genes. The stuck point must
*also* be a local optimum of B to trap the population — and **the intersection
of "locally optimal for A" and "locally optimal for B" is much smaller than
either set alone.** With enough coupled objectives, points that are locally
optimal for *all of them simultaneously* become rare. B's gradient pushes the
shared genes sideways along A's flat ridge until A can descend again.

That is the whole bet, and it is a good one — **but it is conditional.**

### The condition that makes or breaks it (the honest caveat)

The escape argument only works **if the problem spaces share genetic and
representational substrate.** If each domain is controlled by its own
independent block of genes, then:

- selection on B never touches A's genes,
- there is no coupled gradient,
- and "searching many spaces at once" degenerates into **N independent searches
  running side by side** — which does *nothing* to escape any single domain's
  local optimum. It is just parallelism, not transfer.

So the interesting engineering question is **not** "do fish face multiple
problems?" (they do). It is: **do the problems share evolvable machinery, are
they under selection on the same population at the same time, and can we
measure transfer when it happens?** Today the answer to all three is "only
weakly." Sections 3–6 are about fixing that.

There is also a real failure mode to respect: **negative transfer /
interference** ("jack of all trades, master of none"). Coupling is not free —
it can drag a well-adapted domain backward. That is exactly why the plan leads
with *measurement* (§5) and attaches a kill criterion to every step.

---

## 2. What the codebase already gives us

The substrate for this idea already exists, which is why it's worth pursuing.

**One genome faces many sub-problems.** A fish's `ComposableBehavior`
(`core/algorithms/composable/definitions.py`) bundles four decision spaces into
a single evolvable object:

- `ThreatResponse` — predator evasion
- `FoodApproach` — foraging (6 strategies: direct pursuit, predictive
  intercept, circling strike, ambush, zigzag, patrol)
- `SocialMode` — schooling
- `PokerEngagement` — the poker minigame

On top of that, the movement arbiter (`core/movement_strategy.py`,
`core/movement/considerations.py`, ADR-010) layers **soccer ball pursuit** and
optional **code policies**, and the genome separately carries **energy**,
**territory**, **physical**, and **mate-preference** traits. So a single
individual is genuinely being scored, implicitly, across half a dozen problem
spaces every frame.

**Evolvability is already heritable.** Per-trait meta-genes (`mutation_rate`,
`mutation_strength`, `hgt_probability` in `core/genetics/trait.py`) and
macromutation (`algorithm_switch_rate` in `core/evolution/mutation.py`) mean the
search *strategy* itself evolves. Coupling those to cross-domain signals is a
natural extension rather than a rewrite.

**Multiple arenas already exist.** `benchmarks/tank/` (survival, ecosystem
health, selection response) and `benchmarks/soccer/` (training 3k/5k), plus the
poker engine and the Petri world, are separate evaluation surfaces with their
own champions.

### The three gaps

1. **Low pleiotropy.** The four composable sub-behaviors are largely *modular
   and independently inherited* (`core/genetics/behavioral_inheritance.py`
   blends each category separately). A change to `food_approach` genes does not
   touch `threat_response` genes. There are almost no genes that *both* domains
   read — so there is little for transfer to travel through.

2. **Pressures are not co-present.** `ecosystem_health_10k` scores tank survival
   and turnover; soccer `training_5k` scores a *separate* population in a
   *separate* arena. No single population is simultaneously selected on foraging
   **and** soccer **and** poker. The domains coexist in the code but not in one
   selection event.

3. **Transfer is unmeasured.** Nothing reports "lineages that got better at A
   also got better at B." We could not currently tell transfer from coincidence,
   and the primary objective (`ecosystem_health`) is explicitly *blind* to
   directional quality (EVOLVABILITY §2), let alone cross-domain quality.

---

## 3. Design principle for the plan

Every step below is judged by the EVOLVABILITY north star: **does it make the
system better at evolving**, not "does the tank look busier." Concretely we want
to (a) create shared machinery for transfer to flow through, (b) put the
pressures on one population at once, and (c) **measure transfer as a frozen,
non-gameable quantity** before believing any of it. Order matters: measurement
and a minimal pleiotropic seam come first, big environment changes last.

---

## 4. Proposed changes (documented, not implemented)

Each is a separate proposal / PR. Effort S/M/L, impact ★→★★★, EVOLVABILITY
lever in brackets. Layer-2 (measurement/tooling/objective) items are kept
separate from Layer-1 (algorithm) items per the contribution protocol.

### P1 — Shared "cognitive primitives" in the genotype→phenotype map  [Lever §3.5] · L · ★★★

*The keystone. Without shared substrate there is no transfer (see §1).*

Introduce a small set of **domain-agnostic latent traits** that several
sub-behaviors *read from* instead of each carrying its own private copy:

- `interception_skill` — quality of predicting where a moving target will be.
  Consumed by `FoodApproach.PREDICTIVE_INTERCEPT` **and** soccer ball
  pursuit/kick aiming **and** predator lead-avoidance.
- `risk_tolerance` — one dial feeding poker aggression, ambush patience,
  threat `flee_threshold`, and food/soccer contest decisions.
- `spatial_memory` — reused by patrol foraging, territory, and return-to-goal
  positioning.
- `timing_patience` — ambush waiting, poker fold discipline, kick windup.

Mechanically: add these as genome-level traits and have the relevant
sub-behaviors compute their effective parameter as a function of (shared latent
× local modifier). This deliberately introduces **pleiotropy**: mutating
`interception_skill` now moves foraging *and* soccer at once, creating the
coupled gradient the whole idea depends on.

*Determinism note:* this reshapes the genome and the RNG draw schedule, so it
requires regenerating golden fixtures and re-baselining champions — a heavy,
clearly-scoped change. Ship it behind a config flag first (default off) so it
can be A/B'd against the modular baseline.

**Kill criterion:** if, with shared primitives on, per-lineage competence in the
coupled domains is *no more correlated* than with them off (measured by P4),
the mechanism isn't creating real coupling — revert.

### P2 — A multi-pressure arena: one population, several problems at once  [Lever §3.8] · L · ★★★

Today the pressures live in separate benchmarks. Add an evaluation environment
where the **same gene pool** is exposed to foraging **and** predation **and**
soccer **and** poker within one run — either overlaid (ball + food + crabs +
poker tables all present) or on a rotating schedule so a lineage must survive
several regimes across its life. This is the precondition for §1's escape
argument: co-present gradients on shared genes.

Start as a *new benchmark* (`benchmarks/tank/multispace_*`) with its own
champion, so it can't regress the existing single-domain champions. Keep the
existing benchmarks as single-domain controls.

**Kill criterion:** if the multi-pressure population is strictly dominated on
*every* individual domain by that domain's specialist champion **and** shows no
transfer signal (P4), multi-pressure is just diluting selection — shelve it.

### P3 — Multi-objective selection / a cross-domain MAP-Elites archive  [Levers §3.3, §3.4] · M · ★★

Collapsing several domains to one scalar hides exactly the trade-offs we want to
study. Instead keep a **Pareto front / MAP-Elites archive** keyed by
per-domain competence (a cell for "great forager / weak soccer", another for
"balanced generalist", etc.). This preserves both specialists and generalists,
and lets us ask the money question: **do generalists sitting between niches seed
the jumps that specialists can't reach?** (the concrete escape-from-local-min
event). Reuse the diversity machinery in `core/genetics/diversity.py`.

### P4 — A frozen cross-domain **transfer assay** (held-out ruler)  [Levers §2, §6] · M · ★★★

*Do this early — it is how we tell transfer from coincidence, and it gates P1–P3.*

Mirror the existing frozen `selection_response` assay. Define a **transfer
metric** that a proposal is scored against but may **not** edit in the same PR:

- **Ablation form (cleanest):** evolve a population under pressure A only
  (e.g. foraging), with B's pressure *absent*. Then measure **zero-shot**
  competence on B (e.g. ball interception) versus a control population evolved
  the same length under a B-irrelevant task. Positive transfer = the
  A-trained population is better at B than the control, without ever having
  been selected on B.
- **Correlational form (cheap, continuous):** within a multi-pressure run,
  track per-lineage competence in each domain over generations and report the
  **cross-domain correlation of *improvements*** (does a generation's gain in A
  co-occur with a gain in B, beyond what shared "just being alive" explains?).

Report a decomposed, per-seed number across the canonical seeds **42, 7, 123**
(single-seed trajectory sensitivity, EVOLVABILITY §2). This assay is the
non-gameable evidence that the whole idea works.

### P5 — Curriculum / pressure scheduling  [Lever §3.8, POET-style] · M · ★★

Use P2's arena to test the sharpest version of the claim: **does mastering an
easy domain first let the population solve a hard domain it can't solve cold?**
Introduce domains in sequence, or ramp their weights, and compare against
simultaneous exposure and against the hard-domain-only control. A win here is a
direct, legible demonstration of "progress on one problem unlocked another."

### P6 — Instrumentation & a "transfer event" lens  [Lever §2] · S · ★

Per-lineage, per-domain competence telemetry (extend `core/ecosystem_stats.py`
/ `tools/evolution_report.py`), and a detector that flags when a lineage's rise
in domain B closely follows a rise in domain A. Surface flagged events in the UI
Insights feed (via `tools/post_commentary.py`) so cross-domain transfer becomes
*watchable*, not just a number in a log — consistent with the
entertainment-as-utility principle.

---

## 5. Recommended first experiment (smallest falsifiable test)

Don't build all six. The minimal test of the entire bet is **P4 (correlational
form) + one slice of P1**:

1. Add **one** shared primitive — `interception_skill` — wired into *both*
   `FoodApproach.PREDICTIVE_INTERCEPT` and soccer ball pursuit, behind a
   default-off flag.
2. Add the **ablation transfer assay**: evolve under foraging pressure only
   (no ball reward), then measure zero-shot ball-interception competence, with
   and without the shared primitive, against a control.

**Prediction if the idea is real:** with the shared primitive on, a
food-only-evolved population is measurably better at zero-shot ball interception
than the modular-baseline population — transfer through the shared gene — across
seeds 42/7/123. If it isn't, we've cheaply falsified the strongest form of the
claim before paying for P2/P3/P5.

**Anti-Goodhart:** the transfer assay (P4) is held out and unedited by the same
PR; the shared primitive earns its place only by moving the *frozen* transfer
number, not the objective it might also touch.

---

## 6. Honest risks

- **Negative transfer.** Coupling can drag a strong domain down. P3's archive
  and P4's per-domain breakdown exist precisely to catch this; every step has a
  kill criterion.
- **Diluted selection.** Multi-pressure runs can flatten every gradient
  (EVOLVABILITY §1's trap) — a busier tank that evolves *less*. Guard with
  single-domain controls.
- **Determinism cost.** P1 and P2 rewrite the genome/RNG schedule and force
  fixture + champion re-baselining. Scope them as deliberate, flagged changes,
  not drive-by edits.
- **Goodharting the objective.** Changes to the fitness signal are the
  highest-leverage *and* highest-risk class (EVOLVABILITY §6). The frozen
  transfer assay is the defense; keep objective edits separate from algorithm
  edits.

---

## 7. Where this plugs into the existing map

| This doc | EVOLVABILITY lever | Existing hook |
|---|---|---|
| P1 shared primitives | §3.5 genotype→phenotype map | `core/genetics/`, `composable/definitions.py` |
| P2 multi-pressure arena | §3.8 environment / fitness signal | `benchmarks/`, `core/worlds/`, movement arbiter |
| P3 Pareto / MAP-Elites | §3.3 selection, §3.4 diversity | `core/reproduction/`, `core/genetics/diversity.py` |
| P4 transfer assay | §2 measurement, §6 frozen ruler | pattern of `tools/run_selection_response_assay.py` |
| P5 curriculum | §3.8 POET-style coevolution | P2 arena |
| P6 instrumentation | §2 measurement | `core/ecosystem_stats.py`, `tools/evolution_report.py` |

The next concrete action is to run the §5 experiment through the `/deliberate`
board, framed on lever §3.5 with the P4 transfer assay as its evolvability
metric.
