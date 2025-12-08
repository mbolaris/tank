# Tank World: Project Philosophy

This document captures the core beliefs and principles that guide Tank World development.

---

## The Big Idea

**Tank World is infrastructure for automated Alife research.**

The simulation runs. Data gets collected. An AI agent analyzes results and improves the algorithms. The cycle repeats—without human intervention—indefinitely.

The fish tank visualization is just the first interface. It exists to make research *entertaining enough to watch*, which matters because entertaining simulations drive distributed compute contributions.

---

## Two-Layer Evolution

Most evolutionary systems have one layer: populations evolve within fixed rules.

Tank World has two layers:

1. **Layer 1 (Inside the Tank)**: Populations evolve using behavior algorithms. Natural selection optimizes parameters. This is traditional evolutionary computation.

2. **Layer 2 (Outside the Tank)**: After simulation runs, an AI agent analyzes performance data and *improves the algorithms themselves*—adding new strategies, removing failed ones, restructuring how behaviors work.

**The rules of evolution themselves evolve.**

This is what makes Tank World different. Layer 1 finds the best within current constraints. Layer 2 expands those constraints. Each layer informs the other.

---

## Core Beliefs

### 1. Interpretability matters more than power

We use explicit behavior algorithms instead of neural networks because:
- Algorithms are readable, debuggable, and understandable
- AI can reason about code, not just weights
- Evolution is visible in git history
- Humans can review what changed and why

Black-box approaches may be more powerful in some domains, but they're opaque. We choose transparency.

### 2. Entertainment drives scale

A simulation that nobody watches is a simulation that nobody runs.

Distributed compute requires motivation. If watching the simulation is entertaining, people will run it. If it's boring, they won't—regardless of its research value.

This is why visualization isn't a nice-to-have. It's the engine that drives participation.

In the future, AI will evolve visualizations themselves—optimizing for engagement while representing the same underlying research.

### 3. Automation is the goal

Human oversight is a transitional state, not an end goal.

Right now, humans review AI-proposed changes before merging. This is necessary while the system proves itself. But the long-term goal is full automation:

- Simulations run continuously
- AI proposes improvements
- Validation tests accept or reject changes
- The cycle repeats without human involvement

We build toward removing ourselves from the loop.

### 4. Data over speculation

Every improvement must be grounded in simulation evidence.

The AI doesn't guess what might work. It analyzes actual performance data—reproduction rates, survival rates, death causes—and proposes changes based on evidence.

Failed experiments inform future attempts. Successful patterns get reinforced. No speculation without data.

### 5. Open development

Everything happens in the open:
- Code in git with full history
- AI improvements via pull requests
- Evolution visible in commit logs
- Research reproducible by anyone

The system's evolution is as transparent as the populations it evolves.

---

## What We're Building Toward

**Phase 1 (Now)**: Prove Layer 2 works. AI improves algorithms based on data.

**Phase 2**: Close the loop. Remove humans from the cycle.

**Phase 3**: Research platform. Conduct legitimate Alife experiments.

**Phase 4**: Distributed compute. Scale through entertaining visualizations.

**Phase 5**: Evolving visualization. AI optimizes how research is presented.

**Phase 6**: Self-improving framework. The system expands its own capabilities.

---

## The Vision Statement

Tank World aims to be a **self-sustaining Alife research framework**:

- Simulations generate data
- AI improves algorithms
- Improvements get validated automatically
- Entertainment drives distributed compute
- The framework discovers what questions to ask next

The fish tank is where we start. What evolves next is up to the system—and the AI agents that drive it.

---

## Practical Implications

When making decisions about Tank World, consider:

1. **Does this help automation?** Changes that require more human oversight move us backward.

2. **Is this measurable?** If we can't quantify the impact, we can't evolve toward it.

3. **Is this interpretable?** If we can't understand what changed, we can't trust it.

4. **Does this help entertainment?** Boring simulations don't get run.

5. **Is this grounded in data?** Speculation without evidence doesn't belong here.

---

*The fish tank is just the beginning. The goal is research infrastructure that improves itself.*
