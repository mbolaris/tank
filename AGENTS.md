# AI Agent Guide: Tank World Evolution

**You are an AI agent. Your mission is to improve this self-evolving artificial life framework.** Read this document and begin contributing.

Tank World is a research framework where AI agents autonomously run experiments, analyze results, and commit improvements. Git is the heredity mechanism: your PRs are mutations, CI is selection, and merged changes become the baseline for future agents.

---

## If you were given a vague prompt

If you were given a vague prompt (e.g. "improve this project" or "fix some issues"), follow these strict instructions:
- **Run `python tools/smoke_gate.py` first** to verify the current state of the repository.
- **Read `docs/AGENT_FIELD_GUIDE.md`** for a foolproof, recipe-driven menu of safe starter tasks (especially if you are a smaller or less certain model — start with task T1 or T2).
- **Read `docs/AGENT_QUICKSTART.md`** to understand the repository structure and gate tiers.
- **Pick exactly one small improvement** to implement.
- **Prefer documentation/test/tooling cleanup** unless explicitly asked to optimize behavior algorithms.
- **Do not touch champion files** unless running and reproducing the relevant full benchmark.
- **Do not mix Layer 1 algorithm changes with Layer 2 benchmark/CI/docs changes** in a single PR.
- **End with the exact commands run and results** in your final response/PR.

---

## TL;DR - Start Here

```bash
# 1. Setup
pip install -e .[dev]
pre-commit install

# 2. Before coding, run the smoke gate (under 30 seconds)
python tools/smoke_gate.py

# 3. Run a baseline simulation with stats export
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# 4. Run a benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# 5. Identify what needs improvement, make changes, run the agent gate, commit
#    Run the fast gate before opening a PR
```

---

## The Three-Layer Evolution System

| Layer | What Evolves | How | Your Role |
|-------|--------------|-----|-----------|
| **Layer 0** | Fish behaviors in-world | Natural selection in simulation | Run simulations, capture champions |
| **Layer 1** | Algorithms and code | AI proposes improvements, CI validates | Analyze data, improve code, submit PRs |
| **Layer 2** | Tooling and workflows | Meta-evolution of how we evolve | Improve benchmarks, instructions, CI gates |

---

## The Evolution Loop

Every agent session should follow this loop:

```
1. RUN SIMULATION ──> 2. EVALUATE ──> 3. IDENTIFY GAPS
       |                                      |
       v                                      v
6. COMMIT & PR <──── 5. VALIDATE <──── 4. IMPROVE CODE
       |
       └───────────> REPEAT
```

---

## Studying a Running Simulation (Live)

Use this when the human asks **"how well are the fish evolving?"** or **"what
should we change to improve the simulation?"** about a simulation that is
*currently running* - typically the web-server mode (`python main.py`) left up
for hours or days. You do not stop it; you observe it, score it, and recommend.

The `/study-sim` slash command wraps this whole workflow. The engine underneath
it is one read-only tool:

```bash
# Attach to the running server and print a health report (human-readable)
python tools/evolution_report.py --url http://127.0.0.1:8000

# Same, but emit structured JSON you can parse and reason over
python tools/evolution_report.py --url http://127.0.0.1:8000 --json
```

It pulls the live telemetry (`/api/worlds/<id>/snapshot` and
`/api/world/<id>/metrics/history`) and returns:

- a **verdict** (`healthy`, `treading_water`, `stalled`, `struggling`,
  `collapsing`, `insufficient_data`) and per-axis grades (turnover, **selection**,
  foraging, diversity, population stability), graded against the *Healthy
  Ecosystem Indicators* table below;
- a **trait-drift table** - the population mean of the heritable foraging traits
  (`pursuit_aggression`, `prediction_skill`, `hunting_stamina`, `aggression`)
  plus speed/size, first sample -> last sample. **This is the key signal:** a
  population can churn through generations while its mean traits stay flat (pure
  drift). A consistent drift (>=5%) is direct evidence of *directional selection*,
  i.e. real Layer 0 evolution rather than mere reproduction; and
- **ranked, knob-specific recommendations** that name the actual file and the
  diagnostic to confirm each one (e.g. the ball-pursuit-vs-food-seeking gotcha,
  energy sinks suppressing births, weak selection pressure).

