"""Data models for solution tracking and comparison.

A "solution" in TankWorld represents a complete behavioral strategy that
has demonstrated strong performance in skill games (poker, rock-paper-scissors,
number prediction). Solutions are preserved so they can be:

1. Compared against other solutions
2. Shared across users via git
3. Evaluated by comprehensive benchmark tests
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SolutionMetadata:
    """Metadata about a submitted solution."""

    # Identification
    solution_id: str  # Unique identifier (SHA-256 of strategy + timestamp)
    name: str  # Human-readable name
    description: str  # Description of the strategy

    # Attribution
    author: str  # User who submitted the solution
    submitted_at: str  # ISO format timestamp
    version: str = "1.0.0"  # Solution format version

    # Source tracking
    generation: int = 0  # Fish generation when captured
    simulation_frames: int = 0  # Total frames simulated
    fish_id: int | None = None  # Original fish ID (if applicable)

    # Git tracking
    commit_sha: str | None = None  # Git commit where solution was captured
    branch: str | None = None  # Git branch

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SolutionMetadata:
        """Create from dictionary."""
        return cls(**dict(data))


@dataclass
class BenchmarkResult:
    """Results from benchmarking a solution against standard opponents."""

    # Per-opponent results (bb/100 win rate)
    per_opponent: dict[str, float] = field(default_factory=dict)

    # Aggregate metrics
    weighted_bb_per_100: float = 0.0
    total_hands_played: int = 0
    elo_rating: float = 1200.0

    # Confidence intervals
    confidence_intervals: dict[str, tuple[float, float]] = field(default_factory=dict)

    # Skill tier classification
    skill_tier: str = (
        "beginner"  # failing, novice, beginner, intermediate, advanced, expert, master
    )

    # Timestamp of evaluation
    evaluated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "per_opponent": self.per_opponent,
            "weighted_bb_per_100": self.weighted_bb_per_100,
            "total_hands_played": self.total_hands_played,
            "elo_rating": self.elo_rating,
            "confidence_intervals": {k: list(v) for k, v in self.confidence_intervals.items()},
            "skill_tier": self.skill_tier,
            "evaluated_at": self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BenchmarkResult:
        """Create from dictionary."""
        ci_raw = data.get("confidence_intervals", {})
        ci: dict[str, tuple[float, float]] = {}
        if isinstance(ci_raw, dict):
            for k, v in ci_raw.items():
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    ci[str(k)] = (float(v[0]), float(v[1]))

        per_opp_raw = data.get("per_opponent", {})
        per_opp: dict[str, float] = {}
        if isinstance(per_opp_raw, dict):
            for k, v in per_opp_raw.items():
                per_opp[str(k)] = float(v)

        return cls(
            per_opponent=per_opp,
            weighted_bb_per_100=float(data.get("weighted_bb_per_100", 0.0)),
            total_hands_played=int(data.get("total_hands_played", 0)),
            elo_rating=float(data.get("elo_rating", 1200.0)),
            confidence_intervals=ci,
            skill_tier=str(data.get("skill_tier", "beginner")),
            evaluated_at=str(data.get("evaluated_at", "")),
        )


@dataclass
class SolutionRecord:
    """Complete record of a skill game solution.

    This captures everything needed to recreate and evaluate a strategy:
    - The behavioral algorithm and its parameters
    - Poker strategy configuration
    - Performance metrics at time of capture
    - Benchmark results from standardized evaluation
    """

    # Metadata
    metadata: SolutionMetadata

    # Behavioral algorithm (serialized)
    behavior_algorithm: dict[str, Any] = field(default_factory=dict)

    # Poker strategy (if applicable)
    poker_strategy: dict[str, Any] = field(default_factory=dict)

    # Composable behavior configuration
    composable_behavior: dict[str, Any] | None = None

    # Performance at capture time
    capture_stats: dict[str, Any] = field(default_factory=dict)

    # Benchmark results (populated after evaluation)
    benchmark_result: BenchmarkResult | None = None

    def compute_hash(self) -> str:
        """Compute a deterministic hash of the solution's strategy.

        This is used to detect duplicate solutions.
        """
        # Include only the strategic components, not metadata
        strategy_data = {
            "behavior_algorithm": self.behavior_algorithm,
            "poker_strategy": self.poker_strategy,
            "composable_behavior": self.composable_behavior,
        }
        content = json.dumps(strategy_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": self.metadata.to_dict(),
            "behavior_algorithm": self.behavior_algorithm,
            "poker_strategy": self.poker_strategy,
            "composable_behavior": self.composable_behavior,
            "capture_stats": self.capture_stats,
            "benchmark_result": (
                self.benchmark_result.to_dict() if self.benchmark_result else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SolutionRecord:
        """Create from dictionary."""
        metadata_raw = data.get("metadata")
        metadata_dict = metadata_raw if isinstance(metadata_raw, dict) else {}
        metadata = SolutionMetadata.from_dict(metadata_dict)

        benchmark_raw = data.get("benchmark_result")
        benchmark_dict = benchmark_raw if isinstance(benchmark_raw, dict) else None
        benchmark = BenchmarkResult.from_dict(benchmark_dict) if benchmark_dict else None

        algo_raw = data.get("behavior_algorithm", {})
        poker_raw = data.get("poker_strategy", {})
        comp_raw = data.get("composable_behavior")
        stats_raw = data.get("capture_stats", {})

        return cls(
            metadata=metadata,
            behavior_algorithm=dict(algo_raw) if isinstance(algo_raw, dict) else {},
            poker_strategy=dict(poker_raw) if isinstance(poker_raw, dict) else {},
            composable_behavior=dict(comp_raw) if isinstance(comp_raw, dict) else None,
            capture_stats=dict(stats_raw) if isinstance(stats_raw, dict) else {},
            benchmark_result=benchmark,
        )

    def save(self, directory: str = "solutions") -> str:
        """Save solution to a JSON file.

        Args:
            directory: Directory to save to (relative to project root)

        Returns:
            Path to the saved file
        """
        os.makedirs(directory, exist_ok=True)
        filename = f"{self.metadata.solution_id}.json"
        filepath = os.path.join(directory, filename)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

        return filepath

    @classmethod
    def load(cls, filepath: str) -> SolutionRecord:
        """Load solution from a JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def get_summary(self) -> str:
        """Get a human-readable summary of the solution."""
        lines = [
            f"Solution: {self.metadata.name}",
            f"  ID: {self.metadata.solution_id}",
            f"  Author: {self.metadata.author}",
            f"  Submitted: {self.metadata.submitted_at}",
        ]

        if self.behavior_algorithm:
            algo_class = str(self.behavior_algorithm.get("class", "Unknown"))
            lines.append(f"  Algorithm: {algo_class}")

        if self.benchmark_result:
            lines.append(f"  Elo Rating: {self.benchmark_result.elo_rating:.0f}")
            lines.append(f"  Skill Tier: {self.benchmark_result.skill_tier}")
            lines.append(f"  bb/100: {self.benchmark_result.weighted_bb_per_100:.2f}")

        return "\n".join(lines)


