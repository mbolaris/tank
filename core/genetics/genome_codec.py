"""Genome serialization/deserialization helpers.

This module is the persistence/transfer boundary for `core.genetics.genome.Genome`.
Keeping codecs separate from the domain model reduces coupling and makes it easier
to evolve formats safely.
"""

from __future__ import annotations

import logging
import random as pyrandom
from typing import Any, Callable

from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS, normalize_mate_preferences
from core.genetics.physical import PHYSICAL_TRAIT_SPECS
from core.genetics.trait import (
    apply_trait_meta_from_dict,
    apply_trait_meta_to_trait,
    apply_trait_values_from_dict,
    trait_meta_for_trait,
    trait_meta_to_dict,
    trait_values_to_dict,
)

logger = logging.getLogger(__name__)


def genome_to_dict(
    genome: Any,
    *,
    schema_version: int,
) -> dict[str, Any]:
    """Serialize a genome into JSON-compatible primitives."""
    behavior = genome.behavioral.behavior.value if genome.behavioral.behavior else None
    behavior_dict = behavior.to_dict() if behavior is not None else None
    poker_strategy = (
        genome.behavioral.poker_strategy.value if genome.behavioral.poker_strategy else None
    )
    poker_strategy_dict = poker_strategy.to_dict() if poker_strategy is not None else None

    values: dict[str, Any] = {}
    values.update(trait_values_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    values.update(trait_values_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    trait_meta: dict[str, dict[str, float]] = {}
    trait_meta.update(trait_meta_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    trait_meta.update(trait_meta_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    # Collect trait metadata for complex traits
    for name, trait in (
        ("behavior", genome.behavioral.behavior),
        ("poker_strategy", genome.behavioral.poker_strategy),
        ("mate_preferences", genome.behavioral.mate_preferences),
    ):
        if trait is not None:
            meta = trait_meta_for_trait(trait)
            if meta:
                trait_meta[name] = meta

    # Serialize code policy fields
    code_policy_kind = (
        genome.behavioral.code_policy_kind.value
        if genome.behavioral.code_policy_kind and genome.behavioral.code_policy_kind.value
        else None
    )
    code_policy_component_id = (
        genome.behavioral.code_policy_component_id.value
        if genome.behavioral.code_policy_component_id
        and genome.behavioral.code_policy_component_id.value
        else None
    )
    code_policy_params = (
        dict(genome.behavioral.code_policy_params.value)
        if genome.behavioral.code_policy_params and genome.behavioral.code_policy_params.value
        else None
    )

    # Collect trait metadata for code policy traits
    for name, trait in (
        ("code_policy_kind", genome.behavioral.code_policy_kind),
        ("code_policy_component_id", genome.behavioral.code_policy_component_id),
        ("code_policy_params", genome.behavioral.code_policy_params),
    ):
        if trait is not None:
            meta = trait_meta_for_trait(trait)
            if meta:
                trait_meta[name] = meta

    return {
        "schema_version": schema_version,
        **values,
        # Behavior (new system - replaces behavior_algorithm + poker_algorithm)
        "behavior": behavior_dict,
        # Poker strategy for in-game betting decisions
        "poker_strategy": poker_strategy_dict,
        "mate_preferences": (
            dict(genome.behavioral.mate_preferences.value)
            if genome.behavioral.mate_preferences
            else {}
        ),
        # Code policy fields (optional, for linking to CodePool components)
        "code_policy_kind": code_policy_kind,
        "code_policy_component_id": code_policy_component_id,
        "code_policy_params": code_policy_params,
        "trait_meta": trait_meta,
    }


def genome_from_dict(
    data: dict[str, Any],
    *,
    schema_version_expected: int,
    genome_factory: Callable[[], Any],
    rng: pyrandom.Random | None = None,
) -> Any:
    """Deserialize a genome from JSON-compatible primitives.

    Unknown fields are ignored; missing fields keep randomized defaults from `genome_factory`.
    """
    from core.util.rng import require_rng_param

    rng = require_rng_param(rng, "__init__")
    genome = genome_factory()

    schema_version = data.get("schema_version")
    if schema_version is not None and schema_version != schema_version_expected:
        logger.debug(
            "Deserializing genome schema_version=%s (expected %s)",
            schema_version,
            schema_version_expected,
        )

    apply_trait_values_from_dict(PHYSICAL_TRAIT_SPECS, genome.physical, data)
    apply_trait_values_from_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral, data)

    # Mate preferences (dictionary trait)
    mate_preferences = data.get("mate_preferences")
    if isinstance(mate_preferences, dict):
        from core.genetics.trait import GeneticTrait

        normalized = normalize_mate_preferences(
            {str(key): value for key, value in mate_preferences.items()},
            physical=genome.physical,
        )
        if genome.behavioral.mate_preferences is None:
            genome.behavioral.mate_preferences = GeneticTrait(normalized)
        else:
            genome.behavioral.mate_preferences.value = normalized

    # Evolvability metadata (mutation_rate/mutation_strength/hgt_probability)
    trait_meta = data.get("trait_meta")
    if isinstance(trait_meta, dict):
        try:
            apply_trait_meta_from_dict(PHYSICAL_TRAIT_SPECS, genome.physical, trait_meta)
            apply_trait_meta_from_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral, trait_meta)
        except Exception:
            logger.debug("Failed applying trait_meta; continuing with defaults", exc_info=True)

        # Apply metadata for non-spec traits on BehavioralTraits.
        for name, trait in (
            ("behavior", genome.behavioral.behavior),
            ("poker_strategy", genome.behavioral.poker_strategy),
            ("mate_preferences", genome.behavioral.mate_preferences),
        ):
            if trait is not None:
                meta = trait_meta.get(name)
                if isinstance(meta, dict):
                    apply_trait_meta_to_trait(trait, meta)

    # Behavior (new system)
    try:
        from core.algorithms.composable import ComposableBehavior
        from core.genetics.trait import GeneticTrait

        behavior_data = data.get("behavior")
        if behavior_data and isinstance(behavior_data, dict):
            cb = ComposableBehavior.from_dict(behavior_data)
            if genome.behavioral.behavior is None:
                genome.behavioral.behavior = GeneticTrait(cb)
            else:
                genome.behavioral.behavior.value = cb
    except Exception:
        logger.debug("Failed deserializing behavior; keeping default", exc_info=True)

    # Poker strategy (in-game betting decisions)
    try:
        strat_data = data.get("poker_strategy")
        if strat_data:
            from core.genetics.trait import GeneticTrait
            from core.poker.strategy.implementations import PokerStrategyAlgorithm

            strat = PokerStrategyAlgorithm.from_dict(strat_data)
            if genome.behavioral.poker_strategy is None:
                genome.behavioral.poker_strategy = GeneticTrait(strat)
            else:
                genome.behavioral.poker_strategy.value = strat
    except Exception:
        logger.debug("Failed deserializing poker_strategy; keeping default", exc_info=True)

    # Code policy fields (optional, for linking to CodePool components)
    try:
        from core.genetics.trait import GeneticTrait

        # code_policy_kind
        cp_kind = data.get("code_policy_kind")
        if cp_kind is not None:
            if genome.behavioral.code_policy_kind is None:
                genome.behavioral.code_policy_kind = GeneticTrait(str(cp_kind))
            else:
                genome.behavioral.code_policy_kind.value = str(cp_kind)

        # code_policy_component_id
        cp_id = data.get("code_policy_component_id")
        if cp_id is not None:
            if genome.behavioral.code_policy_component_id is None:
                genome.behavioral.code_policy_component_id = GeneticTrait(str(cp_id))
            else:
                genome.behavioral.code_policy_component_id.value = str(cp_id)

        # code_policy_params
        cp_params = data.get("code_policy_params")
        if cp_params is not None and isinstance(cp_params, dict):
            # Validate and coerce param values to floats
            validated_params = {}
            for key, val in cp_params.items():
                try:
                    validated_params[str(key)] = float(val)
                except (TypeError, ValueError):
                    logger.debug("Invalid code_policy_params[%s]=%r, skipping", key, val)
            if genome.behavioral.code_policy_params is None:
                genome.behavioral.code_policy_params = GeneticTrait(validated_params)
            else:
                genome.behavioral.code_policy_params.value = validated_params

        # Apply trait metadata for code policy traits
        if isinstance(trait_meta, dict):
            for name, trait in (
                ("code_policy_kind", genome.behavioral.code_policy_kind),
                ("code_policy_component_id", genome.behavioral.code_policy_component_id),
                ("code_policy_params", genome.behavioral.code_policy_params),
            ):
                if trait is not None:
                    meta = trait_meta.get(name)
                    if isinstance(meta, dict):
                        apply_trait_meta_to_trait(trait, meta)
    except Exception:
        logger.debug("Failed deserializing code_policy; keeping defaults", exc_info=True)

    invalidate = getattr(genome, "invalidate_caches", None)
    if callable(invalidate):
        invalidate()
    return genome


def genome_debug_snapshot(genome: Any) -> dict[str, Any]:
    """Return a compact, stable dict for logging/debugging."""
    trait_meta: dict[str, dict[str, float]] = {}
    trait_meta.update(trait_meta_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    trait_meta.update(trait_meta_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    values: dict[str, Any] = {}
    values.update(trait_values_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    values.update(trait_values_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    def _algo_name(algo: Any) -> str | None:
        if algo is None:
            return None
        return type(algo).__name__

    # Get behavior info
    behavior = genome.behavioral.behavior
    behavior_info = None
    if behavior and behavior.value:
        cb = behavior.value
        behavior_info = {
            "behavior_id": cb.behavior_id,
            "short_description": cb.short_description,
        }

    # Get code policy info (if present)
    code_policy_info = None
    cp_kind = genome.behavioral.code_policy_kind
    cp_id = genome.behavioral.code_policy_component_id
    if cp_id and cp_id.value:
        code_policy_info = {
            "kind": cp_kind.value if cp_kind else None,
            "component_id": cp_id.value,
            "has_params": bool(
                genome.behavioral.code_policy_params and genome.behavioral.code_policy_params.value
            ),
        }

    return {
        **values,
        "trait_meta": trait_meta,
        "behavior": behavior_info,
        "poker_strategy_type": _algo_name(
            genome.behavioral.poker_strategy.value if genome.behavioral.poker_strategy else None
        ),
        "code_policy": code_policy_info,
        "derived": {
            "speed_modifier": getattr(genome, "speed_modifier", None),
            "metabolism_rate": getattr(genome, "metabolism_rate", None),
            "vision_range": getattr(genome, "vision_range", None),
        },
    }
