# Tank World Vision

## What is Tank World?

Tank World is a **framework for AI-driven automated Artificial Life (Alife) research**. It combines engaging visualization with serious computational research, creating a platform where entertaining simulations drive real scientific discovery.

The core innovation is **two-layer evolution**: populations evolve within simulations (Layer 1), while AI agents evolve the algorithms and parameters themselves between simulation runs (Layer 2). This creates a meta-evolutionary system where the rules of evolution themselves evolve.

## The Ultimate Goal

Tank World aims to be **self-sustaining research infrastructure**:

1. **Run simulations** that generate meaningful performance data
2. **AI agents analyze** the data and propose algorithm improvements
3. **Validate changes** automatically through test simulations
4. **Deploy improvements** and repeat—indefinitely, without human intervention
5. **Scale across a network** of distributed nodes running entertaining visualizations

The fish tank is the first visualization layer. Future versions will allow AI to propose entirely new ways to visualize the research—whatever keeps users engaged and contributing compute. The visualization is not decoration; it's the engine that drives distributed participation.

## The Two-Layer Evolution Paradigm

### Layer 1: Population Evolution (Inside the Tank)

Traditional evolutionary computation. Agents (currently visualized as fish) compete for survival using behavior algorithms and parameters encoded in their genome:

- Natural selection optimizes combinations of algorithms and parameters
- Better strategies lead to more reproduction and survival
- Population discovers locally optimal strategies over generations
- Performance data is collected for analysis

**Limitation**: Layer 1 can only optimize within the space of existing algorithms. It cannot invent new behaviors or restructure how behaviors work.

### Layer 2: Algorithmic Evolution (Outside the Tank)

This is where Tank World diverges from traditional Alife. After a simulation run completes:

1. **Data Collection**: Comprehensive statistics on algorithm performance, survival rates, death causes, and population dynamics
2. **AI Analysis**: An AI agent (like Claude) analyzes the data alongside the current behavior code
3. **Code Evolution**: The AI proposes improvements—new algorithms, parameter range adjustments, removal of ineffective strategies, or entirely new approaches
4. **Validation**: Changes are reviewed, tested, and merged
5. **Next Run**: The improved simulation runs again, generating new data

This creates a continuous loop: **Evolve Population → Analyze Results → Improve Algorithms → Repeat**

### Why Two Layers?

Single-layer evolution hits local optima. The population can only explore what the algorithms allow. With two layers:

- Layer 1 finds the best within current constraints
- Layer 2 expands those constraints based on what's learned
- Each layer informs the other

This mirrors how real biological evolution works: organisms evolve within their genetic constraints (Layer 1), but genetic systems themselves evolved over deep time (Layer 2).

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

## Long-Term Goals

> See [ROADMAP.md](ROADMAP.md) for current implementation priorities and near-term task tracking.

Tank World development proceeds in phases, each building toward fully automated Alife research:

### Phase 1: Foundation (Current)
**Goal**: Prove the two-layer evolution concept works.
- 58 parametrizable behavior algorithms
- Basic AI code evolution workflow (proven: 0% → 100% reproduction rate improvements)
- Fish tank visualization with fractal plants and predators
- Headless mode for fast data collection (10-300x speedup)

### Phase 2: Closed Loop
**Goal**: Remove humans from the loop.
- Fully automated evolution cycles running 24/7
- AI proposes, tests, and validates improvements automatically
- Regression detection rejects changes that reduce fitness
- Self-healing: AI fixes broken code it generates
- Continuous improvement without human intervention

### Phase 3: Research Platform
**Goal**: Produce legitimate Alife research.
- Named experiments with configurable parameters
- Formal metrics: complexity, novelty, open-endedness
- Cross-experiment algorithm migration
- Reproducibility tools for exact replay
- Publication-ready data collection and analysis

### Phase 4: Distributed Compute
**Goal**: Scale through entertainment.
- Users contribute compute by watching entertaining simulations
- Browser-based client—no installation required
- Multi-tank network sharing discoveries
- Algorithm migration across the network
- Fair credit for compute contributions

### Phase 5: Evolving Visualization
**Goal**: AI evolves how research is presented.
- Visualization abstraction separates rendering from simulation
- AI proposes new entity types and visual systems
- Engagement optimization: visualizations that maximize watch time
- Alternative metaphors beyond fish tanks
- User preference learning adapts visuals to individuals

### Phase 6: Self-Improving Framework
**Goal**: The framework expands its own capabilities.
- Meta-evolution: AI improves the evolution system itself
- Research question discovery: AI proposes what to study next
- Framework refactoring: AI restructures codebase for new capabilities
- Capability expansion: system gains abilities humans didn't design
- Emergent research directions surprise developers

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