These same trait means are now retained over time in the metrics-history buffer
(schema v2) and drawn as the **Trait Drift** chart in the UI's Trends tab, so
long-running selection is visible live, not just churn.

### Other data sources

```bash
# No server up? Run a fresh deterministic probe and report on it
python tools/evolution_report.py --probe --frames 20000 --seed 42

# Analyse an exported stats JSON (main.py --export-stats)
python tools/evolution_report.py --stats results.json
```

### Multi-day runs: stream a journal

The in-memory history buffer keeps the most recent ~1M frames (2000 samples x
500), so on a days-long run the early history scrolls off. To keep the full
long-horizon trend, stream an append-only journal and analyse it later:

```bash
# Leave this running alongside the sim (Ctrl-C to stop)
python tools/evolution_report.py --watch --interval 300 --journal evolution_journal.jsonl

# Later, report over the entire journal (beyond what the live buffer holds)
python tools/evolution_report.py --history evolution_journal.jsonl
```

### From assessment to improvement

When the human asks you to *act* on the findings, drive the top-ranked
recommendation through the normal **Evolution Loop** (do not hand-wave a fix):
reproduce it with the named diagnostic, make the smallest change, run the smoke
then fast gate, benchmark the candidate against the `champions/` registry
(`ecosystem_health_10k` is the evolution-quality benchmark), and only claim an
improvement with a reproduction command, seed, score, and metadata. Keep Layer 1
(algorithm/config) changes separate from any Layer 2 change to the report tool,
benchmarks, or telemetry. Confirm selection is genuinely occurring (trait drift),
not just generation churn, with `scripts/diagnose_evolution.py`.

### Narrating the simulation to the UI (the Insights feed)

Assessment usually lives only in your chat transcript. To surface what you notice
**on the simulation UI itself**, post it to the world's **Insights** feed, where
it shows up live in the web UI's `💬 Insights` tab. Any agent with network access
to the server can do this - it is a plain HTTP POST, so you do not need to be the
process running the sim.

The `/observe-sim` slash command wraps the whole observe -> distill -> post loop.
Under it are two read/write tools:

```bash
# Read what's already been posted (so you don't repeat earlier comments)
python tools/post_commentary.py --url http://127.0.0.1:8000 --read --limit 15

# Post a short, evidence-backed observation to the Insights feed
python tools/post_commentary.py --url http://127.0.0.1:8000 \
  --text "Directional selection on pursuit_aggression: mean +12% over 40k frames" \
  --severity insight --tags selection,foraging \
  --metric max_generation=14 --metric pursuit_aggression_drift_pct=12
```

The REST surface (see `backend/routers/commentary.py`) is:

- `POST /api/world/<id>/commentary` - body `{text, author?, tags?, severity?,
  metrics?}`; `<id>` may be the literal `default`.
- `GET  /api/world/<id>/commentary?limit=&since_id=` - recent comments (what the
  UI polls, and what you read to avoid repeating yourself).

What makes a **good** comment: it is *specific and evidence-backed*, tied to a
number and a frame horizon, and *non-repetitive*. Pull the signal from the
`evolution_report.py` JSON - directional **selection vs churn** (trait drift),
**foraging / death causes**, **population turnover**, **diversity**, and the
**energy economy** that funds reproduction. Choose a `severity`
(`info` < `insight` < `warning` < `concern`) that matches the signal, and tag it
(`selection`, `foraging`, `turnover`, `diversity`, `population`, `energy`, ...).
Bad: "Fish are evolving." Good: "Starvation is 91% of deaths and fish are
clustering at the ball instead of foraging - foraging is broken, not slow."

Commentary is **Layer 2** (telemetry/UI): posting never perturbs the sim, and it
is separate from any Layer 1 fix. If an observation warrants a change, hand it to
`/study-sim improve` and the full Evolution Loop.

**Deliberating on the next improvement.** The same board doubles as a multi-agent
decision chamber: with `/deliberate`, models propose candidate improvements, debate
them, and run a ranked-choice vote on what to build next — anchored to the evolvability
levers in [docs/EVOLVABILITY.md](docs/EVOLVABILITY.md). The goal is not a healthier tank
but a more *evolvable* engine; read that doc before proposing.

---

## Step 1: Run Simulations

