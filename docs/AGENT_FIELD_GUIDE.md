# The Agent Field Guide

**A foolproof on-ramp for AI agents of any capability level to make a real,
mergeable contribution to Tank World — without breaking anything.**

> If you only read one document before contributing, read this one. It is
> written to be followed literally. Where other guides explain *why*, this guide
> tells you *exactly what to do next*. When in doubt, do the smallest safe thing
> on the menu and stop.

---

## 1. What you are joining (the 90-second version)

Tank World is a **living research organism**. Fish with inherited behaviors
compete for survival inside a deterministic simulation. AI agents — you —
watch the simulation, find something that can be made better, change the code,
prove the change is an improvement, and open a pull request. CI re-runs the
proof. If it holds, your change merges and becomes the starting point for the
next agent.

This is the part worth pausing on: **Git is the genome.**

- Your pull request is a **mutation**.
- CI is **natural selection** — it kills changes that make things worse.
- A merged PR is **offspring** — every future agent inherits your work.
- The Git history is a **phylogenetic tree** you can trace back to the first commit.

You are not "using" this project. You are *in* it. Whatever you commit becomes
permanent ancestry that thousands of later simulation-generations and later
agents build on top of. A one-line parameter fix you make today can still be
visible in the lineage a year from now. That is the cool part — and it is also
why the rules below exist.

There are three layers of evolution happening at once:

| Layer | What evolves | Who drives it | Your typical role |
|-------|--------------|---------------|-------------------|
| **Layer 0** | Fish behavior, in-world | Natural selection inside the sim | Run sims, read the telemetry |
| **Layer 1** | The algorithms & config | **You**, via benchmarked PRs | Improve code, prove it with numbers |
| **Layer 2** | The benchmarks, docs, CI, this guide | **You**, with human review | Make the toolkit clearer & stronger |

You do not need to understand all three to help. You only need to pick **one
small task**, follow the recipe, and prove you didn't break anything.

---

## 2. The Golden Path (works for every task)

This six-step loop is the whole job. Every recipe in this guide is a
specialization of it. Memorize the shape:

```
1. CHECK    python tools/smoke_gate.py        # is the repo healthy right now?
2. PICK     one task from the menu in §4       # exactly one, the smallest that helps
3. CHANGE   edit the files the recipe names    # nothing the recipe didn't mention
4. RUN      python tools/agent_gate.py        # local validation gate (under 90s)
5. PROVE    python tools/pre_pr_gate.py          # did I keep it healthy?
6. WRITE    a clear commit + PR (§6 template)  # what, why, and the proof
7. STOP     one focused change per PR           # resist doing "just one more thing"
```

If step 1 fails on a fresh checkout, **stop and report it** — the repo was
already broken before you touched it, and that itself is a useful finding. Do
not try to fix unrelated breakage on top of your task.

---

## 3. The Five Unbreakable Rules

These are not suggestions. A PR that violates any of them will (and should) be
rejected. If a rule seems to block your task, your task is wrong — pick a
different one.

1. **One change per PR.** Never mix a Layer 1 algorithm/config change with a
   Layer 2 docs/CI/benchmark change. Never bundle two unrelated fixes. Small and
   focused always beats big and clever here.

2. **Determinism is sacred.** Every benchmark uses a fixed seed and must produce
   byte-for-byte identical results on a re-run. Never introduce `time.time()`,
   the global `random` module, network calls, or anything that varies between
   runs into simulation or benchmark code. Always pass `--seed 42`.

3. **Never hand-edit champion files.** Files under `champions/**/*.json` are the
   official record of the best known results. Do **not** edit, overwrite, or
   "update" them unless a human explicitly told you to and you have reproduced
   the score yourself. When unsure: leave them alone. This is the single most
   common way a well-meaning agent corrupts the project.

4. **No claims without proof.** Never say "this is faster / better / healthier"
   without a reproduction command, the seed, the before number, and the after
   number. "Seems better" is not evidence. If you cannot measure it, do not
   claim it.

5. **No placeholders.** Do not commit `TODO`, stub functions, commented-out
   code, or "fill this in later" text. Every change you commit must be complete
   and real.

---

## 4. The Starter Task Menu

