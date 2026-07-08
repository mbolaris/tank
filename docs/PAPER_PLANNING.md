# Paper Planning — AI-Agent-Driven Evolution in Tank World

Focus chosen: **Layers 1–2 (AI agents as the evolutionary mechanism)**, the angle that
distinguishes Tank World from conventional ALife testbeds. Most ALife papers study
selection *inside* a simulation; here the novel object of study is an LLM agent that
runs benchmarks, rewrites algorithms, and commits improvements — with git history as the
phylogenetic record. The topics below are ordered by novelty × feasibility given what
already exists in the repo.

---

## Part 1 — Candidate research topics

### T1 (lead candidate). "Git as heredity": characterizing the AI-driven improvement process
**Question.** When LLM agents evolve the algorithm library through the benchmark→PR→CI
loop, what does the *improvement trajectory* look like, and does it resemble biological
evolutionary dynamics (punctuated equilibria, diminishing returns, neutral drift, epistasis)?

**Why it's strong.** You already log the raw data: `champions/tank/*.json` records a scored
`history` of accepted improvements with timestamps and metadata; git history is the full
mutation record including *rejected* branches. No other ALife testbed frames LLM code edits
as a measurable evolutionary process with a fitness registry.

**What to measure.** Fitness-vs-attempt curves per benchmark; acceptance rate over time;
"effect size" distribution of accepted mutations (are gains fat-tailed?); whether later gains
require larger edits (rising epistasis); reversions/regressions. Compare AI-driven search to a
random/parameter-sweep baseline on the same benchmark.

**Gap to fill before writing.** You currently have only 5–6 recorded champions per benchmark.
You need *hundreds* of logged attempts (accepted and rejected) to make statistical claims.
See I1, I3 below.

### T2. Does an evolvability benchmark actually select for more-evolvable systems?
**Question.** `selection_response_10k` explicitly measures directional heritable trait
response while penalizing diversity collapse. Does optimizing against it produce genotype→
phenotype maps that evolve *faster on held-out tasks* than optimizing against a pure-fitness
benchmark (`survival_5k`)?

**Why it's strong.** "Evolvability of evolvability" is a marquee open problem in ALife
(`docs/EVOLVABILITY.md` §6 already frames it). You have the two contrasting benchmarks and a
frozen multi-seed ruler (seeds 42, 7, 123) to test generalization.

**What to measure.** Train agents against each benchmark; evaluate both champion lineages on a
*held-out* third task; test whether the evolvability-optimized lineage transfers better.

### T3. Meta-evolution: do agent-authored changes to the benchmarks/prompts improve Layer 1?
**Question.** Layer 2 lets agents edit the fitness functions, gates, and instructions
themselves. Does letting agents modify the *search process* outperform a fixed process —
or does it collapse into Goodharting the benchmark?

**Why it's strong (and risky).** This is the most conceptually novel claim (self-modifying
research loop), but it's the hardest to make rigorous. Reviewers will immediately ask about
reward hacking. You'd need a held-out evaluator the agent cannot edit. Treat as a stretch
section of T1 rather than a standalone paper unless results are clean.

### T4. Interpretable vs. black-box: what kinds of improvements do LLM agents find?
**Question.** Tank World deliberately uses explicit, named strategies (composable
algorithms) rather than neural nets. Do LLM agents exploit that interpretability — e.g.
recombining existing named behaviors, tuning bounded parameters, or authoring genuinely novel
sub-behaviors? Categorize the *mutation types* the agent produces and which yield the durable
wins.

**Why it's strong.** Directly tests the project's core design bet (interpretable algorithms).
Produces a taxonomy — good, citable, low-controversy contribution. Feasible from git diffs
you already have.

### T5 (supporting / methods). Tank World as a reproducible ALife benchmark suite
A shorter "systems/methods" paper: the determinism guarantees, config-hash verification,
champion/BKS registry, multi-seed held-out rulers, and the three-layer protocol as a
*reusable* platform. Lower novelty ceiling but a good fallback and a natural companion to
T1.

**Recommendation.** Build the paper around **T1** with **T4** as its analytical backbone, and
**T2** as a second experiment if time allows. T3 is a discussion/future-work section. T5 is the
fallback if the AI-agent data doesn't reach significance.

---

## Part 2 — Making the simulator better suited to academic research

These are the gaps between "cool self-evolving repo" and "defensible published result."
Ordered by how much they unblock the topics above.