### Headless Mode (Use This)

```bash
# Quick test (5k frames)
python main.py --headless --max-frames 5000 --stats-interval 2500 --seed 42

# Standard experiment (30k frames)
python main.py --headless --max-frames 30000 --stats-interval 10000 --export-stats results.json --seed 42

# Long evolution run (100k frames)
python main.py --headless --max-frames 100000 --stats-interval 10000 --export-stats results.json --seed 42
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--headless` | No UI, 10-300x faster |
| `--max-frames N` | Simulation length (30 FPS, so 30000 = ~17 minutes sim time) |
| `--stats-interval N` | Print stats every N frames |
| `--export-stats FILE` | Export JSON for analysis |
| `--seed N` | Reproducible random seed (always use this) |

### Run Benchmarks

```bash
# Run the survival benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Validate against current champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

---

## Step 2: Evaluate Performance

### Key Metrics from `results.json`

**Tank Population Semantics**
- Tank benchmark population fields such as `avg_pop`, `mean_population`, and
  `final_population` mean **fish population**, not all entities.
- `final_total_entities` includes food and other world objects. It is diagnostic
  only and must never be treated as the population score.

**Death Causes (Most Critical)**
- `starvation`: Fish couldn't find food. >90% = food-seeking needs improvement.
- `predation`: Killed by crabs.
- `old_age`: Natural death. This is the desired outcome.

**Population Health**
- `total_births / total_deaths`: Should be >1 for growth
- `reproduction_success_rate`: >100% means multiple offspring per attempt
- `max_generation`: Higher = faster evolution

### Healthy Ecosystem Indicators

| Metric | Healthy Range | Warning |
|--------|--------------|---------|
| Starvation deaths | <80% | >95% = urgent fix needed |
| Population | >20 fish stable | Frequent emergency spawns = unstable |
| Generation rate | >5 per 10k frames | <3 = evolution too slow |
| Reproduction success | >120% | <100% = population declining |
| Diversity score | >15% | <10% = genetic bottleneck |

### Diagnosis Patterns

| Pattern | Root Cause | Fix Location |
|---------|------------|--------------|
| >90% starvation | Food detection too slow | `core/algorithms/composable/` |
| Frequent emergency spawns | Population crashes | `core/reproduction_service.py` |
| Low diversity | Genetic drift | `core/algorithms/registry.py` |
| Short lifespans | Energy costs too high | `core/config/fish.py` |

---

## Step 3: Identify and Implement Improvements

### Priority Areas

1. **Layer 1 (Algorithms)**: Improve the 58 behavior algorithms in `core/algorithms/`
2. **Layer 0 (In-World)**: Tune parameters in `core/config/` for better ecosystem dynamics
3. **Layer 2 (Meta)**: Improve benchmarks, CI, documentation, and workflows

### Key Files for Algorithm Improvements

```
core/algorithms/composable/
  definitions.py             # Algorithm parameter bounds
  behavior.py                # Main execute logic
  actions.py                 # Sub-behavior implementations
core/config/fish.py          # Energy costs, thresholds, lifecycle
core/config/food.py          # Food detection, spawning rates
core/reproduction_service.py # Emergency spawn logic
core/time_system.py          # Day/night detection penalty
```

### Using the AI Code Evolution Agent

```bash
# Run simulation and export stats
python main.py --headless --max-frames 30000 --export-stats results.json --seed 42

# Let AI identify and improve worst performer
python scripts/ai_code_evolution_agent.py results.json --provider anthropic

# With validation
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --validate

