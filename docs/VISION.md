# Tank World Vision

## What is Tank World?

**TankWorld is a deterministic artificial-life lab where the evolving organism is not just the agent policy, but the entire *evolution toolkit*—including the instruction sets and workflows used by development agents.**

The system is designed so that *running experiments produces improvements that get committed back to the repository*. Git becomes the heredity mechanism: PRs are mutations, CI is selection, and merged changes are the "offspring" that future agents inherit.

Over time, we want dev-agents to learn not only how to evolve better in-world behaviors, but how to evolve their own instructions and tooling for doing evolution—creating a multi-layer feedback loop between simulation, meta-optimization, and scientific understanding of evolution.

## The Ultimate Goal

Tank World aims to be **self-sustaining research infrastructure** where the development process itself is part of the evolutionary loop:

1. **Run benchmarks** with deterministic seeds that generate reproducible performance data
2. **AI agents analyze** the data against the repository's Best Known Solutions (BKS)
3. **Propose improvements** via PRs that update champion registries with better algorithms/parameters
4. **Validate automatically** through CI that re-runs benchmarks and confirms wins
5. **Merge improvements** that become the new baseline for future evolution
6. **Repeat indefinitely** without human intervention (beyond code review gates)

The fish tank is the first visualization layer—it makes the research **entertaining enough to watch**, which matters because engaging simulations can drive distributed compute contributions. But the deeper innovation is that Git itself becomes the heredity mechanism for this evolving research framework.

## The Three-Layer Evolution Paradigm

Tank World operates as a **three-layer evolutionary system** where each layer has measurable fitness, reproducible evaluation, and a commit protocol for "this is better than best-known."

### Layer 0: In-World Evolution (Inside the Simulation)

Traditional evolutionary computation. Agents (currently visualized as fish) compete for survival using behavior algorithms and parameters encoded in their genome:

- Natural selection optimizes combinations of algorithms and parameters
- Better strategies lead to more reproduction and survival
- Population discovers locally optimal strategies over generations
- **Outputs**: Champion genomes/policies + telemetry + replays per run

**Limitation**: Layer 0 can only optimize within the space of existing algorithms. It cannot invent new behaviors or restructure how behaviors work.

### Layer 1: Experiment Automation (Evolving the Search)

Dev-agents (outside the sim) run experiments, compare candidates, manage populations, and discover better solutions:

1. **Run Benchmarks**: Standard evaluation harnesses with deterministic seeds
2. **Collect Artifacts**: `results.json` (metrics), `champion.json` (best genome), `repro.md` (reproduction guide)
3. **Compare Against BKS**: Check if new results beat the repository's Best Known Solutions registry
4. **Open Evolutionary PRs**: If better, submit PR with updated champion + artifacts + explanation
5. **CI Validates**: Automated re-run confirms the improvement is reproducible before merge

**Outputs**: Improved algorithms, evaluators, selection schemes, mutation operators, curriculum design, diversity preservation.

**Key Insight**: Git becomes the heredity mechanism. PRs are mutations, CI is selection, merged changes are "offspring" that future agents inherit.

### Layer 2: Meta-Evolution (Evolving the Toolkit Itself)

Dev-agents improve the prompts, instructions, harnesses, evaluation protocols, and repo structure so that Layer 1 gets better at producing Layer 0 improvements:

- **Benchmark Design**: Better fitness functions, more informative test cases
- **Instruction Evolution**: Improved agent prompts and workflows for running evolution
- **CI Gates**: Better validation protocols that catch regressions
- **Evaluation Protocols**: More robust ways to measure "better"

**Outputs**: Better "how we evolve" playbooks, improved benchmark suites, stronger selection pressure.

**Critical Constraint**: Each layer must have:
- A **score** (fitness metric)
- A **reproducible eval harness** (deterministic seeds required)
- A **commit protocol** for "this is better than best-known"

### Why Three Layers?

Single-layer evolution (Layer 0 alone) hits local optima—populations can only explore what algorithms allow.

Two-layer evolution (Layers 0 + 1) expands the search space—AI proposes new algorithms based on data.

Three-layer evolution (Layers 0 + 1 + 2) evolves the search process itself—AI improves how we discover improvements.