### I1. Log *every* agent attempt, not just accepted champions (blocks T1, T4)
Right now only wins land in `champions/*.json`. For any statistical claim you need the full
attempt stream: prompt, diff, benchmark score(s), seeds, accept/reject, wall-clock, token cost.
Add an append-only `experiments/ledger.jsonl` written by `ai_code_evolution_agent.py` on every
attempt. This single change is what turns anecdotes into a dataset.

### I2. Fix single-seed fragility — report multi-seed distributions everywhere (blocks all)
CLAUDE.md already warns that `ecosystem_health` is "trajectory-sensitive on a single seed" and
linear in a small integer (`max_generation`). For a paper you cannot headline seed-42 numbers.
Make the multi-seed held-out rulers (42, 7, 123, and ideally 10–30 seeds) the default reported
metric, with means ± CIs and a significance test baked into `validate_improvement.py`. Reviewers
will reject single-seed wins.

### I3. Enough runs for statistics + a proper baseline (blocks T1, T2)
Two needs: (a) volume — hundreds to thousands of logged attempts, which means cheap headless
runs and possibly a small/cheap model in the loop; (b) a **non-AI baseline** search (random edit,
parameter sweep, or evolutionary hill-climb over parameters) so "the LLM helped" is a controlled
claim, not just "things improved."

### I4. Guard against benchmark overfitting / reward hacking (blocks T2, T3)
Add a *held-out* task the agent and its prompts cannot see or edit, and report champion
performance on it. Without this, any Layer-2 result reads as Goodharting. This is the single
most important credibility fix for the meta-evolution story.

### I5. Statistical tooling as first-class output
A `tools/analyze_lineage.py` that turns the ledger + champion history + git log into the paper's
figures: fitness-vs-attempt curves, effect-size histograms, acceptance-rate-over-time, trait-drift
plots (you already have `diagnose_evolution.py` for trait drift). Having the analysis reproducible
from raw logs is itself a reviewability asset.

### I6. Provenance & reproducibility manifest
Each experiment should pin: git SHA, config hash (you have `config_hash`), seed set, Python/env,
model name + version, and prompt template hash. Bundle into the ledger so every figure in the
paper is regenerable. This is cheap and strongly de-risks review.

### I7. Cost/compute accounting
For an AI-agent-driven method, "improvement per token / per GPU-hour / per wall-clock" is a
metric reviewers will want. Log token and time cost per attempt (part of I1) so you can report
efficiency, not just final fitness.

### I8. (Optional) Ablations infrastructure
To claim the loop's *components* matter (CI gate, champion registry, multi-seed validation,
diversity penalty), you'll want to toggle each off and re-run. A config flag layer that records
which mechanisms were active per experiment makes ablation tables trivial.

---

## Suggested next steps
1. Decide scope: confirm T1+T4 as the spine (recommended).
2. Land **I1** (attempt ledger) and **I2** (multi-seed default) first — nothing else is
   publishable without them.
3. Run a pilot: ~100 logged attempts on one benchmark + a random/parameter-sweep baseline;
   inspect the fitness-vs-attempt curve to confirm there's a real, measurable signal.