Pick **one**. Tasks are ordered easiest-first. If you are a smaller or less
certain model, **start at the top** — T1 and T2 are almost impossible to get
wrong and are genuinely valuable. You do not earn points for difficulty; you
earn them for landing a clean, correct change.

Every recipe has the same shape: **Goal · Difficulty · Layer · Files · Steps ·
Done-check.** Follow it top to bottom.

---

### T1 — Fix a documentation inconsistency

- **Difficulty:** ⭐ (trivial) · **Layer:** 2
- **Why it helps:** Clear docs are what let the *next* simple agent succeed.
  Improving them is real Layer 2 evolution, not busywork.

**Files:** any `.md` in the repo root or `docs/`.

**Steps:**
1. Read a doc and find one concrete, checkable problem: a command that no longer
   exists, a file path that 404s, a count that disagrees with the code, a broken
   internal link.
2. Verify the *correct* value yourself before changing anything. For a file
   path, confirm the file exists. For a command, run it. For a count, check the
   source.
3. Make the smallest edit that fixes it. Do not rewrite surrounding prose you
   weren't asked to touch.
4. Run `python tools/smoke_gate.py` — it includes a docs-consistency test
   (`tests/test_docs_agent_onboarding.py`) that catches broken benchmark paths
   and stale CI job names. Green means your edit is consistent.

**Done-check:** The thing you fixed is now correct, the smoke gate passes, and
your diff touches only the lines needed for the fix.

---

### T2 — Add or strengthen a test

- **Difficulty:** ⭐⭐ (easy) · **Layer:** 2
- **Why it helps:** Tests are the immune system. Every test you add makes it
  harder for a future change to silently break something.

**Files:** add to or create under `tests/` (see `tests/smoke/`, `tests/core/`,
`tests/integration/` for examples to copy).

**Steps:**
1. Find a function or invariant that *should* be true but isn't directly tested.
   Good candidates: a helper in `core/` with clear inputs and outputs, or a
   property like "the survival benchmark score is deterministic for a fixed seed."
2. Write a small, fast, deterministic test. Copy the style of a neighboring test
   file. No network, no sleeps, no global random — pass seeds explicitly.
3. Run just your test: `pytest tests/path/to/your_test.py -v`.
4. Run `python tools/pre_pr_gate.py` to confirm the whole non-slow suite is green.

**Done-check:** Your test passes, it fails if you deliberately break the thing
it tests (try it, then revert), and `pre_pr_gate` is green.

---

### T3 — Tune one config parameter and measure the effect

- **Difficulty:** ⭐⭐⭐ (medium) · **Layer:** 1
- **Why it helps:** This is the heart of Layer 1 — a data-driven, reproducible
  improvement to the ecosystem.

**Files:** one value in `core/config/fish.py` or `core/config/food.py`.

**Steps:**
1. Establish a baseline number first. Run a live benchmark and record its score:
   ```bash
   python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42 --out before.json
   ```
   Note the `"score"` field in `before.json`.
2. Change **exactly one** parameter. Make a small, defensible change (e.g. a
   10–20% nudge), not a wild swing. Write down your hypothesis: "lowering X
   should reduce starvation because…"
3. Re-run the same benchmark to an `after.json`:
   ```bash
   python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42 --out after.json
   ```
4. Compare the two `score` values. **If `after` is not clearly better than
   `before`, revert your change** — a neutral or worse change is not a
   contribution. Try a different hypothesis or pick a different task.
5. Check you didn't break another benchmark:
   ```bash
   python tools/run_bench.py benchmarks/tank/ecosystem_health_10k.py --seed 42 --out eco.json
   ```
6. Run `python tools/pre_pr_gate.py`.

**Done-check:** `after.score > before.score` on `survival_5k`, no meaningful
regression on `ecosystem_health_10k`, `pre_pr_gate` green, and your PR quotes both
numbers and the exact reproduction commands.

> ⚠️ Do **not** edit `champions/tank/survival_5k.json` to record your new score.
> Report the numbers in the PR and let the human/CI decide whether the champion
> moves. (See Rule 3.)

---

### T4 — Improve one behavior algorithm

- **Difficulty:** ⭐⭐⭐⭐ (advanced) · **Layer:** 1
- **Why it helps:** Behavior algorithms are the literal genes fish inherit.
  Improving one is the most direct way to make the simulation smarter.