This mirrors how biological evolution works at multiple timescales:
- **Layer 0**: Organisms evolve within genetic constraints (fast, generational)
- **Layer 1**: Genetic systems evolve over deep time (slower, architectural)
- **Layer 2**: Evolvability itself evolves (slowest, meta-architectural)

## Source Control as Heredity

This is the key mechanism that makes Tank World different from other ALife frameworks:

### The Repository-Level Evolution Loop

Every dev-agent follows this protocol:

1. **Run** a standard benchmark suite locally or in CI (deterministic seeds)
2. **Produce artifacts**:
   - `results.json` with metrics
   - `champion.json` with best policy/genome/program + metadata
   - `repro.md` with reproduction instructions
3. **Compare** against the repo's **Best Known Solutions (BKS)** registry
4. **If better**, open a PR that:
   - Updates the champion registry
   - Includes the artifacts
   - Includes explanation + reproduction command
5. **CI re-runs** the eval and **only merges if the win is confirmed**

This is the repository-level version of "selection pressure."

### Best Known Solutions (BKS) Registry

The BKS registry is a first-class directory structure in the repo:

```
tank/
├── benchmarks/           # Evaluation harnesses
│   ├── tank/             # Tank world benchmarks
│   │   ├── survival_30k.py
│   │   ├── reproduction_30k.py
│   │   └── diversity_30k.py
│   ├── gac/              # Genetic Analysis Challenge (future)
│   └── registry.json     # Index of all benchmarks
├── champions/            # Best-known solutions per benchmark
│   ├── tank/
│   │   ├── survival_30k.json
│   │   ├── reproduction_30k.json
│   │   └── diversity_30k.json
│   └── registry.json     # Index of all champions
└── .github/workflows/
    └── bench.yml         # CI that validates improvements
```

### Evolutionary PR Protocol

When a dev-agent discovers an improvement:

**Must include:**
- Benchmark results showing improvement over current BKS
- Updated champion registry entry if claiming a new record
- Reproduction command that works with deterministic seeds
- Clear explanation of what changed and why it's better

**Must pass:**
- CI re-runs the benchmark and confirms the score
- No regressions on other benchmarks
- Code review (human-in-the-loop for Layer 2 changes)

**If merged:**
- The new champion becomes the baseline for future PRs
- Future agents inherit this improvement
- Git history shows the evolutionary lineage

This makes evolution **auditable, reproducible, and incremental**.

## Entertainment-Driven Research

### The Fish Tank Metaphor

Currently, Tank World visualizes its Alife as a fish tank ecosystem:
- Fish with heritable behaviors compete for food
- Fractal plants produce resources
- Predators create selection pressure
- Poker games redistribute energy

This isn't just eye candy—it makes the simulation engaging enough that people want to watch it. The visualization provides:
- Intuitive understanding of what's happening
- Motivation to run longer experiments
- Accessibility for non-researchers

### Future: Evolving Visualization

The fish tank is just the first visualization. Future versions will allow the AI (Layer 2) to evolve not just behavior algorithms, but also:

- **New entity types**: Beyond fish, plants, and crabs
- **New interaction systems**: Beyond eating and poker
- **New visual representations**: The AI could propose entirely different ways to render the simulation based on what drives engagement
- **Engagement optimization**: Visualizations that keep users watching longer

The goal is a system where the AI can propose: "This simulation would be more engaging if we added X" and generate both the simulation logic AND the visualization code.

### Why Visualization Matters for Research

Visualization isn't a nice-to-have—it's central to the research strategy:

1. **Distributed compute requires motivation**: People will run simulations on their machines if they're entertaining to watch. No entertainment = no compute contributions.

2. **Engagement metrics are measurable**: Watch time, return visits, and sharing behavior provide quantifiable signals for what works.

3. **Visualization can evolve**: Just like behavior algorithms, visual representations can be proposed by AI, tested against engagement metrics, and selected for.

4. **The simulation is the substrate, not the goal**: The interesting research happens in the algorithms. The fish tank is one way to make that research visible and engaging—but there could be many others.

In the long term, Tank World may evolve visualizations that humans wouldn't design—optimized purely for engagement while representing the same underlying Alife research.

