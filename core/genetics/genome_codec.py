"""Genome serialization/deserialization helpers.

This module is the persistence/transfer boundary for `core.genetics.genome.Genome`.
Keeping codecs separate from the domain model reduces coupling and makes it easier
to evolve formats safely.
"""

from __future__ import annotations

import logging
import random as pyrandom
from typing import Any, Callable, Dict, Optional

from core.genetics.behavioral import BEHAVIORAL_TRAIT_SPECS
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
    behavior_algorithm: Optional[Dict[str, Any]] = None,
    poker_algorithm: Optional[Dict[str, Any]] = None,
    poker_strategy_algorithm: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Serialize a genome into JSON-compatible primitives."""

    def _algorithm_dict(override: Optional[Dict[str, Any]], algo: Any) -> Optional[Dict[str, Any]]:
        if override is not None:
            return override
        if algo is None:
            return None
        return algo.to_dict()

    behavior_algorithm_dict = _algorithm_dict(
        behavior_algorithm, genome.behavioral.behavior_algorithm.value
    )
    poker_algorithm_dict = _algorithm_dict(
        poker_algorithm, genome.behavioral.poker_algorithm.value
    )
    poker_strategy_dict = _algorithm_dict(
        poker_strategy_algorithm,
        genome.behavioral.poker_strategy_algorithm.value,
    )

    values: Dict[str, Any] = {}
    values.update(trait_values_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    values.update(trait_values_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    trait_meta: Dict[str, Dict[str, float]] = {}
    trait_meta.update(trait_meta_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    trait_meta.update(trait_meta_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    for name, trait in (
        ("behavior_algorithm", genome.behavioral.behavior_algorithm),
        ("poker_algorithm", genome.behavioral.poker_algorithm),
        ("poker_strategy_algorithm", genome.behavioral.poker_strategy_algorithm),
        ("mate_preferences", genome.behavioral.mate_preferences),
    ):
        meta = trait_meta_for_trait(trait)
        if meta:
            trait_meta[name] = meta

    return {
        "schema_version": schema_version,
        **values,
        # Behavioral complex traits
        "behavior_algorithm": behavior_algorithm_dict,
        "poker_algorithm": poker_algorithm_dict,
        "poker_strategy_algorithm": poker_strategy_dict,
        "mate_preferences": dict(genome.behavioral.mate_preferences.value),
        # Non-genetic (but persistable) state
        "learned_behaviors": dict(genome.learned_behaviors),
        "epigenetic_modifiers": dict(genome.epigenetic_modifiers),
        "trait_meta": trait_meta,
    }


def genome_from_dict(
    data: Dict[str, Any],
    *,
    schema_version_expected: int,
    genome_factory: Callable[[], Any],
    rng: Optional[pyrandom.Random] = None,
) -> Any:
    """Deserialize a genome from JSON-compatible primitives.

    Unknown fields are ignored; missing fields keep randomized defaults from `genome_factory`.
    """
    rng = rng or pyrandom
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
        genome.behavioral.mate_preferences.value = {
            str(key): float(value) for key, value in mate_preferences.items()
        }

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
            ("behavior_algorithm", genome.behavioral.behavior_algorithm),
            ("poker_algorithm", genome.behavioral.poker_algorithm),
            ("poker_strategy_algorithm", genome.behavioral.poker_strategy_algorithm),
            ("mate_preferences", genome.behavioral.mate_preferences),
        ):
            meta = trait_meta.get(name)
            if isinstance(meta, dict):
                apply_trait_meta_to_trait(trait, meta)

    # Non-genetic (but persistable) state
    learned = data.get("learned_behaviors")
    if isinstance(learned, dict):
        genome.learned_behaviors = {str(key): float(value) for key, value in learned.items()}
    epigenetic = data.get("epigenetic_modifiers")
    if isinstance(epigenetic, dict):
        genome.epigenetic_modifiers = {str(key): float(value) for key, value in epigenetic.items()}

    # Algorithms
    try:
        from core.algorithms import behavior_from_dict

        behavior_data = data.get("behavior_algorithm")
        if behavior_data:
            genome.behavioral.behavior_algorithm.value = behavior_from_dict(behavior_data)
            if genome.behavioral.behavior_algorithm.value is None:
                logger.warning("Failed to deserialize behavior_algorithm; keeping default")

        poker_data = data.get("poker_algorithm")
        if poker_data:
            genome.behavioral.poker_algorithm.value = behavior_from_dict(poker_data)
            if genome.behavioral.poker_algorithm.value is None:
                logger.warning("Failed to deserialize poker_algorithm; keeping default")
    except Exception:
        logger.debug("Failed deserializing behavior algorithms; keeping defaults", exc_info=True)

    try:
        strat_data = data.get("poker_strategy_algorithm")
        if strat_data:
            from core.poker.strategy.implementations import PokerStrategyAlgorithm

            genome.behavioral.poker_strategy_algorithm.value = (
                PokerStrategyAlgorithm.from_dict(strat_data)
            )
    except Exception:
        logger.debug("Failed deserializing poker_strategy_algorithm; keeping default", exc_info=True)

    invalidate = getattr(genome, "invalidate_caches", None)
    if callable(invalidate):
        invalidate()
    return genome


def genome_debug_snapshot(genome: Any) -> Dict[str, Any]:
    """Return a compact, stable dict for logging/debugging."""
    trait_meta: Dict[str, Dict[str, float]] = {}
    trait_meta.update(trait_meta_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    trait_meta.update(trait_meta_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    values: Dict[str, Any] = {}
    values.update(trait_values_to_dict(PHYSICAL_TRAIT_SPECS, genome.physical))
    values.update(trait_values_to_dict(BEHAVIORAL_TRAIT_SPECS, genome.behavioral))

    def _algo_name(algo: Any) -> Optional[str]:
        if algo is None:
            return None
        return type(algo).__name__

    return {
        **values,
        "trait_meta": trait_meta,
        "learned_behaviors_count": len(getattr(genome, "learned_behaviors", {}) or {}),
        "epigenetic_modifiers_count": len(getattr(genome, "epigenetic_modifiers", {}) or {}),
        "behavior_algorithm_type": _algo_name(
            genome.behavioral.behavior_algorithm.value
        ),
        "poker_algorithm_type": _algo_name(genome.behavioral.poker_algorithm.value),
        "poker_strategy_algorithm_type": _algo_name(
            genome.behavioral.poker_strategy_algorithm.value
        ),
        "derived": {
            "speed_modifier": getattr(genome, "speed_modifier", None),
            "metabolism_rate": getattr(genome, "metabolism_rate", None),
            "vision_range": getattr(genome, "vision_range", None),
        },
    }
