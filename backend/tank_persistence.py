"""Tank state persistence for Tank World Net.

This module handles saving and loading complete tank states to/from disk,
enabling durable simulations that can be resumed after restarts.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

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


def save_tank_state(tank_id: str, manager: Any) -> Optional[str]:
    """Save complete tank state to disk.

    Args:
        tank_id: The tank identifier
        manager: SimulationManager instance

    Returns:
        Filepath of saved snapshot, or None if save failed
    """
    try:
        from backend.entity_transfer import serialize_entity_for_transfer

        # Generate snapshot filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tank_dir = ensure_tank_directory(tank_id)
        snapshot_file = tank_dir / f"snapshot_{timestamp}.json"

        # Serialize all entities
        entities = []
        for entity in manager.world.engine.entities_list:
            serialized = serialize_entity_for_transfer(entity)
            if serialized:
                entities.append(serialized)
            else:
                # Also serialize Food and Nectar for complete state
                from core.entities import Food, PlantNectar

                if isinstance(entity, PlantNectar):
                    entities.append({
                        "type": "plant_nectar",
                        "id": id(entity),
                        "x": entity.pos.x,
                        "y": entity.pos.y,
                        "energy": entity.energy,
                        "source_plant_id": getattr(entity, "source_plant_id", None),
                        "source_plant_x": getattr(entity, "source_plant_x", entity.x),
                        "source_plant_y": getattr(entity, "source_plant_y", entity.y),
                    })
                elif isinstance(entity, Food):
                    entities.append({
                        "type": "food",
                        "id": id(entity),
                        "x": entity.pos.x,
                        "y": entity.pos.y,
                        "energy": entity.energy,
                        "food_type": entity.food_type,
                    })

        # Build complete snapshot
        snapshot = {
            "version": "1.0",
            "tank_id": tank_id,
            "saved_at": datetime.utcnow().isoformat(),
            "frame": manager.world.frame_count,
            "metadata": {
                "name": manager.tank_info.name,
                "description": manager.tank_info.description,
                "allow_transfers": manager.tank_info.allow_transfers,
                "is_public": manager.tank_info.is_public,
                "owner": manager.tank_info.owner,
                "seed": manager.tank_info.seed,
            },
            "entities": entities,
            "ecosystem": {
                "total_births": manager.world.engine.ecosystem.total_births,
                "total_deaths": manager.world.engine.ecosystem.total_deaths,
                "current_generation": manager.world.engine.ecosystem.current_generation,
                "death_causes": dict(manager.world.engine.ecosystem.death_causes),
                "poker_stats": {
                    "total_fish_games": manager.world.engine.ecosystem.total_fish_poker_games,
                    "total_plant_games": manager.world.engine.ecosystem.total_plant_poker_games,
                },
            },
            "paused": manager.world.paused,
        }

        # Write to file
        with open(snapshot_file, "w") as f:
            json.dump(snapshot, f, indent=2)

        logger.info(f"Saved tank {tank_id[:8]} state to {snapshot_file.name} ({len(entities)} entities)")
        return str(snapshot_file)

    except Exception as e:
        logger.error(f"Failed to save tank {tank_id[:8]} state: {e}", exc_info=True)
        return None


def load_tank_state(snapshot_path: str) -> Optional[Dict[str, Any]]:
    """Load tank state from a snapshot file.

    Args:
        snapshot_path: Path to the snapshot JSON file

    Returns:
        Snapshot data dictionary, or None if load failed
    """
    try:
        with open(snapshot_path, "r") as f:
            snapshot = json.load(f)

        # Validate snapshot format
        required_fields = ["version", "tank_id", "frame", "metadata", "entities"]
        for field in required_fields:
            if field not in snapshot:
                logger.error(f"Invalid snapshot: missing field '{field}'")
                return None

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
        from core.entities.food import Food
        from core.entities.plant_nectar import PlantNectar

        # Clear existing entities
        target_world.engine.entities_list.clear()
        target_world.engine.spatial_grid.clear()

        # Restore entities
        restored_count = 0
        for entity_data in snapshot["entities"]:
            entity_type = entity_data.get("type")

            if entity_type in ("fish", "fractal_plant"):
                # Use existing deserialization logic
                entity = deserialize_entity(entity_data, target_world)
                if entity:
                    target_world.engine.add_entity(entity)
                    restored_count += 1

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
                        screen_width=target_world.engine.environment.width,
                        screen_height=target_world.engine.environment.height,
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

            elif entity_type == "plant_nectar":
                # Restore nectar
                nectar = PlantNectar(
                    x=entity_data["x"],
                    y=entity_data["y"],
                    energy=entity_data["energy"],
                    environment=target_world.engine.environment,
                )
                # Restore nectar source plant info if available
                if "source_plant_x" in entity_data:
                    nectar.source_plant_x = entity_data["source_plant_x"]
                    nectar.source_plant_y = entity_data["source_plant_y"]
                if "source_plant_id" in entity_data:
                    nectar.source_plant_id = entity_data["source_plant_id"]
                target_world.engine.add_entity(nectar)
                restored_count += 1

        # Restore frame number
        target_world.frame = snapshot["frame"]

        # Restore ecosystem statistics
        if "ecosystem" in snapshot:
            eco = target_world.engine.ecosystem
            eco_data = snapshot["ecosystem"]
            eco.total_births = eco_data.get("total_births", 0)
            eco.total_deaths = eco_data.get("total_deaths", 0)
            eco.current_generation = eco_data.get("current_generation", 0)
            eco.death_causes = eco_data.get("death_causes", {})
            if "poker_stats" in eco_data:
                eco.total_fish_poker_games = eco_data["poker_stats"].get("total_fish_games", 0)
                eco.total_plant_poker_games = eco_data["poker_stats"].get("total_plant_games", 0)

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
            with open(snapshot_file, "r") as f:
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