### AI Oceanographer Narration

Visualization alone isn’t enough. Most people need a story.

A planned layer for Tank World is an AI narrator that acts as an in-sim oceanographer. Its responsibilities:

- **Explain experiments in plain language**
  “This tank is exploring energy-efficient foraging strategies under predation pressure,” instead of “we’re running an EA on fitness function F.”

- **Call out emergent behavior**
  Highlight when new strategies appear, niches form, or species collapse – and tie those events back to changes in the underlying algorithms.

- **Map tank activity to real-world frames**
  When appropriate, relate what the tank is doing to real domains: routing, scheduling, optimization, or (eventually) problem templates that users actually care about. Most of these will be proxy problems, and the system should be explicit about that.

- **Experiment with formats**
  Short “episodes,” daily summaries, or longer-form “nature documentaries” built from logs and replay data – all generated automatically from the simulation history.

This “AI oceanographer” doesn’t change the core two-layer evolution paradigm, but it makes the system legible and worth watching for non-experts. If people enjoy following the story of their tank, they will keep donating compute to the underlying research.

## Development Roadmap

> See [ROADMAP.md](ROADMAP.md) for current implementation priorities and near-term task tracking.

Tank World development proceeds in phases, building toward fully automated research where the development process itself is part of the evolutionary loop:

### Phase 0: Foundation (Complete)
**Status**: ✅ Done
- 58 parametrizable behavior algorithms with registry
- Deterministic simulation with headless mode (10-300x speedup)
- Fish tank visualization with fractal plants and predators
- Basic AI code evolution workflow (proven: 0% → 100% reproduction rate improvements)
- Multi-world backend architecture (Tank/Petri + soccer minigame)

### Phase 1: Evolution Loop MVP (Current Priority)
**Goal**: Establish the BKS registry and evolutionary PR protocol.

**Definition of done:**
- ✅ One benchmark suite per flagship mode (at least Tank + one other)
- ✅ A BKS (Best Known Solutions) registry in the repo
- ✅ A CI job that validates "improvement claims"
- ✅ A stable artifact format for champions
- ✅ A documented "how to contribute evolutionary wins" protocol

**Concrete deliverables:**
- `benchmarks/` directory with initial Tank benchmarks (survival, reproduction, diversity)
- `champions/` directory with registry tracking best-known solutions
- `tools/run_bench.py` that outputs standardized `results.json`
- GitHub Action that runs benchmarks and compares against registry
- `docs/EVO_CONTRIBUTING.md` explaining the evolutionary PR protocol

**Why this matters**: Without this foundation, "Layer 1 evolution" remains informal and hard to validate. This is the backbone that makes git-as-heredity real.

### Phase 2: Closed Loop Automation
**Goal**: Remove humans from Layer 1 evolution loop.
- Fully automated evolution cycles running 24/7
- AI proposes, tests, and validates improvements automatically
- Regression detection rejects changes that reduce fitness
- Self-healing: AI fixes broken code it generates
- Continuous improvement without human intervention (code review gate remains)

### Phase 3: Layer 2 Meta-Evolution
**Goal**: Agents evolve their own instructions and tooling.
- Benchmark design evolution (better fitness functions)
- Instruction set evolution (improved agent prompts/workflows)
- CI gate evolution (better validation protocols)
- Evaluation protocol evolution (more robust metrics)
- Human review required for all Layer 2 changes (hard gate)

### Phase 4: Research Platform
**Goal**: Produce legitimate Alife research with publishable results.
- Genetic Analysis Challenge (GAC) benchmark suite
- Formal metrics: complexity, novelty, open-endedness, evolvability
- Cross-experiment algorithm migration and transfer learning
- Reproducibility tools for exact replay
- Publication-ready data collection and analysis

### Phase 5: Distributed Compute
**Goal**: Scale through entertainment.
- Users contribute compute by watching entertaining simulations
- Browser-based client—no installation required
- Multi-tank network sharing discoveries
- Algorithm migration across the network
- Fair credit for compute contributions