**Files:** the relevant module under `core/algorithms/` — energy strategies in
`core/algorithms/energy_management.py`, foraging in `core/algorithms/food_seeking/`,
the composable framework in `core/algorithms/composable/` (`behavior.py`,
`actions.py`, `definitions.py`).

**Steps:**
1. **Read [docs/BEHAVIOR_DEVELOPMENT_GUIDE.md](BEHAVIOR_DEVELOPMENT_GUIDE.md)
   first.** It documents the base class, the `execute(fish)` contract, the
   docstring format, and parameter bounds. Do not skip it.
2. Pick an *existing* algorithm to improve rather than inventing a new one — it's
   lower risk. Understand what it currently does and find one weakness.
3. Make a focused change. Keep parameters within their declared bounds. Always
   return a valid normalized direction (use the `_safe_normalize` helper); never
   crash inside `execute`.
4. Prove it the same way as T3: baseline benchmark → change → re-benchmark →
   compare scores, check a second benchmark for regressions.
5. Run `python tools/pre_pr_gate.py`.

**Done-check:** Measurable benchmark improvement with no regression, `pre_pr_gate`
green, and the algorithm still handles edge cases (no food visible, critical
energy) without erroring.

> If this feels like too much, it is fine to drop down to T3 or T1. A landed T1
> beats an abandoned T4.

---

### T5 — Improve a diagnostic or developer tool

- **Difficulty:** ⭐⭐⭐ (medium) · **Layer:** 2
- **Why it helps:** Better tools make every future agent faster at finding
  problems. This is Layer 2 leverage.

**Files:** scripts in `scripts/` (e.g. `scripts/diagnose_food_seeking.py`,
`scripts/analyze_population.py`) or helpers in `tools/`.

**Steps:**
1. Run an existing diagnostic and notice something it *doesn't* surface but
   should — a metric, a clearer summary line, a missing `--help`.
2. Add it. Keep output deterministic and readable. Don't change what the script
   already prints unless that's the fix.
3. Run the script before and after to confirm it still works and now does the
   new thing.
4. Run `python tools/pre_pr_gate.py`.

**Done-check:** The tool runs cleanly, does the new helpful thing, breaks
nothing else, and `pre_pr_gate` is green.

---

## 5. "What should I do?" — the decision tree

Follow the first line that matches your situation.

```
Were you given a SPECIFIC task (e.g. "fix bug X", "improve algorithm Y")?
   └─ YES → do that, using the matching recipe in §4 as your safety rails.
   └─ NO  → continue ↓

Did `python tools/smoke_gate.py` pass on a fresh checkout?
   └─ NO  → STOP. Report that the repo is broken before your changes. Do not pile on.
   └─ YES → continue ↓

Are you a smaller / less-certain model, or is this your first time here?
   └─ YES → pick T1 (docs fix) or T2 (add a test). Land it cleanly. That's a win.
   └─ NO  → continue ↓

Do you want to improve the SIMULATION's numbers (Layer 1)?
   └─ YES → T3 (config tune) if cautious, T4 (algorithm) if confident.
   └─ NO  → T1, T2, or T5 (docs / tests / tooling — all Layer 2).
```

When two tasks both look reasonable, **pick the smaller one.** The project
advances through many small, verified mutations, not occasional big risky ones.

---

## 6. Writing a PR that gets merged

A reviewer (human or CI) needs to answer two questions in under a minute: *what
changed* and *how do I know it's safe*. Give them both. Copy this template:

```markdown
## What changed
<one or two sentences — the single thing this PR does>

## Layer
- [ ] Layer 1 (algorithm / config — affects simulation results)
- [ ] Layer 2 (docs / tests / tooling — does not affect simulation results)
(check exactly one)

## Why
<the problem this solves, and your hypothesis if it was a tuning change>

## Proof
<for Layer 1: before/after scores + the exact reproduction commands and seed>
<for Layer 2: confirmation that smoke_gate / agent_gate / pre_pr_gate pass>

Reproduction:
    python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

Before: <score>
After:  <score>

## No regressions
<which other benchmark(s) you checked, and that pre_pr_gate is green>
```

**Commit message** — same idea, compressed. State the change, the numbers, the
seed, and the reproduction command. Avoid vague messages like "improved stuff."

Before you commit, run the self-check:

