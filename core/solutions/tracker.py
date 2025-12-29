"""Solution tracking for identifying and preserving best performing strategies.

The SolutionTracker monitors simulation performance and identifies candidates
for preservation as "best solutions" that can be shared and compared.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.solutions.models import (
    BenchmarkResult,
    SolutionMetadata,
    SolutionRecord,
)

if TYPE_CHECKING:
    from core.entities import Fish

logger = logging.getLogger(__name__)


class SolutionTracker:
    """Tracks and preserves the best skill game solutions.

    This class monitors fish performance during simulation and provides
    methods to:
    1. Identify the current best performers
    2. Capture their strategies as SolutionRecords
    3. Save solutions to the solutions/ directory
    4. Submit solutions to git for sharing
    """

    def __init__(
        self,
        solutions_dir: str = "solutions",
        min_games_threshold: int = 50,
        auto_capture_enabled: bool = False,
    ):
        """Initialize the solution tracker.

        Args:
            solutions_dir: Directory to store solutions
            min_games_threshold: Minimum games required to be considered
            auto_capture_enabled: Whether to auto-capture best solutions
        """
        self.solutions_dir = solutions_dir
        self.min_games_threshold = min_games_threshold
        self.auto_capture_enabled = auto_capture_enabled

        # Track best solutions seen
        self._best_by_elo: Optional[SolutionRecord] = None
        self._best_by_winrate: Optional[SolutionRecord] = None
        self._best_by_roi: Optional[SolutionRecord] = None

        # History of captured solutions
        self._captured_hashes: set = set()

        os.makedirs(solutions_dir, exist_ok=True)

    def identify_best_fish(
        self,
        fish_list: List["Fish"],
        metric: str = "elo",
        top_n: int = 5,
    ) -> List[Tuple["Fish", float]]:
        """Identify the best performing fish by a given metric.

        Args:
            fish_list: List of all fish in the simulation
            metric: Metric to rank by ("elo", "win_rate", "roi", "net_energy")
            top_n: Number of top performers to return

        Returns:
            List of (fish, score) tuples, sorted by score descending
        """
        candidates = []

        for fish in fish_list:
            if not hasattr(fish, "poker_stats") or fish.poker_stats is None:
                continue

            stats = fish.poker_stats
            if stats.total_games < self.min_games_threshold:
                continue

            if metric == "elo":
                # Use estimated Elo based on performance
                score = self._estimate_elo(stats)
            elif metric == "win_rate":
                score = stats.get_win_rate()
            elif metric == "roi":
                score = stats.get_roi()
            elif metric == "net_energy":
                score = stats.get_net_energy()
            else:
                score = stats.get_net_energy()

            candidates.append((fish, score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_n]

    def _estimate_elo(self, stats) -> float:
        """Estimate Elo rating from poker stats.

        This is a rough estimate based on win rate and ROI.
        Actual Elo should be computed via benchmark evaluation.
        """
        base_elo = 1200.0

        # Adjust based on win rate (50% = baseline)
        win_rate = stats.get_win_rate()
        elo_adjustment = (win_rate - 0.5) * 400  # +/- 200 for 25% deviation

        # Adjust based on ROI
        roi = stats.get_roi()
        roi_adjustment = min(100, max(-100, roi * 10))  # Cap at +/- 100

        # Bonus for showdown skill
        showdown_wr = stats.get_showdown_win_rate()
        showdown_bonus = (showdown_wr - 0.5) * 100

        return base_elo + elo_adjustment + roi_adjustment + showdown_bonus

    def capture_solution(
        self,
        fish: "Fish",
        name: Optional[str] = None,
        description: Optional[str] = None,
        author: str = "TankWorld",
    ) -> SolutionRecord:
        """Capture a fish's strategy as a SolutionRecord.

        Args:
            fish: The fish to capture
            name: Optional name for the solution
            description: Optional description
            author: Author attribution

        Returns:
            The created SolutionRecord
        """
        now = datetime.utcnow()
        timestamp = now.isoformat()

        # Get behavior algorithm data
        behavior_data = {}
        composable_data = None

        if hasattr(fish, "genome") and fish.genome is not None:
            behavioral = fish.genome.behavioral
            if behavioral is not None and behavioral.behavior is not None:
                composable = behavioral.behavior
                if hasattr(composable, "value") and composable.value is not None:
                    behavior_data = composable.value.to_dict()
                if hasattr(composable, "to_dict"):
                    composable_data = composable.to_dict()

        # Get poker stats
        capture_stats = {}
        if hasattr(fish, "poker_stats") and fish.poker_stats is not None:
            capture_stats = fish.poker_stats.get_stats_dict()

        # Generate solution ID
        content_hash = hashlib.sha256(
            json.dumps(behavior_data, sort_keys=True).encode()
        ).hexdigest()[:8]
        solution_id = f"{content_hash}_{now.strftime('%Y%m%d_%H%M%S')}"

        # Get git info if available
        commit_sha = self._get_git_commit()
        branch = self._get_git_branch()

        # Create metadata
        metadata = SolutionMetadata(
            solution_id=solution_id,
            name=name or f"Solution_{fish.fish_id}",
            description=description or f"Strategy from fish {fish.fish_id}",
            author=author,
            submitted_at=timestamp,
            generation=fish.generation if hasattr(fish, "generation") else 0,
            fish_id=fish.fish_id if hasattr(fish, "fish_id") else None,
            commit_sha=commit_sha,
            branch=branch,
        )

        # Create record
        record = SolutionRecord(
            metadata=metadata,
            behavior_algorithm=behavior_data,
            composable_behavior=composable_data,
            capture_stats=capture_stats,
        )

        # Track that we've captured this hash
        self._captured_hashes.add(record.compute_hash())

        return record

    def save_solution(self, solution: SolutionRecord) -> str:
        """Save a solution to the solutions directory.

        Args:
            solution: The solution to save

        Returns:
            Path to the saved file
        """
        filepath = solution.save(self.solutions_dir)
        logger.info(f"Saved solution to {filepath}")
        return filepath

    def load_all_solutions(self) -> List[SolutionRecord]:
        """Load all solutions from the solutions directory.

        Returns:
            List of all SolutionRecord objects
        """
        solutions = []

        if not os.path.exists(self.solutions_dir):
            return solutions

        for filename in os.listdir(self.solutions_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.solutions_dir, filename)
                try:
                    solution = SolutionRecord.load(filepath)
                    solutions.append(solution)
                except Exception as e:
                    logger.warning(f"Failed to load solution from {filepath}: {e}")

        return solutions

    def submit_to_git(
        self,
        solution: SolutionRecord,
        commit_message: Optional[str] = None,
        push: bool = True,
    ) -> bool:
        """Submit a solution to git for sharing.

        Args:
            solution: The solution to submit
            commit_message: Optional custom commit message
            push: Whether to push to remote

        Returns:
            True if successful, False otherwise
        """
        try:
            # Save solution first
            filepath = self.save_solution(solution)

            # Stage the file
            subprocess.run(
                ["git", "add", filepath],
                check=True,
                capture_output=True,
            )

            # Create commit message
            if commit_message is None:
                commit_message = (
                    f"Submit solution: {solution.metadata.name}\n\n"
                    f"Author: {solution.metadata.author}\n"
                    f"Solution ID: {solution.metadata.solution_id}\n"
                )
                if solution.benchmark_result:
                    commit_message += (
                        f"Elo: {solution.benchmark_result.elo_rating:.0f}\n"
                        f"Skill Tier: {solution.benchmark_result.skill_tier}\n"
                    )

            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True,
                capture_output=True,
            )

            if push:
                # Get current branch
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                branch = result.stdout.strip()

                # Push
                subprocess.run(
                    ["git", "push", "-u", "origin", branch],
                    check=True,
                    capture_output=True,
                )

            logger.info(f"Successfully submitted solution {solution.metadata.solution_id} to git")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to submit solution to git: {e}")
            return False

    def get_best_solution(self, metric: str = "elo") -> Optional[SolutionRecord]:
        """Get the best solution by a given metric.

        Args:
            metric: Metric to use ("elo", "win_rate", "roi")

        Returns:
            The best solution, or None if none captured
        """
        if metric == "elo":
            return self._best_by_elo
        elif metric == "win_rate":
            return self._best_by_winrate
        elif metric == "roi":
            return self._best_by_roi
        return self._best_by_elo

    def update_best_if_improved(
        self,
        fish: "Fish",
        author: str = "TankWorld",
    ) -> Optional[SolutionRecord]:
        """Update best solution if the fish is an improvement.

        Args:
            fish: Fish to evaluate
            author: Author attribution

        Returns:
            New SolutionRecord if this is an improvement, None otherwise
        """
        if not hasattr(fish, "poker_stats") or fish.poker_stats is None:
            return None

        stats = fish.poker_stats
        if stats.total_games < self.min_games_threshold:
            return None

        current_elo = self._estimate_elo(stats)
        best_elo = 0.0
        if self._best_by_elo and self._best_by_elo.capture_stats:
            best_stats = self._best_by_elo.capture_stats
            # Estimate Elo from stored stats
            best_wr = best_stats.get("win_rate", 0.5)
            best_roi = best_stats.get("roi", 0)
            best_elo = 1200 + (best_wr - 0.5) * 400 + best_roi * 10

        if current_elo > best_elo:
            solution = self.capture_solution(fish, author=author)
            self._best_by_elo = solution

            if self.auto_capture_enabled:
                self.save_solution(solution)

            logger.info(
                f"New best solution: Elo {current_elo:.0f} (was {best_elo:.0f})"
            )
            return solution

        return None

    def is_duplicate(self, solution: SolutionRecord) -> bool:
        """Check if a solution is a duplicate of one already captured.

        Args:
            solution: The solution to check

        Returns:
            True if duplicate, False otherwise
        """
        return solution.compute_hash() in self._captured_hashes

    def _get_git_commit(self) -> Optional[str]:
        """Get the current git commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def _get_git_branch(self) -> Optional[str]:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def generate_leaderboard(
        self,
        solutions: Optional[List[SolutionRecord]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate a leaderboard from solutions.

        Args:
            solutions: Optional list of solutions (loads all if not provided)

        Returns:
            List of leaderboard entries sorted by Elo
        """
        if solutions is None:
            solutions = self.load_all_solutions()

        leaderboard = []
        for solution in solutions:
            entry = {
                "rank": 0,  # Will be set below
                "solution_id": solution.metadata.solution_id,
                "name": solution.metadata.name,
                "author": solution.metadata.author,
                "submitted_at": solution.metadata.submitted_at,
                "elo_rating": 1200.0,
                "skill_tier": "beginner",
                "bb_per_100": 0.0,
            }

            if solution.benchmark_result:
                entry["elo_rating"] = solution.benchmark_result.elo_rating
                entry["skill_tier"] = solution.benchmark_result.skill_tier
                entry["bb_per_100"] = solution.benchmark_result.weighted_bb_per_100

            leaderboard.append(entry)

        # Sort by Elo descending
        leaderboard.sort(key=lambda x: x["elo_rating"], reverse=True)

        # Set ranks
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return leaderboard
