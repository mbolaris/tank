"""Bounded-size maintenance for the species registry.

Every birth that does not join an existing species creates a provisional
lineage in :attr:`SpeciesRegistry.species`.  Nothing removed them, so a
long-running world accumulated one record per speciation event forever --
88k records after 1.6M frames -- and
:meth:`SpeciesRegistry.evaluate_provisional_species` rescanned the whole dict
on every frame.  That single scan grew to ~78% of the simulation thread and
dragged a 34-fish world from 30 fps down to 12.

This module drops provisional lineages that are dead and unreachable, which
bounds the dict by the *living* population rather than by total history.

Taxonomy is presentation-only: it labels simulation output but never
participates in the rules (see the ``non_deterministic_keys`` set in
:mod:`core.replay.fingerprint`).  Pruning therefore cannot change benchmark
scores or replay fingerprints.  It can still change which *names* appear, so
the guards below keep every record that a future birth could be classified
against, plus the ancestry chain the phylogeny view walks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.taxonomy.registry import SpeciesRegistry

logger = logging.getLogger(__name__)

# A provisional lineage must be memberless for this long before it is eligible
# to be dropped.  Generous by design: pruning is a memory/CPU optimization, and
# the cost of keeping a record slightly too long is negligible next to the cost
# of dropping one that a birth was about to rejoin.
DEFAULT_PRUNE_TTL_FRAMES = 27_000  # ~15 minutes at 30 fps


def _build_children_index(registry: SpeciesRegistry) -> dict[str, list[str]]:
    """Map each taxon id to the ids that name it as their parent."""
    children: dict[str, list[str]] = {}
    for tid, rec in registry.species.items():
        if rec.parent_taxon_id:
            children.setdefault(rec.parent_taxon_id, []).append(tid)
    return children


def compute_retained_ids(registry: SpeciesRegistry) -> set[str]:
    """Return every taxon id that must survive a prune pass.

    A record is retained when it is any of:

    * **Formal** -- ``established`` or ``extinct``.  These are the published
      taxonomy and the fallback candidate pool in ``classify_and_assign``.
    * **Living** -- it still has members.
    * **Reachable** -- ``get_related_species`` can offer it as a classification
      candidate for a birth into a living lineage.  That function walks to the
      parent, the siblings (the parent's other children), and the children, so
      all three hops are retained even when memberless.
    * **Ancestral** -- an ancestor of anything retained above, so the
      ``parent_taxon_id`` chain the phylogeny view walks stays unbroken and the
      split-threshold check in ``evaluate_provisional_species`` still finds its
      parent record.
    """
    species = registry.species
    children = _build_children_index(registry)

    live = {tid for tid, rec in species.items() if rec.living_member_ids}

    keep = {tid for tid, rec in species.items() if rec.status != "provisional"}
    keep |= live

    # Classification candidates reachable from any living lineage.
    for tid in live:
        parent = species[tid].parent_taxon_id
        if parent:
            keep.add(parent)
            keep.update(children.get(parent, ()))  # siblings
        keep.update(children.get(tid, ()))  # children

    # Ancestor closure over everything retained so far.
    for tid in list(keep):
        cursor = species[tid].parent_taxon_id if tid in species else None
        while cursor and cursor in species and cursor not in keep:
            keep.add(cursor)
            cursor = species[cursor].parent_taxon_id

    return keep


def find_prunable_ids(
    registry: SpeciesRegistry,
    frame: int,
    ttl_frames: int = DEFAULT_PRUNE_TTL_FRAMES,
) -> list[str]:
    """Return the ids of dead, unreachable, stale provisional lineages.

    The result is sorted so a prune pass is reproducible regardless of dict or
    set iteration order.
    """
    keep = compute_retained_ids(registry)
    cutoff = frame - ttl_frames

    prunable = [
        tid
        for tid, rec in registry.species.items()
        if tid not in keep
        and rec.status == "provisional"
        and not rec.living_member_ids
        and rec.last_seen_frame <= cutoff
    ]
    prunable.sort()
    return prunable


def prune_dead_lineages(
    registry: SpeciesRegistry,
    frame: int,
    ttl_frames: int = DEFAULT_PRUNE_TTL_FRAMES,
) -> int:
    """Drop dead, unreachable provisional lineages. Returns the number removed.

    ``next_prov_id`` is deliberately left untouched: ids stay monotonic so a
    pruned id is never reissued to a different lineage.
    """
    prunable = find_prunable_ids(registry, frame, ttl_frames)
    for tid in prunable:
        del registry.species[tid]

    if prunable:
        logger.info(
            "Taxonomy prune: dropped %d dead provisional lineages at frame %d (%d retained)",
            len(prunable),
            frame,
            len(registry.species),
        )
    return len(prunable)
