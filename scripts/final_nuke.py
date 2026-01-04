import shutil
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nuke")

DATA_DIR = Path("data/tanks")
CONN_FILE = Path("data/connections.json")
KEEPER_ID = "e623dbd8-cb56-4672-ae46-eb3f87dc3df5"


def nuke():
    # 1. Delete connections.json
    if CONN_FILE.exists():
        try:
            os.remove(CONN_FILE)
            logger.info(f"Deleted {CONN_FILE}")
        except Exception as e:
            logger.error(f"Failed to delete connection file: {e}")
    else:
        logger.info("No connection file found.")

    # 2. Cleanup tanks
    if not DATA_DIR.exists():
        logger.error("DATA_DIR not found!")
        return

    kept = False
    for p in DATA_DIR.iterdir():
        if not p.is_dir():
            continue

        if p.name == KEEPER_ID:
            logger.info(f"KEEPING: {p.name}")
            kept = True
        else:
            logger.info(f"DELETING: {p.name}")
            try:
                shutil.rmtree(p)
            except Exception as e:
                logger.error(f"Failed to delete {p.name}: {e}")

    if not kept:
        logger.warning(f"WARNING: Keeper tank {KEEPER_ID} not found in {DATA_DIR}!")


if __name__ == "__main__":
    nuke()
