"""Tests for the solution tracking and comparison system.

This module tests the core functionality of the solution tracking system,
including solution creation, serialization, benchmarking, and comparison.
"""

import json
import os
import tempfile
from datetime import datetime

import pytest

from core.solutions import (
    SolutionBenchmark,
    SolutionRecord,
    SolutionTracker,
)
from core.solutions.benchmark import SolutionBenchmarkConfig
from core.solutions.models import (
    BenchmarkResult,
    SolutionComparison,
    SolutionMetadata,
)


class TestSolutionMetadata:
    """Tests for SolutionMetadata."""

    def test_create_metadata(self):
        """Test creating solution metadata."""
        metadata = SolutionMetadata(
            solution_id="test_123",
            name="Test Solution",
            description="A test solution",
            author="tester",
            submitted_at="2024-01-01T00:00:00",
        )

        assert metadata.solution_id == "test_123"
        assert metadata.name == "Test Solution"
        assert metadata.author == "tester"

    def test_metadata_serialization(self):
        """Test metadata to_dict and from_dict."""
        metadata = SolutionMetadata(
            solution_id="test_123",
            name="Test Solution",
            description="A test solution",
            author="tester",
            submitted_at="2024-01-01T00:00:00",
            generation=5,
            fish_id=42,
        )

        data = metadata.to_dict()
        restored = SolutionMetadata.from_dict(data)

        assert restored.solution_id == metadata.solution_id
        assert restored.name == metadata.name
        assert restored.generation == metadata.generation
        assert restored.fish_id == metadata.fish_id


class TestBenchmarkResult:
    """Tests for BenchmarkResult."""

    def test_create_result(self):
        """Test creating benchmark result."""
        result = BenchmarkResult(
            per_opponent={"balanced": 5.0, "tight_aggressive": 10.0},
            weighted_bb_per_100=7.5,
            total_hands_played=1000,
            elo_rating=1450.0,
            skill_tier="intermediate",
        )

        assert result.elo_rating == 1450.0
        assert result.per_opponent["balanced"] == 5.0

    def test_result_serialization(self):
        """Test benchmark result serialization."""
        result = BenchmarkResult(
            per_opponent={"balanced": 5.0},
            weighted_bb_per_100=5.0,
            elo_rating=1400.0,
            confidence_intervals={"balanced": (-2.0, 12.0)},
            skill_tier="intermediate",
            evaluated_at="2024-01-01T00:00:00",
        )

        data = result.to_dict()
        restored = BenchmarkResult.from_dict(data)

        assert restored.elo_rating == result.elo_rating
        assert restored.per_opponent == result.per_opponent
        assert restored.confidence_intervals["balanced"] == (-2.0, 12.0)


