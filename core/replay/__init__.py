"""Replay utilities (record/replay + snapshot fingerprinting).

This package provides:
- Stable snapshot fingerprinting for determinism regression detection
- A minimal JSONL replay format for recording/replaying steps and mode switches
"""

from core.replay.fingerprint import SnapshotFingerprinter, fingerprint_snapshot
from core.replay.jsonl import JsonlReplayReader, JsonlReplayWriter, ReplayFormatError

__all__ = [
    "JsonlReplayReader",
    "JsonlReplayWriter",
    "ReplayFormatError",
    "SnapshotFingerprinter",
    "fingerprint_snapshot",
]
