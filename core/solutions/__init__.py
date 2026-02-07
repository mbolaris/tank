"""Solution tracking and comparison system.

This module provides tools for identifying, preserving, and comparing
the best skill game solutions produced by the simulation.
"""

from core.solutions.benchmark import SolutionBenchmark
from core.solutions.models import (
    BenchmarkResult,
    SolutionComparison,
    SolutionMetadata,
    SolutionRecord,
)
from core.solutions.tracker import SolutionTracker

__all__ = [
    "BenchmarkResult",
    "SolutionBenchmark",
    "SolutionComparison",
    "SolutionMetadata",
    "SolutionRecord",
    "SolutionTracker",
]
