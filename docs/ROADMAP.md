# Tank World Roadmap

> **Vision**: A deterministic artificial-life lab where the evolving organism is not just the agent policy, but the entire *evolution toolkit*—including the instruction sets and workflows used by development agents.

---

## Core Vision

Tank World is an **evolution engine whose own development process is part of the evolutionary loop**. Git becomes the heredity mechanism: PRs are mutations, CI is selection, and merged changes are the "offspring" that future agents inherit.

The system operates at three layers:
- **Layer 0**: In-world evolution (fish policies evolve inside simulations)
- **Layer 1**: Experiment automation (dev-agents evolve algorithms via benchmarks + PRs)
- **Layer 2**: Meta-evolution (dev-agents evolve their own instructions and tooling)

### Critical Infrastructure

Before any other features, we need the **Evolution Loop MVP**:
- Best Known Solutions (BKS) registry for reproducible benchmarks
- Evolutionary PR protocol with CI validation
- Standard benchmark suite for Tank world
- Formal "better than best-known" commit protocol

**Why this matters**: Without formal BKS + validation, "Layer 1 evolution" remains informal theater. This is the backbone that makes git-as-heredity real.

### Supported World Modes (Secondary Priority)

| Mode | Description |
|------|-------------|
| **Tank** | Fish eat, play poker, avoid hazards (current baseline, will get first benchmark suite) |
| **Petri** | Same agents/genetics/energy, rendered as microbes/nutrients |
| **Soccer** | Evolved agents become soccer players (RCSS integration) |

Multi-world support is valuable, but **only after Evolution Loop MVP is complete**. New modes add new benchmark tracks, not just visuals.

---

## Current Status

| Area | Status |
|------|--------|
| **Backend abstractions** | ✅ `WorldBackend`, `SystemPack`, world registry exist |
| **Snapshot builders** | ✅ Per-world snapshot builders implemented |
| **Observation registry** | ✅ Exists; tank-specific observation builders in tank world code |
| **Action registry** | ✅ ActionRegistry with world-specific translators |
| **Mutation queue** | ✅ Exists; spawn/remove centralized via engine |
| **RCSS integration** | Protocol + adapter + tests exist (no full end-to-end world loop yet) |
| **Petri mode** | ✅ First-class frontend rendering + mode-aware UI + circular dish |
| **Brain contracts** | ✅ `BrainObservation`/`BrainAction` in `core/brains/contracts.py` |

---

## Near-Term Goals (Evolution Loop MVP)

**Priority 1: Establish the evolutionary backbone. No new features until this is complete.**

### 1. BKS Registry Infrastructure

**Goal**: Create the formal Best Known Solutions registry structure.

- [ ] Create `benchmarks/` directory with Tank benchmarks:
  - [ ] `benchmarks/tank/survival_30k.py` - Maximize average lifespan over 30k frames
  - [ ] `benchmarks/tank/reproduction_30k.py` - Maximize total births over 30k frames
  - [ ] `benchmarks/tank/diversity_30k.py` - Maximize algorithm diversity (Shannon entropy)
- [ ] Create `benchmarks/registry.json` index
- [ ] Create `champions/` directory structure:
  - [ ] `champions/tank/` subdirectory
  - [ ] `champions/registry.json` index
  - [ ] Define champion JSON schema (score, algorithm, genome, commit, seed, repro command)

### 2. Benchmark Tooling

**Goal**: Standard tools for running benchmarks and validating improvements.

- [ ] Implement `tools/run_bench.py`:
  - [ ] Takes benchmark path + seed as args
  - [ ] Runs headless simulation
  - [ ] Outputs standardized `results.json` with metrics
  - [ ] Includes reproduction metadata
- [ ] Implement `tools/validate_improvement.py`:
  - [ ] Compares new results against current champion
  - [ ] Returns clear "better/worse/equal" verdict
  - [ ] Outputs diff for PRs

### 3. CI Validation

**Goal**: Automated validation of evolutionary PRs.

- [ ] Create `.github/workflows/bench.yml`:
  - [ ] Detects changes to `champions/` directory
  - [ ] Re-runs claimed benchmarks with deterministic seeds
  - [ ] Confirms score improvements
  - [ ] Checks for regressions on other benchmarks
  - [ ] Only allows merge if validation passes

### 4. Documentation

**Goal**: Clear protocol for evolutionary contributions.

- [ ] Create `docs/EVO_CONTRIBUTING.md`:
  - [ ] Evolutionary PR protocol requirements
  - [ ] Step-by-step workflow examples
  - [ ] Champion registry format specification
  - [ ] CI validation process explanation
- [ ] Update `CONTRIBUTING.md` to reference evolutionary PRs
- [ ] Add benchmark documentation to each benchmark file

### 5. First Champions

**Goal**: Establish baseline champions for all Tank benchmarks.

- [ ] Run initial benchmarks and record champions:
  - [ ] `champions/tank/survival_30k.json`
  - [ ] `champions/tank/reproduction_30k.json`
  - [ ] `champions/tank/diversity_30k.json`
- [ ] Validate that CI can reproduce all champions
- [ ] Document reproduction process