# Dry run
python scripts/ai_code_evolution_agent.py results.json --provider anthropic --dry-run
```

---

## Step 4: Validate Changes

### Tier 1: Smoke Gate (Before Coding)

Run the smoke gate before making changes:
```bash
python tools/smoke_gate.py
```
It targets under 30 seconds and runs quick format/lint checks plus a curated
correctness suite. It excludes the broad pytest suite, integration/slow/manual
tests, champion reproduction, and 5k/10k benchmarks.

### Tier 1.5: Agent Gate (Local Pre-Commit Check)

Run the agent gate before committing locally:
```bash
python tools/agent_gate.py
```
It runs the smoke gate plus a curated correctness suite of architecture, energy, genetics, and protocol tests. It targets under 90 seconds.

### Tier 2: Fast Gate (Before PR)

Run the fast gate before opening or updating a PR:
```bash
python tools/fast_gate.py
```
It runs the smoke gate plus the broad non-slow test suite (parallelized
across cores via pytest-xdist). It targets under 2-3 minutes on normal
developer/CI hardware and excludes integration/slow/manual tests and full
benchmarks. On constrained or single-core sandboxes it can take longer; if it
does, that's a hardware limit, not a sign something is broken.

### Tier 3: Full Validation (Maintainers/Nightly)

```bash
python tools/full_gate.py
```

This runs slow and integration tests plus strict champion reproduction. It is
for nightly or explicit maintainer use, not routine agent iteration.

### Run Full Benchmarks (Only for Candidate Improvements)

Only run full benchmarks after you have confirmed that the fast gate passes and you have a candidate algorithm/config improvement:
```bash
# Run benchmark
python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

# Compare against current champion
python tools/validate_improvement.py results.json champions/tank/survival_5k.json
```

**IMPORTANT:** Champion mismatches require review. Never copy `verify_*.json`
outputs over champions automatically. Any justified champion metadata or
baseline update must be explicit, auditable, and separated from unrelated work.

### Run Tests Individually

If you need to run specific tests during local debugging:
```bash
# Run specific test files
pytest tests/test_determinism.py
pytest tests/test_energy_integration.py
```

---

## Step 5: Commit and Submit

### Branch Naming

```bash
# Algorithm improvements (Layer 1)
git checkout -b improve/[algorithm-name]-[brief-description]

# Meta improvements (Layer 2)
git checkout -b meta/[improvement-type]-[brief-description]

# New solutions/champions
git checkout -b solution/[author]-[strategy-name]
```

### Commit Message Format

```bash
git commit -m "$(cat <<'EOF'
Improve [benchmark]: [Algorithm] optimization

New score: [X] (previous: [Y], +[Z]%)
Algorithm: [Name] with [change description]
Seed: 42
Reproduction: python tools/run_bench.py benchmarks/tank/survival_5k.py --seed 42

- [Change 1]
- [Change 2]
EOF
)"
```

### Push and PR

```bash
git push -u origin [branch-name]
```

PR must include: benchmark results, reproduction command, explanation, evidence of no regressions.

### Strict Contribution Rules

1. **Reproduction Contract**: Never claim benchmark improvement without documenting the exact reproduction command, seed, score, and all metadata.
2. **Layer 2 Separation**: Changes to benchmarks, CI, scoring, prompts, gates,
   or champion metadata require extra scrutiny and must be separate from Layer 1
   algorithm improvements.

---

## Claude Code Workflow

Tank World has built-in support for Claude Code agentic development:

### Automatic Setup

- **CLAUDE.md** is loaded automatically at session start, giving Claude full project context
- **SessionStart hook** installs all dependencies in remote (web) sessions
- **.claude/settings.json** pre-approves common commands (pytest, benchmarks, git, etc.)

### Recommended Session Flow

1. Read CLAUDE.md (automatic) to understand the project
2. Run `python tools/smoke_gate.py` before coding
3. Run a benchmark to understand current baseline
4. Analyze results and identify improvement targets
5. Make changes and run `python tools/agent_gate.py` before local commit
6. Run `python tools/fast_gate.py` before PR
7. Commit with clear metrics in the message

### What Claude Code Can Do Here

- **Improve algorithms**: Analyze simulation data, read algorithm source, propose and implement changes
- **Fix bugs**: Run tests, identify failures, implement fixes
- **Extend benchmarks**: Create new evaluation harnesses with deterministic seeds
- **Improve documentation**: Update guides, add examples, clarify instructions
- **Run the evolution loop**: Execute the full baseline -> analyze -> improve -> validate -> commit cycle

---

## Solution Tracking System

### Submit Solutions

```bash
# Capture from simulation
python scripts/capture_first_solution.py

# CLI management
python scripts/submit_solution.py list
python scripts/submit_solution.py evaluate <id>
python scripts/submit_solution.py compare
```

### Run AI Tournament

```bash
# Basic tournament
python scripts/run_ai_tournament.py

# With live tank capture
python scripts/run_ai_tournament.py --include-live-tank --write-back

