# World Loop Contract

This document defines the standard world loop contract that all world backends must implement to share the common engine core.

## Overview

All worlds (Tank, Petri, Soccer) implement the same phase loop and action/observation interfaces. This enables:

- **Consistent API**: External brains interact with any world through the same interface
- **Shared engine core**: Worlds reuse common infrastructure without code duplication
- **World-agnostic backend**: The backend layer can manage any world type uniformly

## Contract Definition

All world backends implement `MultiAgentWorldBackend` (defined in `core/worlds/interfaces.py`):

```python
class MultiAgentWorldBackend(ABC):
    def reset(self, seed: int | None, config: dict | None) -> StepResult: ...
    def step(self, actions: dict[str, Any] | None) -> StepResult: ...
    def get_current_snapshot(self) -> dict[str, Any]: ...
    def get_current_metrics(self) -> dict[str, Any]: ...

    @property
    def world_type(self) -> str: ...  # "tank", "petri", "soccer", etc.
```

### StepResult Dataclass

The `StepResult` contains all outputs from a simulation step:

| Field | Type | Description |
|-------|------|-------------|
| `obs_by_agent` | `dict[str, Any]` | Per-agent observations |
| `snapshot` | `dict[str, Any]` | World state for rendering |
| `events` | `list[dict]` | Significant events (births, deaths, poker) |
| `metrics` | `dict[str, Any]` | Aggregate statistics |
| `done` | `bool` | Episode termination flag |
| `info` | `dict[str, Any]` | Backend-specific metadata |
| `spawns` | `list[Any]` | Entity spawn records (optional) |
| `removals` | `list[Any]` | Entity removal records (optional) |
| `energy_deltas` | `list[Any]` | Energy delta records (recorded per-frame) |
| `render_hint` | `dict | None` | Rendering metadata (optional) |

### RenderHint

The `render_hint` provides frontend-agnostic rendering metadata:

```python
{
    "style": "side" | "topdown",  # View perspective
    "entity_style": "fish" | "microbe" | "player",  # Entity visualization
    "camera": {...},  # Optional camera settings
}
```

Built-in render hints:
- **Tank**: `{"style": "side", "entity_style": "fish"}`
- **Petri**: `{"style": "topdown", "entity_style": "microbe"}`
- **Soccer**: `{"style": "topdown", "entity_style": "player"}`

## Phase Order

The simulation engine executes phases in this order:

1. **FRAME_START**: Reset counters, increment frame, reconcile plants
2. **TIME_UPDATE**: Advance day/night cycle
3. **ENVIRONMENT**: Update ecosystem and detection modifiers
4. **ENTITY_ACT**: Update all entities, collect spawns/deaths
5. **LIFECYCLE**: Process deaths, add/remove entities
6. **SPAWN**: Auto-spawn food, update spatial positions
7. **COLLISION**: Handle physical collisions
8. **INTERACTION**: Handle social interactions (poker proximity, games)
9. **REPRODUCTION**: Handle mating and emergency spawns
10. **FRAME_END**: Update statistics, rebuild caches

> [!IMPORTANT]
> See `core/update_phases.py` for the canonical phase enum definition.

## Mutation Ownership Rule

Entity mutations (spawns/removals) MUST go through the designated mutation queue:

| Context | API to Use |
|---------|------------|
| Systems (e.g., ReproductionSystem) | `engine.request_spawn()`, `engine.request_remove()` |
| Entities (e.g., Fish reproduction) | `request_spawn()`, `request_remove()` from `core.util.mutations` |

**Direct mutations are forbidden during phases:**

```python
# ❌ WRONG - will raise RuntimeError during phases
engine.add_entity(fish)
engine.remove_entity(fish)

# ✅ CORRECT - queues mutation for safe processing
engine.request_spawn(fish, reason="reproduction")
engine.request_remove(fish, reason="death")
```

The engine applies queued mutations at safe commit points between phases via `_apply_entity_mutations()`.

## Action Registry

The `ActionRegistry` (in `core/actions/action_registry.py`) provides world-agnostic action translation:

```python
from core.actions import get_action_space, translate_action

# Get available actions for a world
space = get_action_space("tank")
# {"movement": {"type": "continuous", "shape": (2,), ...}}

# Translate raw action to domain Action
action = translate_action("tank", "fish_123", {"velocity": (1.0, 2.0)})
```

### Registering a Custom Translator

```python
from core.actions.action_registry import ActionSpace, register_action_translator

class MyWorldActionTranslator:
    def get_action_space(self) -> ActionSpace:
        return {"movement": {"type": "continuous", "shape": (2,)}}

    def translate_action(self, agent_id: str, raw_action: Any) -> Action:
        return Action(entity_id=agent_id, target_velocity=raw_action)

register_action_translator("my_world", MyWorldActionTranslator())
```

## Adding a New World

1. **Create backend adapter** in `core/worlds/{world_type}/backend.py`:
   ```python
   class MyWorldBackendAdapter(MultiAgentWorldBackend):
       @property
       def world_type(self) -> str:
           return "my_world"

       def reset(self, seed, config) -> StepResult:
           # Initialize world, return initial state
           ...

       def step(self, actions) -> StepResult:
           # Advance simulation, return step result
           ...
   ```

2. **Register with WorldRegistry** in `core/worlds/registry.py`:
   ```python
   WorldRegistry.register_world_type(
       world_type="my_world",
       factory=lambda **kwargs: MyWorldBackendAdapter(**kwargs),
       mode_pack=create_my_world_mode_pack(),
   )
   ```

3. **(Optional) Create action translator** in `core/worlds/{world_type}/actions.py`

4. **Add tests** for contract compliance in `tests/test_worldloop_contract.py`

## Built-in Worlds

| World | Backend | Engine | Description |
|-------|---------|--------|-------------|
| tank | `TankWorldBackendAdapter` | `SimulationEngine` | Fish ecosystem simulation |
| petri | `PetriWorldBackendAdapter` | Reuses Tank | Microbe simulation (same rules, different visuals) |
| soccer | `SoccerWorldBackendAdapter` | Custom | Soccer RL training with pure-Python physics |
| soccer_training | `SoccerTrainingWorldBackendAdapter` | Custom | Soccer skill training environment |

## Related Files

- `core/worlds/interfaces.py` - `MultiAgentWorldBackend`, `StepResult`
- `core/worlds/contracts.py` - `WorldType`, `RenderHint`, `WorldLoop` protocol
- `core/worlds/registry.py` - `WorldRegistry` for world instantiation
- `core/actions/action_registry.py` - Action translation registry
- `core/simulation/engine.py` - Core simulation engine with phase loop
- `core/update_phases.py` - Phase enum and utilities
- `tests/test_worldloop_contract.py` - Contract compliance tests
