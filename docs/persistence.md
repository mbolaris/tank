# Persistence System

This document describes the snapshot persistence system for Tank World
simulation state. It lets durable worlds resume after a server restart and
backs the auto-save service.

## Schema Version

Current schema version: **3.0** (`SNAPSHOT_VERSION` in
`core/contracts/version.py` — the single source of truth).

Every snapshot is stamped with `schema_version`. Loading is **strict**: a
snapshot whose version is missing or not exactly `3.0` is rejected with a
`VersionMismatchError` (a `PersistenceError` subclass). There is **no
migration of old saves** — this is a deliberate pre-release policy that keeps
the restore path simple and honest.

### Version History

| Version | Changes |
|---------|---------|
| 3.0 | Strict schema. Every entity carries an explicit `type` field; no type inference, no legacy id restoration, no field-level migration. |
| 2.0 | Removed `genome.max_energy` (now derived from fish size). Added explicit entity-type serialization. |
| 1.0 | Original schema with `genome.max_energy` stored. |

> Genome payloads and WebSocket state payloads carry their own independent
> version fields (`GENOME_SCHEMA_VERSION`, `STATE_SCHEMA_VERSION`) and validate
> them at their own boundaries. The snapshot `schema_version` governs only the
> snapshot envelope.

## Snapshot Structure

```json
{
  "schema_version": "3.0",
  "world_id": "unique-world-identifier",
  "seed": 42,
  "frame": 12345,
  "paused": false,
  "saved_at": "2026-01-01T00:00:00Z",
  "config": {},
  "entities": [ ... ],
  "metrics_history": { ... }
}
```

### Top-level Fields

- `schema_version` — schema version string (stamped at save time)
- `world_id` — unique world identifier
- `seed` — RNG seed the world was created with
- `frame` — frame count at time of save
- `paused` — whether the world was paused
- `saved_at` — ISO-8601 save timestamp
- `entities` — array of serialized entities (see below)
- `metrics_history` — optional metrics history payload, when available

### Entity Types

Each entry in `entities` has an explicit `type` field (required — restore
raises `PersistenceError` if it is missing):

| Type | Description | Key Fields |
|------|-------------|------------|
| `fish` | Fish entity | `id`, `species`, `genome_data`, `energy`, `x`, `y` |
| `plant` | Plant entity | `id`, `genome_data`, `root_spot_id`, `energy`, `x`, `y` |
| `plant_nectar` | Plant nectar | `source_plant_id`, `energy`, `x`, `y` |
| `food` | Food item | `food_type`, `energy`, `x`, `y` |
| `crab` | Crab predator | `genome_data`, `energy`, `x`, `y` |
| `castle` | Castle decoration | `x`, `y`, `width`, `height` |

Entity (de)serialization is centralized in
`core/transfer/entity_transfer.py`, shared by both snapshots and live
tank-to-tank migration.

## Reference Integrity and Restore Order

Restoration is multi-pass so entities do not need to be saved in dependency
order:

1. **Pass 1** — fish, plants, crabs and food are restored. Restored plants are
   indexed by id.
2. **Pass 2** — nectar is restored and linked to its source plant via
   `source_plant_id`. Nectar whose source plant was not restored is skipped
   with a single consolidated warning (not spammed per-nectar).
3. **Pass 3** — castles are restored.

After restore, two bootstrap steps run:

- **Transient elements** (soccer ball / goals) are never persisted; they are
  re-created from config so a restored world is immediately playable.
- **Static elements** (the tank Castle) are recreated if a partial snapshot
  omitted them, then the restored world is validated.

## API Reference

All functions live in `backend/world_persistence.py`.

### Saving State

```python
from backend.world_persistence import save_world_state, save_snapshot_data

# Capture + persist in one call (runner.world must implement capture_state_for_save()).
filepath = save_world_state(world_id, runner, metadata={"name": "My World"})

# Or persist a pre-captured snapshot dict directly.
filepath = save_snapshot_data(world_id, snapshot)
```

### Loading State

```python
from backend.world_persistence import load_snapshot, restore_world_from_snapshot

snapshot = load_snapshot("/path/to/snapshot.json")
if snapshot:
    success = restore_world_from_snapshot(snapshot, target_world)
```

### Listing and Managing Snapshots

```python
from backend.world_persistence import (
    list_world_snapshots,
    get_latest_snapshot,
    find_all_world_snapshots,
    cleanup_old_snapshots,
    delete_snapshot,
    delete_world_data,
)

snapshots = list_world_snapshots(world_id)        # newest first
latest = get_latest_snapshot(world_id)            # path or None
all_latest = find_all_world_snapshots()           # {world_id: path}
cleanup_old_snapshots(world_id, max_snapshots=10) # retention
```

Snapshots are stored under `data/worlds/{world_id}/snapshots/snapshot_*.json`.

## Testing

```bash
pytest tests/test_persistence_hardening.py tests/test_crab_persistence.py \
       tests/test_entity_transfer_codecs.py -v
```

These verify round-trip save/load, plant–nectar reference integrity, crab
persistence, and that snapshots carry the schema version.
