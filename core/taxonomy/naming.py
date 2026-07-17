from __future__ import annotations

import hashlib
from collections.abc import Mapping

from core.taxonomy.profile import TaxonomyProfile


def _stable_hash(s: str) -> int:
    """Deterministically hash a string to an integer."""
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _hash_to_syllables(hash_val: int) -> str:
    """Convert an integer hash into a short pronounceable syllable block."""
    syllables = [
        "ba",
        "co",
        "da",
        "fe",
        "go",
        "ha",
        "ji",
        "ki",
        "lo",
        "mu",
        "na",
        "pi",
        "ra",
        "se",
        "ti",
        "vo",
        "wa",
        "xi",
        "yo",
        "zu",
    ]
    idx1 = hash_val % len(syllables)
    idx2 = (hash_val // len(syllables)) % len(syllables)
    return syllables[idx1] + syllables[idx2]


def calculate_trait_saliences(
    profile: TaxonomyProfile,
    parent_profile: TaxonomyProfile | None,
    other_profiles: list[TaxonomyProfile],
) -> dict[str, float]:
    """Calculate the salience of each trait in the profile.

    salience = 0.4 * absolute_salience + 0.6 * distinctive_salience
    """
    saliences: dict[str, float] = {}

    # Find the closest reference profile for distinctive salience
    ref_profile = parent_profile
    if ref_profile is None and other_profiles:
        # Find nearest by profile distance
        ref_profile = min(other_profiles, key=lambda op: profile.distance(op))

    for name, val in profile.traits.items():
        # Absolute salience: distance from midpoint 0.5
        absolute_salience = abs(val - 0.5)

        # Distinctive salience: distance from reference trait value
        if ref_profile is not None:
            ref_val = ref_profile.traits.get(name, 0.5)
            # handle circular distance for color/pigment hue
            if name in ("color_hue", "pigment_hue"):
                diff = abs(val - ref_val) % 1.0
                distinctive_salience = min(diff, 1.0 - diff)
            else:
                distinctive_salience = abs(val - ref_val)
        else:
            distinctive_salience = 0.0

        saliences[name] = 0.4 * absolute_salience + 0.6 * distinctive_salience

    return saliences


class CommonNameGenerator:
    """Generates deterministic player-facing common names for species."""

    @staticmethod
    def generate_name(
        profile: TaxonomyProfile,
        parent_profile: TaxonomyProfile | None,
        other_profiles: list[TaxonomyProfile],
        registry_names: set[str],
        seed_hash: int,
    ) -> str:
        saliences = calculate_trait_saliences(profile, parent_profile, other_profiles)

        if profile.is_microbe:
            name = CommonNameGenerator._generate_microbe_name(profile, saliences)
        else:
            name = CommonNameGenerator._generate_fish_name(profile, saliences)

        # Resolve collisions
        return CommonNameGenerator._resolve_collision(name, registry_names, seed_hash)

    @staticmethod
    def _generate_fish_name(profile: TaxonomyProfile, saliences: dict[str, float]) -> str:
        # Fish categories: Appearance, Behavior, Body Type
        # 1. Appearance terms
        appearance_traits = ["color_hue", "pattern_type", "pattern_intensity", "template_id"]
        best_app = max(appearance_traits, key=lambda t: saliences.get(t, 0.0))
        app_term = CommonNameGenerator._get_fish_appearance_term(profile, best_app)

        # 2. Behavior terms
        behavior_traits = [
            "aggression",
            "social_tendency",
            "pursuit_aggression",
            "prediction_skill",
            "hunting_stamina",
            "food_approach",
            "threat_response",
            "social_mode",
        ]
        best_beh = max(behavior_traits, key=lambda t: saliences.get(t, 0.0))
        beh_term = CommonNameGenerator._get_fish_behavior_term(profile, best_beh)

        # 3. Body Type terms
        body_term = CommonNameGenerator._get_fish_body_type_term(profile.traits)

        # Combine: Appearance + Behavior + Body Type
        # Ensure we have at least 2 words, up to 3
        words = []
        if app_term:
            words.append(app_term)
        if beh_term:
            words.append(beh_term)
        words.append(body_term)

        return " ".join(words)

    @staticmethod
    def _get_fish_appearance_term(profile: TaxonomyProfile, trait: str) -> str:
        hue = profile.traits.get("color_hue", 0.5)
        intensity = profile.traits.get("pattern_intensity", 0.5)
        pattern_type = int(round(profile.traits.get("pattern_type", 0.0) * 5))

        if intensity < 0.2:
            return "Pale" if hue < 0.3 or hue > 0.8 else "Dusky"
        if intensity < 0.35:
            return "Silver"

        if trait == "pattern_type" or intensity > 0.6:
            patterns = {1: "Spotted", 2: "Banded", 3: "Mottled", 4: "Speckled", 5: "Striated"}
            if pattern_type in patterns:
                return patterns[pattern_type]

        # Map hue
        h = hue % 1.0
        if h < 0.04 or h >= 0.96:
            return "Crimson"
        elif h < 0.12:
            return "Amber"
        elif h < 0.22:
            return "Golden"
        elif h < 0.42:
            return "Emerald"
        elif h < 0.58:
            return "Azure"
        elif h < 0.72:
            return "Indigo"
        elif h < 0.88:
            return "Violet"
        else:
            return "Crimson"

    @staticmethod
    def _get_fish_behavior_term(profile: TaxonomyProfile, trait: str) -> str:
        agg = profile.traits.get("aggression", 0.5)
        social = profile.traits.get("social_tendency", 0.5)
        food_app = int(round(profile.traits.get("food_approach", 0.0) * 5))
        threat = int(round(profile.traits.get("threat_response", 0.0) * 3))

        if trait == "social_tendency" or trait == "social_mode":
            return "Schooling" if social > 0.5 else "Solitary"
        if trait == "food_approach":
            # Direct pursuit = 0, predictive = 1, circling = 2, ambush = 3, zigzag = 4, patrol = 5
            mapping = {
                0: "Pursuit",
                1: "Predictive",
                2: "Schooling",
                3: "Ambush",
                4: "Zigzag",
                5: "Patrolling",
            }
            return mapping.get(food_app, "Social")
        if trait == "threat_response":
            # panic = 0, stealth = 1, freeze = 2, erratic = 3
            mapping = {0: "Wary", 1: "Stealth", 2: "Freezing", 3: "Erratic"}
            return mapping.get(threat, "Bold")
        if trait == "aggression" or trait == "pursuit_aggression":
            return "Bold" if agg > 0.5 else "Wary"
        if trait == "prediction_skill":
            return "Predictive"
        if trait == "hunting_stamina":
            return "Solitary"

        return "Social"

    @staticmethod
    def _get_fish_body_type_term(traits: Mapping[str, float]) -> str:
        size = traits.get("size_modifier", 0.5)
        aspect = traits.get("body_aspect", 0.5)
        fin = traits.get("fin_size", 0.5)
        tail = traits.get("tail_size", 0.5)
        eye = traits.get("eye_size", 0.5)

        if fin > 0.6 and tail > 0.6:
            return "Crownfin"
        if aspect < 0.4 and fin < 0.4:
            return "Needlefin"
        if aspect < 0.4 and size > 0.5:
            return "Longbody"
        if aspect > 0.65 and size > 0.65:
            return "Broadback"
        if aspect > 0.65 and fin < 0.4:
            return "Roundfin"
        if size < 0.4 and aspect < 0.4:
            return "Dartfish"
        if fin > 0.6:
            return "Sailfin"
        if tail > 0.6:
            return "Fan-tail"
        if eye > 0.6:
            return "Bigeye"

        return "Riverfin"

    @staticmethod
    def _generate_microbe_name(profile: TaxonomyProfile, saliences: dict[str, float]) -> str:
        # Microbe format: Appearance or Colony + Ecology or Behavior + Morphology
        # 1. Colony / Appearance
        hue = profile.traits.get("pigment_hue", 0.5)
        intensity = profile.traits.get("texture_pattern", 0.5)

        if intensity < 0.25:
            app_term = "Pale"
        else:
            h = hue % 1.0
            if h < 0.04 or h >= 0.96:
                app_term = "Scarlet"
            elif h < 0.12:
                app_term = "Amber"
            elif h < 0.22:
                app_term = "Golden"
            elif h < 0.58:
                app_term = "Bluefilm"
            elif h < 0.72:
                app_term = "Violet"
            else:
                app_term = "Pale"

        # 2. Ecology / Behavior
        motility = profile.traits.get("motility_aggression", 0.5)
        swarming = profile.traits.get("social_swarming", 0.5)
        food_app = int(round(profile.traits.get("food_approach", 0.0) * 5))

        ecology_traits = ["motility_aggression", "social_swarming", "food_approach"]
        best_eco = max(ecology_traits, key=lambda t: saliences.get(t, 0.0))

        if best_eco == "motility_aggression":
            eco_term = "Hunter" if motility > 0.6 else "Scavenger"
        elif best_eco == "social_swarming":
            eco_term = "Swarm" if swarming > 0.6 else "Grazer"
        else:
            # food approach mapping
            mapping = {
                0: "Hunter",
                1: "Hunter",
                2: "Grazer",
                3: "Shield",
                4: "Glider",
                5: "Drifter",
            }
            eco_term = mapping.get(food_app, "Grazer")

        # 3. Morphology
        shape = profile.traits.get("shape_aspect", 0.5)
        elongation = profile.traits.get("elongation_fins", 0.5)
        cell_size = profile.traits.get("cell_size", 0.5)

        if shape > 0.7:
            morph_term = "Rod"
        elif shape < 0.3:
            morph_term = "Coccus"
        elif elongation > 0.6:
            morph_term = "Spiral"
        elif cell_size > 0.7:
            morph_term = "Cluster"
        elif cell_size < 0.3:
            morph_term = "Spore"
        else:
            morph_term = "Filament"

        return f"{app_term} {eco_term} {morph_term}"

    @staticmethod
    def _resolve_collision(name: str, registry_names: set[str], seed_hash: int) -> str:
        if name not in registry_names:
            return name

        qualifiers = [
            "Northern",
            "Southern",
            "Eastern",
            "Western",
            "Kelpborn",
            "Abyssal",
            "Pelagic",
            "Benthic",
            "Tidal",
            "Lagoon",
            "Reef",
            "Delta",
            "Deepwater",
            "Shallow",
            "Estuary",
        ]
        q_idx = seed_hash % len(qualifiers)
        candidate = f"{qualifiers[q_idx]} {name}"
        if candidate not in registry_names:
            return candidate

        q_idx2 = (seed_hash // len(qualifiers)) % len(qualifiers)
        if q_idx2 == q_idx:
            q_idx2 = (q_idx2 + 1) % len(qualifiers)
        candidate = f"{qualifiers[q_idx2]} {name}"
        if candidate not in registry_names:
            return candidate

        tanks = ["Delta", "Alpha", "Omega", "Beta", "Gamma", "Prime", "Epsilon", "Zeta"]
        t_idx = seed_hash % len(tanks)
        candidate = f"{name} of Tank {tanks[t_idx]}"
        if candidate not in registry_names:
            return candidate

        s1 = _hash_to_syllables(seed_hash)
        return f"{name} ({s1})"


class ScientificNameGenerator:
    """Generates stable fictionary binomial Latin-like scientific names."""

    @staticmethod
    def select_genus(profile: TaxonomyProfile, parent_genus: str | None = None) -> str:
        """Choose the genus before resolving an epithet collision."""
        if parent_genus is not None:
            return parent_genus
        if profile.is_microbe:
            return ScientificNameGenerator._generate_microbe_genus(profile.traits)
        return ScientificNameGenerator._generate_fish_genus(profile.traits)

    @staticmethod
    def generate_name(
        profile: TaxonomyProfile,
        parent_profile: TaxonomyProfile | None,
        other_profiles: list[TaxonomyProfile],
        parent_genus: str | None,
        occupied_names_in_genus: set[str],
        seed_hash: int,
    ) -> tuple[str, str]:
        """Generate a scientific binomial name: (genus, species)."""
        # Determine Genus
        genus = ScientificNameGenerator.select_genus(profile, parent_genus)

        # Generate Epithet
        saliences = calculate_trait_saliences(profile, parent_profile, other_profiles)
        sorted_traits = sorted(saliences.keys(), key=lambda k: saliences[k], reverse=True)

        epithet = None
        for trait in sorted_traits:
            if profile.is_microbe:
                candidate = ScientificNameGenerator._get_microbe_epithet(profile, trait)
            else:
                candidate = ScientificNameGenerator._get_fish_epithet(profile, trait)

            if candidate and candidate not in occupied_names_in_genus:
                epithet = candidate
                break

        if epithet is None:
            # Fallback epithet
            fallback = "tenax"
            if fallback not in occupied_names_in_genus:
                epithet = fallback
            else:
                # Add deterministic syllable suffix to make it unique
                syl = _hash_to_syllables(seed_hash)
                epithet = f"{fallback}{syl}"

        return genus, epithet

    @staticmethod
    def _generate_fish_genus(traits: Mapping[str, float]) -> str:
        aspect = traits.get("body_aspect", 0.5)
        fin = traits.get("fin_size", 0.5)
        eye = traits.get("eye_size", 0.5)
        social = traits.get("social_tendency", 0.5)
        agg = traits.get("aggression", 0.5)

        if social > 0.65:
            return "Synpinna"
        if social < 0.35:
            return "Monopinna"
        if agg < 0.35:
            return "Cryptichthys"
        if aspect < 0.35:
            return "Dolichopinna"
        if eye > 0.65:
            return "Megaophthalmichthys"
        if aspect > 0.65:
            return "Brachypinna"
        if fin > 0.65:
            return "Altichthys"

        return "Planctichthys"

    @staticmethod
    def _generate_microbe_genus(traits: Mapping[str, float]) -> str:
        motility = traits.get("motility_aggression", 0.5)
        swarming = traits.get("social_swarming", 0.5)
        shape = traits.get("shape_aspect", 0.5)
        elongation = traits.get("elongation_fins", 0.5)

        if shape < 0.3:
            if swarming > 0.6:
                return "Pelliculococcus"
            return "Coccobacter"
        if shape > 0.7:
            return "Bacillobacter"
        if elongation > 0.6:
            return "Helicovora"
        if motility > 0.6:
            return "Mobilibacter"
        if swarming > 0.6:
            return "Filamentobacter"

        return "Saccharobacter"

    @staticmethod
    def _get_fish_epithet(profile: TaxonomyProfile, trait: str) -> str | None:
        val = profile.traits.get(trait, 0.5)

        if trait in ("social_tendency", "social_mode"):
            return "gregarius" if val > 0.5 else "solitarius"
        if trait == "food_approach":
            food_app = int(round(val * 5))
            if food_app == 1:
                return "praesagus"
            if food_app == 3:
                return "insidians"
            if food_app == 4:
                return "erraticus"
        if trait == "threat_response":
            threat = int(round(val * 3))
            if threat == 0:
                return "fugax"
            if threat == 3:
                return "erraticus"
        if trait in ("fin_size", "tail_size"):
            if val > 0.6:
                return "longipinnis"
        if trait == "eye_size":
            if val > 0.6:
                return "macrophthalmus"
        if trait == "color_hue":
            h = val % 1.0
            if h < 0.04 or h >= 0.96:
                return "ruber"
            elif h < 0.22:
                return "aureus"
            elif h < 0.58:
                return "caeruleus"
        if trait == "pattern_type":
            pt = int(round(val * 5))
            if pt == 1:
                return "maculatus"
            if pt == 2:
                return "fasciatus"
        if trait == "aggression":
            return "vorax" if val > 0.5 else "tenax"
        if trait == "lifespan_modifier":
            return "longevus" if val > 0.6 else "tenax"
        if trait == "hunting_stamina":
            return "tenax"

        return None

    @staticmethod
    def _get_microbe_epithet(profile: TaxonomyProfile, trait: str) -> str | None:
        val = profile.traits.get(trait, 0.5)

        if trait == "social_swarming":
            return "gregarius" if val > 0.6 else "solitarius"
        if trait == "food_approach":
            food_app = int(round(val * 5))
            if food_app == 1:
                return "praesagus"
            if food_app == 3:
                return "insidians"
        if trait == "motility_aggression":
            return "rapax" if val > 0.6 else "mobilis"
        if trait == "metabolism_lifespan":
            return "dormiens" if val > 0.6 else "tenax"
        if trait == "texture_pattern":
            return "maculatus" if val > 0.6 else "tenax"
        if trait == "pigment_hue":
            h = val % 1.0
            if h < 0.04 or h >= 0.96:
                return "ruber"
            elif h < 0.22:
                return "aureus"
            elif h < 0.58:
                return "caeruleus"

        return None
