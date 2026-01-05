# Tank World Roadmap

> **Vision**: One flexible agent-based simulation engine that supports multiple world modes with different rules and visualizations.

---

## Core Vision

Tank World is designed to be a **multi-modal simulation engine** where the same core systems (genetics, energy, behaviors) power different world types with specialized rules and visualizations.

### Supported World Modes

| Mode | Description |
|------|-------------|
| **Tank** | Fish eat, play poker, avoid hazards (current baseline) |
| **Petri** | Same agents/genetics/energy, rendered as microbes/nutrients (optional rule tweaks) |
| **Soccer** | Evolved agents become soccer players (RCSS integration), training world drives evolution |

### Core Invariants (All Worlds)

- Genetics + code-pool genome
- Energy ledger / lifecycle
- Behavior policy execution
- Deterministic stepping per world instance
- Clean phase boundaries + mutation ownership

---

## Current Status

| Area | Status |
|------|--------|
| **Backend abstractions** | `WorldBackend`, `SystemPack`, world registry exist |
| **Snapshot builders** | Per-world snapshot builders implemented |
| **Observation registry** | Exists; tank-specific observation builders in tank world code |
| **Mutation queue** | Exists; spawn/remove trending centralized |
| **RCSS integration** | Protocol + adapter + tests exist (no full end-to-end world loop yet) |
| **Petri mode** | Exists but needs first-class frontend rendering and mode-aware UI |

---

## Near-Term Goals

*Keep Tank stable while refactoring.*

### 1. Mode-Aware UI Plumbing (Highest Leverage)

- [ ] Fix frontend WS handler to preserve `mode_id` + `view_mode`
- [ ] Renderer selection uses these fields consistently
- [ ] Add tiny mode/view badge for debugging
- [ ] Add regression test for mode preservation

### 2. Make Petri Mode Visually Real

- [ ] Dedicated `PetriTopDownRenderer` driven by `render_hint`
- [ ] No tank hacks in Petri renderer
- [ ] Minimal UI hint showing current mode

### 3. Tank Uses Genome Code Pool (Movement First)

- [ ] Introduce "movement policy contract"
- [ ] Run movement through `GenomeCodePool.execute_policy` when configured
- [ ] Safe fallback to legacy `MovementStrategy`
- [ ] Tests: policy path works + fallback works + exceptions don't crash

### 4. Soccer Groundwork → Real World Loop

- [ ] Implement `rcss_world` that can step and translate actions/observations
- [ ] Build deterministic `FakeRCSSServer` for CI tests
- [ ] End-to-end test: action → emitted command → parsed observation

---

## Medium-Term Goals

*Architectural improvements for long-term maintainability.*

### One Runner Contract ✅

Unified the two runtime stacks (`WorldRunner` + `SimulationRunner/TankWorldAdapter`) into a single `RunnerProtocol`:

- `RunnerProtocol` defines the interface all runners must satisfy
- `SimulationRunner` exposes public methods (`get_entities_snapshot`, `get_stats`, etc.)
- `TankWorldAdapter` no longer reaches into private `_collect_*` methods
- Eliminated dead code (`_create_plant_player_data`, `_get_fish_genome_data`)

### Componentize the Agent

- Replace the Fish god-object with a compositional root + components/hooks
- World-specific capabilities are components, not subclasses/forks
- Strict boundaries: domain logic emits events; ledger/telemetry consumes events

### Standardize Action + Observation Contracts

- Registry-based observation builders (already started)
- Mirror for action translation (ActionRegistry)
- "Same genome policy" works across Tank/Petri/Soccer with adapters


---

## Long-Term Goals

*Soccer evolution success.*

### Training World for Soccer

- `SoccerTraining` world: cheap/deterministic, used for evolution
- Periodically evaluate champions in real RCSS matches
- Fitness functions: goal contribution, positioning, teamwork, stamina/energy discipline

### Genome = Python Code Pool

- Genome references code components/policies stored in the pool
- Expandable: any Python-expressible component can be introduced
- Strong sandboxing + determinism strategy per world

---

## Guiding Rules

1. **No tank-specific imports in generic policy modules**
2. **All spawns/removals go through central queues** (no mid-frame list mutation)
3. **Strict phase order enforced by tests**
4. **Small modules, typed interfaces, "world owns world logic"**
5. **Add regression tests whenever you cut a new seam** (WS parsing, observation/action registries, persistence)

---

*Last updated: January 2026*
