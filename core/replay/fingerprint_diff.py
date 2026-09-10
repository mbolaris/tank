"""Locate and explain the first divergence between two fingerprint streams.

The gate this feeds has a specific acceptance bar (docs/IMPROVEMENT_PROPOSALS.md
1.0): it must name the earliest divergent **frame, phase, entity, RNG stream
and state field**, because a gate that only reports "the digests differ" costs
the next agent the same multi-day bisect the entry already paid for once.

Streams are read defensively. Older v1 artifacts carry only whole-snapshot and
per-entity-type digests, so every richer field degrades to ``None`` rather than
failing - a two-year-old CI artifact is still worth comparing.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from core.simulation.pipeline import FRAME_ENTRY_STEP

__all__ = [
    "compare_fingerprint_streams",
    "format_divergence_report",
]

# What an identical-RNG / differing-snapshot pair means, and vice versa. This
# is the single most useful thing the report says: it splits "the arithmetic
# drifted" from "a decision changed", which need completely different fixes.
_VERDICT_FLOAT_DRIFT = "float_drift"
_VERDICT_RNG_DESYNC = "rng_desync"
_VERDICT_UNKNOWN = "unknown"

_VERDICT_NOTES = {
    _VERDICT_FLOAT_DRIFT: (
        "RNG states match at this checkpoint, so both runs made the same "
        "decisions and drew the same numbers; the difference is arithmetic. "
        "Look at platform libm (see docs/CROSS_PLATFORM_DIVERGENCE.md), not at "
        "control flow."
    ),
    _VERDICT_RNG_DESYNC: (
        "RNG states differ, so the runs have consumed different draw counts: a "
        "branch went the other way somewhere at or before this checkpoint. "
        "Look for the decision, not for float noise."
    ),
    _VERDICT_UNKNOWN: (
        "This stream predates RNG-state recording, so the float-drift vs "
        "RNG-desync question cannot be answered from it. Re-run the benchmark "
        "with --fingerprint-out to get it."
    ),
}


def compare_fingerprint_streams(left_path: str | Path, right_path: str | Path) -> dict[str, object]:
    """Return the first exact and rounded divergences between two streams."""
    left = _read_checkpoints(left_path)
    right = _read_checkpoints(right_path)
    frames = sorted(set(left) | set(right))
    rng_frame = _first_rng_divergence(left, right, frames)
    return {
        "exact": _first_divergence(left, right, frames, "exact", rng_frame),
        "rounded": _first_divergence(left, right, frames, "rounded", rng_frame),
        "first_rng_divergence_frame": rng_frame,
        "environment_delta": _environment_delta(left_path, right_path),
    }


def _read_checkpoints(path: str | Path) -> dict[int, dict[str, object]]:
    checkpoints: dict[int, dict[str, object]] = {}
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if record.get("type") == "checkpoint":
                checkpoints[int(record["frame"])] = record
    return checkpoints


def _read_header(path: str | Path) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if record.get("type") == "header":
                return dict(record)
            break
    return {}


def _environment_delta(left_path: str | Path, right_path: str | Path) -> dict[str, object]:
    """Report manifest keys that differ, flattened one level.

    Two runs of identical code that diverge are, by definition, being told
    something different by their environment, so the first question is always
    "what was different about the machines".
    """
    left = _read_header(left_path).get("environment", {})
    right = _read_header(right_path).get("environment", {})
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return {}
    delta: dict[str, object] = {}
    for key in sorted(set(left) | set(right)):
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value != right_value:
            delta[key] = {"left": left_value, "right": right_value}
    return delta


def _rng_map(record: Mapping[str, object] | None) -> dict[str, object] | None:
    if record is None:
        return None
    raw = record.get("rng")
    return dict(raw) if isinstance(raw, Mapping) else None


def _first_rng_divergence(
    left: Mapping[int, dict[str, object]],
    right: Mapping[int, dict[str, object]],
    frames: list[int],
) -> int | None:
    for frame in frames:
        left_rng = _rng_map(left.get(frame))
        right_rng = _rng_map(right.get(frame))
        if left_rng is None or right_rng is None:
            continue
        if left_rng != right_rng:
            return frame
    return None


def _rng_section(
    left_record: Mapping[str, object],
    right_record: Mapping[str, object],
    frame: int,
    rng_frame: int | None,
) -> dict[str, object]:
    left_rng = _rng_map(left_record)
    right_rng = _rng_map(right_record)
    if left_rng is None or right_rng is None:
        return {"verdict": _VERDICT_UNKNOWN, "note": _VERDICT_NOTES[_VERDICT_UNKNOWN]}

    names = sorted(set(left_rng) | set(right_rng))
    diverged = [name for name in names if left_rng.get(name) != right_rng.get(name)]
    matched = [name for name in names if name not in diverged]
    verdict = _VERDICT_RNG_DESYNC if diverged else _VERDICT_FLOAT_DRIFT
    section: dict[str, object] = {
        "verdict": verdict,
        "note": _VERDICT_NOTES[verdict],
        "diverged": diverged,
        "matched": matched,
    }
    if rng_frame is not None and rng_frame < frame:
        section["first_rng_divergence_frame"] = rng_frame
        section["note"] = (
            f"{_VERDICT_NOTES[verdict]} RNG states already differed at frame "
            f"{rng_frame}, before this snapshot divergence - start there."
        )
    return section


def _phase_rows(record: Mapping[str, object] | None) -> list[dict[str, object]]:
    if record is None:
        return []
    raw = record.get("phases")
    return [dict(row) for row in raw] if isinstance(raw, list) else []


def _first_divergent_phase(
    left_record: Mapping[str, object],
    right_record: Mapping[str, object],
    precision: str,
) -> dict[str, object]:
    """Name the pipeline step whose completion first shows the difference."""
    left_rows = _phase_rows(left_record)
    right_rows = _phase_rows(right_record)
    if not left_rows or not right_rows:
        return {"phase": None, "phase_source": "unavailable"}

    # The frame-entry row is recorded before any step runs, so a difference
    # already visible there was inherited, not caused here.
    if (
        left_rows[0].get("step") == FRAME_ENTRY_STEP
        and right_rows
        and right_rows[0].get("step") == FRAME_ENTRY_STEP
        and left_rows[0].get(precision) != right_rows[0].get(precision)
    ):
        return {
            "phase": None,
            "phase_source": "carried_in_from_earlier_frame",
            "phase_hint": (
                "The frames differed before this one began, so the phase is in "
                "an earlier frame. Re-run both sides with --fingerprint-every 1 "
                "over the preceding window to land on the exact phase."
            ),
        }

    for index, left_row in enumerate(left_rows):
        if index >= len(right_rows):
            return {"phase": str(left_row.get("step")), "phase_source": "step_count_mismatch"}
        right_row = right_rows[index]
        if left_row.get("step") != right_row.get("step"):
            return {"phase": str(left_row.get("step")), "phase_source": "step_order_mismatch"}
        if left_row.get(precision) != right_row.get(precision):
            return {"phase": str(left_row.get("step")), "phase_source": "step_digests"}
    # Every step of this frame agreed, so the state that differs was already
    # different when the frame began - the divergence is older than this frame.
    return {"phase": None, "phase_source": "carried_in_from_earlier_frame"}


def _detail_map(parts: Mapping[str, object], key: str) -> dict[str, object]:
    raw = parts.get(key)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _entity_section(
    left_parts: Mapping[str, object], right_parts: Mapping[str, object]
) -> dict[str, object] | None:
    left_entities = _detail_map(left_parts, "entities_by_id")
    right_entities = _detail_map(right_parts, "entities_by_id")
    if not left_entities and not right_entities:
        return None

    changed = sorted(
        name
        for name in set(left_entities) & set(right_entities)
        if left_entities[name] != right_entities[name]
    )
    return {
        "changed": changed,
        "only_left": sorted(set(left_entities) - set(right_entities)),
        "only_right": sorted(set(right_entities) - set(left_entities)),
        "changed_count": len(changed),
    }


def _field_section(
    left_parts: Mapping[str, object], right_parts: Mapping[str, object]
) -> dict[str, list[str]] | None:
    left_fields = _detail_map(left_parts, "fields")
    right_fields = _detail_map(right_parts, "fields")
    if not left_fields and not right_fields:
        return None

    fields: dict[str, list[str]] = {}
    for entity_type in sorted(set(left_fields) | set(right_fields)):
        left_type = left_fields.get(entity_type)
        right_type = right_fields.get(entity_type)
        left_type = left_type if isinstance(left_type, Mapping) else {}
        right_type = right_type if isinstance(right_type, Mapping) else {}
        differing = sorted(
            name
            for name in set(left_type) | set(right_type)
            if left_type.get(name) != right_type.get(name)
        )
        if differing:
            fields[entity_type] = differing
    return fields


def _first_divergence(
    left: Mapping[int, dict[str, object]],
    right: Mapping[int, dict[str, object]],
    frames: list[int],
    precision: str,
    rng_frame: int | None,
) -> dict[str, object] | None:
    if not frames:
        return {"frame": None, "reason": "no_checkpoints"}

    for frame in frames:
        left_record = left.get(frame)
        right_record = right.get(frame)
        if left_record is None or right_record is None:
            return {"frame": frame, "reason": "missing_checkpoint"}

        left_parts = _parts(left_record, precision)
        right_parts = _parts(right_record, precision)
        if left_parts.get("snapshot") == right_parts.get("snapshot"):
            continue

        left_types = _detail_map(left_parts, "entity_types")
        right_types = _detail_map(right_parts, "entity_types")
        divergence: dict[str, object] = {
            "frame": frame,
            "reason": "fingerprint_mismatch",
            "differing_parts": [
                name
                for name in ("world", "entities")
                if left_parts.get(name) != right_parts.get(name)
            ],
            "differing_entity_types": sorted(
                name
                for name in set(left_types) | set(right_types)
                if left_types.get(name) != right_types.get(name)
            ),
            "left_entity_counts": left_record.get("entity_counts", {}),
            "right_entity_counts": right_record.get("entity_counts", {}),
            "rng": _rng_section(left_record, right_record, frame, rng_frame),
        }
        divergence.update(_first_divergent_phase(left_record, right_record, precision))

        entities = _entity_section(left_parts, right_parts)
        if entities is not None:
            divergence["entities_detail"] = entities
        fields = _field_section(left_parts, right_parts)
        if fields is not None:
            divergence["fields"] = fields
        return divergence
    return None


def _parts(record: Mapping[str, object], precision: str) -> dict[str, object]:
    raw = record.get(precision)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _format_one(label: str, divergence: Mapping[str, object] | None) -> list[str]:
    if divergence is None:
        return [f"{label}: identical"]
    if divergence.get("reason") != "fingerprint_mismatch":
        return [f"{label}: {divergence.get('reason')} (frame {divergence.get('frame')})"]

    lines = [f"{label}: diverged at frame {divergence['frame']}"]
    phase = divergence.get("phase")
    source = divergence.get("phase_source")
    lines.append(f"  phase:  {phase if phase else '(unattributed)'}  [{source}]")
    hint = divergence.get("phase_hint")
    if hint:
        lines.append(f"          {hint}")

    rng = divergence.get("rng", {})
    if isinstance(rng, Mapping):
        diverged = rng.get("diverged") or []
        streams = ", ".join(diverged) if diverged else "none"
        lines.append(f"  rng:    verdict={rng.get('verdict')} diverged_streams={streams}")
        lines.append(f"          {rng.get('note', '')}")

    entities = divergence.get("entities_detail")
    if isinstance(entities, Mapping):
        changed = entities.get("changed") or []
        shown = ", ".join(str(name) for name in changed[:10])
        more = "" if len(changed) <= 10 else f" (+{len(changed) - 10} more)"
        lines.append(f"  entity: {entities.get('changed_count', 0)} changed: {shown}{more}")
        for side in ("only_left", "only_right"):
            missing = entities.get(side) or []
            if missing:
                lines.append(f"          {side}: {', '.join(str(n) for n in missing[:10])}")

    fields = divergence.get("fields")
    if isinstance(fields, Mapping) and fields:
        for entity_type, names in fields.items():
            listed = names if isinstance(names, list) else []
            lines.append(f"  field:  {entity_type}: {', '.join(str(n) for n in listed)}")
    elif fields is not None:
        lines.append("  field:  (no per-field difference; check world-level keys)")

    raw_types = divergence.get("differing_entity_types")
    types = raw_types if isinstance(raw_types, list) else []
    if types:
        lines.append(f"  types:  {', '.join(str(name) for name in types)}")
    return lines


def format_divergence_report(comparison: Mapping[str, object]) -> str:
    """Render a comparison as the five-part identification, for humans."""

    def section(name: str) -> Mapping[str, object] | None:
        value = comparison.get(name)
        return value if isinstance(value, Mapping) else None

    lines: list[str] = []
    lines.extend(_format_one("exact  ", section("exact")))
    lines.append("")
    lines.extend(_format_one("rounded", section("rounded")))

    delta = comparison.get("environment_delta")
    if isinstance(delta, Mapping) and delta:
        lines.append("")
        lines.append("environment differences:")
        for key, values in delta.items():
            lines.append(f"  {key}: {values.get('left')!r} != {values.get('right')!r}")
    return "\n".join(lines)
