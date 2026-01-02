# World Feature Hooks Architecture

## Overview

The **World Feature Hooks** system makes the backend `SimulationRunner` truly world-agnostic by abstracting world-specific features (like poker, benchmarking, and tank-only commands) into optional plugin-like interfaces.

Previously, the runner was tank-centric with hardcoded assumptions about poker, plants, fish, and benchmarking. Now any world type can run without that overhead.

## Key Concepts

### Three-Layer Design

```
┌─────────────────────────────────────────┐
│   Backend / Frontend Communication      │
│  (WebSocket, REST, State Payloads)     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│     SimulationRunner (Universal)        │
│  - Pause/Resume/Reset commands          │
│  - State building (frame, entities)     │
│  - Frame loop timing                    │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│    World-Specific Hooks (Optional)      │
│  - TankWorldHooks (poker, benchmarks)   │
│  - NoOpWorldHooks (default, non-tank)   │
│  - Extensible for future worlds         │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│   World Backends + Simulation Core      │
│  - TankWorld / TankWorldBackendAdapter  │
│  - SoccerTrainingWorld                  │
│  - PetriWorld                           │
│  - SimulationEngine + Entities          │
└─────────────────────────────────────────┘
```

### Responsibilities

| Layer                  | Responsibility                                                  |
|------------------------|-------------------------------------------------------------|
| **World Hooks**        | Feature plugins: Poker, benchmarking, tank-only commands     |
| **SimulationRunner**   | Universal simulation control: pause, resume, state building  |
| **World Backend**      | World-specific entity management, physics, rules             |

## The WorldHooks Protocol

Defined in `backend/runner/world_hooks.py`, this protocol specifies what worlds *may* implement:

```python
class WorldHooks(Protocol):
    def supports_command(self, command: str) -> bool:
        """Check if this world handles a specific command."""
        ...

    def handle_command(self, runner, command: str, data: dict) -> dict | None:
        """Execute a world-specific command."""
        ...

    def build_world_extras(self, runner) -> dict:
        """Provide world-specific state (poker events, leaderboard, etc)."""
        ...

    def warmup(self, runner) -> None:
        """Initialize world-specific features on runner start."""
        ...

    def cleanup(self, runner) -> None:
        """Clean up resources on runner stop."""
        ...
```

## Implementations

### TankWorldHooks

Encapsulates all tank-specific features:

- **Poker Events & Leaderboard**: Collects and formats poker gameplay data
- **Evolution Benchmark Tracker**: Longitudinal skill evaluation (optional, controlled by env var)
- **Human Poker Interaction** (placeholder for future)
- **Tank-specific Commands**: `start_human_poker`, `stop_human_poker`, `auto_evaluate_poker`

**Initialization**: Called in `SimulationRunner.world_hooks.warmup(self)`
- Sets up evolution benchmark tracker if enabled
- Prepares poker event collection

**State Contribution**: `build_world_extras()` returns:
```python
{
    "poker_events": [PokerEventPayload, ...],
    "poker_leaderboard": [PokerLeaderboardEntryPayload, ...],
    "auto_evaluation": AutoEvaluateStatsPayload | None,
}
```

### NoOpWorldHooks

Default no-op implementation for non-tank worlds:
- Returns empty dicts for extras
- Doesn't support any special commands
- No-op warmup/cleanup

Used by: Soccer, Petri, and any future world types that don't need special features.

## Integration with SimulationRunner

### Initialization (`__init__`)

```python
# Create hooks based on world type
self.world_hooks = get_hooks_for_world(world_type)

# Call warmup to initialize features
self.world_hooks.warmup(self)

# Expose attributes for backward compatibility (Tank only)
self.human_poker_game = getattr(self.world_hooks, "human_poker_game", None)
self.evolution_benchmark_tracker = getattr(self.world_hooks, "evolution_benchmark_tracker", None)
```

### State Building (`_build_full_state`)

```python
# Build universal state
state_dict = {
    "frame": frame,
    "entities": entities,
    "stats": stats,
    # ...
}

# Add world-specific extras
extras = self.world_hooks.build_world_extras(self)
state_dict.update(extras)

# If Tank, extras include poker_events, poker_leaderboard, etc.
# If non-Tank, extras is empty
```

### Command Handling (`handle_command`)

```python
# 1. Try hooks first (poker commands, world-specific)
if self.world_hooks.supports_command(command):
    result = self.world_hooks.handle_command(self, command, data)
    if result is not None:
        return result

# 2. Try universal handlers (pause, resume, reset)
handler = universal_handlers.get(command)
if handler:
    return handler(data)

# 3. Try tank-specific handlers for backward compatibility
if self.world_type == "tank":
    handler = tank_handlers.get(command)
    if handler:
        return handler(data)

# 4. Return error
return error(f"Unknown command: {command}")
```

## Backward Compatibility

### Tank World

Tank still receives exactly the same state payloads with all features:
- `poker_events` in full/delta state
- `poker_leaderboard` in full state
- All tank-specific commands (add_food, spawn_fish, set_plant_energy_input) still work
- `human_poker_game`, `standard_poker_series`, `evolution_benchmark_tracker` attributes still accessible

### Non-Tank Worlds

- Get universal state (frame, entities, stats) without tank overhead
- Gracefully reject tank-specific commands with error responses
- No tank-centric code runs (no poker event collection, no fish-specific logic)
- Can extend with their own hooks in the future

## Adding a New World Type

To add world-specific features for a new world (e.g., "my_world"):

1. **Create a hooks class** in `backend/runner/world_hooks.py`:
   ```python
   class MyWorldHooks:
       def supports_command(self, command: str) -> bool:
           return command in {"my_custom_command"}

       def handle_command(self, runner, command, data):
           if command == "my_custom_command":
               return {"success": True, "result": "..."}
           return None

       def build_world_extras(self, runner) -> dict:
           return {
               "my_feature": self._collect_my_feature(runner),
           }

       # ... other methods
   ```

2. **Register in factory**:
   ```python
   def get_hooks_for_world(world_type: str):
       if world_type == "my_world":
           return MyWorldHooks()
       else:
           return NoOpWorldHooks()
   ```

3. **(Optional) Extend state payloads** in `backend/state_payloads.py` to include your new features.

4. **Write tests** to verify:
   - Features initialize correctly
   - State includes expected fields
   - Commands work as intended

## Benefits

1. **Separation of Concerns**: Tank logic is isolated from universal simulation code
2. **Extensibility**: New world types can add features without modifying core runner
3. **No Overhead**: Non-tank worlds don't execute tank code (no fish scanning, poker evaluation)
4. **Testability**: Hooks can be unit-tested independently
5. **Backward Compatibility**: Tank world behavior is unchanged from user perspective

## Future Improvements

- Formal hooks registry/discovery (if many world types are added)
- Lazy loading of hooks (only load TankWorldHooks if world_type=="tank")
- Hook middleware/composition (chain multiple hooks together)
- Hooks for other cross-cutting concerns (logging, profiling, etc.)
