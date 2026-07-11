from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import pytest

from core.genetics import Genome
from core.taxonomy.profile import (
    FishTaxonomyProfileBuilder,
    MicrobeTaxonomyProfileBuilder,
    TaxonomyProfile,
)
from core.taxonomy.registry import SpeciesRegistry
from core.taxonomy.naming import CommonNameGenerator, ScientificNameGenerator
from core.taxonomy.system import TaxonomySystem


@dataclass
class MockEnvironment:
    world_type: str = "tank"

    def get_all_entities(self) -> list[Any]:
        return []


class MockEntity:
    def __init__(
        self, fish_id: int, genome: Genome, world_type: str = "tank", parent_id: int | None = None
    ):
        self.fish_id = fish_id
        self.genome = genome
        self.environment = MockEnvironment(world_type=world_type)
        self.parent_id = parent_id
        self.generation = 0
        self.tank_id = "test_tank"
        self.taxon_id = None
        self.common_name = ""
        self.scientific_name = ""
        self.species_confidence = ""
        self.origin_tank_id = None
        self.type_specimen_id = None
        self.strain_id = None


def test_taxonomy_profile_builders():
    rng = random.Random(42)
    genome = Genome.random(rng=rng, use_algorithm=True)
    fish_entity = MockEntity(fish_id=1, genome=genome, world_type="tank")
    microbe_entity = MockEntity(fish_id=2, genome=genome, world_type="petri")

    fish_builder = FishTaxonomyProfileBuilder()
    microbe_builder = MicrobeTaxonomyProfileBuilder()

    fish_profile = fish_builder.build_profile(fish_entity)
    microbe_profile = microbe_builder.build_profile(microbe_entity)

    assert isinstance(fish_profile, TaxonomyProfile)
    assert not fish_profile.is_microbe
    assert len(fish_profile.traits) > 0
    assert all(0.0 <= v <= 1.0 for v in fish_profile.traits.values())

    assert isinstance(microbe_profile, TaxonomyProfile)
    assert microbe_profile.is_microbe
    assert len(microbe_profile.traits) > 0
    assert all(0.0 <= v <= 1.0 for v in microbe_profile.traits.values())

    # Distance calculation checks
    dist_self = fish_profile.distance(fish_profile)
    assert dist_self == pytest.approx(0.0)

    dist_other_domain = fish_profile.distance(microbe_profile)
    assert dist_other_domain == 1.0

    with pytest.raises(TypeError):
        fish_profile.traits["size_modifier"] = 0.0  # type: ignore[index]


def test_naming_algorithms():
    rng = random.Random(123)
    genome = Genome.random(rng=rng, use_algorithm=True)
    fish = MockEntity(fish_id=10, genome=genome)

    fish_builder = FishTaxonomyProfileBuilder()
    profile = fish_builder.build_profile(fish)

    # Test scientific naming
    genus, epithet = ScientificNameGenerator.generate_name(
        profile,
        parent_profile=None,
        other_profiles=[],
        parent_genus=None,
        occupied_names_in_genus=set(),
        seed_hash=42,
    )
    assert genus in [
        "Synpinna",
        "Monopinna",
        "Cryptichthys",
        "Dolichopinna",
        "Megaophthalmichthys",
        "Brachypinna",
        "Altichthys",
        "Planctichthys",
    ]
    assert epithet in [
        "gregarius",
        "solitarius",
        "praesagus",
        "insidians",
        "fugax",
        "erraticus",
        "longipinnis",
        "macrophthalmus",
        "ruber",
        "aureus",
        "caeruleus",
        "maculatus",
        "fasciatus",
        "vorax",
        "tenax",
        "longevus",
    ] or epithet.startswith("tenax")

    # Test common naming
    common_name = CommonNameGenerator.generate_name(
        profile,
        parent_profile=None,
        other_profiles=[],
        registry_names=set(),
        seed_hash=42,
    )
    assert len(common_name.split()) >= 2
    assert len(common_name.split()) <= 3


def test_microbe_naming_algorithms():
    rng = random.Random(456)
    genome = Genome.random(rng=rng, use_algorithm=True)
    microbe = MockEntity(fish_id=20, genome=genome, world_type="petri")

    builder = MicrobeTaxonomyProfileBuilder()
    profile = builder.build_profile(microbe)

    # Test scientific naming
    genus, epithet = ScientificNameGenerator.generate_name(
        profile,
        parent_profile=None,
        other_profiles=[],
        parent_genus=None,
        occupied_names_in_genus=set(),
        seed_hash=99,
    )
    assert genus in [
        "Mobilibacter",
        "Pelliculococcus",
        "Helicovora",
        "Saccharobacter",
        "Thermobacter",
        "Coccobacter",
        "Bacillobacter",
        "Filamentobacter",
    ]
    assert epithet in [
        "gregarius",
        "solitarius",
        "praesagus",
        "insidians",
        "rapax",
        "mobilis",
        "dormiens",
        "tenax",
        "maculatus",
    ] or epithet.startswith("tenax")

    # Test common naming
    common_name = CommonNameGenerator.generate_name(
        profile,
        parent_profile=None,
        other_profiles=[],
        registry_names=set(),
        seed_hash=99,
    )
    assert len(common_name.split()) == 3


