import os
import tempfile
import unittest

from tools import run_bench, validate_improvement


class TestRunBench(unittest.TestCase):
    def test_load_benchmark(self):
        # Create a dummy benchmark file
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("BENCHMARK_ID = 'test/bench'\n")
            f.write("def run(seed):\n")
            f.write("    return {'score': 100, 'seed': seed}\n")
            bench_path = f.name

        try:
            module = run_bench.load_benchmark_module(bench_path)
            self.assertEqual(module.BENCHMARK_ID, "test/bench")
            result = module.run(42)
            self.assertEqual(result["score"], 100)
            self.assertEqual(result["seed"], 42)
        finally:
            os.unlink(bench_path)


class TestValidateImprovement(unittest.TestCase):
    def test_detect_improvement(self):
        champion = {"champion": {"score": 100.0, "algorithm": "OldAlgo"}}
        result = {"score": 110.0, "metadata": {"algorithm": "NewAlgo"}}

        # Test improvement
        self.assertTrue(validate_improvement.is_improvement(result, champion))

        # Test regression
        result["score"] = 90.0
        self.assertFalse(validate_improvement.is_improvement(result, champion))

        # Test tie
        result["score"] = 100.0
        self.assertFalse(validate_improvement.is_improvement(result, champion))

    def test_update_champion(self):
        champion_data = {
            "benchmark_id": "test/bench",
            "version": 1,
            "champion": {"score": 100.0, "commit": "old_commit", "timestamp": 1234567890},
            "history": [],
        }

        new_result = {
            "score": 110.0,
            "metadata": {"algorithm": "NewAlgo"},
            "runtime_seconds": 10.0,
            "seed": 42,
            "benchmark_id": "test/bench",
            "score_breakdown": {"metric_a": 10.5, "metric_b": 20.0},
        }

        updated = validate_improvement.update_champion_data(champion_data, new_result)

        self.assertEqual(updated["champion"]["score"], 110.0)
        self.assertEqual(updated["version"], 2)
        self.assertEqual(len(updated["history"]), 1)
        self.assertEqual(updated["history"][0]["score"], 100.0)
        self.assertEqual(updated["history"][0]["commit"], "old_commit")
        self.assertEqual(
            updated["champion"]["score_breakdown"], {"metric_a": 10.5, "metric_b": 20.0}
        )

    def test_matrix_improvement_tightened_rules(self) -> None:
        # Champion has matrix results: 3 seeds, score 100 on each
        champion = {
            "champion": {
                "score": 100.0,
                "per_seed": {
                    "1": {"score": 100.0},
                    "2": {"score": 100.0},
                    "3": {"score": 100.0},
                },
                "scores": [100.0, 100.0, 100.0],
                "seeds": [1, 2, 3],
            }
        }

        # Case 1: 2 tiny wins + 1 huge loss (catastrophic regression)
        # Seed 1: 101 (+1)
        # Seed 2: 101 (+1)
        # Seed 3: 10 (-90%) -> drops by > 10%
        result_catastrophic = {
            "score": 70.67,
            "per_seed": {
                "1": {"score": 101.0},
                "2": {"score": 101.0},
                "3": {"score": 10.0},
            },
            "scores": [101.0, 101.0, 10.0],
            "seeds": [1, 2, 3],
        }
        self.assertFalse(validate_improvement.is_improvement(result_catastrophic, champion))

        # Case 2: Mean did not improve
        # Seed 1: 101 (+1)
        # Seed 2: 101 (+1)
        # Seed 3: 95 (-5%) -> acceptable drop under 10%, but mean is (101+101+95)/3 = 99 < 100
        result_mean_worse = {
            "score": 99.0,
            "per_seed": {
                "1": {"score": 101.0},
                "2": {"score": 101.0},
                "3": {"score": 95.0},
            },
            "scores": [101.0, 101.0, 95.0],
            "seeds": [1, 2, 3],
        }
        self.assertFalse(validate_improvement.is_improvement(result_mean_worse, champion))

        # Case 3: Majority did not win (1 win, 2 ties)
        # Seed 1: 101 (+1)
        # Seed 2: 100 (0)
        # Seed 3: 100 (0)
        # Mean is (101+100+100)/3 = 100.33 > 100
        result_no_majority = {
            "score": 100.33,
            "per_seed": {
                "1": {"score": 101.0},
                "2": {"score": 100.0},
                "3": {"score": 100.0},
            },
            "scores": [101.0, 100.0, 100.0],
            "seeds": [1, 2, 3],
        }
        self.assertFalse(validate_improvement.is_improvement(result_no_majority, champion))

        # Case 4: A real improvement (2 wins + 1 acceptable small loss, and mean improves)
        # Seed 1: 105 (+5)
        # Seed 2: 105 (+5)
        # Seed 3: 95 (-5%) -> drop under 10%
        # Mean is (105+105+95)/3 = 101.67 > 100
        result_valid_improvement = {
            "score": 101.67,
            "per_seed": {
                "1": {"score": 105.0},
                "2": {"score": 105.0},
                "3": {"score": 95.0},
            },
            "scores": [105.0, 105.0, 95.0],
            "seeds": [1, 2, 3],
        }
        self.assertTrue(validate_improvement.is_improvement(result_valid_improvement, champion))
