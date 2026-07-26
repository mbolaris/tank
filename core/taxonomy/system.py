from __future__ import annotations

import logging
from typing import Any

from core.taxonomy.profile import FishTaxonomyProfileBuilder, MicrobeTaxonomyProfileBuilder
from core.taxonomy.pruning import DEFAULT_PRUNE_TTL_FRAMES, prune_dead_lineages
from core.taxonomy.registry import SpeciesRecord, SpeciesRegistry

logger = logging.getLogger(__name__)

# Taxonomy is presentation-only, so these cadences trade label latency for CPU
# and never affect simulation outcomes. They live here rather than in
# core/config/ on purpose: core.config constants feed the benchmark
# ``config_hash``, and bumping that would invalidate every champion record.
DEFAULT_EVAL_INTERVAL_FRAMES = 30  # ~1s at 30 fps
DEFAULT_PRUNE_INTERVAL_FRAMES = 9_000  # ~5 min at 30 fps


class TaxonomySystem:
    """Orchestrates taxonomy profiling, species classification, and naming."""

    def __init__(
        self,
        registry_file: str | None = None,
        *,
        eval_interval_frames: int = DEFAULT_EVAL_INTERVAL_FRAMES,
        prune_interval_frames: int = DEFAULT_PRUNE_INTERVAL_FRAMES,
        prune_ttl_frames: int = DEFAULT_PRUNE_TTL_FRAMES,
    ):
        """Initialize the taxonomy system.

        Args:
            registry_file: Optional path to persist the species registry to.
            eval_interval_frames: Frames between provisional-species scans.
                ``1`` restores the original every-frame behavior.
            prune_interval_frames: Frames between prune passes; ``0`` disables
                pruning and lets the registry grow without bound.
            prune_ttl_frames: How long a lineage must be memberless before it
                becomes eligible for pruning.
        """
        self.registry = SpeciesRegistry(registry_file=registry_file)
        self.fish_builder = FishTaxonomyProfileBuilder()
        self.microbe_builder = MicrobeTaxonomyProfileBuilder()

        self.eval_interval_frames = eval_interval_frames
        self.prune_interval_frames = prune_interval_frames
        self.prune_ttl_frames = prune_ttl_frames
        self._last_evaluation_frame: int | None = None
        self._last_prune_frame: int | None = None

        # Entity ID to Taxon ID lookup cache
        self._entity_to_taxon_id: dict[int, str] = {}
        self.frame_count: int = 0

    def load(self, filepath: str | None = None) -> None:
        """Load species registry from file."""
        self.registry.load(filepath)
        # Re-populate entity-to-taxon mapping from the loaded registry
        self._entity_to_taxon_id.clear()
        for rec in self.registry.species.values():
            for entity_id in rec.living_member_ids:
                self._entity_to_taxon_id[entity_id] = rec.taxon_id

    def save(self, filepath: str | None = None) -> None:
        """Save species registry to file."""
        self.registry.save(filepath)

    def register_birth(self, entity: Any) -> None:
        """Profile and assign a newly born organism to a species taxon."""
        self._register_entity(entity, count_as_birth=True)

    def register_existing(self, entity: Any) -> None:
        """Rehydrate an imported/restored organism without recording a birth."""
        self._register_entity(entity, count_as_birth=False)

    def _register_entity(self, entity: Any, *, count_as_birth: bool) -> None:
        """Profile an entity and add it to the registry's living membership."""
        # Detect if microbe or fish
        is_microbe = entity.environment.world_type == "petri"

        builder = self.microbe_builder if is_microbe else self.fish_builder
        profile = builder.build_profile(entity)

        # Check if the entity already has a pre-assigned taxon (e.g., from loading/transfer)
        existing_taxon_id = entity.taxon_id
        if existing_taxon_id:
            if existing_taxon_id in self.registry.species:
                record = self.registry.species[existing_taxon_id]
                record.living_member_ids.add(entity.fish_id)
                record.member_profiles_cache[entity.fish_id] = profile
                if count_as_birth:
                    record.total_births += 1
                record.last_seen_frame = max(record.last_seen_frame, self.frame_count)
                record.update_medoid()
                self._entity_to_taxon_id[entity.fish_id] = existing_taxon_id
                return
            else:
                # Reconstruct / import species from deserialization
                genus = entity.scientific_name.split()[0] if entity.scientific_name else None
                record = SpeciesRecord(
                    taxon_id=existing_taxon_id,
                    type_profile=profile,
                    current_medoid_profile=profile,
                    founder_ids=[entity.fish_id],
                    parent_taxon_id=None,
                    genus_id=genus,
                    common_name=entity.common_name or "Transferred Species",
                    scientific_name=entity.scientific_name or "Transferred Species",
                    created_frame=self.frame_count,
                    last_seen_frame=self.frame_count,
                    status=entity.species_confidence or "established",
                    living_member_ids={entity.fish_id},
                    total_births=1 if count_as_birth else 0,
                    min_generation=entity.generation,
                    max_generation=entity.generation,
                    type_specimen_id=entity.fish_id,
                )
                record.member_profiles_cache[entity.fish_id] = profile
                self.registry.species[existing_taxon_id] = record
                self._entity_to_taxon_id[entity.fish_id] = existing_taxon_id
                return

        # Normal speciation/assignment flow
        parent_id = entity.parent_id
        parent_taxon_id = self._entity_to_taxon_id.get(parent_id) if parent_id is not None else None

        record = self.registry.classify_and_assign(
            profile=profile,
            parent_taxon_id=parent_taxon_id,
            entity_id=entity.fish_id,
            generation=entity.generation,
            frame=self.frame_count,
        )

        # Set properties on the entity
        entity.taxon_id = record.taxon_id
        entity.common_name = record.common_name
        entity.scientific_name = record.scientific_name
        entity.species_confidence = record.status
        entity.type_specimen_id = record.type_specimen_id
        entity.strain_id = f"{record.common_name.replace(' ', '-')}-strain" if is_microbe else None

        self._entity_to_taxon_id[entity.fish_id] = record.taxon_id

    def record_death(self, entity_id: int) -> None:
        """Handle entity death by updating species membership."""
        self.registry.record_death(entity_id)
        if entity_id in self._entity_to_taxon_id:
            del self._entity_to_taxon_id[entity_id]

    def _is_evaluation_due(self, frame: int) -> bool:
        """Whether the provisional-species scan should run on this frame.

        The scan is O(registry size) and only ever promotes a lineage that has
        already met multi-generation criteria, so running it every frame bought
        nothing but CPU. Sampling it costs at most ``eval_interval_frames`` of
        delay before a species is formally established.
        """
        if self.eval_interval_frames <= 1:
            return True
        if self._last_evaluation_frame is None:
            return True
        return (frame - self._last_evaluation_frame) >= self.eval_interval_frames

    def _prune_registry_if_due(self, frame: int) -> None:
        """Drop dead, unreachable provisional lineages on a slow cadence."""
        if self.prune_interval_frames <= 0:
            return
        if self._last_prune_frame is not None:
            if (frame - self._last_prune_frame) < self.prune_interval_frames:
                return
        self._last_prune_frame = frame
        prune_dead_lineages(self.registry, frame, self.prune_ttl_frames)

    def update(self, environment: Any, frame: int) -> None:
        """Perform periodic updates (e.g. check provisional lineages)."""
        self.frame_count = frame
        if environment is None:
            return
        entities = environment.agents or []

        # Imported and restored fish retain their taxon label on the entity,
        # but their new world's in-memory registry needs the corresponding
        # membership before descendants can inherit it.  This scan is a pure
        # bookkeeping reconciliation; it never records another birth.
        for entity in entities:
            entity_id = entity.fish_id if hasattr(entity, "fish_id") else None
            if entity_id is not None and entity_id not in self._entity_to_taxon_id:
                self.register_existing(entity)

        self._prune_registry_if_due(frame)

        if not self._is_evaluation_due(frame):
            return

        self._last_evaluation_frame = frame
        newly_established = self.registry.evaluate_provisional_species(frame)

        if newly_established and environment:
            # Map old provisional IDs to new established IDs for living fish
            id_updates = {old_id: rec.taxon_id for old_id, rec in newly_established}

            # Fetch all entities in simulation
            for ent in entities:
                ent_id = ent.fish_id if hasattr(ent, "fish_id") else None
                if ent_id is not None:
                    old_taxon_id = ent.taxon_id
                    if old_taxon_id in id_updates:
                        rec = self.registry.species[id_updates[old_taxon_id]]
                        ent.taxon_id = rec.taxon_id
                        ent.common_name = rec.common_name
                        ent.scientific_name = rec.scientific_name
                        ent.species_confidence = rec.status

                        # Update lookups
                        self._entity_to_taxon_id[ent_id] = rec.taxon_id
