"""World state persistence for the unified WorldManager.

This module handles saving and loading complete world states to/from disk,
enabling durable simulations that can be resumed after restarts.

Schema Versioning:
    - Version 1.0: Original schema with genome.max_energy
    - Version 2.0: Removed genome.max_energy (now computed from size)
                   Fish max_energy is dynamically computed from lifecycle size

Compatibility:
    - Old saves with max_energy are loaded successfully (max_energy ignored)
"""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner

logger = logging.getLogger(__name__)

# Current schema version for saved snapshots
from core.worlds.tank.schema import SCHEMA_VERSION

# Base directory for all world data (reusing existing path for compatibility)
DATA_DIR = Path("data/tanks")


def ensure_world_directory(world_id: str) -> Path:
    """Ensure the data directory for a world exists.

    Args:
        world_id: The world identifier

    Returns:
        Path to the world's data directory
    """
    world_dir = DATA_DIR / world_id / "snapshots"
    world_dir.mkdir(parents=True, exist_ok=True)
    return world_dir


def save_snapshot_data(world_id: str, snapshot: Dict[str, Any]) -> Optional[str]:
    """Save pre-captured snapshot data to disk.

    Args:
        world_id: The world identifier
        snapshot: The complete snapshot dictionary

    Returns:
        Filepath of saved snapshot, or None if save failed
    """
    try:
        # Generate snapshot filename with timestamp
        saved_at = snapshot.get("saved_at")
        if saved_at:
            try:
                timestamp = datetime.fromisoformat(saved_at).strftime("%Y%m%d_%H%M%S")
            except ValueError:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snapshot["saved_at"] = datetime.now(timezone.utc).isoformat()

        world_dir = ensure_world_directory(world_id)
        snapshot_file = world_dir / f"snapshot_{timestamp}.json"

        # Write to file
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)

        logger.info(
            f"Saved world {world_id[:8]} state to {snapshot_file.name} "
            f"({len(snapshot.get('entities', []))} entities)"
        )
        return str(snapshot_file)

    except Exception as e:
        logger.error(f"Failed to save world {world_id[:8]} state: {e}", exc_info=True)
        return None