def test_registry_classify_and_speciation():
    registry = SpeciesRegistry()
    # Tweak thresholds to speed up test
    registry.min_living_members = 2
    registry.min_successful_births = 2
    registry.min_persistence_generations = 1

    rng = random.Random(777)
    genome1 = Genome.random(rng=rng, use_algorithm=True)
    f1 = MockEntity(fish_id=1, genome=genome1)

    # 1. First classification creates a provisional species
    builder = FishTaxonomyProfileBuilder()
    p1 = builder.build_profile(f1)
    rec1 = registry.classify_and_assign(
        p1, parent_taxon_id=None, entity_id=1, generation=0, frame=100
    )
    assert rec1.status == "provisional"
    assert rec1.taxon_id == "prov_1"
    assert rec1.common_name != "Provisional Lineage #1"
    assert len(rec1.common_name.split()) >= 2
    assert len(rec1.scientific_name.split()) == 2
    provisional_common_name = rec1.common_name
    provisional_scientific_name = rec1.scientific_name

    # 2. Second classification of similar entity joins provisional
    f2 = MockEntity(fish_id=2, genome=genome1)
    p2 = builder.build_profile(f2)
    rec2 = registry.classify_and_assign(
        p2, parent_taxon_id="prov_1", entity_id=2, generation=1, frame=110
    )
    assert rec2.taxon_id == "prov_1"
    assert rec2.total_births == 2
    assert rec2.max_generation == 1

    # 3. Evaluate speciation - criteria met -> established!
    newly_est = registry.evaluate_provisional_species(frame=120)
    assert len(newly_est) == 1
    old_id, new_rec = newly_est[0]
    assert old_id == "prov_1"
    assert new_rec.taxon_id == "taxon_1"
    assert new_rec.status == "established"
    assert len(new_rec.common_name) > 0
    assert len(new_rec.scientific_name) > 0
    # Species labels describe the immutable type profile; establishment should
    # not rename a lineage after its medoid moves slightly.
    assert new_rec.common_name == provisional_common_name
    assert new_rec.scientific_name == provisional_scientific_name


def test_newly_founded_species_avoid_epithet_collisions_within_a_genus():
    registry = SpeciesRegistry()
    profile = TaxonomyProfile(
        {
            "size_modifier": 0.5,
            "body_aspect": 0.5,
            "fin_size": 0.5,
            "tail_size": 0.5,
            "eye_size": 0.5,
            "lifespan_modifier": 0.5,
            "color_hue": 0.5,
            "pattern_type": 0.0,
            "pattern_intensity": 0.5,
            "template_id": 0.0,
            "aggression": 0.5,
            "social_tendency": 0.5,
            "pursuit_aggression": 0.5,
            "prediction_skill": 0.5,
            "hunting_stamina": 0.5,
            "food_approach": 0.0,
            "threat_response": 0.0,
            "social_mode": 0.0,
            "movement_policy_family": 0.0,
        },
        is_microbe=False,
    )

    first = registry.classify_and_assign(profile, None, entity_id=1, generation=0, frame=1)
    second = registry.classify_and_assign(profile, None, entity_id=2, generation=0, frame=2)

    assert first.genus_id == second.genus_id
    assert first.scientific_name != second.scientific_name


def test_serialization():
    registry = SpeciesRegistry()
    rng = random.Random(888)
    genome = Genome.random(rng=rng, use_algorithm=True)
    f = MockEntity(fish_id=1, genome=genome)
    builder = FishTaxonomyProfileBuilder()
    p = builder.build_profile(f)

    registry.classify_and_assign(p, parent_taxon_id=None, entity_id=1, generation=0, frame=10)

    # Dict roundtrip
    serialized = registry.to_dict()
    deserialized = SpeciesRegistry.from_dict(serialized)

    assert deserialized.next_prov_id == registry.next_prov_id
    assert "prov_1" in deserialized.species
    rec = deserialized.species["prov_1"]
    assert rec.total_births == 1
    assert rec.type_profile.is_microbe == p.is_microbe


def test_restored_entity_rehydrates_taxonomy_without_a_new_birth():
    rng = random.Random(999)
    entity = MockEntity(fish_id=12, genome=Genome.random(rng=rng, use_algorithm=True))
    entity.taxon_id = "taxon_imported"
    entity.common_name = "Azure Schooling Sailfin"
    entity.scientific_name = "Synpinna gregaria"
    entity.species_confidence = "established"
    entity.environment.agents = [entity]

    system = TaxonomySystem()
    system.update(entity.environment, frame=50)

    record = system.registry.species["taxon_imported"]
    assert record.living_member_ids == {12}
    assert record.total_births == 0
    assert system._entity_to_taxon_id[12] == "taxon_imported"