### Phase 6: Evolving Visualization
**Goal**: AI evolves how research is presented.
- Visualization abstraction separates rendering from simulation
- AI proposes new entity types and visual systems
- Engagement optimization: visualizations that maximize watch time
- Alternative metaphors beyond fish tanks
- User preference learning adapts visuals to individuals

## Critical Constraints (Anti-Degeneration Measures)

These constraints prevent the system from devolving into vague "self-improvement theater":

### 1. Determinism is Non-Negotiable
**Problem**: Non-deterministic evaluation makes "better" meaningless.

**Solution**:
- All benchmarks must use fixed seeds
- Simulation must be byte-for-byte reproducible
- CI must be able to re-run and confirm any claimed improvement
- If eval isn't deterministic and stable, evolution becomes theater

### 2. Best-Known Must Be Formal
**Problem**: Informal "this seems better" claims have no selection pressure.

**Solution**:
- Canonical `champions/` registry in repo (single source of truth)
- CI enforces that PRs claiming improvements actually beat BKS
- No merged PR without reproducible benchmark win
- Git history becomes the evolutionary lineage

### 3. Instruction Evolution Requires Hard Gates
**Problem**: Self-modifying instructions can optimize for easy wins and drift into prompt soup.

**Solution**:
- **Layer 1 (algorithm evolution)**: Automated merge if benchmarks pass
- **Layer 2 (instruction evolution)**: Human review REQUIRED
- Instruction changes must demonstrate benchmarked improvements
- No "seems smarter" without measurable fitness gains

### 4. Reproducibility Required
**Problem**: Irreproducible results can't be validated or built upon.

**Solution**:
- Every improvement PR must include reproduction command
- Champion registry includes exact seed, commit hash, runtime
- CI must successfully reproduce the result before merge
- Documentation must explain how to reproduce from scratch

### 5. No Legacy Anything Before First Release
**Problem**: Accumulated cruft prevents clean architecture.

**Solution**:
- Get the Evolution Loop MVP right before calling it "1.0"
- Clean slate: if it doesn't serve the three-layer vision, cut it
- BKS registry and evolutionary PR protocol are table stakes
- The repo structure IS the heredity mechanism—make it clean

## Design Principles

### Interpretability Over Opacity
We use explicit behavior algorithms instead of neural networks because:
- Behaviors are debuggable and understandable
- Changes can be reviewed by humans
- AI can reason about code, not just weights
- Evolution of algorithms is visible

### Human in the Loop
Layer 2 evolution requires human oversight:
- AI proposes changes via pull requests
- Humans review before merging
- Safety and quality maintained
- Learning accumulates in git history

### Data-Driven Evolution
All AI improvements are grounded in simulation data:
- No speculation without evidence
- Performance metrics drive priorities
- Failed experiments inform future attempts
- Reproducible results

### Entertainment as Utility
Making simulations entertaining isn't frivolous:
- Engaged users run longer experiments
- Visualization reveals insights
- Distributed compute needs motivation
- Science communication built in

## How AI Agents Participate

When an AI agent (like Claude) participates in Layer 2 evolution:

1. **Receive**: Simulation statistics JSON with algorithm performance data
2. **Analyze**: Identify underperforming algorithms and their failure modes
3. **Research**: Read current algorithm source code
4. **Propose**: Generate improved code with explanations
5. **Validate**: Changes are tested before deployment
6. **Learn**: Results inform future improvement attempts

The AI acts as an "AI Junior Developer" that works continuously, proposing incremental improvements based on evidence.

## Success Metrics

How do we know Tank World is succeeding?

### Short-term
- Algorithm diversity maintained across generations
- AI improvements measurably increase fitness metrics
- Simulations remain engaging to watch

### Medium-term
- Novel behaviors emerge that humans didn't design
- AI proposes improvements humans wouldn't have thought of
- Research insights from population dynamics

### Long-term
- Contributions to Alife research literature
- Self-sustaining distributed research platform
- Framework complexity grows through AI evolution
- Open-ended evolution achieved

## Join the Evolution

Tank World is open source and welcomes contributions:
- Run simulations and share data
- Review AI-proposed improvements
- Develop new visualization systems
- Extend the algorithm library
- Propose new research directions

The fish tank is just the beginning. What evolves next is up to us—and the AI.