def save_world_state(
    world_id: str, runner: "SimulationRunner", metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Save complete world state to disk.

    Args:
        world_id: The world identifier
        runner: SimulationRunner instance
        metadata: Optional metadata to merge into snapshot (name, description, etc.)

    Returns:
        Filepath of saved snapshot, or None if save failed
    """
    try:
        # Get the world adapter from the runner
        world = runner.world

        # Check if the world adapter has capture_state_for_save
        if hasattr(world, "capture_state_for_save"):
            snapshot = world.capture_state_for_save()
            if snapshot:
                # Merge provided metadata
                if metadata:
                    snapshot.update(metadata)
                return save_snapshot_data(world_id, snapshot)

        logger.warning(f"World {world_id[:8]} does not support state capture")
        return None

    except Exception as e:
        logger.error(f"Failed to save world {world_id[:8]} state: {e}", exc_info=True)
        return None


def load_snapshot(snapshot_path: str) -> Optional[Dict[str, Any]]:
    """Load a snapshot from disk.

    Args:
        snapshot_path: Path to the snapshot file

    Returns:
        Snapshot dictionary, or None if load failed
    """
    try:
        with open(snapshot_path) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load snapshot {snapshot_path}: {e}", exc_info=True)
        return None


def restore_world_from_snapshot(
    snapshot: Dict[str, Any],
    target_world: Any,
) -> bool:
    """Restore world state from a snapshot.

    Args:
        snapshot: The snapshot dictionary
        target_world: The world adapter to restore into

    Returns:
        True if restoration succeeded, False otherwise
    """
    try:
        from core.entities import Food, PlantNectar
        from core.entities.plant import Plant
        from core.transfer.entity_transfer import deserialize_entity

        def _infer_entity_type(entity_data: Dict[str, Any]) -> Optional[str]:
            """Regression-safe inference for snapshots missing type field."""
            if "species" in entity_data and "genome_data" in entity_data:
                return "fish"
            if "root_spot_id" in entity_data and "genome_data" in entity_data:
                return "plant"
            return None

        # Resolve engine from target_world (which might be an adapter)
        engine = None
        if hasattr(target_world, "world") and hasattr(target_world.world, "engine"):
            engine = target_world.world.engine
        elif hasattr(target_world, "engine"):
            engine = target_world.engine

        if engine is None:
            logger.error("Failed to resolve engine for restoration")
            return False

        # Restore frame count on the engine
        if "frame" in snapshot:
            engine.frame_count = snapshot["frame"]

        # Clear existing entities
        engine.entities_list.clear()
        if engine.environment:
            engine.environment.spatial_grid.clear()

        # Reset root spots
        if hasattr(engine, "root_spot_manager") and engine.root_spot_manager:
            for spot in engine.root_spot_manager.spots:
                spot.release()

        # Track restored plants for nectar association
        plants_by_id: Dict[int, Plant] = {}
        nectar_data_list = []
        restored_count = 0

        # Pass 1: Restore non-nectar entities
        for entity_data in snapshot.get("entities", []):
            entity_type = entity_data.get("type") or _infer_entity_type(entity_data)

            if entity_type and "type" not in entity_data:
                entity_data["type"] = entity_type

            if entity_type == "plant_nectar":
                nectar_data_list.append(entity_data)
                continue

            if entity_type in ("fish", "plant"):
                # Use deserialization logic from entity_transfer
                entity = deserialize_entity(entity_data, target_world)
                if entity:
                    # Restore original ID for consistency
                    if isinstance(entity, Plant) and "id" in entity_data:
                        entity.plant_id = entity_data["id"]
                    engine.add_entity(entity)
                    restored_count += 1
                    if isinstance(entity, Plant):
                        plants_by_id[entity.plant_id] = entity

            elif entity_type == "food":
                # Restore food
                from core.entities.resources import LiveFood

                food_type = entity_data.get("food_type", "basic")
                x = entity_data["x"]
                y = entity_data["y"]

                if food_type == "live":
                    food = LiveFood(environment=engine.environment, x=x, y=y)
                else:
                    food = Food(x=x, y=y, food_type=food_type, environment=engine.environment)

                food.energy = entity_data.get("energy", 10)
                engine.add_entity(food)
                restored_count += 1

        # Pass 2: Restore nectar with plant references
        for nectar_data in nectar_data_list:
            source_plant_id = nectar_data.get("source_plant_id")
            source_plant = plants_by_id.get(source_plant_id) if source_plant_id else None

            nectar = PlantNectar(
                x=nectar_data["x"],
                y=nectar_data["y"],
                source_plant=source_plant,
                environment=engine.environment,
            )
            nectar.energy = nectar_data.get("energy", 5)
            engine.add_entity(nectar)

            restored_count += 1

        # Pass 3: Restore castles
        # Iterate again to find castles (or could initiate in pass 1, but order matters little for castle)
        for entity_data in snapshot.get("entities", []):
            if entity_data.get("type") == "castle":
                from core.entities.base import Castle

                x = entity_data.get("x", 375)
                y = entity_data.get("y", 475)

                castle = Castle(environment=engine.environment, x=x, y=y)
                # Apply size if stored
                if "width" in entity_data and "height" in entity_data:
                    castle.set_size(entity_data["width"], entity_data["height"])

                engine.add_entity(castle)
                restored_count += 1

        # Restore paused state
        if "paused" in snapshot and hasattr(target_world, "paused"):
            target_world.paused = snapshot["paused"]

        logger.info(
            f"Restored world {snapshot.get('tank_id', 'unknown')[:8]} to frame {snapshot.get('frame', 0)} "
            f"({restored_count} entities)"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to restore world from snapshot: {e}", exc_info=True)
        return False


def list_world_snapshots(world_id: str) -> List[Dict[str, Any]]:
    """List all available snapshots for a world.

    Args:
        world_id: The world identifier

    Returns:
        List of snapshot metadata (filename, timestamp, frame)
    """
    world_dir = DATA_DIR / world_id / "snapshots"
    if not world_dir.exists():
        return []

    snapshots = []
    for snapshot_file in sorted(world_dir.glob("snapshot_*.json"), reverse=True):
        try:
            # Read just the metadata without loading full state
            with open(snapshot_file) as f:
                data = json.load(f)
                snapshots.append(
                    {
                        "filename": snapshot_file.name,
                        "filepath": str(snapshot_file),
                        "saved_at": data.get("saved_at"),
                        "frame": data.get("frame"),
                        "entity_count": len(data.get("entities", [])),
                        "size_bytes": snapshot_file.stat().st_size,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to read snapshot {snapshot_file.name}: {e}")
            continue

    return snapshots


def get_latest_snapshot(world_id: str) -> Optional[str]:
    """Get the path to the most recent snapshot for a world.

    Args:
        world_id: The world identifier

    Returns:
        Path to the latest snapshot file, or None if no snapshots exist
    """
    snapshots = list_world_snapshots(world_id)
    if not snapshots:
        return None

    # Snapshots are sorted by newest first
    return snapshots[0]["filepath"]


def find_all_world_snapshots() -> Dict[str, str]:
    """Find the latest snapshot for each world that has saved data.

    Returns:
        Dictionary mapping world_id to latest snapshot path
    """
    if not DATA_DIR.exists():
        logger.debug(f"DATA_DIR not found at {DATA_DIR.resolve()}")
        return {}

    logger.info(f"Scanning for snapshots in {DATA_DIR.resolve()}")

    world_snapshots = {}

    # Iterate through all world directories
    for world_dir in DATA_DIR.iterdir():
        if not world_dir.is_dir():
            continue

        world_id = world_dir.name
        latest_snapshot = get_latest_snapshot(world_id)

        if latest_snapshot:
            world_snapshots[world_id] = latest_snapshot
            logger.debug(f"Found snapshot for world {world_id[:8]}: {latest_snapshot}")

    logger.info(f"Found {len(world_snapshots)} worlds with saved snapshots")
    return world_snapshots


def delete_snapshot(snapshot_path: str) -> bool:
    """Delete a snapshot file.

    Args:
        snapshot_path: Path to the snapshot file

    Returns:
        True if deletion succeeded, False otherwise
    """
    try:
        Path(snapshot_path).unlink()
        logger.info(f"Deleted snapshot {Path(snapshot_path).name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete snapshot {snapshot_path}: {e}")
        return False


def delete_world_data(world_id: str) -> bool:
    """Delete all persisted data for a specific world.

    Args:
        world_id: The world identifier

    Returns:
        True if the world data directory was removed, False otherwise
    """
    world_dir = DATA_DIR / world_id
    try:
        if not world_dir.exists():
            logger.info(f"No persisted data found for world {world_id[:8]}")
            return False

        shutil.rmtree(world_dir)
        logger.info(f"Deleted persisted data for world {world_id[:8]}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete data for world {world_id[:8]}: {e}")
        return False


def cleanup_old_snapshots(world_id: str, max_snapshots: int = 10) -> int:
    """Delete oldest snapshots beyond the retention limit.

    Args:
        world_id: The world identifier
        max_snapshots: Maximum number of snapshots to keep

    Returns:
        Number of snapshots deleted
    """
    snapshots = list_world_snapshots(world_id)
    if len(snapshots) <= max_snapshots:
        return 0

    # Delete oldest snapshots
    deleted = 0
    for snapshot in snapshots[max_snapshots:]:
        if delete_snapshot(snapshot["filepath"]):
            deleted += 1

    logger.info(f"Cleaned up {deleted} old snapshots for world {world_id[:8]}")
    return deleted
