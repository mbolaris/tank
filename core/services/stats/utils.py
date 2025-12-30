"""Utility functions for statistics calculation.

This module provides shared helper functions used across stat calculators.
"""

from typing import Any, Dict, List

from core.statistics_utils import compute_meta_stats


def calculate_meta_stats(traits: List[Any], prefix: str) -> Dict[str, Any]:
    """Calculate meta-statistics (mutation rate, strength, HGT) for a list of traits.

    Args:
        traits: List of GeneticTrait objects
        prefix: Prefix for the output keys (e.g., 'adult_size')

    Returns:
        Dictionary with mean and std dev for mutation rate, strength, and HGT
    """
    meta = compute_meta_stats(traits)
    return {
        f"{prefix}_mut_rate_mean": meta.mut_rate_mean,
        f"{prefix}_mut_rate_std": meta.mut_rate_std,
        f"{prefix}_mut_strength_mean": meta.mut_strength_mean,
        f"{prefix}_mut_strength_std": meta.mut_strength_std,
        f"{prefix}_hgt_prob_mean": meta.hgt_prob_mean,
        f"{prefix}_hgt_prob_std": meta.hgt_prob_std,
    }


def humanize_gene_label(key: str) -> str:
    """Convert a gene key to a human-readable label.

    Args:
        key: Snake_case gene identifier

    Returns:
        Human-readable label
    """
    special = {
        "size_modifier": "Size Modifier",
        "adult_size": "Adult Size",
        "template_id": "Template",
        "pattern_type": "Pattern",
        "pattern_intensity": "Pattern Intensity",
        "lifespan_modifier": "Lifespan Mod",
    }
    if key in special:
        return special[key]
    return " ".join(part.capitalize() for part in key.split("_"))
