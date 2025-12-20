"""Transfer history tracking for Tank World Net.

This module logs all entity transfers between tanks and provides
query capabilities for the transfer history.
"""

import json
import logging
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# History storage
HISTORY_FILE = Path("data/transfers.log")
_transfer_history: Deque["TransferRecord"] = deque(maxlen=100)  # Keep last 100 in memory


@dataclass
class TransferRecord:
    """Record of a single entity transfer between tanks."""

    transfer_id: str
    timestamp: str  # ISO format
    entity_type: str  # "fish" or "plant"
    entity_old_id: int
    entity_new_id: Optional[int]
    source_tank_id: str
    source_tank_name: str
    destination_tank_id: str
    destination_tank_name: str
    success: bool
    error: Optional[str] = None
    generation: Optional[int] = None  # Fish generation (for tracking migration stats)


def log_transfer(
    entity_type: str,
    entity_old_id: int,
    entity_new_id: Optional[int],
    source_tank_id: str,
    source_tank_name: str,
    destination_tank_id: str,
    destination_tank_name: str,
    success: bool,
    error: Optional[str] = None,
    generation: Optional[int] = None,
) -> TransferRecord:
    """Log a transfer event.

    Args:
        entity_type: Type of entity ("fish" or "plant")
        entity_old_id: Entity ID in source tank
        entity_new_id: Entity ID in destination tank (None if failed)
        source_tank_id: Source tank identifier
        source_tank_name: Source tank display name
        destination_tank_id: Destination tank identifier
        destination_tank_name: Destination tank display name
        success: Whether transfer succeeded
        error: Error message if failed

    Returns:
        The created TransferRecord
    """
    record = TransferRecord(
        transfer_id=str(uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        entity_type=entity_type,
        entity_old_id=entity_old_id,
        entity_new_id=entity_new_id,
        source_tank_id=source_tank_id,
        source_tank_name=source_tank_name,
        destination_tank_id=destination_tank_id,
        destination_tank_name=destination_tank_name,
        success=success,
        error=error,
        generation=generation,
    )

    # Add to in-memory history
    _transfer_history.append(record)

    # Append to log file
    _append_to_log(record)

    status = "success" if success else f"failed: {error}"
    logger.info(
        f"Transfer {entity_type} #{entity_old_id} "
        f"{source_tank_name} → {destination_tank_name} ({status})"
    )

    return record


def _append_to_log(record: TransferRecord) -> None:
    """Append a transfer record to the persistent log file.

    Args:
        record: The transfer record to append
    """
    try:
        # Ensure log directory exists
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Append as JSON line
        with open(HISTORY_FILE, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    except Exception as e:
        logger.error(f"Failed to write transfer log: {e}")


def get_transfer_history(
    limit: int = 50,
    tank_id: Optional[str] = None,
    success_only: bool = False,
) -> List[Dict]:
    """Get transfer history records.

    Args:
        limit: Maximum number of records to return
        tank_id: Filter by tank ID (source or destination)
        success_only: Only return successful transfers

    Returns:
        List of transfer records (most recent first)
    """
    # Convert deque to list and reverse for most recent first
    records = list(_transfer_history)
    records.reverse()

    # Apply filters
    if tank_id:
        records = [
            r
            for r in records
            if r.source_tank_id == tank_id or r.destination_tank_id == tank_id
        ]

    if success_only:
        records = [r for r in records if r.success]

    # Apply limit
    records = records[:limit]

    # Convert to dicts
    return [asdict(r) for r in records]


def get_transfer_by_id(transfer_id: str) -> Optional[Dict]:
    """Get a specific transfer by ID.

    Args:
        transfer_id: The transfer UUID

    Returns:
        Transfer record dict, or None if not found
    """
    for record in _transfer_history:
        if record.transfer_id == transfer_id:
            return asdict(record)
    return None


def get_tank_transfer_stats(tank_id: str) -> Dict[str, int]:
    """Get transfer statistics for a tank.

    Args:
        tank_id: The tank identifier

    Returns:
        Dictionary with transfer counts
    """
    stats = {
        "transfers_in": 0,
        "transfers_out": 0,
        "transfers_in_success": 0,
        "transfers_out_success": 0,
        "transfers_in_failed": 0,
        "transfers_out_failed": 0,
    }

    for record in _transfer_history:
        if record.destination_tank_id == tank_id:
            stats["transfers_in"] += 1
            if record.success:
                stats["transfers_in_success"] += 1
            else:
                stats["transfers_in_failed"] += 1

        if record.source_tank_id == tank_id:
            stats["transfers_out"] += 1
            if record.success:
                stats["transfers_out_success"] += 1
            else:
                stats["transfers_out_failed"] += 1

    return stats


def load_history_from_file() -> int:
    """Load transfer history from the log file into memory.

    Returns:
        Number of records loaded
    """
    if not HISTORY_FILE.exists():
        logger.info("No transfer history file found, starting fresh")
        return 0

    try:
        loaded = 0
        with open(HISTORY_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    record = TransferRecord(**data)
                    _transfer_history.append(record)
                    loaded += 1
                except Exception as e:
                    logger.warning(f"Failed to parse history line: {e}")
                    continue

        logger.info(f"Loaded {loaded} transfer records from history file")
        return loaded

    except Exception as e:
        logger.error(f"Failed to load transfer history: {e}")
        return 0


def clear_history() -> None:
    """Clear all transfer history (memory and file).

    WARNING: This is destructive and cannot be undone.
    """
    _transfer_history.clear()
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    logger.warning("Transfer history cleared")


# Load history on module import
load_history_from_file()
