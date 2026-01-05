import logging
import shutil
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nuke")

DATA_DIR = Path("data/tanks")
KEEPER_ID = "e623dbd8-cb56-4672-ae46-eb3f87dc3df5"


def nuke():
    if not DATA_DIR.exists():
        logger.error("DATA_DIR not found!")
        return

    kept = False
    trash_dir = Path(f"data/tanks_trash_final_{int(time.time())}")

    # Identify keeper path
    keeper_path = DATA_DIR / KEEPER_ID

    if not keeper_path.exists():
        logger.error(f"Keeper {KEEPER_ID} not found! Scanning for alternatives...")
        # Fallback: keep the one with most snapshots?
        # For now, just list what we have
        for p in DATA_DIR.iterdir():
            logger.info(f"Found: {p.name}")
        return

    # Move EVERYTHING else to trash
    trash_dir.mkdir(parents=True, exist_ok=True)

    for p in DATA_DIR.iterdir():
        if p.name == KEEPER_ID:
            logger.info(f"Keeping {p.name}")
            kept = True
            continue

        logger.info(f"Trashing {p.name}")
        try:
            shutil.move(str(p), str(trash_dir / p.name))
        except Exception as e:
            logger.error(f"Failed to trash {p.name}: {e}")

    logger.info("Cleanup complete.")


if __name__ == "__main__":
    nuke()
