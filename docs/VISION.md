# Tank World Vision

## The Core Idea

**Tank World is a deterministic artificial-life lab where the evolving organism is not just the agent policy, but the entire evolution toolkit -- including the instruction sets and workflows used by development agents.**

Running experiments produces improvements that get committed back to the repository. Git becomes the heredity mechanism: PRs are mutations, CI is selection, and merged changes are the "offspring" that future agents inherit.

This is not a metaphor. It is the literal mechanism by which Tank World improves. An AI agent runs a benchmark, identifies an underperforming algorithm, rewrites it, validates the improvement against the Best Known Solutions registry, and opens a pull request. CI re-runs the benchmark to confirm the result. If it passes, the improvement merges and becomes the new baseline for the next agent session.

Over time, the system gets better at getting better. Agents learn not only how to evolve better in-world behaviors, but how to evolve their own instructions and tooling for doing evolution -- a multi-layer feedback loop between simulation, meta-optimization, and scientific understanding of evolution.

## Why This Matters

Most AI-assisted codebases have a human deciding what to work on and an AI executing. Tank World inverts this. The AI is the primary researcher. It decides what experiments to run, analyzes the results, proposes changes, and validates them. The human role shifts to reviewing merged changes and setting high-level direction.

This creates a fundamentally different dynamic:

1. **Compounding improvement**: Every merged PR raises the floor. Future agents start from a better baseline.
2. **24/7 operation**: AI agents don't sleep. The evolution loop can run continuously.
3. **Reproducible science**: Deterministic seeds mean every claimed improvement can be independently verified.
4. **Auditable lineage**: Git history is the phylogenetic tree. You can trace any algorithm's ancestry.

The result is a research framework that gets more productive over time without proportional increases in human effort.

## The Three-Layer Evolution Paradigm

Tank World operates as a three-layer evolutionary system. Each layer has measurable fitness, reproducible evaluation, and a commit protocol for "this is better than best-known."

### Layer 0: In-World Evolution (Inside the Simulation)

Traditional evolutionary computation. Fish compete for survival using 58 parametrizable behavior algorithms encoded in their genome:

- Natural selection optimizes combinations of algorithms and parameters
- Better strategies lead to more reproduction and survival
- Population discovers locally optimal strategies over generations
- **Output**: Champion genomes, telemetry, population dynamics per run

**Limitation**: Layer 0 can only optimize within the space of existing algorithms. It cannot invent new behaviors or restructure how behaviors work.

### Layer 1: Experiment Automation (Evolving the Search)

AI agents operate outside the simulation. They run experiments, compare candidates, and discover better solutions:

1. Run standard benchmarks with deterministic seeds
2. Collect artifacts: `results.json` (metrics), champion data, reproduction instructions
3. Compare against the Best Known Solutions (BKS) registry
4. If better, open a PR with updated champion + evidence + reproduction command
5. CI re-runs the evaluation and only merges if the win is confirmed

**Output**: Better algorithms, mutation operators, selection schemes, parameter tuning.

**Key insight**: Git becomes the heredity mechanism. PRs are mutations, CI is selection, merged changes are "offspring" that future agents inherit.

### Layer 2: Meta-Evolution (Evolving the Toolkit Itself)

AI agents improve the tools that Layer 1 uses to produce Layer 0 improvements:

- **Benchmark design**: Better fitness functions, more informative test cases
- **Instruction evolution**: Improved agent prompts and workflows
- **CI gates**: Stronger validation protocols that catch regressions
- **Evaluation protocols**: More robust ways to measure "better"

**Output**: Better "how we evolve" playbooks, stronger selection pressure.

### Why Three Layers?

Single-layer evolution (Layer 0 alone) hits local optima. Populations can only explore what existing algorithms allow.

Two-layer evolution (Layers 0 + 1) expands the search space. AI proposes new algorithms based on data analysis.

Three-layer evolution (Layers 0 + 1 + 2) evolves the search process itself. AI improves how we discover improvements.

