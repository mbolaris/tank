"""Lineage tracker restoration for same-world snapshot restore.

Split out of world_persistence.py (which stays under the god-class line
ratchet) since this is a self-contained concern: rebuilding LineageTracker
state after a snapshot restore, including a fallback for older snapshots
that predate the explicit ``lineage_log`` field.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def restore_lineage_state(snapshot: dict[str, Any], engine: Any) -> None:
    """Restore lineage tracker state from a snapshot.

    Current snapshots persist the lineage log explicitly. Older snapshots only
    have living fish entities, so we rebuild a partial tree and add placeholder
    ancestors for missing saved parent IDs instead of flattening children to root.
    """
    ecosystem = getattr(engine, "ecosystem", None)
    lineage = getattr(ecosystem, "lineage", None)
    if lineage is None:
        return

    raw_records = snapshot.get("lineage_log")
    if isinstance(raw_records, list):
        records = [dict(record) for record in raw_records if isinstance(record, dict)]
    else:
        records = _build_lineage_from_restored_fish(engine)

    lineage.lineage_log = _with_missing_parent_placeholders(records)
    alive_fish_ids = {
        entity.fish_id
        for entity in getattr(engine, "entities_list", [])
        if getattr(entity, "snapshot_type", None) == "fish"
    }
    lineage.update_alive_fish(alive_fish_ids)


def _build_lineage_from_restored_fish(engine: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    frame = getattr(engine, "frame_count", 0)

    for entity in getattr(engine, "entities_list", []):
        if getattr(entity, "snapshot_type", None) != "fish":
            continue

        color = "#00ff00"
        genome = getattr(entity, "genome", None)
        if genome is not None and hasattr(genome, "get_color_tint"):
            try:
                r, g, b = genome.get_color_tint()
                color = f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                logger.debug("Failed to derive restored fish lineage color", exc_info=True)

        records.append(
            {
                "id": str(entity.fish_id),
                "parent_id": (
                    str(entity.parent_id)
                    if getattr(entity, "parent_id", None) is not None
                    else "root"
                ),
                "generation": getattr(entity, "generation", 0),
                "algorithm": _get_fish_algorithm_name(entity),
                "color": color,
                "birth_time": frame,
                "tank_name": getattr(getattr(entity, "environment", None), "tank_name", None),
            }
        )

    return records


def _with_missing_parent_placeholders(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid_ids = {
        str(record["id"])
        for record in records
        if isinstance(record, dict) and record.get("id") is not None
    }
    valid_ids.add("root")

    placeholders: dict[str, dict[str, Any]] = {}
    for record in records:
        parent_id_raw = record.get("parent_id", "root")
        parent_id = str(parent_id_raw) if parent_id_raw is not None else "root"
        if parent_id in valid_ids or parent_id in placeholders:
            continue

        try:
            generation = max(0, int(record.get("generation", 1)) - 1)
        except (TypeError, ValueError):
            generation = 0

        placeholders[parent_id] = {
            "id": parent_id,
            "parent_id": "root",
            "generation": generation,
            "algorithm": "Restored ancestor",
            "color": "#94a3b8",
            "birth_time": record.get("birth_time", 0),
            "tank_name": record.get("tank_name"),
            "is_placeholder": True,
        }

    if placeholders:
        logger.info(
            "Lineage: Added %d restored ancestor placeholder(s) for snapshot parents",
            len(placeholders),
        )

    return [*placeholders.values(), *records]


def _get_fish_algorithm_name(fish: Any) -> str:
    extractor = getattr(fish, "_extract_algorithm_name", None)
    behavior = getattr(getattr(getattr(fish, "genome", None), "behavioral", None), "behavior", None)
    behavior_value = getattr(behavior, "value", None)
    behavior_id = getattr(behavior_value, "behavior_id", None)
    if callable(extractor) and behavior_id:
        return str(extractor(behavior_id))
    return "Unknown"


def advance_fish_id_counter(engine: Any) -> None:
    ecosystem = getattr(engine, "ecosystem", None)
    if ecosystem is None:
        return

    fish_ids = [
        entity.fish_id
        for entity in getattr(engine, "entities_list", [])
        if getattr(entity, "snapshot_type", None) == "fish"
    ]
    if fish_ids:
        ecosystem.next_fish_id = max(ecosystem.next_fish_id, max(fish_ids) + 1)