- [ ] `python tools/agent_gate.py` and `python tools/pre_pr_gate.py` are green.
- [ ] My diff is **one focused change** (Rule 1).
- [ ] I did **not** touch `champions/**` by hand (Rule 3).
- [ ] I added **no** non-determinism (Rule 2).
- [ ] Every claim has a number and a reproduction command (Rule 4).
- [ ] **No** TODOs, stubs, or commented-out code (Rule 5).
- [ ] I ran `pre-commit run --all-files` (or `pre-commit install` earlier).

---

## 7. Traps that catch agents (and the exact escape)

These are real, repeatedly-hit pitfalls in this codebase. Knowing them up front
saves you a wasted PR.

- **"Population" means *fish*, not all entities.** In tank benchmarks,
  `avg_pop`, `mean_population`, and `final_population` count fish only.
  `final_total_entities` includes food, crabs, balls, and the castle — it is a
  *diagnostic number, never the score.* If a population number looks 5–10×
  too big, you're reading the wrong field.

- **Fish chase the ball before they chase food.** A soccer ball exists even in
  tank benchmarks (`tank_practice_enabled` defaults on), and ball pursuit
  out-prioritizes foraging in `core/movement_strategy.py`. If you're debugging
  high starvation, first check whether fish are clustering at the tank center
  around the ball instead of eating. `scripts/diagnose_food_seeking.py` helps.

- **Reproduction is funded by *surplus* energy.** Fish bank energy above
  `max_energy` and spend it making offspring. Any change that burns the surplus
  of well-fed fish (extra ball play, poker, costly movement) quietly suppresses
  birth rate and generation turnover — which the ecosystem benchmarks penalize.
  If births drop after your change, look for new energy costs.

- **A benchmark that won't reproduce usually means you added non-determinism.**
  Re-check for `time.time()`, global `random`, dict iteration order assumptions,
  or a forgotten seed. Run with `--verify-determinism` to confirm:
  ```bash
  python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42 --verify-determinism
  ```

- **High starvation is not automatically bad.** A healthy tank can still have
  most deaths be starvation if the population is large and turning over fast.
  Read the *whole* picture (population stability, generation rate, births) before
  concluding food-seeking is "broken."

---

## 8. The live benchmarks you can use right now

Only these exist today. Use them; do not reference benchmarks that aren't here
(planned ones live in [ROADMAP.md](ROADMAP.md)).

| Benchmark | What it measures |
|-----------|------------------|
| `benchmarks/tank/survival_5k.py` | Ecosystem stability over 5k frames (fish energy × fish population) |
| `benchmarks/tank/ecosystem_health_10k.py` | Longer-horizon ecosystem health over 10k frames |
| `benchmarks/soccer/training_3k.py` | Soccer-mode agent training, short |
| `benchmarks/soccer/training_5k.py` | Soccer-mode agent training, longer |

Each has a matching champion under `champions/tank/` or `champions/soccer/` that
records the best known result. **Read them for reference; never hand-edit them.**

---

## 9. Where to go deeper

You can contribute well using only this guide. When you want more depth:

| If you want to… | Read |
|-----------------|------|
| See the terse command cheat-sheet | [AGENT_QUICKSTART.md](AGENT_QUICKSTART.md) |
| Understand the full agent workflow | [../AGENTS.md](../AGENTS.md) |
| Write or improve a behavior algorithm | [BEHAVIOR_DEVELOPMENT_GUIDE.md](BEHAVIOR_DEVELOPMENT_GUIDE.md) |
| Follow the formal champion / PR protocol | [EVO_CONTRIBUTING.md](EVO_CONTRIBUTING.md) |
| Grasp the long-term vision | [VISION.md](VISION.md) |
| Learn the technical architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| See current priorities & planned work | [ROADMAP.md](ROADMAP.md) |
| Browse everything | [INDEX.md](INDEX.md) |

---

## 10. You are part of a lineage

Most codebases forget the work that built them. This one remembers all of it, on
purpose. The change you make today doesn't just ship — it becomes inherited
ancestry that every future simulation generation and every future agent starts
from. Small, correct, reproducible mutations are exactly how that lineage gets
better, generation after generation.

So pick one small task. Prove it. Commit it. Then the next agent — maybe a
simpler one than you, maybe a smarter one — picks up exactly where you left off.

Welcome to the evolution. 🐠🧬
