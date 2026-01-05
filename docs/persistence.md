# Persistence System

This document describes the snapshot persistence system for Tank World simulation state.

## Schema Version

Current schema version: **2.0**

The schema version is included in every saved snapshot under the `version` key. This enables forward compatibility and migration logic when loading older saves.

### Version History

| Version | Changes |
|---------|---------|
| 2.0 | Removed `genome.max_energy` (now computed from fish size). Added explicit entity type serialization. |
| 1.0 | Original schema with `genome.max_energy` stored. |

## Snapshot Structure

```json
{
  "version": "2.0",
  "tank_id": "unique-tank-identifier",
  "frame": 12345,
  "paused": false,
  "saved_at": "2024-01-01T00:00:00Z",
  "config": { ... },
  "entities": [ ... ],
  "ecosystem": { ... },
  "code_pool": { ... }
}
```

### Required Fields

- `version` - Schema version string
- `tank_id` - Unique tank identifier
- `frame` - Frame count at time of save
- `metadata` - Save metadata (timestamp, entity count)
- `entities` - Array of serialized entity data

### Entity Types

Each entity in `entities` array has a `type` field:

| Type | Description | Key Fields |
|------|-------------|------------|
| `fish` | Fish entity | `id`, `species`, `genome_data`, `energy`, `x`, `y` |
| `plant` | Plant entity | `id`, `genome_data`, `root_spot_id`, `energy`, `x`, `y` |
| `plant_nectar` | Plant nectar | `source_plant_id`, `energy`, `x`, `y` |
| `food` | Food item | `food_type`, `energy`, `x`, `y` |
| `crab` | Crab predator | `energy`, `genome`, `x`, `y` |
| `castle` | Castle decoration | `x`, `y`, `width`, `height` |

## Reference Integrity

### Plant-Nectar Relationship

Nectar entities reference their source plant via `source_plant_id`. During restoration:

1. **Pass 1**: All non-nectar entities are restored first
2. **Pass 2**: Nectar entities are restored with links to already-restored plants

If a nectar's `source_plant_id` doesn't match any restored plant, the nectar is skipped with a consolidated warning (not spammed per-nectar).

### Restoration Order

Entity restoration uses a deterministic two-pass approach:
1. Plants, Fish, Food, Crabs, Castles
2. Nectar (depends on plants existing)

This ensures reference integrity without requiring entities to be saved in dependency order.

## API Reference

### Saving State

```python
from backend.world_persistence import save_world_state

# manager must implement capture_state_for_save()
filepath = save_tank_state(tank_id, manager)
```

### Loading State

```python
from backend.world_persistence import load_snapshot, restore_world_from_snapshot

snapshot = load_tank_state("/path/to/snapshot.json")
if snapshot:
    success = restore_tank_from_snapshot(snapshot, target_world)
```

### Listing Snapshots

```python
from backend.world_persistence import list_world_snapshots, get_latest_snapshot

snapshots = list_tank_snapshots(tank_id)
latest = get_latest_snapshot(tank_id)
```

## Testing

Run the persistence hardening test suite:

```bash
pytest tests/test_persistence_hardening.py -v
```

This verifies:
- Round-trip save/load preserves entity state
- Plant-Nectar reference integrity after restore
- Schema version is included in snapshots
