"""Tests for genome sanitization (defense against untrusted external data)."""

import math
import random

import pytest

from core.genetics import Genome
from core.genetics.sanitization import (
    sanitize_dict,
    sanitize_float,
    sanitize_float_params,
    sanitize_genome_dict,
    sanitize_int,
    sanitize_mate_preferences,
    sanitize_string,
    validate_external_genome,
)


class TestSanitizeFloat:
    def test_normal_float(self):
        assert sanitize_float(0.5) == 0.5

    def test_none_returns_default(self):
        assert sanitize_float(None, default=1.0) == 1.0

    def test_nan_returns_default(self):
        assert sanitize_float(float("nan"), default=0.0) == 0.0

    def test_inf_returns_default(self):
        assert sanitize_float(float("inf"), default=0.0) == 0.0
        assert sanitize_float(float("-inf"), default=0.0) == 0.0

    def test_string_number(self):
        assert sanitize_float("3.14", default=0.0) == pytest.approx(3.14)

    def test_non_numeric_string(self):
        assert sanitize_float("hello", default=0.0) == 0.0

    def test_boolean_rejected(self):
        assert sanitize_float(True, default=0.0) == 0.0

    def test_clamped_to_min(self):
        assert sanitize_float(-100, min_val=0.0) == 0.0

    def test_clamped_to_max(self):
        assert sanitize_float(100, max_val=1.0) == 1.0


class TestSanitizeInt:
    def test_normal_int(self):
        assert sanitize_int(5) == 5

    def test_float_truncated(self):
        assert sanitize_int(3.7) == 3

    def test_none_returns_default(self):
        assert sanitize_int(None, default=0) == 0

    def test_boolean_rejected(self):
        assert sanitize_int(True, default=0) == 0

    def test_clamped(self):
        assert sanitize_int(999, max_val=5) == 5


class TestSanitizeString:
    def test_normal_string(self):
        assert sanitize_string("hello_world") == "hello_world"

    def test_non_string_returns_default(self):
        assert sanitize_string(123, default="x") == "x"

    def test_truncated(self):
        long_str = "a" * 1000
        result = sanitize_string(long_str, max_length=10)
        assert len(result) == 10

    def test_unsafe_characters_rejected(self):
        # SQL injection attempt
        assert sanitize_string("'; DROP TABLE --", default="safe") == "safe"

    def test_shell_injection_rejected(self):
        assert sanitize_string("$(rm -rf /)", default="safe") == "safe"

    def test_allowed_characters(self):
        assert sanitize_string("my-policy_v2.0") == "my-policy_v2.0"