**Definition of Done**: An AI agent (or human) can run a benchmark, beat the current BKS, open a PR with the champion update, and have CI automatically validate and approve the merge (with code review gate).

---

## Deferred Goals (Post-MVP)

*These are valuable but blocked until Evolution Loop MVP is complete.*

### Mode-Aware UI (Completed, Maintenance Only)

- [x] Frontend WS handler preserves `mode_id` + `view_mode`
- [x] Renderer selection uses `render_hint.style` consistently
- [x] Mode/view badge for debugging added
- [x] Regression tests for mode preservation
- [x] Dedicated `PetriTopDownRenderer` driven by `render_hint`
- [x] Circular dish with perimeter-based root spots

### Tank Uses Genome Code Pool (Deferred)

- [ ] Introduce "movement policy contract"
- [ ] Run movement through `GenomeCodePool.execute_policy` when configured
- [ ] Safe fallback to legacy `MovementStrategy`
- [ ] Tests: policy path works + fallback works + exceptions don't crash

### Soccer Groundwork (Deferred)

- [ ] Implement `rcss_world` that can step and translate actions/observations
- [ ] Build deterministic `FakeRCSSServer` for CI tests
- [ ] End-to-end test: action → emitted command → parsed observation

---

## Medium-Term Goals (Post-Evolution Loop MVP)

*Expand benchmark coverage and enable Layer 2 meta-evolution.*

### Expand Benchmark Suite

- [ ] Add Petri mode benchmarks:
  - [ ] `benchmarks/petri/survival_30k.py`
  - [ ] `benchmarks/petri/reproduction_30k.py`
- [ ] Add Soccer training benchmarks (when Soccer world is ready):
  - [ ] `benchmarks/soccer/goal_contribution.py`
  - [ ] `benchmarks/soccer/positioning.py`
- [ ] Add cross-mode benchmarks:
  - [ ] Algorithm portability across Tank/Petri/Soccer
  - [ ] Transfer learning effectiveness

### Genetic Analysis Challenge (GAC)

**Goal**: Benchmark suite where fitness = ability to understand evolution.

- [ ] Implement synthetic evolutionary data generator:
  - [ ] Ground truth phylogenies, selection coefficients, drift
  - [ ] Hidden parameters agents must infer
- [ ] Create GAC benchmarks:
  - [ ] `benchmarks/gac/selection_inference.py` - Infer selection strength
  - [ ] `benchmarks/gac/regime_classification.py` - Classify evolutionary regime
  - [ ] `benchmarks/gac/prediction.py` - Predict next-gen allele distribution
- [ ] Add GAC champions to registry

### Layer 2 Meta-Evolution Infrastructure

**Goal**: Enable agents to evolve their own instructions and tooling.

- [ ] Create `instructions/` directory for agent prompts/workflows
- [ ] Implement benchmark for instruction quality:
  - [ ] Measure: "how many improvements did this instruction set produce?"
  - [ ] Track instruction lineage in Git
- [ ] Add Layer 2 validation gates:
  - [ ] Require benchmarked improvements for instruction changes
  - [ ] Human review REQUIRED for all Layer 2 PRs
  - [ ] Prevent "prompt soup" via hard constraints

### Closed Loop Automation

- [ ] Automated agent that runs benchmarks on schedule
- [ ] Automated PR creation for improvements
- [ ] Self-healing: agent fixes broken code it generates
- [ ] Regression detection rejects fitness-reducing changes

---

## Long-Term Goals

*Full three-layer evolutionary system.*

### Layer 0 Expansion (In-World Evolution)

- [ ] Neural network policy option (alternative to algorithmic)
- [ ] More world types with different selection pressures
- [ ] Cross-world policy transfer and adaptation

### Layer 1 Maturity (Experiment Automation)

- [ ] Curriculum learning: progressive difficulty benchmarks
- [ ] Multi-objective optimization (Pareto front tracking)
- [ ] Population-based training across benchmark suite
- [ ] Automated hyperparameter tuning for evolution

### Layer 2 Maturity (Meta-Evolution)

- [ ] Benchmark design evolution (AI proposes new fitness functions)
- [ ] Instruction set evolution (AI improves its own prompts)
- [ ] CI gate evolution (AI improves validation protocols)
- [ ] Meta-metrics: measure "evolvability" of the toolkit itself

### Research Platform

- [ ] Publication-ready reproducibility tools
- [ ] Formal metrics: complexity, novelty, open-endedness
- [ ] Cross-experiment knowledge transfer
- [ ] Collaboration features for distributed research

### Distributed Compute

- [ ] Browser-based client for compute contributions
- [ ] Multi-tank network with algorithm migration
- [ ] Fair credit system for compute contributions
- [ ] Engagement-optimized visualizations

---

## Guiding Rules

1. **No tank-specific imports in generic policy modules**
2. **All spawns/removals go through central queues** (no mid-frame list mutation)
3. **Strict phase order enforced by tests**
4. **Small modules, typed interfaces, "world owns world logic"**
5. **Add regression tests whenever you cut a new seam** (WS parsing, observation/action registries, persistence)

---

*Last updated: January 2026*
