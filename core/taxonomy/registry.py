from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from core.taxonomy.naming import CommonNameGenerator, ScientificNameGenerator, _stable_hash
from core.taxonomy.profile import TaxonomyProfile

logger = logging.getLogger(__name__)

TAXONOMY_VERSION = "tank-taxonomy-v1"


@dataclass
class SpeciesRecord:
    """Represents a persistent species record in the registry."""

    taxon_id: str
    type_profile: TaxonomyProfile
    current_medoid_profile: TaxonomyProfile
    founder_ids: list[int] = field(default_factory=list)
    parent_taxon_id: str | None = None
    genus_id: str | None = None
    common_name: str = ""
    scientific_name: str = ""
    created_frame: int = 0
    last_seen_frame: int = 0
    status: str = "provisional"  # provisional | established | extinct
    aliases: list[str] = field(default_factory=list)

    # Speciation tracker fields
    living_member_ids: set[int] = field(default_factory=set)
    total_births: int = 0
    min_generation: int = 0
    max_generation: int = 0

    # Cache of currently active members' profiles to compute medoid
    member_profiles_cache: dict[int, TaxonomyProfile] = field(default_factory=dict, repr=False)

    # Type specimen ID (original taxonomic reference member)
    type_specimen_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the record to a dictionary."""
        return {
            "taxon_id": self.taxon_id,
            "type_profile": self.type_profile.to_dict(),
            "current_medoid_profile": self.current_medoid_profile.to_dict(),
            "founder_ids": self.founder_ids,
            "parent_taxon_id": self.parent_taxon_id,
            "genus_id": self.genus_id,
            "common_name": self.common_name,
            "scientific_name": self.scientific_name,
            "created_frame": self.created_frame,
            "last_seen_frame": self.last_seen_frame,
            "status": self.status,
            "aliases": self.aliases,
            "living_member_ids": list(self.living_member_ids),
            "total_births": self.total_births,
            "min_generation": self.min_generation,
            "max_generation": self.max_generation,
            "type_specimen_id": self.type_specimen_id,
            "member_profiles_cache": {
                str(k): v.to_dict() for k, v in self.member_profiles_cache.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpeciesRecord:
        """Load a record from a dictionary."""
        type_prof = TaxonomyProfile.from_dict(data["type_profile"])
        med_prof = TaxonomyProfile.from_dict(data["current_medoid_profile"])

        record = cls(
            taxon_id=data["taxon_id"],
            type_profile=type_prof,
            current_medoid_profile=med_prof,
            founder_ids=data["founder_ids"],
            parent_taxon_id=data["parent_taxon_id"],
            genus_id=data["genus_id"],
            common_name=data["common_name"],
            scientific_name=data["scientific_name"],
            created_frame=data["created_frame"],
            last_seen_frame=data["last_seen_frame"],
            status=data["status"],
            aliases=data["aliases"],
            living_member_ids=set(data["living_member_ids"]),
            total_births=data["total_births"],
            min_generation=data["min_generation"],
            max_generation=data["max_generation"],
            type_specimen_id=data.get("type_specimen_id"),
        )

        cache_data = data.get("member_profiles_cache", {})
        record.member_profiles_cache = {
            int(k): TaxonomyProfile.from_dict(v) for k, v in cache_data.items()
        }
        return record

    def update_medoid(self) -> None:
        """Update the current medoid profile based on cached member profiles."""
        if not self.member_profiles_cache:
            return
        profiles = list(self.member_profiles_cache.values())
        if len(profiles) == 1:
            self.current_medoid_profile = profiles[0]
            return

        best_profile = profiles[0]
        min_total_dist = float("inf")

        for p in profiles:
            total_dist = sum(p.distance(other) for other in profiles)
            if total_dist < min_total_dist:
                min_total_dist = total_dist
                best_profile = p

        self.current_medoid_profile = best_profile


class SpeciesRegistry:
    """Manages the persistent species classification registry and naming."""

    def __init__(self, registry_file: str | None = None):
        """Initialize the species registry."""
        self.species: dict[str, SpeciesRecord] = {}
        self.registry_file = registry_file

        # Speciation config params
        self.join_threshold: float = 0.15
        self.split_threshold: float = 0.1875  # 1.25 * join_threshold
        self.min_living_members: int = 5
        self.min_persistence_generations: int = 3
        self.min_successful_births: int = 8

        # Counter for ids
        self.next_prov_id: int = 1
        self.next_est_id: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entire registry state."""
        return {
            "taxonomy_version": TAXONOMY_VERSION,
            "species": {k: v.to_dict() for k, v in self.species.items()},
            "join_threshold": self.join_threshold,
            "split_threshold": self.split_threshold,
            "min_living_members": self.min_living_members,
            "min_persistence_generations": self.min_persistence_generations,
            "min_successful_births": self.min_successful_births,
            "next_prov_id": self.next_prov_id,
            "next_est_id": self.next_est_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], registry_file: str | None = None) -> SpeciesRegistry:
        """Load registry state from a dictionary."""
        reg = cls(registry_file=registry_file)
        reg.join_threshold = data.get("join_threshold", 0.15)
        reg.split_threshold = data.get("split_threshold", 0.1875)
        reg.min_living_members = data.get("min_living_members", 5)
        reg.min_persistence_generations = data.get("min_persistence_generations", 3)
        reg.min_successful_births = data.get("min_successful_births", 8)
        reg.next_prov_id = data.get("next_prov_id", 1)
        reg.next_est_id = data.get("next_est_id", 1)

        reg.species = {k: SpeciesRecord.from_dict(v) for k, v in data.get("species", {}).items()}
        return reg

    def save(self, filepath: str | None = None) -> None:
        """Persist registry to file."""
        fp = filepath or self.registry_file
        if not fp:
            return
        try:
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info("Saved species registry to %s", fp)
        except OSError as exc:
            logger.error("Failed to save species registry: %s", exc)

    def load(self, filepath: str | None = None) -> None:
        """Load registry from file."""
        fp = filepath or self.registry_file
        if not fp or not os.path.exists(fp):
            return
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            loaded = self.from_dict(data, registry_file=self.registry_file)
            self.species = loaded.species
            self.join_threshold = loaded.join_threshold
            self.split_threshold = loaded.split_threshold
            self.min_living_members = loaded.min_living_members
            self.min_persistence_generations = loaded.min_persistence_generations
            self.min_successful_births = loaded.min_successful_births
            self.next_prov_id = loaded.next_prov_id
            self.next_est_id = loaded.next_est_id
            logger.info("Loaded species registry from %s", fp)
        except (OSError, ValueError, TypeError) as exc:
            logger.error("Failed to load species registry: %s", exc)

    def get_related_species(self, parent_taxon_id: str | None) -> list[str]:
        """Find taxon_ids of related species to the given parent species."""
        if not parent_taxon_id or parent_taxon_id not in self.species:
            return []

        related = {parent_taxon_id}
        parent_rec = self.species[parent_taxon_id]

        # 1. Grandparent (parent of parent)
        if parent_rec.parent_taxon_id and parent_rec.parent_taxon_id in self.species:
            related.add(parent_rec.parent_taxon_id)
            # 2. Siblings (other children of grandparent)
            for tid, rec in self.species.items():
                if rec.parent_taxon_id == parent_rec.parent_taxon_id:
                    related.add(tid)

        # 3. Children of parent
        for tid, rec in self.species.items():
            if rec.parent_taxon_id == parent_taxon_id:
                related.add(tid)

        return list(related)

    def classify_and_assign(
        self,
        profile: TaxonomyProfile,
        parent_taxon_id: str | None,
        entity_id: int,
        generation: int,
        frame: int,
    ) -> SpeciesRecord:
        """Classify a new organism and assign it to a species or create a provisional one."""
        # 1. Find candidates
        candidates: list[str] = []

        # If we have a parent, we look at related species
        if parent_taxon_id:
            candidates = self.get_related_species(parent_taxon_id)

        # If no parent, or no candidates found, consider all established species
        # This allows initial seeds or emergency clones without donors to group up
        if not candidates:
            candidates = [tid for tid, rec in self.species.items() if rec.status == "established"]

        # Calculate membership distance to candidates
        best_candidate: SpeciesRecord | None = None
        best_distance = float("inf")

        for tid in candidates:
            rec = self.species.get(tid)
            if not rec:
                continue

            # distance calculation formula:
            # membership_distance = 0.70 * distance_to_current_medoid + 0.30 * distance_to_type_profile
            dist_medoid = profile.distance(rec.current_medoid_profile)
            dist_type = profile.distance(rec.type_profile)
            membership_dist = 0.70 * dist_medoid + 0.30 * dist_type

            if membership_dist < best_distance:
                best_distance = membership_dist
                best_candidate = rec

        # Assign to nearest candidate if within JOIN_THRESHOLD
        if best_candidate is not None and best_distance <= self.join_threshold:
            record = best_candidate
            record.living_member_ids.add(entity_id)
            record.member_profiles_cache[entity_id] = profile
            record.total_births += 1
            record.min_generation = min(record.min_generation, generation)
            record.max_generation = max(record.max_generation, generation)
            record.last_seen_frame = max(record.last_seen_frame, frame)
            record.update_medoid()

            # If extinct, mark revived
            if record.status == "extinct":
                record.status = "established"
                logger.info(
                    "Species %s (%s) revived after extinction!", record.common_name, record.taxon_id
                )

            return record

        # Otherwise, create a new provisional lineage
        prov_id = f"prov_{self.next_prov_id}"
        self.next_prov_id += 1

        parent_record = self.species.get(parent_taxon_id) if parent_taxon_id else None
        parent_profile = parent_record.type_profile if parent_record is not None else None
        reference_profiles = [
            self.species[tid].current_medoid_profile for tid in candidates if tid in self.species
        ]
        parent_genus = parent_record.genus_id if parent_record is not None else None
        genus = ScientificNameGenerator.select_genus(profile, parent_genus)
        occupied_epithets = {
            rec.scientific_name.split()[1]
            for rec in self.species.values()
            if rec.genus_id == genus and len(rec.scientific_name.split()) > 1
        }
        seed_hash = _stable_hash(_profile_seed(profile, parent_taxon_id))
        common_name = CommonNameGenerator.generate_name(
            profile,
            parent_profile,
            reference_profiles,
            {rec.common_name for rec in self.species.values() if rec.common_name},
            seed_hash,
        )
        generated_genus, epithet = ScientificNameGenerator.generate_name(
            profile,
            parent_profile,
            reference_profiles,
            genus,
            occupied_epithets,
            seed_hash,
        )
        scientific_name = f"{generated_genus} {epithet}"

        record = SpeciesRecord(
            taxon_id=prov_id,
            type_profile=profile,
            current_medoid_profile=profile,
            founder_ids=[entity_id],
            parent_taxon_id=parent_taxon_id,
            genus_id=generated_genus,
            common_name=common_name,
            scientific_name=scientific_name,
            created_frame=frame,
            last_seen_frame=frame,
            status="provisional",
            living_member_ids={entity_id},
            total_births=1,
            min_generation=generation,
            max_generation=generation,
            type_specimen_id=entity_id,
        )
        record.member_profiles_cache[entity_id] = profile

        self.species[prov_id] = record
        return record

    def record_death(self, entity_id: int) -> None:
        """Record death of an organism and update its species medoid/status."""
        for tid, rec in self.species.items():
            if entity_id in rec.living_member_ids:
                rec.living_member_ids.remove(entity_id)
                if entity_id in rec.member_profiles_cache:
                    del rec.member_profiles_cache[entity_id]
                rec.update_medoid()

                # Check for extinction
                if rec.status == "established" and len(rec.living_member_ids) == 0:
                    rec.status = "extinct"
                    logger.info("Species %s (%s) went extinct.", rec.common_name, rec.taxon_id)
                break

    def evaluate_provisional_species(self, frame: int) -> list[tuple[str, SpeciesRecord]]:
        """Evaluate provisional lineages and establish them if they meet criteria.

        Returns a list of tuples containing (old_provisional_id, newly_established_record).
        """
        newly_established = []
        all_profiles = [
            rec.current_medoid_profile
            for rec in self.species.values()
            if rec.status == "established"
        ]

        for tid, rec in list(self.species.items()):
            if rec.status != "provisional":
                continue

            # speciation criteria:
            # - minimum living members >= 5
            # - minimum successful births >= 8
            # - minimum persistence >= 3 generations
            # - distance from parent medoid > SPLIT_THRESHOLD (if it has parent species)
            # - mean internal distance < JOIN_THRESHOLD

            if len(rec.living_member_ids) < self.min_living_members:
                continue
            if rec.total_births < self.min_successful_births:
                continue
            if (rec.max_generation - rec.min_generation) < self.min_persistence_generations:
                continue

            # Check distance from parent medoid
            if rec.parent_taxon_id and rec.parent_taxon_id in self.species:
                parent_rec = self.species[rec.parent_taxon_id]
                parent_dist = rec.current_medoid_profile.distance(parent_rec.current_medoid_profile)
                if parent_dist <= self.split_threshold:
                    continue

            # Check internal cohesion (mean distance among living members)
            profiles = list(rec.member_profiles_cache.values())
            if len(profiles) > 1:
                total_internal_dist = 0.0
                pairs = 0
                for i in range(len(profiles)):
                    for j in range(i + 1, len(profiles)):
                        total_internal_dist += profiles[i].distance(profiles[j])
                        pairs += 1
                mean_internal_dist = total_internal_dist / pairs if pairs > 0 else 0.0
                if mean_internal_dist > self.join_threshold:
                    continue

            # Establish the species!
            old_id = rec.taxon_id
            self.establish_species(rec, all_profiles, frame)
            newly_established.append((old_id, rec))
            all_profiles.append(rec.current_medoid_profile)

        return newly_established

    def establish_species(
        self, rec: SpeciesRecord, established_profiles: list[TaxonomyProfile], frame: int
    ) -> None:
        """Establish a provisional lineage into a formal species."""
        rec.status = "established"
        est_id = f"taxon_{self.next_est_id}"
        self.next_est_id += 1

        # Determine Genus
        parent_genus = None
        if rec.parent_taxon_id and rec.parent_taxon_id in self.species:
            parent_rec = self.species[rec.parent_taxon_id]
            parent_dist = rec.current_medoid_profile.distance(parent_rec.current_medoid_profile)
            # Genus inheritance: broad parent genus inherits unless very distant
            # GENUS_THRESHOLD = 2-3 * SPECIES_THRESHOLD (e.g. 2.5 * 0.15 = 0.375)
            genus_threshold = 2.5 * self.join_threshold
            if parent_dist <= genus_threshold:
                parent_genus = parent_rec.genus_id

        # Unique scientific names inside the selected genus.  The old code
        # compared against an empty string for an independently-founded taxon,
        # allowing duplicate epithets in the same genus.
        genus_key = ScientificNameGenerator.select_genus(rec.type_profile, parent_genus)
        occupied_epithets = {
            s.scientific_name.split()[1]
            for s in self.species.values()
            if s.scientific_name
            and len(s.scientific_name.split()) > 1
            and s.scientific_name.split()[0] == genus_key
        }

        seed_hash = _stable_hash(_profile_seed(rec.type_profile, rec.parent_taxon_id))

        # A provisional label is generated from the immutable type profile at
        # lineage creation.  Formal establishment promotes that stable name,
        # rather than renaming an organism after a small population drift.
        if rec.common_name and rec.scientific_name and rec.scientific_name != "Provisionalis":
            rec.genus_id = rec.scientific_name.split()[0]
        else:
            # Generate scientific name
            parent_prof = (
                self.species[rec.parent_taxon_id].type_profile
                if (rec.parent_taxon_id and rec.parent_taxon_id in self.species)
                else None
            )
            genus, epithet = ScientificNameGenerator.generate_name(
                rec.type_profile,
                parent_prof,
                established_profiles,
                genus_key,
                occupied_epithets,
                seed_hash,
            )
            rec.genus_id = genus
            rec.scientific_name = f"{genus} {epithet}"
            existing_common_names = {s.common_name for s in self.species.values() if s.common_name}
            rec.common_name = CommonNameGenerator.generate_name(
                rec.type_profile,
                parent_prof,
                established_profiles,
                existing_common_names,
                seed_hash,
            )

        # Swap taxon_id in species registry
        old_id = rec.taxon_id
        rec.taxon_id = est_id
        self.species[est_id] = rec
        del self.species[old_id]

        logger.info(
            "Formally Speciated! %s (%s) has emerged from parent %s.",
            rec.common_name,
            rec.scientific_name,
            rec.parent_taxon_id,
        )


def _profile_seed(profile: TaxonomyProfile, parent_taxon_id: str | None) -> str:
    """Stable name seed from the taxonomy version, type profile, and ancestry."""
    trait_values = ",".join(f"{name}={value:.6f}" for name, value in sorted(profile.traits.items()))
    return f"{TAXONOMY_VERSION}|{parent_taxon_id or ''}|{int(profile.is_microbe)}|{trait_values}"