class TestSanitizeDict:
    def test_normal_dict(self):
        result = sanitize_dict({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_non_dict_returns_empty(self):
        assert sanitize_dict("not a dict") == {}
        assert sanitize_dict(None) == {}
        assert sanitize_dict([1, 2, 3]) == {}

    def test_too_many_keys_truncated(self):
        big = {f"k{i}": i for i in range(200)}
        result = sanitize_dict(big, max_keys=10)
        assert len(result) <= 10

    def test_deep_nesting_blocked(self):
        # Create deeply nested dict
        d = {"leaf": 1}
        for _ in range(20):
            d = {"nested": d}
        result = sanitize_dict(d, max_depth=3)
        # Should have been truncated
        depth = 0
        current = result
        while isinstance(current, dict) and "nested" in current:
            current = current["nested"]
            depth += 1
        assert depth <= 3

    def test_non_string_keys_skipped(self):
        result = sanitize_dict({1: "a", "b": 2})
        assert "b" in result
        assert len(result) == 1


class TestSanitizeFloatParams:
    def test_normal_params(self):
        result = sanitize_float_params({"speed": 0.5, "range": 1.2})
        assert result == {"speed": 0.5, "range": 1.2}

    def test_none_returns_none(self):
        assert sanitize_float_params(None) is None

    def test_non_dict_returns_none(self):
        assert sanitize_float_params("not a dict") is None

    def test_nan_values_replaced(self):
        result = sanitize_float_params({"speed": float("nan")})
        assert result is not None
        assert result["speed"] == 0.0

    def test_clamped_to_bounds(self):
        result = sanitize_float_params({"x": 100.0}, min_val=-5.0, max_val=5.0)
        assert result is not None
        assert result["x"] == 5.0

    def test_max_count_enforced(self):
        big = {f"p{i}": float(i) for i in range(100)}
        result = sanitize_float_params(big, max_count=5)
        assert result is not None
        assert len(result) <= 5


class TestSanitizeMatePreferences:
    def test_normal_preferences(self):
        result = sanitize_mate_preferences(
            {
                "prefer_similar_size": 0.7,
                "prefer_high_aggression": 0.8,
            }
        )
        assert result["prefer_similar_size"] == 0.7
        assert result["prefer_high_aggression"] == 0.8

    def test_weight_clamped_to_0_1(self):
        result = sanitize_mate_preferences({"prefer_similar_size": 5.0})
        assert result["prefer_similar_size"] == 1.0

    def test_non_dict_returns_empty(self):
        assert sanitize_mate_preferences(None) == {}
        assert sanitize_mate_preferences("bad") == {}


class TestSanitizeGenomeDict:
    def test_empty_dict(self):
        result = sanitize_genome_dict({})
        assert isinstance(result, dict)

    def test_non_dict_returns_empty(self):
        assert sanitize_genome_dict(None) == {}
        assert sanitize_genome_dict("bad") == {}
        assert sanitize_genome_dict(42) == {}

    def test_valid_genome_passes_through(self):
        rng = random.Random(42)
        genome = Genome.random(use_algorithm=True, rng=rng)
        data = genome.to_dict()
        result = sanitize_genome_dict(data)
        assert isinstance(result, dict)

    def test_nan_in_physical_traits(self):
        data = {
            "physical": {
                "size_modifier": float("nan"),
                "fin_size": float("inf"),
            }
        }
        result = sanitize_genome_dict(data)
        physical = result.get("physical", {})
        # NaN/Inf should be replaced with defaults
        assert not math.isnan(physical.get("size_modifier", 0))
        assert not math.isinf(physical.get("fin_size", 0))

    def test_out_of_range_traits_clamped(self):
        data = {
            "physical": {"size_modifier": 999.0},
            "behavioral": {"aggression": -5.0},
        }
        result = sanitize_genome_dict(data)
        assert result["physical"]["size_modifier"] <= 2.0  # Max bound
        assert result["behavioral"]["aggression"] >= 0.0  # Min bound

    def test_malicious_behavior_params_sanitized(self):
        data = {
            "behavioral": {
                "behavior": {
                    "type": "ComposableBehavior",
                    "threat_response": 999,  # Out of range
                    "parameters": {
                        "flee_speed": float("nan"),
                        "pursuit_speed": 999.0,
                    },
                }
            }
        }
        result = sanitize_genome_dict(data)
        behavior = result["behavioral"]["behavior"]
        assert behavior["threat_response"] <= 3  # Max valid enum
        assert not math.isnan(behavior["parameters"]["flee_speed"])
        assert behavior["parameters"]["pursuit_speed"] <= 1.4  # Max bound


class TestValidateExternalGenome:
    def test_valid_genome(self):
        rng = random.Random(42)
        genome = Genome.random(use_algorithm=True, rng=rng)
        result = validate_external_genome(genome.to_dict())
        assert result["valid"]
        assert len(result["issues"]) == 0

    def test_non_dict_is_invalid(self):
        result = validate_external_genome("bad data")
        assert not result["valid"]
        assert len(result["issues"]) > 0

    def test_missing_sections_warned(self):
        result = validate_external_genome({})
        assert len(result["warnings"]) > 0

    def test_nan_values_reported(self):
        data = {"physical": {"size_modifier": float("nan")}}
        result = validate_external_genome(data)
        assert any("NaN" in issue for issue in result["issues"])

    def test_always_returns_sanitized(self):
        data = {"physical": {"size_modifier": float("nan")}}
        result = validate_external_genome(data)
        assert "sanitized" in result
        assert isinstance(result["sanitized"], dict)
