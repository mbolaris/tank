"""Crash-safe JSON files for the backend's on-disk state.

A plain ``open(path, "w")`` truncates the file first and fills it in as
``json.dump`` goes, so a process killed mid-write (Ctrl+C during an auto-save,
a crash, a power cut) leaves a file that is cut off partway through. For a
world snapshot that means the newest save is unreadable at the next start.

``write_json_atomic`` writes a sibling temp file and swaps it into place with
``os.replace``, which is atomic on both POSIX and Windows: a reader sees either
the old file or the new one, never half of one.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Prefix given to a file that could not be parsed, so globs like
#: ``snapshot_*.json`` stop picking it up while it stays on disk for inspection.
CORRUPT_PREFIX = "CORRUPT_"


def write_json_atomic(path: Path | str, data: Any, *, indent: int | None = 2) -> None:
    """Serialize ``data`` to ``path`` so the file is never left half-written.

    Raises whatever serialization or I/O raises; the destination is untouched
    in that case and the temp file is removed.
    """
    target = Path(path)
    # Same directory, so os.replace never has to cross a filesystem. The
    # ".tmp" suffix keeps it out of every "*.json" glob that reads these dirs.
    tmp = target.with_name(f"{target.name}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def quarantine_if_corrupt(path: Path, error: BaseException) -> Path | None:
    """Rename a file that failed to parse out of the way; return its new path.

    Without this a truncated snapshot is re-read and re-warned about on every
    start, and it can never age out because retention only counts files it can
    parse. Only a parse failure (``ValueError``, which covers
    ``json.JSONDecodeError`` and ``UnicodeDecodeError``) quarantines: an
    ``OSError`` such as a file briefly locked by another process on Windows
    says nothing about the contents, so that file is left alone. Returns None
    when nothing was renamed.
    """
    if not isinstance(error, ValueError):
        return None
    quarantined = path.with_name(f"{CORRUPT_PREFIX}{path.name}")
    try:
        path.replace(quarantined)
    except OSError as e:
        logger.error(f"Failed to quarantine unreadable file {path.name}: {e}")
        return None
    logger.warning(f"Quarantined unreadable file as {quarantined.name}")
    return quarantined