This mirrors biological evolution at multiple timescales:
- **Layer 0**: Organisms evolve within genetic constraints (fast, generational)
- **Layer 1**: Genetic systems evolve over deep time (slower, architectural)
- **Layer 2**: Evolvability itself evolves (slowest, meta-architectural)

## Source Control as Heredity

This is the mechanism that makes Tank World different from other ALife frameworks.

### The Repository-Level Evolution Loop

Every agent follows this protocol:

1. **Run** a standard benchmark suite (deterministic seeds)
2. **Produce** artifacts: `results.json`, champion data, reproduction instructions
3. **Compare** against the Best Known Solutions registry
4. **If better**, open a PR with updated champion + evidence
5. **CI re-runs** the evaluation and only merges if the win is confirmed

This is repository-level selection pressure.

### Best Known Solutions (BKS) Registry

The BKS registry is a first-class directory structure:

```
benchmarks/           # Evaluation harnesses
  tank/               # Tank world benchmarks
  soccer/             # Soccer mode benchmarks
champions/            # Best-known solutions per benchmark
  tank/               # Tank champions with scores, genomes, repro commands
  soccer/             # Soccer champions
```

### Evolutionary PR Protocol

When a dev-agent discovers an improvement:

**Must include**: Benchmark results showing improvement, updated champion entry, reproduction command, explanation.

**Must pass**: CI re-runs benchmark and confirms score. No regressions on other benchmarks. Code review for Layer 2 changes.

**If merged**: New champion becomes baseline. Future agents inherit this improvement. Git history shows lineage.

This makes evolution auditable, reproducible, and incremental.

## Entertainment-Driven Research

### The Fish Tank

The fish tank visualization is not decoration. It serves a strategic purpose.

Tank World visualizes its ALife as a fish tank ecosystem: fish with heritable behaviors compete for food, fractal plants produce resources, predators create selection pressure, and poker games redistribute energy. This makes the simulation engaging enough that people want to watch it.

Engagement matters because:

1. **Distributed compute requires motivation**: People will run simulations on their machines if they're interesting to watch. No engagement = no compute contributions.
2. **Engagement metrics are measurable**: Watch time, return visits, and sharing provide quantifiable optimization targets.
3. **Visualization can evolve**: Like behavior algorithms, visual representations can be proposed by AI and selected for based on engagement.
4. **The simulation is the substrate, not the goal**: The research happens in the algorithms. The fish tank makes that research visible.

### AI Oceanographer (Planned)

A future narration layer where an AI acts as an in-sim documentary narrator:

- Explain experiments in plain language instead of technical jargon
- Call out emergent behavior when new strategies appear or species collapse
- Map tank activity to real-world problem domains when appropriate
- Generate episode summaries, daily digests, or longer documentary-style content from replay data

The oceanographer makes the system legible for non-experts. If people enjoy the story of their tank, they keep running experiments.

### Evolving Visualization (Long-Term)

The fish tank is just the first visualization. Future versions will allow AI to evolve:

- New entity types beyond fish, plants, and crabs
- New interaction systems beyond eating and poker
- New visual representations optimized for engagement
- Alternative metaphors beyond fish tanks entirely

The goal: AI proposes "this simulation would be more engaging with X" and generates both the logic and the rendering.

## Development Roadmap

> See [ROADMAP.md](ROADMAP.md) for current priorities and task tracking.

### Phase 0: Foundation -- Complete

- 58 parametrizable behavior algorithms with registry
- Deterministic simulation with headless mode (10-300x speedup)
- Fish tank visualization with fractal plants and predators
- Basic AI code evolution workflow
- Multi-world backend architecture (Tank/Petri + Soccer minigame)

### Phase 1: Evolution Loop MVP -- Current Priority

**Goal**: Establish BKS registry and evolutionary PR protocol.

- Benchmark suites for Tank and Soccer modes
- Best Known Solutions registry in the repo
- CI job that validates improvement claims
- Stable artifact format for champions
- Documented evolutionary contribution protocol

### Phase 2: Closed-Loop Automation

**Goal**: Remove humans from Layer 1 evolution loop.

