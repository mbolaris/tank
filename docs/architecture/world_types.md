# World Types Architecture

This document describes the available world types and their shared/unique systems.

## Canonical Registry

All world types are defined in **`core/modes/`** via `ModePackDefinition`. The `core/worlds/registry.py` is the single source of truth for available world types and their capabilities.

```python
from core.worlds.registry import WorldRegistry

# List all available modes
modes = WorldRegistry.list_mode_packs()

# Get a specific mode pack
tank_pack = WorldRegistry.get_mode_pack("tank")
print(tank_pack.supports_persistence)  # True
```

The backend registry (`backend/world_registry.py`) only attaches runtime snapshot builders to the core mode packs.

## Available World Types

| Mode ID | World Type | View Mode | Persistent | Actions | Websocket | Transfer | Has Fish |
|---------|-----------|-----------|------------|---------|-----------|----------|----------|
| `tank` | tank | side | yes | no | yes | yes | yes |
| `petri` | petri | topdown | yes | no | no | yes | yes |
| `soccer` | soccer | topdown | no | yes | no | no | no |

## Capability Flags

Each world type defines capability flags:

- **`supports_persistence`**: Can save/restore world state (tanks persist their fish population)
- **`supports_actions`**: Requires agent actions each step (soccer needs player inputs)
- **`supports_websocket`**: Supports real-time websocket updates
- **`supports_transfer`**: Supports entity transfer between worlds (fish migration)
- **`has_fish`**: Contains fish entities and fish-specific systems

## Shared Systems

All world types share these core systems:

### Genetics & Evolution
- Genome encoding for traits (speed, size, color genes)
- Mutation during reproduction
- Natural selection through energy/survival mechanics

### Energy System
- Energy consumption per action (movement, reproduction)
- Energy gain from food/resources
- Starvation when energy depletes

### Behaviors
- Behavior trees for autonomous decision-making
- State machines for complex behavior patterns
- Priority-based action selection

### Lifecycle
- Birth/spawning with inherited traits
- Aging and growth
- Death from starvation, predation, or natural causes

## Mode-Specific Rules

### Tank Mode
- Side-view aquarium visualization
- Fish swim in 2D (x, y coordinates)
- Food floats down from top
- Plants provide oxygen and food
- Fish transfer between tanks supported

### Petri Mode
- Top-down petri dish visualization
- Same simulation rules as tank
- Different visual perspective for organism studies

### Soccer Mode
- 2-team competitive gameplay
- Episodic (match-based, not persistent)
- Requires agent actions for player movement
- Goal-based scoring and rewards

## Config Normalization

Use `normalize_config()` for consistent config handling:

```python
from core.worlds.config_utils import normalize_config

# Normalize legacy keys and fill defaults
config = normalize_config("tank", {"width": 800, "fps": 60})
# Returns: {"screen_width": 800, "frame_rate": 60, ...defaults...}
```

## API Endpoint

The `/api/worlds/types` endpoint returns all registered world types with their capabilities:

```json
[
  {
    "mode_id": "tank",
    "world_type": "tank",
    "view_mode": "side",
    "display_name": "Fish Tank",
    "supports_persistence": true,
    "supports_actions": false,
    "supports_websocket": true,
    "supports_transfer": true,
    "has_fish": true
  }
]
```
