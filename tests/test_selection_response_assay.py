from __future__ import annotations

from benchmarks.tank.selection_response_10k import score_samples
from tools.run_selection_response_assay import _aggregate_metadata


def test_selection_response_score_rewards_drift_with_retained_diversity():
    samples = [
        {
            "frame": 1000,
            "max_generation": 1,
            "population": 30,
            "diversity_score": 0.40,
            "traits": {
                "pursuit_aggression": 0.50,
                "prediction_skill": 0.50,
                "hunting_stamina": 0.50,
                "aggression": 0.50,
                "speed": 1.00,
                "size": 1.00,
            },
        },
        {
            "frame": 10000,
            "max_generation": 6,
            "population": 32,
            "diversity_score": 0.36,
            "traits": {
                "pursuit_aggression": 0.60,
                "prediction_skill": 0.40,
                "hunting_stamina": 0.58,
                "aggression": 0.51,
                "speed": 1.10,
                "size": 1.00,
            },
        },
    ]

    result = score_samples(samples, seed=42)

    assert result["score"] > 0.0
    assert result["metadata"]["selection_detected"] is True
    assert result["metadata"]["selected_trait_count"] == 4
    assert result["metadata"]["diversity_retention"] == 0.9


def test_selection_response_score_is_zero_without_directional_drift():
    samples = [
        {
            "frame": 1000,
            "max_generation": 1,
            "population": 30,
            "diversity_score": 0.40,
            "traits": {"pursuit_aggression": 0.50, "speed": 1.00},
        },
        {
            "frame": 10000,
            "max_generation": 6,
            "population": 31,
            "diversity_score": 0.40,
            "traits": {"pursuit_aggression": 0.51, "speed": 1.01},
        },
    ]

    result = score_samples(samples, seed=42)

    assert result["score"] == 0.0
    assert result["metadata"]["selection_detected"] is False


def test_multi_seed_aggregate_preserves_decomposition():
    per_seed = [
        {
            "seed": 42,
            "score": 10.0,
            "metadata": {
                "selection_detected": True,
                "selected_trait_fraction": 0.5,
                "drift_per_generation_pct": 2.0,
                "diversity_delta": -0.1,
                "diversity_retention": 0.8,
                "quality_per_generation": 0.9,
                "generation_rate_per_10k": 5.0,
                "diversity_last": 0.3,
            },
        },
        {
            "seed": 7,
            "score": 20.0,
            "metadata": {
                "selection_detected": True,
                "selected_trait_fraction": 1.0,
                "drift_per_generation_pct": 4.0,
                "diversity_delta": 0.0,
                "diversity_retention": 1.0,
                "quality_per_generation": 0.7,
                "generation_rate_per_10k": 7.0,
                "diversity_last": 0.4,
            },
        },
    ]

    metadata = _aggregate_metadata(per_seed)

    assert metadata["mean_score"] == 15.0
    assert metadata["all_selection_detected"] is True
    assert metadata["mean_selected_trait_fraction"] == 0.75
    assert metadata["min_final_diversity"] == 0.3