@dataclass
class SolutionComparison:
    """Results from comparing multiple solutions."""

    # Solutions compared (by ID)
    solution_ids: list[str] = field(default_factory=list)

    # Rankings (1st place = best)
    rankings: dict[str, int] = field(default_factory=dict)

    # Head-to-head results (solution_id -> opponent_id -> win_rate)
    head_to_head: dict[str, dict[str, float]] = field(default_factory=dict)

    # Statistical significance of differences
    significant_differences: list[tuple[str, str, float]] = field(default_factory=list)

    # Comparison timestamp
    compared_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "solution_ids": self.solution_ids,
            "rankings": self.rankings,
            "head_to_head": self.head_to_head,
            "significant_differences": [list(diff) for diff in self.significant_differences],
            "compared_at": self.compared_at,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SolutionComparison:
        """Create from dictionary."""
        sol_ids_raw = data.get("solution_ids", [])
        sol_ids = [str(x) for x in sol_ids_raw] if isinstance(sol_ids_raw, list) else []

        rankings_raw = data.get("rankings", {})
        rankings = (
            {str(k): int(v) for k, v in rankings_raw.items()}
            if isinstance(rankings_raw, dict)
            else {}
        )

        h2h_raw = data.get("head_to_head", {})
        h2h: dict[str, dict[str, float]] = {}
        if isinstance(h2h_raw, dict):
            for k1, v1 in h2h_raw.items():
                if isinstance(v1, dict):
                    h2h[str(k1)] = {str(k2): float(v2) for k2, v2 in v1.items()}

        sig_raw = data.get("significant_differences", [])
        sig_diffs: list[tuple[str, str, float]] = []
        if isinstance(sig_raw, list):
            for item in sig_raw:
                if isinstance(item, (list, tuple)) and len(item) == 3:
                    sig_diffs.append((str(item[0]), str(item[1]), float(item[2])))

        return cls(
            solution_ids=sol_ids,
            rankings=rankings,
            head_to_head=h2h,
            significant_differences=sig_diffs,
            compared_at=str(data.get("compared_at", "")),
        )

    def get_summary(self) -> str:
        """Get a human-readable summary of the comparison."""
        lines = [
            "Solution Comparison Results",
            f"  Compared: {len(self.solution_ids)} solutions",
            f"  Date: {self.compared_at}",
            "",
            "Rankings:",
        ]

        # Sort by ranking
        sorted_rankings = sorted(self.rankings.items(), key=lambda x: x[1])
        for solution_id, rank in sorted_rankings:
            lines.append(f"  #{rank}: {solution_id}")

        if self.significant_differences:
            lines.append("")
            lines.append("Significant Differences:")
            for sol1, sol2, diff in self.significant_differences:
                lines.append(f"  {sol1} vs {sol2}: {diff:.2f} bb/100")

        return "\n".join(lines)
