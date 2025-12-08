"""Utility to scan and optionally fix orphaned lineage records.

Usage:
  python scripts/fix_lineage.py --file path/to/snapshot.json [--fix]

The script will look for a top-level `ecosystem` object containing `lineage_log`.
If `--fix` is provided, it will write a new file with `_fixed` suffix containing
the sanitized lineage where missing parents are remapped to "root" and the
original parent is preserved in `_original_parent_id`.
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scan_and_fix_lineage(lineage_log: List[Dict[str, Any]]) -> (List[Dict[str, Any]], int):
    valid_ids = {rec.get("id") for rec in lineage_log}
    valid_ids.add("root")
    fixed = []
    orphan_count = 0

    for rec in lineage_log:
        parent_id = rec.get("parent_id", "root")
        if parent_id not in valid_ids:
            orphan_count += 1
            new_rec = dict(rec)
            new_rec["_original_parent_id"] = parent_id
            new_rec["parent_id"] = "root"
            fixed.append(new_rec)
        else:
            fixed.append(dict(rec))

    return fixed, orphan_count


def load_snapshot(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(path: Path, data: Dict[str, Any]):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help="Path to snapshot JSON file")
    p.add_argument("--fix", action="store_true", help="Write out fixed snapshot")
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        logger.error("File not found: %s", path)
        raise SystemExit(1)

    data = load_snapshot(path)

    # Heuristics: accept three formats:
    # 1) Top-level list (the /api/lineage endpoint returns a list)
    # 2) dict with key 'lineage_log'
    # 3) dict with 'ecosystem': {'lineage_log': [...]}
    lineage_log = None
    data_is_list = False
    if isinstance(data, list):
        lineage_log = data
        data_is_list = True
    elif isinstance(data, dict):
        if "ecosystem" in data and isinstance(data["ecosystem"], dict) and "lineage_log" in data["ecosystem"]:
            lineage_log = data["ecosystem"]["lineage_log"]
        elif "lineage_log" in data:
            lineage_log = data["lineage_log"]

    if lineage_log is None:
        logger.error("Could not find lineage_log in snapshot file")
        raise SystemExit(2)

    fixed, orphan_count = scan_and_fix_lineage(lineage_log)
    logger.info("Found %d orphaned lineage record(s)", orphan_count)

    if args.fix:
        # Write fixed data back into snapshot structure. Respect original shape
        if data_is_list:
            out = fixed
        else:
            out = dict(data)
            if "ecosystem" in out and isinstance(out["ecosystem"], dict) and "lineage_log" in out["ecosystem"]:
                out["ecosystem"]["lineage_log"] = fixed
            elif "lineage_log" in out:
                out["lineage_log"] = fixed

        out_path = path.with_name(path.stem + "_fixed" + path.suffix)
        save_snapshot(out_path, out)
        logger.info("Wrote fixed snapshot to %s", out_path)


if __name__ == "__main__":
    main()
