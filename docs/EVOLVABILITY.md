# EVOLVABILITY — the map for evolving the evolution engine

This is the working reference for any agent (or human) proposing, debating, voting on,
or building an improvement to Tank World. Our north star is not a healthier fish tank —
it is an **evolution engine that keeps getting better at discovering better solutions**
(open‑ended evolution). This doc exists so proposals are **bold, grounded, and
non‑repetitive**: it maps the evolvability *levers* to the code that implements them,
ports the relevant research canon onto this codebase, and keeps a graveyard of what has
already been tried.

Use it with the `/deliberate` board (propose → debate → ranked‑choice vote) and the
`/study-sim improve` build loop. See also `AGENTS.md` (the Evolution Loop), `CLAUDE.md`,
and `docs/VISION.md`.

---

## 1. The one trap to avoid

**Optimizing the fish's comfort is not the same as improving evolvability.** A change
that lets every fish survive *flattens the selection gradient* — everyone reproduces, so
nothing is selected — and is a **regression** for us even though the tank "looks
healthier." A change that sharpens selection, sustains variation, and lets the population
keep discovering better strategies is a **win**, even if mortality stays high. Judge every
idea by: *does it make the system better at evolving?*

---

## 2. How we measure "more evolvable"

| Signal | What it tells us | Where it comes from |
|---|---|---|
| **Directional selection vs churn** | Are trait means *drifting* in a fitness‑tracking direction, or just turning over flat (pure drift)? This is the single most important signal. | **Live:** `tools/evolution_report.py --url … --json` (`trait_drift` / `selection_detected`) and the UI's **Trait Drift** chart. **Controlled check (a fresh seeded probe, not the live tank):** `scripts/diagnose_evolution.py` — the *builder's* validation tool, not a live lens. |
| **Sustained diversity** | Is the gene pool keeping the raw material to keep innovating, or prematurely converging? | `core/genetics/diversity.py` (`genetic_distance`, Shannon entropy), `core/genetic_diversity_tracker.py`, `diversity_score` |
| **Quality‑gain per generation** | Are new generations *better*, or merely newer? | trait drift × turnover together; lineage outcomes |
| **The fitness signal** | The Layer‑1 objective the build loop optimizes | `benchmarks/tank/ecosystem_health_10k.py` |

**Know the benchmark's shape — and its blind spot.** `ecosystem_health_10k` scores:

```
score = generation_rate × diversity_bonus × stability_bonus × (1 − starvation_penalty)
```

It rewards turnover, multiple algorithms, and population stability. It does **not**
directly reward *directional selection* or *quality‑per‑generation* — so it can be gamed
by fast churn with flat traits. That blind spot is itself one of the highest‑leverage
things to fix (see §3.8 and §6). And because the score is roughly linear in
`max_generation`, it is **trajectory‑sensitive on a single seed** — always verify across
seeds **42, 7, 123**.

---

## 3. The levers (mapped to code)

Tank World already has a **rich** evolutionary machine — including heritable, self‑adapting
mutation operators, which most toy systems lack. The bold move is usually to *reconfigure
or couple* these levers, not to reinvent basics. Each lever below names where it lives and
points at directions worth a proposal.

### 3.1 Variation operators — mutation
- **Code:** `core/evolution/mutation.py` (`MutationConfig`: `base_rate≈0.12`, `base_strength≈0.10`, **`algorithm_switch_rate≈0.08`** = macromutation to a whole new behavior algorithm, plus min/max bounds); `core/genetics/trait.py` (**heritable per‑trait meta‑genes** `mutation_rate`, `mutation_strength`, `hgt_probability` with `mutate_meta()` and `META_MUTATION_*` bounds).
- **State:** evolvability is *already heritable and self‑adapting* — a real strength to build on.
- **Bold directions:** couple meta‑genes to a **live signal** (raise exploration when diversity collapses or fitness stalls — adaptive *plasticity of evolvability*); learned operator selection; targeted hypermutation of stagnant lineages.

### 3.2 Recombination & horizontal gene transfer (HGT)
- **Code:** `core/evolution/inheritance.py` (`inherit_trait`, `inherit_discrete_trait`, `inherit_algorithm`, `crossover_algorithms_weighted`); `core/genetics/genome.py` (`GeneticCrossoverMode`, `from_parents` vs `from_parents_recombination`); `hgt_probability` on each trait.
- **Bold directions:** modular/subtree crossover of composable behaviors; HGT biased toward successful lineages (a "memetic" gene market); make the crossover *mode itself* heritable and let it evolve.

