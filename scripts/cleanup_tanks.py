
import logging
import shutil
import warnings
from pathlib import Path
from typing import Dict, Any

# Suppress DeprecationWarnings from simplejson/json interaction if any
warnings.simplefilter('ignore', DeprecationWarning)

from backend.tank_persistence import list_tank_snapshots, load_tank_state, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

BACKUP_DIR = Path("data/tanks_backup")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def analyze_tanks():
    if not DATA_DIR.exists():
        logger.error(f"DATA_DIR {DATA_DIR} does not exist!")
        return

    tanks = []
    
    logger.info("Analyzing tanks in data/tanks/...")
    
    for tank_dir in DATA_DIR.iterdir():
        if not tank_dir.is_dir():
            continue
            
        tank_id = tank_dir.name
        snapshots = list_tank_snapshots(tank_id)
        
        if not snapshots:
            logger.warning(f"Tank {tank_id[:8]}: No snapshots found.")
            tanks.append({
                "id": tank_id,
                "path": tank_dir,
                "score": -1,
                "reason": "empty"
            })
            continue

        latest_snap_meta = snapshots[0]
        try:
            # We don't load the full state to be fast, unless needed. 
            # list_tank_snapshots already returns entity_count from metadata read.
            entity_count = latest_snap_meta.get("entity_count", 0)
            frame = latest_snap_meta.get("frame", 0)
            
            # Simple heuristic: Older tanks with more entities are likely "better" 
            # (or newer tanks with entities? Usually users want the one they were working on)
            # Actually, "proliferation" means new tanks are created EMPTY (or default).
            # Default tank usually has ~13-30 entities.
            
            # If we see multiple tanks, we prefer the one with the HIGHEST frame count (most progress).
            score = frame + (entity_count * 0.1) 
            
            tanks.append({
                "id": tank_id,
                "path": tank_dir,
                "score": score,
                "frame": frame,
                "entities": entity_count,
                "reason": f"Frame {frame}, Entities {entity_count}"
            })
        except Exception as e:
            logger.error(f"Error analyzing {tank_id}: {e}")
            tanks.append({"id": tank_id, "path": tank_dir, "score": -1, "reason": "error"})

    # Sort by score descending
    tanks.sort(key=lambda x: x["score"], reverse=True)
    
    if not tanks:
        logger.info("No tanks found.")
        return

    logger.info(f"Found {len(tanks)} tanks:")
    for i, t in enumerate(tanks):
        marker = " [KEEP]" if i == 0 else " [ARCHIVE]"
        logger.info(f"{marker} {t['id'][:8]}: {t['reason']} (Score: {t['score']})")

    # Execute Cleanup
    keeper = tanks[0]
    to_archive = tanks[1:]
    
    if not to_archive:
        logger.info("Only one tank found. No cleanup needed.")
        return

    logger.info("\nMoving duplicate tanks to data/tanks_backup/...")
    
    for t in to_archive:
        src = t["path"]
        dst = BACKUP_DIR / t["id"]
        if dst.exists():
            shutil.rmtree(dst) # Overwrite backup if exists
        
        logger.info(f"Moving {t['id'][:8]}...")
        shutil.move(str(src), str(dst))
        
    logger.info("\nCleanup complete!")
    logger.info(f"Kept tank: {keeper['id']}")
    logger.info(f"Archived {len(to_archive)} tanks to {BACKUP_DIR}")

if __name__ == "__main__":
    analyze_tanks()
