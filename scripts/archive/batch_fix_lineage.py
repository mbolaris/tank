"""Batch-run the snapshot lineage fixer across data/tanks snapshots.

This script will scan all snapshot_*.json files under data/tanks and run
the same scan/fix logic as scripts/fix_lineage.py. For any snapshot that
has orphaned lineage records, it will write a fixed file with _fixed
suffix and then back up the original (add .bak) and replace it with the
fixed version. Changes are logged.

Run with: python scripts/batch_fix_lineage.py
"""

import importlib.util
import json
import logging
from pathlib import Path


def load_scan_function() -> callable:
    """Dynamically load `scan_and_fix_lineage` from scripts/fix_lineage.py."""
    fix_path = Path(__file__).parent / "fix_lineage.py"
    spec = importlib.util.spec_from_file_location("fix_lineage", str(fix_path))
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module.scan_and_fix_lineage


scan_and_fix_lineage = load_scan_function()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_snapshots(base: Path):
    for tank_dir in base.iterdir():
        if not tank_dir.is_dir():
            continue
        snap_dir = tank_dir / "snapshots"
        if not snap_dir.exists():
            continue
        yield from snap_dir.glob("snapshot_*.json")


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def process_snapshot(path: Path):
    logger.info("Scanning %s", path)
    data = load(path)

    # Find lineage_log as in fix_lineage.py
    lineage_log = None
    if isinstance(data, dict):
        if (
            "ecosystem" in data
            and isinstance(data["ecosystem"], dict)
            and "lineage_log" in data["ecosystem"]
        ):
            lineage_log = data["ecosystem"]["lineage_log"]
        elif "lineage_log" in data:
            lineage_log = data["lineage_log"]

    if lineage_log is None:
        logger.debug("No lineage_log found in %s", path)
        return 0

    fixed, orphan_count = scan_and_fix_lineage(lineage_log)
    if orphan_count == 0:
        logger.info("No orphans in %s", path)
        return 0

    # Prepare replacement data
    out = dict(data)
    if (
        "ecosystem" in out
        and isinstance(out["ecosystem"], dict)
        and "lineage_log" in out["ecosystem"]
    ):
        out["ecosystem"]["lineage_log"] = fixed
    elif "lineage_log" in out:
        out["lineage_log"] = fixed

    fixed_path = path.with_name(path.stem + "_fixed" + path.suffix)
    save(fixed_path, out)
    # Backup original and replace
    backup_path = path.with_suffix(path.suffix + ".bak")
    path.replace(backup_path)
    fixed_path.replace(path)

    logger.info("Fixed %d orphan(s) in %s (backup: %s)", orphan_count, path, backup_path)
    return orphan_count


def main():
    base = Path("data/tanks")
    if not base.exists():
        logger.error("No data/tanks directory found")
        return

    total_orphans = 0
    files_processed = 0
    for snap in find_snapshots(base):
        try:
            orphans = process_snapshot(snap)
            total_orphans += orphans
            files_processed += 1
        except Exception as e:
            logger.error("Error processing %s: %s", snap, e)

    logger.info(
        "Processed %d snapshot files. Total orphaned records fixed: %d",
        files_processed,
        total_orphans,
    )


if __name__ == "__main__":
    main()