### 3.3 Selection gradient — who gets to reproduce
- **Code:** `core/reproduction/reproduction_service.py`, `core/reproduction/reproduction_system.py`, `core/config/fish.py` (energy thresholds, lifecycle). **Gotcha:** reproduction is funded by **overflow** energy (banked *above* `max_energy`).
- **Bold directions:** soft/tournament/fitness‑proportional selection on *relative* rank rather than an absolute energy threshold; truncation selection; sharpen or flatten the gradient deliberately and measure selection response.

### 3.4 Diversity maintenance / anti‑convergence
- **Code:** `core/genetics/diversity.py`, `core/genetic_diversity_tracker.py`, `core/ecosystem_stats.py`.
- **Bold directions:** fitness sharing / niching; **novelty search**; **speciation** that protects young or novel lineages from being out‑competed before they bloom; a **MAP‑Elites** archive that keeps the champion of each behavior niche.

### 3.5 Genotype → phenotype map (the encoding)
- **Code:** `core/genetics/genome.py`, `core/genetics/expression.py`, `core/genetics/behavioral.py`, `core/genetics/physical.py`; the behavior space in `core/algorithms/composable/definitions.py` (the 58 strategies and their parameter bounds), `behavior.py`, `actions.py`.
- **Why it matters:** evolvability is largely a property of the *map*. A more evolvable encoding makes good variation cheap to reach.
- **Bold directions:** indirect/**developmental encoding** (CPPN‑style) so one gene reshapes many correlated traits; modular/hierarchical genomes; widen the morphospace or behavior‑primitive set so there is more to discover.

### 3.6 Sexual selection / mate choice
- **Code:** `core/genetics/mate_preferences.py` (already present: `prefer_similar_size`, `prefer_different_color`, `prefer_high_energy`, `prefer_high_aggression`, `prefer_high_social_tendency`, …; inherited from parents).
- **Bold directions:** runaway sexual selection as an open‑ended driver; **assortative mating → sympatric speciation** (split the gene pool into niches); mate choice on *novelty* rather than fitness.

### 3.7 Reproduction strategy
- **Code:** `GeneticCrossoverMode` and the two paths in `core/genetics/genome.py`; sexual vs asexual stats in `core/reproduction/reproduction_stats_manager.py`.
- **Bold directions:** let sexual‑vs‑asexual be a heritable, context‑sensitive switch (e.g. sex under stress); evolve recombination rate.

### 3.8 The environment & the fitness signal itself (highest leverage, highest risk)
- **Code:** `benchmarks/tank/ecosystem_health_10k.py` (the Layer‑1 objective); the world's pressures — food (`core/config/food.py`), crabs/predation, plants/energy, poker, soccer; `core/config/*`.
- **Why it matters:** the *selective pressure* is what evolution responds to. Changing it changes everything downstream. This is literally "evolving the evolution engine."
- **Bold directions:** a **coevolving environment** (POET / minimal‑criterion coevolution) that gets harder exactly as the population adapts; multiple coexisting niches; a predator–prey **arms race**; rebuild the fitness signal to reward *directional quality*, not churn. **Caveat:** changes to the objective can Goodhart the very number we trust — see §6.

---

## 4. The canon, ported to fish

A springboard, not a fence. Each is a known route to open‑endedness; the third column is
the nearest lever above.

| Idea | How it could land in Tank World | Lever |
|---|---|---|
| **Novelty search / Quality‑Diversity (MAP‑Elites)** | Reward *interesting* behavior, archive a champion per behavior niche | §3.4, §3.8 |
| **POET / Minimal‑Criterion Coevolution** | Let the environment evolve to keep just‑barely challenging the fish | §3.8 |
| **NEAT speciation & protected innovation** | Shield young/novel lineages so fragile inventions survive infancy | §3.4, §3.6 |
| **CPPN / indirect (developmental) encoding** | One gene reshapes a whole body plan or behavior tree | §3.5 |
| **Evolution of evolvability** | Self‑adapting mutation/HGT — *already partly here* (§3.1); extend & couple to signals | §3.1 |
| **Sexual selection / mate choice** | Drive open‑ended ornament/behavior races; speciation via assortative mating | §3.6 |
| **Baldwin effect** | Let lifetime learning (skill‑games) steer which genes win | §3.5 |
| **Major transitions / cooperation** | Schooling, kin selection, division of labour → new level of organization | §3.3, schooling algos |
| **Niche construction** | Organisms reshape their own selective environment (plants, energy) | §3.8 |

---

## 5. Ideas graveyard & load‑bearing constraints

A living log so the board doesn't re‑propose dead ends. **Builders: append outcomes here**
(win *or* loss) with a one‑line lesson; the `/deliberate` META round proposes additions.

**Load‑bearing constraints (don't fight these blindly):**
- **Ball pursuit pre‑empts food‑seeking.** In `core/movement_strategy.py`, soccer‑ball
  pursuit runs before composable food pursuit, and the ball exists even in benchmark
  configs. A foraging intervention that ignores this will quietly fail.
- **Reproduction is funded by overflow energy** (banked above `max_energy`). Energy sinks
  (ball play, poker) suppress births; "give fish more energy" raises reproduction only if
  it becomes *surplus*.
- **`ecosystem_health` is trajectory‑sensitive on one seed** (≈linear in `max_generation`).
  A single‑seed win is often a mirage — verify on seeds 7 and 123.
- **Determinism is non‑negotiable.** All benchmarks use fixed seeds; any change that
  introduces nondeterminism is rejected regardless of its score.

**Tried (template — add real entries as experiments land):**

```
- YYYY-MM-DD | <idea> | lever §X.Y | hypothesis: <…> | result: <bench Δ, seeds, drift Δ>
  | verdict: adopted / rejected / inconclusive | lesson: <one line>
```

- 2026-07-01 | Behavioral assortative mating (`prefer_similar_behavior` heritable mate
  preference, matched on threat_response/food_approach/social_mode/poker_engagement via
  `ComposableBehavior.similarity()`) | lever §3.6 + §3.4 | hypothesis: shielding
  behaviorally-similar mates from dilution by the majority strategy would sustain diversity
  and protect novel/minority niches without weakening selection | result:
  `run_selection_response_assay.py` seeds 42/7/123, mean composite score 50.57 → 48.99
  (−3.1%, dominated by offsetting per-seed swings: seed 7 −49%, seed 123 +75%, seed 42 flat
  — within the documented seed-trajectory noise band); mean drift-per-generation improved
  +8.1% (kill criterion passed: no seed showed degraded drift or population collapse); mean
  `diversity_delta` was flat (+0.066 → +0.068) and `min_final_diversity` across seeds fell
  (0.304 → 0.269) | verdict: inconclusive — merged as a safe, neutral-default (0.5 = no-op)
  heritable lever since it passes its own kill criterion and adds a new evolvable dimension,
  but it is **not** a demonstrated diversity win | lesson: the preference starts neutral and
  only diverges via mutation, so a 10k-frame/~7–9-generation window may be too short for a
  freshly-introduced heritable trait to reach an allele frequency that visibly changes
  population dynamics. Retest over a longer horizon (30k+ frames) or with a biased initial
  distribution before concluding the mechanism does or doesn't work.

- 2026-07-01 | Panic Button -- diversity-triggered hypermutation (plasticity of evolvability) | lever §3.1 | hypothesis: a population-level panic reflex that scales mutation rate and strength exactly when diversity collapses prevents premature convergence without degrading directional selection | result: `run_selection_response_assay.py` seeds 42/7/123, mean composite score 48.99 → 53.20 (+8.6%), mean selected trait fraction 0.78 → 0.89 (+14%), mean drift-per-generation 3.45% → 3.62% (+4.9%), diversity delta maintained (0.02), min final diversity 0.249 | verdict: adopted | lesson: seeded clamping of mutation parameters during hypermutation prevents destructive runaway dynamics while successfully boosting selection response.

---

## 6. Open problem — a frozen evolvability benchmark

`ecosystem_health_10k` is the objective the build loop optimizes, but if proposals may
*edit the objective they are scored on*, they can move the goalposts and "win" without the
engine actually getting better. The durable fix is a **frozen, held‑out measure of
evolvability** — e.g. the population's **selection response** (trait drift under a fixed
perturbation across held‑out seeds) — that proposals are scored against but may **not**
modify.

The first frozen assay is now:

```bash
# Held-out multi-seed ruler (default seeds: 42, 7, 123)
python tools/run_selection_response_assay.py

# Single-seed benchmark-compatible surface
python tools/run_bench.py benchmarks/tank/selection_response_10k.py --seed 42
```

It reports a decomposed score: directional trait drift per generation, sustained
diversity, and quality-per-generation. Treat it as held out: a PR that edits this assay
must not claim an improvement from the edited assay in the same change. Changes to the
fitness signal remain the highest‑leverage *and* highest‑risk class of work, kept
separate from Layer‑1 changes and justified rigorously.

---

## 7. Proposing well

Anchor every proposal to a **lever (§3)** and a **measurement (§2)**, and structure it as
the `/deliberate` rubric expects:

> **VISION** (the big bet — what new evolutionary dynamic it unleashes) · **LEVER** (§3.x) ·
> **FIRST EXPERIMENT** (smallest change that tests the bet) · **EVOLVABILITY METRIC** (how
> we'll *see* it work, across seeds 42/7/123) · **ANTI‑GOODHART** (why it isn't a gamed
> proxy).

Be **bold in ambition, rigorous in justification**: dream big, then name the small first
experiment that would prove or kill it. A safe 5% parameter tweak is the floor, not the
goal.
