"""Solution tracking and comparison system.

This module provides tools for identifying, preserving, and comparing
the best skill game solutions produced by the simulation.
"""

from core.solutions.models import (
    SolutionRecord,
    SolutionMetadata,
    BenchmarkResult,
    SolutionComparison,
)
from core.solutions.tracker import SolutionTracker
from core.solutions.benchmark import SolutionBenchmark

__all__ = [
    "SolutionRecord",
    "SolutionMetadata",
    "BenchmarkResult",
    "SolutionComparison",
    "SolutionTracker",
    "SolutionBenchmark",
]
