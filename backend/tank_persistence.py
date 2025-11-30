"""Tank state persistence for Tank World Net.

This module handles saving and loading complete tank states to/from disk,
enabling durable simulations that can be resumed after restarts.

Schema Versioning:
    - Version 1.0: Original schema with genome.max_energy
    - Version 2.0: Removed genome.max_energy (now computed from size)
                   Fish max_energy is dynamically computed from fish.size
                   
Backwards Compatibility:
    - All genome fields use .get() with sensible defaults
    - Old saves with max_energy are loaded successfully (max_energy ignored)
    - New fields added to Genome will have defaults in Genome dataclass
"""

import json
import logging
import shutil
from datetime import datetime
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
            # Only attempt to serialize transferable entities using the transfer logic
            # This prevents "Cannot transfer entity of type X" warnings for things like Food, Crab, etc.
            from core.entities import Fish, FractalPlant

            if isinstance(entity, (Fish, FractalPlant)):
                serialized = serialize_entity_for_transfer(entity)
                if serialized:
                    entities.append(serialized)
            else:
                # Also serialize Food, Nectar, Castle, and Crab for complete state
                from core.entities import Food, PlantNectar
                from core.entities.base import Castle
                from core.entities.predators import Crab

                if isinstance(entity, PlantNectar):
                    entities.append({
                        "type": "plant_nectar",
                        "id": id(entity),
                        "x": entity.pos.x,
                        "y": entity.pos.y,
                        "energy": entity.energy,
                        "source_plant_id": getattr(entity, "source_plant_id", None),
                        "source_plant_x": getattr(entity, "source_plant_x", entity.pos.x),
                        "source_plant_y": getattr(entity, "source_plant_y", entity.pos.y),
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
                elif isinstance(entity, Castle):
                    entities.append({
                        "type": "castle",
                        "x": entity.pos.x,
                        "y": entity.pos.y,
                        "width": entity.width,
                        "height": entity.height,
                    })
                elif isinstance(entity, Crab):
                    # Serialize crab with genome
                    genome_data = {
                        "speed_modifier": entity.genome.speed_modifier,
                        "size_modifier": entity.genome.size_modifier,
                        "metabolism_rate": entity.genome.metabolism_rate,
                        "color_hue": entity.genome.color_hue,
                        "vision_range": entity.genome.vision_range,
                    }
                    entities.append({
                        "type": "crab",
                        "x": entity.pos.x,
                        "y": entity.pos.y,
                        "energy": entity.energy,
                        "max_energy": entity.max_energy,
                        "genome": genome_data,
                        "hunt_cooldown": entity.hunt_cooldown,
                    })

        # Build complete snapshot
        snapshot = {
            "version": SCHEMA_VERSION,
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
        
    Note:
        This function handles schema migrations automatically:
        - v1.0 snapshots: genome.max_energy will be ignored on load
        - v2.0 snapshots: max_energy computed from fish size
    """
    try:
        with open(snapshot_path) as f:
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

        # Clear existing entities
        target_world.engine.entities_list.clear()
        if target_world.engine.environment:
            target_world.engine.environment.spatial_grid.clear()

        # Reset root spots
        if hasattr(target_world.engine, "root_spot_manager") and target_world.engine.root_spot_manager:
            for spot in target_world.engine.root_spot_manager.spots:
                spot.release()

        # Restore entities
        from core.entities.fractal_plant import FractalPlant

        # Track restored plants for nectar association
        plants_by_id = {}
        nectar_data_list = []
        restored_count = 0

        # Pass 1: Restore non-nectar entities
        for entity_data in snapshot["entities"]:
            entity_type = entity_data.get("type")

            if entity_type == "plant_nectar":
                nectar_data_list.append(entity_data)
                continue

            if entity_type in ("fish", "fractal_plant"):
                # Use existing deserialization logic
                entity = deserialize_entity(entity_data, target_world)
                if entity:
                    target_world.engine.add_entity(entity)
                    restored_count += 1
                    if isinstance(entity, FractalPlant):
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

            elif entity_type == "castle":
                # Restore castle
                from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH
                from core.entities.base import Castle

                castle = Castle(
                    environment=target_world.engine.environment,
                    x=entity_data["x"],
                    y=entity_data["y"],
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
                )
                # Restore size if it was saved
                if "width" in entity_data and "height" in entity_data:
                    castle.set_size(entity_data["width"], entity_data["height"])
                target_world.engine.add_entity(castle)
                restored_count += 1

            elif entity_type == "crab":
                # Restore crab
                from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH
                from core.entities.predators import Crab
                from core.genetics import Genome

                # Reconstruct genome
                genome_data = entity_data.get("genome", {})
                genome = Genome(
                    speed_modifier=genome_data.get("speed_modifier", 1.0),
                    size_modifier=genome_data.get("size_modifier", 1.0),
                    metabolism_rate=genome_data.get("metabolism_rate", 1.0),
                    color_hue=genome_data.get("color_hue", 0.5),
                    vision_range=genome_data.get("vision_range", 100.0),
                )

                crab = Crab(
                    environment=target_world.engine.environment,
                    genome=genome,
                    x=entity_data["x"],
                    y=entity_data["y"],
                    screen_width=SCREEN_WIDTH,
                    screen_height=SCREEN_HEIGHT,
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
