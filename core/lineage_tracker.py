"""Lineage tracking for phylogenetic tree visualization.

This module tracks parent-child relationships between fish for
building phylogenetic trees in the frontend.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

MAX_LINEAGE_LOG_SIZE = 10000


class LineageTracker:
    """Tracks fish lineage for phylogenetic tree visualization.

    Maintains a log of birth records with parent-child relationships,
    generation info, algorithm, and color for tree rendering.

    Smart pruning ensures complete ancestry is preserved for all living fish.
    Only extinct lineages (dead fish with no living descendants) are pruned.
    """

    def __init__(self):
        """Initialize the lineage tracker."""
        self.lineage_log: List[Dict[str, Any]] = []
        self._alive_fish_ids: Set[int] = set()
        self._fixed_orphans: Set[str] = (
            set()
        )  # Track already-fixed orphans to avoid repeat warnings

    def update_alive_fish(self, alive_fish_ids: Set[int]) -> None:
        """Update the set of alive fish IDs and trigger smart pruning.

        Args:
            alive_fish_ids: Set of fish IDs that are currently alive
        """
        self._alive_fish_ids = alive_fish_ids
        self._smart_prune_if_needed()

    def record_birth(
        self,
        fish_id: int,
        parent_id: Optional[int],
        generation: int,
        algorithm_name: str,
        color: str,
        birth_frame: int,
        tank_name: Optional[str] = None,
    ) -> None:
        """Record a fish birth in the lineage log.

        Args:
            fish_id: ID of the new fish
            parent_id: ID of parent fish (None for initial spawn)
            generation: Generation number
            algorithm_name: Name of the fish's algorithm
            color: Color hex string (e.g., "#00ff00")
            birth_frame: Frame number when fish was born
            tank_name: Name of the tank where fish was born
        """
        lineage_record = {
            "id": str(fish_id),
            "parent_id": str(parent_id) if parent_id is not None else "root",
            "generation": generation,
            "algorithm": algorithm_name,
            "color": color,
            "birth_time": birth_frame,
            "tank_name": tank_name,
        }
        self.lineage_log.append(lineage_record)

        # Add to alive set
        self._alive_fish_ids.add(fish_id)

    def _build_ancestor_set(self, alive_ids: Set[int]) -> Set[str]:
        """Build the complete set of ancestor IDs for all living fish.

        Traces the ancestry chain for each living fish back to root,
        collecting all ancestor IDs along the way.

        Args:
            alive_ids: Set of currently alive fish IDs

        Returns:
            Set of all ancestor IDs (as strings) that must be preserved
        """
        # Build ID -> record lookup for fast parent traversal
        id_to_record: Dict[str, Dict[str, Any]] = {rec["id"]: rec for rec in self.lineage_log}

        ancestors: Set[str] = set()
        alive_str_ids = {str(fid) for fid in alive_ids}

        # For each living fish, trace back to root
        for alive_id in alive_str_ids:
            current_id = alive_id
            visited = set()  # Prevent infinite loops from bad data

            while current_id and current_id != "root" and current_id not in visited:
                visited.add(current_id)
                ancestors.add(current_id)

                record = id_to_record.get(current_id)
                if record:
                    current_id = record.get("parent_id", "root")
                else:
                    break

        return ancestors

    def _smart_prune_if_needed(self) -> None:
        """Smart prune that preserves complete ancestry for living fish.

        Only removes records that are:
        1. NOT ancestors of any living fish
        2. Dead (not in alive_fish_ids)

        This ensures the phylogenetic tree is always complete for living fish.
        """
        if len(self.lineage_log) <= MAX_LINEAGE_LOG_SIZE:
            return

        # Build set of all ancestors of living fish
        ancestors_to_keep = self._build_ancestor_set(self._alive_fish_ids)

        # Find prunable records: not in ancestor set and not alive
        alive_str_ids = {str(fid) for fid in self._alive_fish_ids}
        prunable_indices: List[int] = []

        for i, rec in enumerate(self.lineage_log):
            rec_id = rec["id"]
            # Keep if: is alive OR is an ancestor of someone alive
            if rec_id not in alive_str_ids and rec_id not in ancestors_to_keep:
                prunable_indices.append(i)

        # Calculate how many to prune
        excess = len(self.lineage_log) - MAX_LINEAGE_LOG_SIZE
        to_remove = prunable_indices[:excess]

        if to_remove:
            logger.debug(
                "Lineage: Pruning %d extinct lineage records (keeping %d ancestor records)",
                len(to_remove),
                len(ancestors_to_keep),
            )

        # Remove in reverse order to preserve indices
        for i in reversed(to_remove):
            self.lineage_log.pop(i)

    def _fix_orphans_permanently(self) -> int:
        """Fix orphaned records permanently in the lineage log.

        Returns:
            Number of orphans fixed
        """
        valid_ids = {rec.get("id") for rec in self.lineage_log}
        valid_ids.add("root")

        orphan_count = 0

        for record in self.lineage_log:
            rec_id = record.get("id")
            parent_id = record.get("parent_id", "root")

            # If parent_id references a missing id and we haven't fixed this before
            if parent_id not in valid_ids:
                orphan_count += 1
                if rec_id not in self._fixed_orphans:
                    logger.warning(
                        "Lineage: Orphaned record detected - id=%s parent_id=%s; remapping to root",
                        rec_id,
                        parent_id,
                    )
                    self._fixed_orphans.add(rec_id)

                # Permanently fix in the actual record
                record["_original_parent_id"] = parent_id
                record["parent_id"] = "root"

        return orphan_count

    def get_lineage_data(self, alive_fish_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
        """Get complete lineage data for phylogenetic tree visualization.

        Args:
            alive_fish_ids: Set of fish IDs that are currently alive

        Returns:
            List of lineage records with parent-child relationships and alive status
        """
        if alive_fish_ids is None:
            alive_fish_ids = self._alive_fish_ids
        else:
            # Update our internal tracking
            self._alive_fish_ids = alive_fish_ids

        # Fix any orphans permanently (modifies lineage_log in place)
        orphan_count = self._fix_orphans_permanently()

        if orphan_count > 0:
            logger.info(
                "Lineage: Fixed %d orphaned lineage record(s) by remapping parents to root",
                orphan_count,
            )

        enriched_lineage: List[Dict[str, Any]] = []

        for record in self.lineage_log:
            sanitized = dict(record)

            # Determine alive status
            try:
                fish_numeric_id = int(sanitized["id"]) if sanitized.get("id") != "root" else -1
            except Exception:
                fish_numeric_id = -1

            sanitized["is_alive"] = fish_numeric_id in alive_fish_ids
            enriched_lineage.append(sanitized)

        return enriched_lineage

    def clear(self) -> None:
        """Clear the lineage log."""
        self.lineage_log.clear()
        self._alive_fish_ids.clear()
        self._fixed_orphans.clear()
