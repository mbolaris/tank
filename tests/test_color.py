"""Tests for core.color module."""

import pytest
from core.color import hue_to_rgb, FISH_COLOR_SATURATION


class TestHueToRgb:
    """Tests for the hue_to_rgb color conversion function."""

    def test_returns_tuple_of_three_ints(self):
        """Should return a tuple of 3 integers."""
        result = hue_to_rgb(0.5)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(v, int) for v in result)

    def test_values_in_valid_range(self):
        """All RGB values should be between 0 and 255."""
        for hue in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
            r, g, b = hue_to_rgb(hue)
            assert 0 <= r <= 255, f"Red out of range for hue={hue}"
            assert 0 <= g <= 255, f"Green out of range for hue={hue}"
            assert 0 <= b <= 255, f"Blue out of range for hue={hue}"

    def test_low_saturation_stays_light(self):
        """With default saturation=0.3, colors should be pastel (light)."""
        r, g, b = hue_to_rgb(0.0, saturation=0.3)
        # All values should be above 178 (pastel range)
        assert r >= 178
        assert g >= 178
        assert b >= 178

    def test_full_saturation_gives_vivid_colors(self):
        """With saturation=1.0, should get vivid colors."""
        r, g, b = hue_to_rgb(0.0, saturation=1.0)
        # Red should be vivid (255) at hue=0
        assert r == 255
        assert g == 0
        assert b == 0

    def test_zero_saturation_gives_white(self):
        """With saturation=0.0, should get pure white."""
        r, g, b = hue_to_rgb(0.5, saturation=0.0)
        assert r == 255
        assert g == 255
        assert b == 255

    def test_hue_0_is_red_ish(self):
        """Hue 0.0 should be in the red range."""
        r, g, b = hue_to_rgb(0.0, saturation=1.0)
        assert r == 255
        assert g == 0

    def test_hue_third_is_green_ish(self):
        """Hue ~0.33 should be in the green range."""
        r, g, b = hue_to_rgb(0.33, saturation=1.0)
        assert g == 255

    def test_hue_two_thirds_is_blue_ish(self):
        """Hue ~0.66 should be in the blue range."""
        r, g, b = hue_to_rgb(0.66, saturation=1.0)
        assert b == 255


class TestFishColorSaturation:
    """Tests for the FISH_COLOR_SATURATION constant."""

    def test_saturation_is_float(self):
        """The saturation constant should be a float."""
        assert isinstance(FISH_COLOR_SATURATION, float)

    def test_saturation_in_valid_range(self):
        """Saturation should be between 0 and 1."""
        assert 0.0 <= FISH_COLOR_SATURATION <= 1.0
