"""Filesystem layout for persisted world data.

Kept separate from ``world_persistence`` so the path-safety rule lives in one
small, obvious place rather than inside the much larger snapshot module.
"""

from pathlib import Path

# Base directory for all world data
DATA_DIR = Path("data/worlds")


def world_data_dir(world_id: str, base: Path | None = None) -> Path:
    """Resolve a world's data directory, refusing ids that escape ``base``.

    World ids are server-generated UUIDs today, so this is defence in depth
    rather than a fix for a live bug — but these paths feed ``shutil.rmtree``
    and file writes, and a future caller that forwards a client-supplied id
    (a path parameter decodes ``..%2F..`` straight into a traversal) would
    turn that into arbitrary deletion. Cheaper to close here than to rely on
    every caller remembering.

    ``base`` is passed explicitly by callers that keep their own rebindable
    ``DATA_DIR`` (the test suite redirects it at runtime to avoid writing into
    the real repo), so validation stays here without capturing the directory.
    """
    if not world_id or world_id in (".", ".."):
        raise ValueError(f"Invalid world id: {world_id!r}")

    candidate = Path(world_id)
    if candidate.is_absolute() or len(candidate.parts) != 1 or candidate.name != world_id:
        raise ValueError(f"Invalid world id: {world_id!r}")

    return (DATA_DIR if base is None else base) / world_id
