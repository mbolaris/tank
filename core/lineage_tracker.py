"""Lineage tracking for phylogenetic tree visualization.

This module tracks parent-child relationships between fish for
building phylogenetic trees in the frontend.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

MAX_LINEAGE_LOG_SIZE = 5000


class LineageTracker:
    """Tracks fish lineage for phylogenetic tree visualization.

    Maintains a log of birth records with parent-child relationships,
    generation info, algorithm, and color for tree rendering.
    """

    def __init__(self):
        """Initialize the lineage tracker."""
        self.lineage_log: List[Dict[str, Any]] = []

    def record_birth(
        self,
        fish_id: int,
        parent_id: Optional[int],
        generation: int,
        algorithm_name: str,
        color: str,
        birth_frame: int,
    ) -> None:
        """Record a fish birth in the lineage log.

        Args:
            fish_id: ID of the new fish
            parent_id: ID of parent fish (None for initial spawn)
            generation: Generation number
            algorithm_name: Name of the fish's algorithm
            color: Color hex string (e.g., "#00ff00")
            birth_frame: Frame number when fish was born
        """
        lineage_record = {
            "id": str(fish_id),
            "parent_id": str(parent_id) if parent_id is not None else "root",
            "generation": generation,
            "algorithm": algorithm_name,
            "color": color,
            "birth_time": birth_frame,
        }
        self.lineage_log.append(lineage_record)

        # Prune if over capacity, preserving ancestry chains
        self._prune_if_needed()

    def _prune_if_needed(self) -> None:
        """Prune old records while preserving ancestry chains.

        Only removes records that are NOT referenced as a parent by any
        other record. This prevents orphaning descendants when the log
        exceeds MAX_LINEAGE_LOG_SIZE.
        """
        if len(self.lineage_log) <= MAX_LINEAGE_LOG_SIZE:
            return

        # Build set of all parent_ids referenced by current records
        referenced_parents: Set[str] = {
            rec["parent_id"] for rec in self.lineage_log
        }

        # Find prunable record indices (not referenced as parent by anyone)
        prunable_indices: List[int] = []
        for i, rec in enumerate(self.lineage_log):
            rec_id = rec["id"]
            if rec_id not in referenced_parents:
                prunable_indices.append(i)

        # Calculate how many to prune
        excess = len(self.lineage_log) - MAX_LINEAGE_LOG_SIZE
        to_remove = prunable_indices[:excess]

        # Remove in reverse order to preserve indices
        for i in reversed(to_remove):
            self.lineage_log.pop(i)

    def get_lineage_data(
        self, alive_fish_ids: Optional[Set[int]] = None
    ) -> List[Dict[str, Any]]:
        """Get complete lineage data for phylogenetic tree visualization.

        Args:
            alive_fish_ids: Set of fish IDs that are currently alive

        Returns:
            List of lineage records with parent-child relationships and alive status
        """
        if alive_fish_ids is None:
            alive_fish_ids = set()

        # Build set of valid IDs (include explicit 'root')
        valid_ids = {rec.get("id") for rec in self.lineage_log}
        valid_ids.add("root")

        enriched_lineage: List[Dict[str, Any]] = []
        orphan_count = 0

        for record in self.lineage_log:
            rec_id = record.get("id")
            parent_id = record.get("parent_id", "root")

            # If parent_id references a missing id, remap to root
            if parent_id not in valid_ids:
                orphan_count += 1
                logger.warning(
                    "Lineage: Orphaned record detected - id=%s parent_id=%s; remapping to root",
                    rec_id,
                    parent_id,
                )
                sanitized = dict(record)
                sanitized["parent_id"] = "root"
                sanitized["_original_parent_id"] = parent_id
            else:
                sanitized = dict(record)

            # Determine alive status
            try:
                fish_numeric_id = (
                    int(sanitized["id"]) if sanitized.get("id") != "root" else -1
                )
            except Exception:
                fish_numeric_id = -1

            sanitized["is_alive"] = fish_numeric_id in alive_fish_ids
            enriched_lineage.append(sanitized)

        if orphan_count > 0:
            logger.info(
                "Lineage: Fixed %d orphaned lineage record(s) by remapping parents to root",
                orphan_count,
            )

        return enriched_lineage

    def clear(self) -> None:
        """Clear the lineage log."""
        self.lineage_log.clear()
