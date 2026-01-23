from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class SnapshotFingerprinter:
    """Compute stable fingerprints for JSON-compatible snapshots."""

    digest_size: int = 16
    algorithm: str = "blake2b"
    float_precision: int | None = 6
    non_deterministic_keys: frozenset[str] = frozenset(
        {
            # Wall-clock / runtime performance
            "elapsed_real_time",
            "simulation_speed",
            # Common timestamp-ish fields (best-effort)
            "timestamp",
            "wall_time",
            "created_at",
            "updated_at",
        }
    )

    def fingerprint(self, snapshot: Mapping[str, Any]) -> str:
        canonical = canonicalize_for_fingerprint(
            snapshot,
            non_deterministic_keys=self.non_deterministic_keys,
            float_precision=self.float_precision,
        )
        payload = json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        if self.algorithm != "blake2b":
            raise ValueError(f"Unsupported fingerprint algorithm: {self.algorithm}")
        return hashlib.blake2b(payload, digest_size=self.digest_size).hexdigest()


def fingerprint_snapshot(snapshot: dict[str, Any]) -> str:
    """Convenience wrapper using default fingerprinter."""

    return SnapshotFingerprinter().fingerprint(snapshot)


def canonicalize_for_fingerprint(
    value: Any,
    non_deterministic_keys: Iterable[str] | None = None,
    float_precision: int | None = 6,
) -> Any:
    """Return a canonical, JSON-compatible structure for stable hashing.

    - Drops known non-deterministic keys anywhere in the structure.
    - Sorts dict keys.
    - Sorts lists of dicts by canonical JSON content to remove incidental ordering.
    """

    drop_keys = set(non_deterministic_keys or [])

    def _canon(v: Any) -> Any:
        if isinstance(v, float):
            if float_precision is None:
                return v
            return round(v, int(float_precision))

        if isinstance(v, Mapping):
            items: dict[str, Any] = {}
            for k, vv in v.items():
                if k in drop_keys:
                    continue
                items[str(k)] = _canon(vv)
            return {k: items[k] for k in sorted(items.keys())}

        if isinstance(v, (list, tuple)):
            canon_list = [_canon(x) for x in v]
            if canon_list and all(isinstance(x, Mapping) for x in canon_list):
                return sorted(canon_list, key=_canonical_json_for_sort)
            return canon_list

        return v

    return _canon(value)


def _canonical_json_for_sort(mapping: Mapping[str, Any]) -> str:
    # mapping is expected to be canonical already (keys sorted recursively).
    return json.dumps(
        mapping,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