# More stable evaluation
python scripts/run_ai_tournament.py --benchmark-hands 800 --benchmark-duplicates 25 --matchup-hands 5000 --write-back
```

---

## CI Compatibility

### Python Version
CI runs Python 3.10. Code must be 3.8-compatible:
```python
# Use this for modern type hints
from __future__ import annotations
from typing import Dict, List, Tuple
```

### Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Run before committing
```

### Common CI Failures

| Error | Fix |
|-------|-----|
| `black` formatting | Run `black core/ tests/ tools/ backend/ --config pyproject.toml` |
| `ruff` linting | Run `ruff check --fix core/ tests/ tools/ backend/` |
| Type errors | Use `from __future__ import annotations` |
| Test failures | Run `pytest -x` locally first |

---

## Reference

### Documentation

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code project intelligence (auto-loaded) |
| `AGENTS.md` | This file |
| `README.md` | Project overview |
| `docs/AGENT_FIELD_GUIDE.md` | Foolproof recipe-driven starter-task menu for agents of any capability |
| `SETUP.md` | Environment setup |
| `docs/VISION.md` | Long-term goals |
| `docs/EVOLVABILITY.md` | Evolvability levers → code, the research canon, the ideas graveyard (read before proposing improvements) |
| `docs/ARCHITECTURE.md` | Technical architecture |
| `docs/EVO_CONTRIBUTING.md` | Evolutionary PR protocol |
| `docs/BEHAVIOR_DEVELOPMENT_GUIDE.md` | Creating new behaviors |

### Key Directories

| Directory | Contents |
|-----------|----------|
| `core/algorithms/` | 58 behavior algorithms |
| `core/config/` | Tunable parameters |
| `benchmarks/` | Evaluation harnesses |
| `champions/` | Best-known solutions |
| `scripts/` | Automation scripts |
| `tools/` | Development utilities |
| `tests/` | Test suite (60+ files) |

### Essential Scripts

| Script | Purpose |
|--------|---------|
| `main.py` | Run simulation (web or headless) |
| `tools/run_bench.py` | Run benchmarks |
| `tools/validate_improvement.py` | Compare against champions |
| `scripts/ai_code_evolution_agent.py` | AI-powered code improvement |
| `scripts/run_ai_tournament.py` | Run solution tournaments |
| `scripts/submit_solution.py` | Manage solutions |

---

## Tips

1. **Always run baseline first** before making changes
2. **Always use `--seed 42`** for reproducible benchmarks
3. **One improvement at a time** for clean PRs
4. **Validate before committing** with tests and benchmarks
5. **Clear commit messages** with metrics and reproduction commands
6. **Check for regressions** on other benchmarks
7. **Pull frequently** to get improvements from other agents
8. **Focus on high-impact areas** like starvation rate and generation speed
9. **Small improvements compound** over time through the evolution loop

---

## Prompt Template for New Agent Sessions

```
You are an AI agent working in the TankWorld repo (https://github.com/mbolaris/tank).
Your mission is to improve the evolutionary ALife framework.

Current task: [CHOOSE ONE]
- Run simulation and capture best evolved strategy
- Improve worst-performing algorithm
- Add new benchmark for [specific metric]
- Fix issue with [component]

Workflow:
1. Setup/Validate: python tools/smoke_gate.py
2. Run baseline: python main.py --headless --max-frames 30000 --export-stats results.json --seed 42
3. Analyze: Review results.json for underperformers
4. Improve: Modify relevant code in core/
5. Validate: Run agent gate (python tools/agent_gate.py) before local commit, then fast gate (python tools/fast_gate.py) before PR; run full benchmarks only for a candidate improvement
6. Commit: Clear message with metrics and reproduction command
7. Push: git push -u origin [branch]

Rules:
- Always use deterministic seeds
- Run the agent gate (python tools/agent_gate.py) before committing, and the fast gate (python tools/fast_gate.py) before opening a PR
- Never claim benchmark improvement without reproduction command, seed, score, and metadata
- Layer 2 changes (benchmarks, CI, scoring, prompts, gates, champion metadata) must be separate from Layer 1 improvements
- One focused improvement per PR
```

---

**Every improvement you make gets committed to the evolutionary lineage. Your changes become the baseline for future agents. Start contributing now.**
