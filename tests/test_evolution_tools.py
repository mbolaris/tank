import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add tools directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools")))

import run_bench
import validate_improvement


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
        }

        updated = validate_improvement.update_champion_data(champion_data, new_result)

        self.assertEqual(updated["champion"]["score"], 110.0)
        self.assertEqual(updated["version"], 2)
        self.assertEqual(len(updated["history"]), 1)
        self.assertEqual(updated["history"][0]["score"], 100.0)
        self.assertEqual(updated["history"][0]["commit"], "old_commit")
