"""Replay utilities (record/replay + snapshot fingerprinting).

This package provides:
- Stable snapshot fingerprinting for determinism regression detection
- A minimal JSONL replay format for recording/replaying steps and mode switches
"""

from core.replay.fingerprint import SnapshotFingerprinter, fingerprint_snapshot
from core.replay.fingerprint_stream import FingerprintStreamRecorder, compare_fingerprint_streams
from core.replay.jsonl import JsonlReplayReader, JsonlReplayWriter, ReplayFormatError

__all__ = [
    "FingerprintStreamRecorder",
    "JsonlReplayReader",
    "JsonlReplayWriter",
    "ReplayFormatError",
    "SnapshotFingerprinter",
    "compare_fingerprint_streams",
    "fingerprint_snapshot",
]