class TestSolutionRecord:
    """Tests for SolutionRecord."""

    def test_create_solution(self):
        """Test creating a solution record."""
        metadata = SolutionMetadata(
            solution_id="test_123",
            name="Test Solution",
            description="Test",
            author="tester",
            submitted_at="2024-01-01T00:00:00",
        )

        solution = SolutionRecord(
            metadata=metadata,
            behavior_algorithm={"class": "GreedyFoodSeeker", "parameters": {}},
        )

        assert solution.metadata.solution_id == "test_123"
        assert solution.behavior_algorithm["class"] == "GreedyFoodSeeker"

    def test_solution_hash(self):
        """Test solution hash computation."""
        metadata = SolutionMetadata(
            solution_id="test_1",
            name="Test",
            description="Test",
            author="tester",
            submitted_at="2024-01-01T00:00:00",
        )

        sol1 = SolutionRecord(
            metadata=metadata,
            behavior_algorithm={"class": "A", "parameters": {"x": 1}},
        )

        # Same strategy should have same hash
        metadata2 = SolutionMetadata(
            solution_id="test_2",
            name="Other",
            description="Other",
            author="other",
            submitted_at="2024-01-02T00:00:00",
        )
        sol2 = SolutionRecord(
            metadata=metadata2,
            behavior_algorithm={"class": "A", "parameters": {"x": 1}},
        )

        assert sol1.compute_hash() == sol2.compute_hash()

        # Different strategy should have different hash
        sol3 = SolutionRecord(
            metadata=metadata,
            behavior_algorithm={"class": "B", "parameters": {"x": 2}},
        )

        assert sol1.compute_hash() != sol3.compute_hash()

    def test_solution_serialization(self):
        """Test solution save and load."""
        metadata = SolutionMetadata(
            solution_id="test_save",
            name="Save Test",
            description="Testing save/load",
            author="tester",
            submitted_at=datetime.utcnow().isoformat(),
        )

        solution = SolutionRecord(
            metadata=metadata,
            behavior_algorithm={"class": "TestAlgo", "parameters": {"a": 1, "b": 2}},
            capture_stats={"wins": 10, "losses": 5},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = solution.save(tmpdir)
            assert os.path.exists(filepath)

            loaded = SolutionRecord.load(filepath)
            assert loaded.metadata.solution_id == solution.metadata.solution_id
            assert loaded.behavior_algorithm == solution.behavior_algorithm
            assert loaded.capture_stats == solution.capture_stats

    def test_solution_summary(self):
        """Test solution summary generation."""
        metadata = SolutionMetadata(
            solution_id="test_summary",
            name="Summary Test",
            description="Test",
            author="tester",
            submitted_at="2024-01-01T00:00:00",
        )

        solution = SolutionRecord(
            metadata=metadata,
            behavior_algorithm={"class": "TestAlgo"},
            benchmark_result=BenchmarkResult(
                elo_rating=1500.0,
                skill_tier="advanced",
                weighted_bb_per_100=8.5,
            ),
        )

        summary = solution.get_summary()
        assert "Summary Test" in summary
        assert "1500" in summary
        assert "advanced" in summary


class TestSolutionTracker:
    """Tests for SolutionTracker."""

    def test_tracker_initialization(self):
        """Test tracker initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = SolutionTracker(solutions_dir=tmpdir)
            assert os.path.exists(tmpdir)

    def test_save_and_load_solutions(self):
        """Test saving and loading solutions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = SolutionTracker(solutions_dir=tmpdir)

            # Create and save a solution
            metadata = SolutionMetadata(
                solution_id="track_test",
                name="Tracker Test",
                description="Test",
                author="tester",
                submitted_at=datetime.utcnow().isoformat(),
            )
            solution = SolutionRecord(metadata=metadata)
            tracker.save_solution(solution)

            # Load all solutions
            loaded = tracker.load_all_solutions()
            assert len(loaded) == 1
            assert loaded[0].metadata.solution_id == "track_test"

    def test_duplicate_detection(self):
        """Test duplicate solution detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = SolutionTracker(solutions_dir=tmpdir)

            metadata1 = SolutionMetadata(
                solution_id="dup_1",
                name="First",
                description="Test",
                author="tester",
                submitted_at=datetime.utcnow().isoformat(),
            )
            sol1 = SolutionRecord(
                metadata=metadata1,
                behavior_algorithm={"class": "Same", "parameters": {}},
            )

            # Simulate capture
            tracker._captured_hashes.add(sol1.compute_hash())

            # Same strategy, different metadata
            metadata2 = SolutionMetadata(
                solution_id="dup_2",
                name="Second",
                description="Test",
                author="other",
                submitted_at=datetime.utcnow().isoformat(),
            )
            sol2 = SolutionRecord(
                metadata=metadata2,
                behavior_algorithm={"class": "Same", "parameters": {}},
            )

            assert tracker.is_duplicate(sol2)

    def test_leaderboard_generation(self):
        """Test leaderboard generation from solutions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = SolutionTracker(solutions_dir=tmpdir)

            # Create solutions with different ratings
            for i, (name, elo) in enumerate([
                ("Best", 1600),
                ("Middle", 1400),
                ("Worst", 1200),
            ]):
                metadata = SolutionMetadata(
                    solution_id=f"lead_{i}",
                    name=name,
                    description="Test",
                    author="tester",
                    submitted_at=datetime.utcnow().isoformat(),
                )
                solution = SolutionRecord(
                    metadata=metadata,
                    benchmark_result=BenchmarkResult(elo_rating=elo),
                )
                tracker.save_solution(solution)

            leaderboard = tracker.generate_leaderboard()
            assert len(leaderboard) == 3
            assert leaderboard[0]["name"] == "Best"
            assert leaderboard[0]["rank"] == 1
            assert leaderboard[2]["name"] == "Worst"
            assert leaderboard[2]["rank"] == 3


class TestSolutionComparison:
    """Tests for SolutionComparison."""

    def test_comparison_serialization(self):
        """Test comparison to_dict and from_dict."""
        comparison = SolutionComparison(
            solution_ids=["a", "b", "c"],
            rankings={"a": 1, "b": 2, "c": 3},
            head_to_head={"a": {"b": 0.6, "c": 0.7}},
            significant_differences=[("a", "c", 10.5)],
            compared_at="2024-01-01T00:00:00",
        )

        data = comparison.to_dict()
        restored = SolutionComparison.from_dict(data)

        assert restored.solution_ids == comparison.solution_ids
        assert restored.rankings == comparison.rankings
        assert restored.compared_at == comparison.compared_at

    def test_comparison_summary(self):
        """Test comparison summary generation."""
        comparison = SolutionComparison(
            solution_ids=["sol_a", "sol_b"],
            rankings={"sol_a": 1, "sol_b": 2},
            significant_differences=[("sol_a", "sol_b", 15.0)],
            compared_at="2024-01-01T00:00:00",
        )

        summary = comparison.get_summary()
        assert "sol_a" in summary
        assert "#1" in summary


class TestSolutionBenchmark:
    """Tests for SolutionBenchmark.

    Note: These tests use minimal settings for speed.
    Full benchmarks are done separately.
    """

    def _make_solution(self, solution_id: str) -> SolutionRecord:
        metadata = SolutionMetadata(
            solution_id=solution_id,
            name=f"Test {solution_id}",
            description="Test solution",
            author="test_runner",
            submitted_at=datetime.utcnow().isoformat(),
        )
        return SolutionRecord(
            metadata=metadata,
            benchmark_result=BenchmarkResult(
                elo_rating=1200.0,
                skill_tier="beginner",
                evaluated_at=datetime.utcnow().isoformat(),
            ),
        )

    @pytest.fixture
    def fast_config(self):
        """Config for fast testing."""
        return SolutionBenchmarkConfig(
            hands_per_opponent=10,
            num_duplicate_sets=2,
            opponents=["always_fold", "random"],
        )

    def test_benchmark_initialization(self, fast_config):
        """Test benchmark initialization."""
        benchmark = SolutionBenchmark(fast_config)
        assert benchmark.config.hands_per_opponent == 10

    @pytest.mark.slow
    def test_evaluate_solution(self, fast_config):
        """Test evaluating a single solution."""
        benchmark = SolutionBenchmark(fast_config)

        metadata = SolutionMetadata(
            solution_id="bench_test",
            name="Benchmark Test",
            description="Test",
            author="tester",
            submitted_at=datetime.utcnow().isoformat(),
        )
        solution = SolutionRecord(metadata=metadata)

        result = benchmark.evaluate_solution(solution)

        assert result.elo_rating > 0
        assert result.total_hands_played > 0
        assert len(result.per_opponent) == len(fast_config.opponents)

    def test_generate_report(self, fast_config):
        """Test report generation."""
        benchmark = SolutionBenchmark(fast_config)

        # Create solutions with pre-set results (no actual evaluation)
        solutions = []
        for i, (name, elo) in enumerate([("First", 1500), ("Second", 1400)]):
            metadata = SolutionMetadata(
                solution_id=f"report_{i}",
                name=name,
                description="Test",
                author="tester",
                submitted_at=datetime.utcnow().isoformat(),
            )
            solution = SolutionRecord(
                metadata=metadata,
                benchmark_result=BenchmarkResult(
                    elo_rating=elo,
                    weighted_bb_per_100=elo - 1400,
                    per_opponent={"always_fold": 100.0},
                    skill_tier="intermediate",
                    evaluated_at=datetime.utcnow().isoformat(),
                ),
            )
            solutions.append(solution)

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = os.path.join(tmpdir, "report.txt")
            report = benchmark.generate_report(solutions, report_path)

            assert os.path.exists(report_path)
            assert "First" in report
            assert "Second" in report
            assert "#1" in report

    def test_head_to_head_is_order_invariant(self):
        """Same pair should produce same result regardless of argument ordering."""
        benchmark = SolutionBenchmark(SolutionBenchmarkConfig())

        sol_a = self._make_solution("h2h_a")
        sol_b = self._make_solution("h2h_b")

        a_vs_b = benchmark.run_head_to_head(sol_a, sol_b, num_hands=80)
        b_vs_a = benchmark.run_head_to_head(sol_b, sol_a, num_hands=80)

        assert a_vs_b[0] == pytest.approx(b_vs_a[1], abs=1e-12)
        assert a_vs_b[1] == pytest.approx(b_vs_a[0], abs=1e-12)

    def test_compare_solutions_invariant_to_input_order(self):
        """compare_solutions should not change if the input list is permuted."""
        benchmark = SolutionBenchmark(SolutionBenchmarkConfig())

        sol_a = self._make_solution("cmp_a")
        sol_b = self._make_solution("cmp_b")
        sol_c = self._make_solution("cmp_c")

        c1 = benchmark.compare_solutions([sol_a, sol_b, sol_c], hands_per_matchup=80)
        c2 = benchmark.compare_solutions([sol_c, sol_a, sol_b], hands_per_matchup=80)

        assert set(c1.head_to_head.keys()) == set(c2.head_to_head.keys())
        for row_id, row in c1.head_to_head.items():
            assert set(row.keys()) == set(c2.head_to_head[row_id].keys())
            for col_id, wr in row.items():
                assert wr == pytest.approx(c2.head_to_head[row_id][col_id], abs=1e-12)


class TestIntegration:
    """Integration tests for the solution tracking system."""

    @pytest.mark.slow
    def test_full_workflow(self):
        """Test complete workflow: create, save, load, evaluate, compare."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create tracker
            tracker = SolutionTracker(solutions_dir=tmpdir)

            # 2. Create solutions
            solutions = []
            for i in range(2):
                metadata = SolutionMetadata(
                    solution_id=f"workflow_{i}",
                    name=f"Solution {i}",
                    description="Integration test",
                    author="test_runner",
                    submitted_at=datetime.utcnow().isoformat(),
                )
                solution = SolutionRecord(
                    metadata=metadata,
                    behavior_algorithm={"class": f"Algo{i}", "parameters": {}},
                )
                solutions.append(solution)
                tracker.save_solution(solution)

            # 3. Load solutions
            loaded = tracker.load_all_solutions()
            assert len(loaded) == 2

            # 4. Evaluate (with minimal config for speed)
            benchmark = SolutionBenchmark(
                SolutionBenchmarkConfig(
                    hands_per_opponent=5,
                    num_duplicate_sets=1,
                    opponents=["always_fold"],
                )
            )

            for sol in loaded:
                result = benchmark.evaluate_solution(sol)
                sol.benchmark_result = result
                tracker.save_solution(sol)

            # 5. Generate leaderboard
            leaderboard = tracker.generate_leaderboard()
            assert len(leaderboard) == 2

            # 6. Generate report
            report = benchmark.generate_report(loaded)
            assert "Solution 0" in report or "Solution 1" in report


# Special test for comprehensive solution comparison (marked slow)
@pytest.mark.slow
class TestComprehensiveBenchmark:
    """Comprehensive benchmark tests for comparing all submitted solutions.

    These tests are designed to be run periodically to compare all
    solutions in the repository.
    """

    def test_compare_all_solutions(self):
        """Compare all submitted solutions in the solutions/ directory.

        This test:
        1. Loads all solutions from solutions/
        2. Evaluates any that haven't been evaluated
        3. Generates a comparison report
        4. Outputs rankings

        Run with: pytest tests/test_solution_tracking.py::TestComprehensiveBenchmark -v
        """
        solutions_dir = "solutions"
        if not os.path.exists(solutions_dir):
            pytest.skip("No solutions directory found")

        tracker = SolutionTracker(solutions_dir=solutions_dir)
        solutions = tracker.load_all_solutions()

        if len(solutions) < 1:
            pytest.skip("No solutions to compare")

        benchmark = SolutionBenchmark(
            SolutionBenchmarkConfig(
                hands_per_opponent=200,
                num_duplicate_sets=10,
            )
        )

        # Evaluate solutions without benchmark results
        for sol in solutions:
            if sol.benchmark_result is None:
                print(f"\nEvaluating: {sol.metadata.name}...")
                result = benchmark.evaluate_solution(sol, verbose=True)
                sol.benchmark_result = result
                tracker.save_solution(sol)

        # Generate and print report
        report = benchmark.generate_report(solutions)
        print("\n" + report)

        # Verify all solutions have results
        for sol in solutions:
            assert sol.benchmark_result is not None
            assert sol.benchmark_result.elo_rating > 0
