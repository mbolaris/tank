"""Tank state persistence for Tank World Net.

This module handles saving and loading complete tank states to/from disk,
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
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Current schema version for saved snapshots
SCHEMA_VERSION = "2.0"

# Base directory for all tank data
DATA_DIR = Path("data/tanks")


def ensure_tank_directory(tank_id: str) -> Path:
    """Ensure the data directory for a tank exists.

    Args:
        tank_id: The tank identifier

    Returns:
        Path to the tank's data directory
    """
    tank_dir = DATA_DIR / tank_id / "snapshots"
    tank_dir.mkdir(parents=True, exist_ok=True)
    return tank_dir


def save_snapshot_data(tank_id: str, snapshot: Dict[str, Any]) -> Optional[str]:
    """Save pre-captured snapshot data to disk.

    Args:
        tank_id: The tank identifier
        snapshot: The complete snapshot dictionary

    Returns:
        Filepath of saved snapshot, or None if save failed
    """
    try:
        # Generate snapshot filename with timestamp
        # Use the timestamp from the snapshot if available, otherwise current time
        saved_at = snapshot.get("saved_at")
        if saved_at:
            try:
                timestamp = datetime.fromisoformat(saved_at).strftime("%Y%m%d_%H%M%S")
            except ValueError:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snapshot["saved_at"] = datetime.now(timezone.utc).isoformat()

        tank_dir = ensure_tank_directory(tank_id)
        snapshot_file = tank_dir / f"snapshot_{timestamp}.json"

        # Write to file
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)

        logger.info(f"Saved tank {tank_id[:8]} state to {snapshot_file.name} ({len(snapshot.get('entities', []))} entities)")
        return str(snapshot_file)

    except Exception as e:
        logger.error(f"Failed to save tank {tank_id[:8]} state: {e}", exc_info=True)
        return None


def save_tank_state(tank_id: str, manager: Any) -> Optional[str]:
    """Save complete tank state to disk.

    Args:
        tank_id: The tank identifier
        manager: SimulationManager instance

    Returns:
        Filepath of saved snapshot, or None if save failed
    """
    # For backward compatibility or direct synchronous usage
    if hasattr(manager, "capture_state_for_save"):
        snapshot = manager.capture_state_for_save()
        if snapshot:
            return save_snapshot_data(tank_id, snapshot)
        return None

    # Fallback to old logic if manager doesn't support capture_state_for_save
    # (This shouldn't happen with updated SimulationManager, but good for safety)
    try:

        # ... (rest of the old logic would go here, but we can just fail or warn)
        logger.warning("save_tank_state called on manager without capture_state_for_save")
        return None
    except Exception as e:
        logger.error(f"Failed to save tank {tank_id[:8]} state: {e}", exc_info=True)
        return None


def load_tank_state(snapshot_path: str) -> Optional[Dict[str, Any]]:
    """Load tank state from a snapshot file.

    Args:
        snapshot_path: Path to the snapshot JSON file

    Returns:
        Snapshot data dictionary, or None if load failed

    Note:
        This function handles schema migrations automatically:
        - v1.0 snapshots: genome.max_energy will be ignored on load
        - v2.0 snapshots: max_energy computed from fish size
    """
    try:
        resolved_path = Path(snapshot_path).resolve()
        data_root = DATA_DIR.resolve()

        if not resolved_path.is_relative_to(data_root):
            logger.error("Rejected snapshot load outside data directory: %s", resolved_path)
            return None

        with open(resolved_path) as f:
            snapshot = json.load(f)

        # Validate snapshot format
        required_fields = ["version", "tank_id", "frame", "metadata", "entities"]
        for field in required_fields:
            if field not in snapshot:
                logger.error(f"Invalid snapshot: missing field '{field}'")
                return None

        # Log version info for debugging
        version = snapshot.get("version", "unknown")
        if version != SCHEMA_VERSION:
            logger.info(f"Loading snapshot with schema version {version} (current: {SCHEMA_VERSION})")

        logger.info(
            f"Loaded snapshot for tank {snapshot['tank_id'][:8]} "
            f"from {Path(snapshot_path).name} ({len(snapshot['entities'])} entities)"
        )
        return snapshot

    except Exception as e:
        logger.error(f"Failed to load snapshot {snapshot_path}: {e}", exc_info=True)
        return None


def restore_tank_from_snapshot(snapshot: Dict[str, Any], target_world: Any) -> bool:
    """Restore a tank's state from snapshot data.

    Args:
        snapshot: Snapshot data dictionary
        target_world: TankWorld instance to restore into

    Returns:
        True if restoration succeeded, False otherwise
    """
    try:
        from backend.entity_transfer import deserialize_entity
        from core.entities import Food, PlantNectar

        def _infer_entity_type(entity_data: Dict[str, Any]) -> Optional[str]:
            # Regression-safe inference for snapshots created during a brief window where
            # entity dicts were missing their `type` field.
            if "species" in entity_data and "genome_data" in entity_data:
                return "fish"
            if "root_spot_id" in entity_data and "genome_data" in entity_data:
                return "plant"
            return None

        # Clear existing entities
        target_world.engine.entities_list.clear()
        if target_world.engine.environment:
            target_world.engine.environment.spatial_grid.clear()

        # Reset root spots
        if hasattr(target_world.engine, "root_spot_manager") and target_world.engine.root_spot_manager:
            for spot in target_world.engine.root_spot_manager.spots:
                spot.release()

        # Restore entities
        from core.entities.plant import Plant

        # Track restored plants for nectar association
        plants_by_id = {}
        nectar_data_list = []
        restored_count = 0

        # Pass 1: Restore non-nectar entities
        for entity_data in snapshot["entities"]:
            entity_type = entity_data.get("type") or _infer_entity_type(entity_data)
            
            if entity_type and "type" not in entity_data:
                entity_data["type"] = entity_type

            if entity_type == "plant_nectar":
                nectar_data_list.append(entity_data)
                continue

            if entity_type in ("fish", "plant"):
                # Use existing deserialization logic
                entity = deserialize_entity(entity_data, target_world)
                if entity:
                    # Fix for ID mismatch: Restore original ID for consistency (critical for Nectar->Plant links)
                    if isinstance(entity, Plant) and "id" in entity_data:
                        entity.plant_id = entity_data["id"]
                        # Ensure plant_manager's ID counter is higher than this ID to avoid collisions
                        plant_manager = getattr(target_world.engine, "plant_manager", None)
                        if plant_manager is not None and hasattr(plant_manager, "_next_plant_id"):
                            if entity.plant_id >= plant_manager._next_plant_id:
                                plant_manager._next_plant_id = entity.plant_id + 1

                    target_world.engine.add_entity(entity)
                    restored_count += 1
                    if isinstance(entity, Plant):
                        plants_by_id[entity.plant_id] = entity

            elif entity_type == "food":
                # Restore food - check if it's live food
                from core.entities.resources import LiveFood

                food_type = entity_data["food_type"]
                x = entity_data["x"]
                y = entity_data["y"]

                if food_type == "live":
                    # Create LiveFood instance to preserve movement behavior
                    food = LiveFood(
                        environment=target_world.engine.environment,
                        x=x,
                        y=y,
                    )
                else:
                    # Regular stationary food
                    food = Food(
                        x=x,
                        y=y,
                        food_type=food_type,
                        environment=target_world.engine.environment,
                    )

                food.energy = entity_data["energy"]
                target_world.engine.add_entity(food)
                restored_count += 1

            elif entity_type == "castle":
                # Restore castle
                from core.entities.base import Castle

                castle = Castle(
                    environment=target_world.engine.environment,
                    x=entity_data["x"],
                    y=entity_data["y"],
                )
                # Restore size if it was saved
                if "width" in entity_data and "height" in entity_data:
                    castle.set_size(entity_data["width"], entity_data["height"])
                target_world.engine.add_entity(castle)
                restored_count += 1

            elif entity_type == "crab":
                # Restore crab
                from core.entities.predators import Crab
                from core.genetics import Genome

                # Reconstruct genome - old saves may have deprecated fields, just use size and color
                genome_data = entity_data.get("genome", {})
                # Create genome using random() then override with saved values
                # Use a seeded RNG for determinism during restoration
                import random as pyrandom
                restore_rng = pyrandom.Random(entity_data.get("x", 0) + entity_data.get("y", 0))
                genome = Genome.random(rng=restore_rng)
                genome.physical.size_modifier.value = genome_data.get("size_modifier", 1.0)
                genome.physical.color_hue.value = genome_data.get("color_hue", 0.5)

                crab = Crab(
                    environment=target_world.engine.environment,
                    genome=genome,
                    x=entity_data["x"],
                    y=entity_data["y"],
                )
                crab.energy = entity_data.get("energy", crab.max_energy)
                crab.max_energy = entity_data.get("max_energy", crab.max_energy)
                crab.hunt_cooldown = entity_data.get("hunt_cooldown", 0)
                target_world.engine.add_entity(crab)
                restored_count += 1

        # Pass 2: Restore nectar
        for entity_data in nectar_data_list:
            source_plant_id = entity_data.get("source_plant_id")
            source_plant = plants_by_id.get(source_plant_id)

            if source_plant:
                nectar = PlantNectar(
                    x=entity_data["x"],
                    y=entity_data["y"],
                    source_plant=source_plant,
                    environment=target_world.engine.environment,
                )
                nectar.energy = entity_data["energy"]
                target_world.engine.add_entity(nectar)
                restored_count += 1
            else:
                logger.warning(f"Skipping nectar restoration: missing source plant {source_plant_id}")

        # Restore frame number
        target_world.engine.frame_count = snapshot["frame"]

        # Restore ecosystem statistics
        if "ecosystem" in snapshot:
            eco = target_world.engine.ecosystem
            eco_data = snapshot["ecosystem"]
            eco.total_births = eco_data.get("total_births", 0)
            eco.total_deaths = eco_data.get("total_deaths", 0)
            eco.current_generation = eco_data.get("current_generation", 0)
            if "death_causes" in eco_data:
                eco.death_causes.clear()
                eco.death_causes.update(eco_data["death_causes"])
            if "poker_stats" in eco_data:
                eco.total_fish_poker_games = eco_data["poker_stats"].get("total_fish_games", 0)
                eco.total_plant_poker_games = eco_data["poker_stats"].get("total_plant_games", 0)
            # Restore lineage log for phylogenetic tree
            if "lineage_log" in eco_data:
                eco.lineage.lineage_log = list(eco_data["lineage_log"])
                logger.debug(f"Restored {len(eco.lineage.lineage_log)} lineage records")

        # Restore paused state
        if "paused" in snapshot:
            target_world.paused = snapshot["paused"]

        logger.info(
            f"Restored tank {snapshot['tank_id'][:8]} to frame {snapshot['frame']} "
            f"({restored_count} entities)"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to restore tank from snapshot: {e}", exc_info=True)
        return False


def list_tank_snapshots(tank_id: str) -> List[Dict[str, Any]]:
    """List all available snapshots for a tank.

    Args:
        tank_id: The tank identifier

    Returns:
        List of snapshot metadata (filename, timestamp, frame)
    """
    tank_dir = DATA_DIR / tank_id / "snapshots"
    if not tank_dir.exists():
        return []

    snapshots = []
    for snapshot_file in sorted(tank_dir.glob("snapshot_*.json"), reverse=True):
        try:
            # Read just the metadata without loading full state
            with open(snapshot_file) as f:
                data = json.load(f)
                snapshots.append({
                    "filename": snapshot_file.name,
                    "filepath": str(snapshot_file),
                    "saved_at": data.get("saved_at"),
                    "frame": data.get("frame"),
                    "entity_count": len(data.get("entities", [])),
                    "size_bytes": snapshot_file.stat().st_size,
                })
        except Exception as e:
            logger.warning(f"Failed to read snapshot {snapshot_file.name}: {e}")
            continue

    return snapshots


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


def delete_tank_data(tank_id: str) -> bool:
    """Delete all persisted data for a specific tank.

    Args:
        tank_id: The tank identifier

    Returns:
        True if the tank data directory was removed, False otherwise
    """

    tank_dir = DATA_DIR / tank_id
    try:
        if not tank_dir.exists():
            logger.info(f"No persisted data found for tank {tank_id[:8]}")
            return False

        shutil.rmtree(tank_dir)
        logger.info(f"Deleted persisted data for tank {tank_id[:8]}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete data for tank {tank_id[:8]}: {e}")
        return False


def cleanup_old_snapshots(tank_id: str, max_snapshots: int = 10) -> int:
    """Delete oldest snapshots beyond the retention limit.

    Args:
        tank_id: The tank identifier
        max_snapshots: Maximum number of snapshots to keep

    Returns:
        Number of snapshots deleted
    """
    snapshots = list_tank_snapshots(tank_id)
    if len(snapshots) <= max_snapshots:
        return 0

    # Delete oldest snapshots
    deleted = 0
    for snapshot in snapshots[max_snapshots:]:
        if delete_snapshot(snapshot["filepath"]):
            deleted += 1

    logger.info(f"Cleaned up {deleted} old snapshots for tank {tank_id[:8]}")
    return deleted


def get_latest_snapshot(tank_id: str) -> Optional[str]:
    """Get the path to the most recent snapshot for a tank.

    Args:
        tank_id: The tank identifier

    Returns:
        Path to the latest snapshot file, or None if no snapshots exist
    """
    snapshots = list_tank_snapshots(tank_id)
    if not snapshots:
        return None

    # Snapshots are sorted by newest first
    return snapshots[0]["filepath"]


def find_all_tank_snapshots() -> Dict[str, str]:
    """Find the latest snapshot for each tank that has saved data.

    Returns:
        Dictionary mapping tank_id to latest snapshot path
    """
    if not DATA_DIR.exists():
        return {}

    tank_snapshots = {}

    # Iterate through all tank directories
    for tank_dir in DATA_DIR.iterdir():
        if not tank_dir.is_dir():
            continue

        tank_id = tank_dir.name
        latest_snapshot = get_latest_snapshot(tank_id)

        if latest_snapshot:
            tank_snapshots[tank_id] = latest_snapshot
            logger.debug(f"Found snapshot for tank {tank_id[:8]}: {latest_snapshot}")

    logger.info(f"Found {len(tank_snapshots)} tanks with saved snapshots")
    return tank_snapshots