4. From the pilot, pick the venue (ALIFE/ECAL conference if the dynamics are clean; workshop/
   arXiv if it's an early but interesting result; journal only once multi-seed stats are solid).
5. Draft the intro around the "git as heredity / AI as the evolutionary operator" framing.

---

## Part 3 — Concrete instrumentation backlog (first PRs)

Part 2 names the gaps; this is the ordered, buildable version. Each item is a small,
self-contained PR that improves research instrumentation **without changing simulation
behavior** — deliberately low-risk while the repo is stabilizing. Do them roughly in this
order; the first two are the highest-leverage steps toward a real dataset.

The guiding principle: turn the paper direction into instrumentation before attempting an
"AI scientist" pipeline. Prefer standard-library-only tools and focused subprocess/unit
tests over new dependencies.

### P1. Fix `scripts/diagnose.py` false import failures (contributor onboarding)
On a fresh checkout *without* an editable install, `python scripts/diagnose.py` run from the
repo root puts `scripts/` on `sys.path[0]` (not the repo root), so the `Import core` and
`Import backend` checks can falsely report `ModuleNotFoundError` even though the repo is fine.
`tools/run_bench.py` already avoids this by inserting the repo root into `sys.path` (see its
lines 16–18); `diagnose.py` should mirror that. After
`REPO_ROOT = Path(__file__).resolve().parents[1]` add:

```python
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
```

Add a regression test that invokes the script as a subprocess and asserts it does not
falsely fail `Import core` / `Import backend`. Keep all other diagnostic behavior unchanged.
*(Note: on an environment where the package is already `pip install -e .`-installed, the
checks pass today because `core` resolves via site-packages — the fix is a robustness change
for the uninstalled case, not a bug visible in CI.)*

### P2. `core/research/attempt_ledger.py` — the append-only attempt ledger (unblocks T1, T4; implements I1)
The highest-leverage paper PR. Ship the schema + JSONL writer/reader **only** — do not wire it
into the agent workflow yet. Create `core/research/attempt_ledger.py` and
`tests/test_attempt_ledger.py`.

Typed `AttemptRecord` (frozen dataclass) fields: `schema_version`, `experiment_id`,
`attempt_id`, `timestamp`, `parent_sha`, `child_sha`, `agent_kind`, `target_benchmark`,
`train_seeds`, `decision` (`accepted`/`rejected`/`error`/`neutral`), `score_before`,
`score_after`, `delta`, `diff_files`, `notes`. Functions: `append_attempt(path, record)` and
`load_attempts(path)`. Tests cover: writes one JSONL line, appends without overwriting,
round-trips cleanly, rejects invalid `decision` values, and creates parent directories.

This is the single change that turns anecdotes into a dataset; keeping it decoupled from the
agent means it can land and be tested in isolation.

### P3. `tools/run_bench_matrix.py` — multi-seed summaries (unblocks all; implements I2/I5)
Reuse the existing benchmark contract (`BENCHMARK_ID` + `run(seed)`) from `tools/run_bench.py`.
A small stdlib-only CLI that runs one benchmark across comma-separated seeds and emits JSON with
`benchmark_id`, `seeds`, `per_seed`, `scores`, `mean`, `min`, `max`, `stdev`, `n`,
`runtime_seconds`, and `expected_runtime_seconds` when available:

```bash
python tools/run_bench_matrix.py benchmarks/soccer/training_3k.py --seeds 42,7,123 --out matrix.json
```

Test with a temporary fake benchmark module. No scipy — bootstrap CIs can come in a later PR.
This directly answers the CLAUDE.md warning about single-seed fragility.

### P4. `tools/check_locked_paths.py` — held-out-evaluator guardrail (unblocks T2/T3; implements I4)
Anti-Goodhart foundation. A CLI that calls `git diff --name-only` and exits nonzero if any
changed file falls under one or more `--locked` paths, printing clear violations:

```bash
python tools/check_locked_paths.py --locked benchmarks/heldout tools/paper_eval.py
```

Unit-test the pure path-matching helper (mock the git output). The `benchmarks/heldout` path
does not exist yet — creating it is the companion I4 task; this tool is the mechanism that keeps
the eventual held-out evaluator uneditable by the agent.

### P5. `tools/classify_patch.py` — coarse mutation taxonomy (supports T4)
Deterministic, rule-based (filename + keyword) classifier of a unified diff into coarse
categories: `docs_only`, `tests_only`, `benchmark_edit`, `reward_function_edit`,
`parameter_tuning`, `frontend_edit`, `backend_edit`, `core_behavior_edit`, `mixed`. JSON output
includes changed files, `lines_added`, `lines_removed`, and `matched_reasons`. Unit-test with
small inline diff strings. No LLM, no external dependency. This is a first-pass answer to T4's
"what kinds of mutations do agents make?" — good enough to bootstrap, refinable later.

### Recommended sequence
P1 → **P2** → P3 → P4 → P5. P2 (the attempt ledger) is the best first task: small, testable,
decoupled, and the thing that actually turns the project toward a defensible paper. None of
these five require touching simulation behavior.

---

## Related reading already in the repo
`docs/VISION.md` (three-layer paradigm), `docs/EVOLVABILITY.md` (§6 frozen evolvability
benchmark, ideas graveyard), `docs/MULTILEVEL_EVOLUTION_STRATEGY.md`, `docs/MULTI_PROBLEM_SPACE_SEARCH.md`,
`scripts/ai_code_evolution_agent.py`, `champions/tank/*.json`, `benchmarks/tank/selection_response_10k.py`.