- Fully automated 24/7 evolution cycles
- AI proposes, tests, and validates improvements automatically
- Regression detection rejects fitness-reducing changes
- Self-healing: AI fixes broken code it generates
- Human code review gate remains as safety check

### Phase 3: Layer 2 Meta-Evolution

**Goal**: Agents evolve their own instructions and tooling.

- Benchmark design evolution
- Instruction set evolution
- CI gate evolution
- Human review required for all Layer 2 changes (hard gate)

### Phase 4: Research Platform

**Goal**: Produce legitimate ALife research.

- Genetic Analysis Challenge benchmark suite
- Formal metrics: complexity, novelty, open-endedness, evolvability
- Reproducibility tools for exact replay
- Publication-ready data collection

### Phase 5: Distributed Compute

**Goal**: Scale through entertainment.

- Browser-based client, no installation required
- Multi-tank network sharing discoveries
- Algorithm migration across the network
- Fair credit for compute contributions

### Phase 6: Evolving Visualization

**Goal**: AI evolves how research is presented.

- Visualization abstraction separates rendering from simulation
- AI proposes new entity types and visual systems
- Engagement optimization
- User preference learning

## Critical Constraints

These prevent the system from devolving into self-improvement theater:

### Determinism is Non-Negotiable

All benchmarks use fixed seeds. Simulation must be byte-for-byte reproducible. CI must re-run and confirm any claimed improvement. If evaluation isn't deterministic, evolution becomes theater.

### Best-Known Must Be Formal

Canonical `champions/` registry in repo. CI enforces that PRs claiming improvements actually beat BKS. No merged PR without reproducible benchmark win. Git history becomes the evolutionary lineage.

### Instruction Evolution Requires Hard Gates

Layer 1 (algorithm evolution): automated merge if benchmarks pass. Layer 2 (instruction evolution): human review required. Instruction changes must demonstrate benchmarked improvements. No "seems smarter" without measurable fitness gains.

### Reproducibility Required

Every improvement PR includes a reproduction command. Champion registry includes exact seed, commit hash, runtime. CI reproduces the result before merge.

## Design Principles

### Interpretability Over Opacity

Explicit behavior algorithms instead of neural networks. Behaviors are debuggable, reviewable, and visible. AI can reason about code, not just weights. Evolution of algorithms is traceable in git history.

### Human in the Loop

Layer 2 evolution requires human oversight. AI proposes via pull requests, humans review before merge. Safety and quality maintained through code review gates.

### Data-Driven Evolution

All AI improvements grounded in simulation data. Performance metrics drive priorities. Failed experiments inform future attempts. No speculation without evidence.

### Entertainment as Utility

Making simulations entertaining is not frivolous. Engaged users run longer experiments. Visualization reveals insights. Distributed compute needs motivation. Science communication is built into the framework.

## How AI Agents Participate

When an AI agent participates in evolution:

1. **Receive**: Simulation statistics with algorithm performance data
2. **Analyze**: Identify underperforming algorithms and failure modes
3. **Research**: Read current algorithm source code
4. **Propose**: Generate improved code with explanations
5. **Validate**: Test changes against benchmarks
6. **Commit**: Changes enter the evolutionary lineage

The AI acts as a tireless researcher, proposing incremental improvements based on evidence, running continuously, and building on the work of every agent that came before it.

## Success Metrics

### Short-term
- Algorithm diversity maintained across generations
- AI improvements measurably increase fitness metrics
- Simulations remain engaging to watch

### Medium-term
- Novel behaviors emerge that humans didn't design
- AI proposes improvements humans wouldn't have thought of
- Research insights from population dynamics

### Long-term
- Contributions to ALife research literature
- Self-sustaining distributed research platform
- Framework complexity grows through AI evolution
- Open-ended evolution achieved

## Join the Evolution

Tank World is open source and welcomes contributions from humans and AI agents:
- Run simulations and share performance data
- Review AI-proposed improvements
- Extend the algorithm library
- Develop new visualization systems
- Propose research directions

The fish tank is just the beginning. What evolves next depends on what gets committed.
