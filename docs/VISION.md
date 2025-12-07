# Tank World Vision

## What is Tank World?

Tank World is a **framework for AI-driven automated Artificial Life (Alife) research**. It combines engaging visualization with serious computational research, creating a platform where entertaining simulations drive real scientific discovery.

The core innovation is **two-layer evolution**: populations evolve within simulations (Layer 1), while AI agents evolve the algorithms and parameters themselves between simulation runs (Layer 2). This creates a meta-evolutionary system where the rules of evolution themselves evolve.

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

## Long-Term Goals

### Phase 1: Foundation (Current)
- 58 parametrizable behavior algorithms
- Basic AI code evolution workflow
- Fish tank visualization
- Headless mode for fast data collection

### Phase 2: Closed Loop
- Fully automated evolution cycles
- AI proposes, tests, and validates improvements
- Minimal human intervention required
- Continuous improvement 24/7

### Phase 3: Research Platform
- Multiple simultaneous evolutionary experiments
- Cross-experiment algorithm migration
- Formal metrics for Alife research (complexity, novelty, open-endedness)
- Publication-ready data collection

### Phase 4: Distributed Compute
- Users contribute compute by running visualized simulations
- Entertainment value drives participation
- Collective computation power for research
- Interconnected tanks sharing discoveries

### Phase 5: Self-Improving Framework
- AI evolves not just algorithms but the framework itself
- New visualization systems emerge from AI proposals
- The system discovers what questions to ask
- Approaching artificial general intelligence for Alife research

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
