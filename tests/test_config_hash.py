"""Tests for champion config-hash guarding (IMPROVEMENT_PROPOSALS.md 1.1)."""

import core.config.fish as fish_config
from core.solutions.config_hash import compute_config_hash, core_config_snapshot
from tools.validate_improvement import check_config_compatibility, update_champion_data


class TestComputeConfigHash:
    def test_stable_across_calls(self):
        h1 = compute_config_hash("tank/survival_5k", 42, {"frames": 5000})
        h2 = compute_config_hash("tank/survival_5k", 42, {"frames": 5000})
        assert h1 == h2

    def test_changes_with_seed(self):
        assert compute_config_hash("tank/survival_5k", 42) != compute_config_hash(
            "tank/survival_5k", 43
        )

    def test_changes_with_benchmark_id(self):
        assert compute_config_hash("tank/survival_5k", 42) != compute_config_hash(
            "tank/ecosystem_health_10k", 42
        )

    def test_changes_with_benchmark_config(self):
        assert compute_config_hash("tank/survival_5k", 42, {"frames": 5000}) != compute_config_hash(
            "tank/survival_5k", 42, {"frames": 6000}
        )

    def test_changes_with_core_config(self, monkeypatch):
        before = compute_config_hash("tank/survival_5k", 42)
        monkeypatch.setattr(fish_config, "EXISTENCE_ENERGY_COST", 999.0)
        after = compute_config_hash("tank/survival_5k", 42)
        assert before != after

    def test_snapshot_covers_sim_config(self):
        snapshot = core_config_snapshot()
        assert "EXISTENCE_ENERGY_COST" in snapshot["fish"]
        # Rendering/transport config must NOT invalidate champions.
        assert "display" not in snapshot
        assert "server" not in snapshot


class TestCheckConfigCompatibility:
    def test_match_allows_comparison(self):
        result = {"score": 1.0, "config_hash": "abc"}
        champion = {"champion": {"score": 2.0, "config_hash": "abc"}}
        assert check_config_compatibility(result, champion) is None

    def test_mismatch_refuses_comparison(self):
        result = {"score": 1.0, "config_hash": "abc"}
        champion = {"champion": {"score": 2.0, "config_hash": "def"}}
        error = check_config_compatibility(result, champion)
        assert error is not None
        assert "re-baseline" in error

    def test_legacy_champion_without_hash_allowed(self):
        result = {"score": 1.0, "config_hash": "abc"}
        champion = {"champion": {"score": 2.0}}
        assert check_config_compatibility(result, champion) is None

    def test_no_champion_allowed(self):
        assert check_config_compatibility({"score": 1.0, "config_hash": "abc"}, None) is None


class TestChampionUpdateCarriesHash:
    def test_update_champion_data_preserves_config_hash(self):
        result = {"score": 3.0, "seed": 42, "benchmark_id": "tank/x", "config_hash": "abc"}
        updated = update_champion_data(None, result)
        assert updated["champion"]["config_hash"] == "abc"

    def test_update_champion_data_without_hash(self):
        result = {"score": 3.0, "seed": 42, "benchmark_id": "tank/x"}
        updated = update_champion_data(None, result)
        assert "config_hash" not in updated["champion"]
