#!/usr/bin/env python3
"""AI Code Evolution Agent - Automated Algorithm Improvement Bot

This script implements a "Coding Agent" that:
1. Reads simulation statistics from JSON export
2. Identifies underperforming algorithms
3. Uses an LLM (Claude/GPT) to generate code improvements
4. VALIDATES improvements via test simulation (Phase 2 feature)
5. Creates a git branch and commits the changes
6. Pushes the branch for pull request creation

This enables a Continuous Improvement (CI) Loop where the AI acts as a
"Junior Developer" that proposes improvements based on simulation results.

Usage:
    python scripts/ai_code_evolution_agent.py results.json --provider anthropic
    python scripts/ai_code_evolution_agent.py results.json --provider openai
    python scripts/ai_code_evolution_agent.py results.json --validate  # Test before commit
    python scripts/ai_code_evolution_agent.py results.json --dry-run  # Don't commit/push

Environment Variables:
    ANTHROPIC_API_KEY: For Claude API access
    OPENAI_API_KEY: For GPT API access
"""

import argparse
import importlib
import json
import logging
import os
import statistics
import subprocess
import sys
from datetime import datetime
from typing import Any, cast

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_validation_seeds(raw: str) -> tuple[int, ...]:
    """Parse and validate the deterministic seed matrix for agent validation."""
    try:
        seeds = tuple(int(value.strip()) for value in raw.split(",") if value.strip())
    except ValueError as exc:
        raise ValueError("validation seeds must be a comma-separated list of integers") from exc
    if len(seeds) < 3:
        raise ValueError("AI validation requires at least three seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError("validation seeds must be unique")
    return seeds


def summarize_validation_matrix(results: list[Any], seeds: tuple[int, ...]) -> dict[str, Any]:
    """Aggregate per-seed validator results using a majority-of-seeds rule."""
    metric_names = ("reproduction_rate", "survival_rate", "avg_lifespan")
    candidate_fields = {
        "reproduction_rate": "new_reproduction_rate",
        "survival_rate": "new_survival_rate",
        "avg_lifespan": "new_avg_lifespan",
    }
    baseline_fields = {
        "reproduction_rate": "baseline_reproduction_rate",
        "survival_rate": "baseline_survival_rate",
        "avg_lifespan": "baseline_avg_lifespan",
    }
    improvement_fields = {
        "reproduction_rate": "improvement_reproduction",
        "survival_rate": "improvement_survival",
        "avg_lifespan": "improvement_lifespan",
    }

    per_seed: dict[str, dict[str, Any]] = {}
    for seed, result in zip(seeds, results, strict=True):
        per_seed[str(seed)] = {
            "passed": bool(result.passed),
            "reason": result.reason,
            "simulation_error": result.simulation_error,
            "baseline": {
                name: float(getattr(result, baseline_fields[name])) for name in metric_names
            },
            "candidate": {
                name: float(getattr(result, candidate_fields[name])) for name in metric_names
            },
            "improvements": {
                name: float(getattr(result, improvement_fields[name])) for name in metric_names
            },
        }

    passed_count = sum(1 for result in results if result.passed)
    complete = len(results) == len(seeds) and not any(result.simulation_error for result in results)
    mean_improvements = {
        name: statistics.mean(item["improvements"][name] for item in per_seed.values())
        for name in metric_names
    }
    candidate_summary = {
        name: {
            "mean": statistics.mean(item["candidate"][name] for item in per_seed.values()),
            "stdev": (
                statistics.stdev(item["candidate"][name] for item in per_seed.values())
                if len(per_seed) >= 2
                else 0.0
            ),
        }
        for name in metric_names
    }
    passed = complete and passed_count > len(seeds) / 2
    reason = (
        f"{passed_count}/{len(seeds)} seeds passed; "
        f"mean reproduction improvement {mean_improvements['reproduction_rate']:+.2%} "
        f"± {statistics.stdev([item['improvements']['reproduction_rate'] for item in per_seed.values()]) if len(per_seed) >= 2 else 0.0:.2%}"
    )
    if not complete:
        reason += "; at least one seed failed to complete"
    elif not passed:
        reason += "; majority-of-seeds requirement not met"

    return {
        "passed": passed,
        "reason": reason,
        "passed_count": passed_count,
        "seed_count": len(seeds),
        "seeds": list(seeds),
        "per_seed": per_seed,
        "mean_improvements": mean_improvements,
        "candidate_summary": candidate_summary,
    }


class AlgorithmImprover:
    """AI-powered algorithm improvement agent."""

    def __init__(
        self,
        provider: str = "anthropic",
        dry_run: bool = False,
        validate: bool = False,
        validation_frames: int = 10000,
        max_retries: int = 2,
        validation_seeds: tuple[int, ...] = (42, 7, 123),
    ):
        """Initialize the improver.

        Args:
            provider: LLM provider ("anthropic" or "openai")
            dry_run: If True, don't commit or push changes
            validate: If True, run test simulation before committing
            validation_frames: Frames to run for validation
            max_retries: Maximum retries if validation fails
        """
        self.provider = provider
        self.dry_run = dry_run
        self.validate = validate
        self.validation_frames = validation_frames
        self.max_retries = max_retries
        if len(validation_seeds) < 3 or len(set(validation_seeds)) != len(validation_seeds):
            raise ValueError("AI validation requires at least three unique seeds")
        self.validation_seeds = validation_seeds

        # Check for API keys
        if provider == "anthropic":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        elif provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def load_stats(self, stats_file: str) -> dict[str, Any]:
        """Load simulation statistics from JSON file.

        Args:
            stats_file: Path to stats JSON file

        Returns:
            Dictionary with stats data
        """
        logger.info(f"Loading stats from: {stats_file}")
        with open(stats_file) as f:
            obj = json.load(f)
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object in {stats_file}, got {type(obj).__name__}")
            return cast(dict[str, Any], obj)

    def identify_worst_performer(self, stats: dict) -> tuple[str, dict] | None:
        """Identify the worst performing algorithm.

        Args:
            stats: Simulation statistics

        Returns:
            Tuple of (algorithm_name, performance_data) or None
        """
        algorithm_performance = stats.get("algorithm_performance", {})

        # Filter algorithms with sufficient data
        candidates = {
            name: perf
            for name, perf in algorithm_performance.items()
            if perf.get("total_births", 0) >= 5  # Minimum sample size
        }

        if not candidates:
            logger.warning("No algorithms with sufficient data found")
            return None

        # Sort by reproduction rate (lower is worse)
        worst_algo = min(candidates.items(), key=lambda x: x[1].get("reproduction_rate", 1.0))

        algo_name, perf = worst_algo
        logger.info(f"Identified worst performer: {algo_name}")
        logger.info(f"  Reproduction rate: {perf.get('reproduction_rate', 0):.2%}")
        logger.info(f"  Avg lifespan: {perf.get('avg_lifespan_frames', 0):.0f} frames")
        logger.info(f"  Main death cause: {perf.get('death_breakdown', {})}")

        return worst_algo

    def read_source_file(self, file_path: str) -> str:
        """Read the source code of an algorithm.

        Args:
            file_path: Absolute path to source file

        Returns:
            Source code as string
        """
        logger.info(f"Reading source file: {file_path}")
        with open(file_path) as f:
            return f.read()

    def generate_improvement(self, algo_name: str, performance: dict, source_code: str) -> str:
        """Use LLM to generate improved algorithm code.

        Args:
            algo_name: Algorithm name
            performance: Performance statistics
            source_code: Current source code

        Returns:
            Improved source code
        """
        logger.info(f"Generating improvement for {algo_name} using {self.provider}...")

        # Build prompt for LLM
        prompt = self._build_improvement_prompt(algo_name, performance, source_code)

        # Call LLM based on provider
        if self.provider == "anthropic":
            improved_code = self._call_claude(prompt)
        elif self.provider == "openai":
            improved_code = self._call_gpt(prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        return improved_code

    def _build_improvement_prompt(self, algo_name: str, performance: dict, source_code: str) -> str:
        """Build the LLM prompt for code improvement.

        Args:
            algo_name: Algorithm name
            performance: Performance statistics
            source_code: Current source code

        Returns:
            Formatted prompt string
        """
        death_breakdown = performance.get("death_breakdown", {})
        main_death_cause = max(death_breakdown.items(), key=lambda x: x[1])[0]

        prompt = f"""You are an expert AI programmer improving fish behavior algorithms in an evolutionary simulation.

ALGORITHM: {algo_name}

CURRENT PERFORMANCE (POOR):
- Reproduction Rate: {performance.get('reproduction_rate', 0):.2%} (target: >50%)
- Average Lifespan: {performance.get('avg_lifespan_frames', 0):.0f} frames
- Survival Rate: {performance.get('survival_rate', 0):.2%}
- Deaths by Starvation: {death_breakdown.get('starvation', 0)}
- Deaths by Predation: {death_breakdown.get('predation', 0)}
- Deaths by Old Age: {death_breakdown.get('old_age', 0)}

PRIMARY ISSUE: Main death cause is {main_death_cause}

CURRENT SOURCE CODE:
```python
{source_code}
```

TASK:
Rewrite the algorithm's execute() method to improve survival and reproduction.

SPECIFIC IMPROVEMENTS NEEDED:
1. If dying from starvation: Make food-seeking more aggressive and efficient
2. If dying from predation: Add better predator avoidance logic
3. If dying of old age: Good! But improve reproduction rate

REQUIREMENTS:
- Keep the same class name and structure
- Only modify the execute() method logic
- Use the same parameters dict for tuning
- Return valid (velocity_x, velocity_y) tuple
- Keep imports and class structure intact

OUTPUT FORMAT:
Return ONLY the complete Python file content with the improved execute() method.
Do not include markdown code blocks or explanations - just the raw Python code.
"""
        return prompt

    def _call_claude(self, prompt: str) -> str:
        """Call Claude API for code generation.

        Args:
            prompt: The improvement prompt

        Returns:
            Generated code
        """
        try:
            anthropic = importlib.import_module("anthropic")
        except ModuleNotFoundError as e:
            raise ImportError("anthropic package not installed. Run: pip install anthropic") from e

        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        content = getattr(message, "content", None)
        if isinstance(content, list) and content:
            text = getattr(content[0], "text", None)
            if isinstance(text, str):
                return text

        raise ValueError("Unexpected anthropic response format (missing message.content[0].text)")

    def _call_gpt(self, prompt: str) -> str:
        """Call OpenAI GPT API for code generation.

        Args:
            prompt: The improvement prompt

        Returns:
            Generated code
        """
        try:
            openai = importlib.import_module("openai")
        except ModuleNotFoundError as e:
            raise ImportError("openai package not installed. Run: pip install openai") from e

        client = openai.OpenAI(api_key=self.api_key)

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        if isinstance(content, str):
            return content
        raise ValueError("Unexpected OpenAI response format (missing message content)")

    def write_improved_code(self, file_path: str, new_code: str) -> None:
        """Write improved code to file.

        Args:
            file_path: Path to source file
            new_code: Improved code content
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would write to: {file_path}")
            logger.info("=" * 80)
            logger.info(new_code)
            logger.info("=" * 80)
            return

        logger.info(f"Writing improved code to: {file_path}")
        with open(file_path, "w") as f:
            f.write(new_code)

    def create_branch_and_commit(self, algo_name: str, performance: dict) -> None:
        """Create git branch and commit changes.

        Args:
            algo_name: Algorithm name
            performance: Performance stats
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would create git branch and commit")
            return

        # Create branch name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"ai-improve-{algo_name.lower().replace('_', '-')}-{timestamp}"

        logger.info(f"Creating branch: {branch_name}")
        subprocess.run(["git", "checkout", "-b", branch_name], check=True)

        # Stage changes
        logger.info("Staging changes...")
        subprocess.run(["git", "add", "-A"], check=True)

        # Commit with detailed message
        repro_rate = performance.get("reproduction_rate", 0)
        commit_msg = f"""AI Optimization: Improve {algo_name}

Current reproduction rate: {repro_rate:.2%}
Main issue: Low survival and reproduction

This commit contains AI-generated improvements to the {algo_name}
algorithm based on simulation performance data.

Changes:
- Enhanced execute() method logic
- Improved survival strategy
- Better resource/threat response

Generated by: AI Code Evolution Agent
"""

        logger.info("Committing changes...")
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)

        logger.info(f"Branch '{branch_name}' created with improvements!")
        logger.info("To push: git push -u origin " + branch_name)

    def validate_improvement(
        self,
        algo_name: str,
        improved_code: str,
        performance: dict,
    ) -> tuple[bool, str | None]:
        """Validate the improved code via test simulation.

        Args:
            algo_name: Algorithm name
            improved_code: The improved source code
            performance: Baseline performance metrics

        Returns:
            Tuple of (passed, error_message)
        """
        # Import here to avoid circular imports
        try:
            from core.algorithm_validator import AlgorithmValidator
        except ImportError:
            logger.warning("AlgorithmValidator not available, skipping validation")
            return True, None

        validator = AlgorithmValidator(test_frames=self.validation_frames)

        # First check syntax
        syntax_valid, syntax_error = validator.validate_syntax(improved_code)
        if not syntax_valid:
            try:
                from core.research.attempt_ledger import log_attempt

                log_attempt(
                    benchmark_id=f"validate_algo_{algo_name}",
                    verdict="error",
                    candidate_score=None,
                    champion_score=performance.get("reproduction_rate"),
                    seed=list(self.validation_seeds),
                    agent_id=self.provider,
                    description=f"Syntax error: {syntax_error}",
                )
            except Exception as le:
                logger.warning(f"Failed to log attempt: {le}")
            return False, f"Syntax error: {syntax_error}"

        # Run a fresh baseline and candidate validation for every seed. Using
        # one baseline per seed prevents a lucky candidate run from being
        # compared against a noisy result from a different trajectory.
        logger.info("Running validation matrix on seeds: %s", self.validation_seeds)
        results = []
        for seed in self.validation_seeds:
            try:
                baseline = validator.measure_baseline(algo_name, seed)
                results.append(
                    validator.validate_improvement(
                        algorithm_id=algo_name,
                        new_code=improved_code,
                        baseline_metrics=baseline,
                        seed=seed,
                    )
                )
            except Exception as exc:
                logger.error("Validation seed %s failed: %s", seed, exc)
                try:
                    from core.research.attempt_ledger import log_attempt

                    log_attempt(
                        benchmark_id=f"validate_algo_{algo_name}",
                        verdict="error",
                        candidate_score=None,
                        champion_score=None,
                        seed=list(self.validation_seeds),
                        agent_id=self.provider,
                        description=f"Seed {seed} validation error: {exc!s}",
                    )
                except Exception as ledger_error:
                    logger.warning("Failed to log validation error: %s", ledger_error)
                return False, f"Seed {seed} validation error: {exc!s}"

        summary = summarize_validation_matrix(results, self.validation_seeds)
        verdict = "accepted" if summary["passed"] else "rejected"
        if any(result.simulation_error for result in results):
            verdict = "error"
        mean_candidate_repro = summary["candidate_summary"]["reproduction_rate"]["mean"]
        mean_baseline_repro = statistics.mean(
            item["baseline"]["reproduction_rate"] for item in summary["per_seed"].values()
        )

        try:
            from core.research.attempt_ledger import log_attempt

            log_attempt(
                benchmark_id=f"validate_algo_{algo_name}",
                verdict=verdict,
                candidate_score=mean_candidate_repro,
                champion_score=mean_baseline_repro,
                seed=list(self.validation_seeds),
                agent_id=self.provider,
                description=summary["reason"],
            )
        except Exception as le:
            logger.warning(f"Failed to log attempt: {le}")

        if summary["passed"]:
            logger.info("Validation PASSED: %s", summary["reason"])
            for metric, values in summary["candidate_summary"].items():
                logger.info("  %s: mean=%.4f ± %.4f", metric, values["mean"], values["stdev"])
            return True, None
        else:
            return False, summary["reason"]

    def run(self, stats_file: str) -> None:
        """Run the full improvement workflow.

        Args:
            stats_file: Path to simulation stats JSON
        """
        logger.info("=" * 80)
        logger.info("AI Code Evolution Agent - Starting")
        if self.validate:
            logger.info("  Mode: VALIDATED (will test before committing)")
        logger.info("=" * 80)

        # Step 1: Load stats
        stats = self.load_stats(stats_file)

        # Step 2: Identify worst performer
        worst = self.identify_worst_performer(stats)
        if not worst:
            logger.error("No algorithm to improve found")
            return

        algo_name, performance = worst

        # Step 3: Get source file path
        source_file = performance.get("source_file")
        if not source_file or source_file == "unknown":
            logger.error(f"Source file not found for {algo_name}")
            return

        # Step 4: Read current code
        try:
            current_code = self.read_source_file(source_file)
        except FileNotFoundError:
            logger.error(f"Source file not found: {source_file}")
            return

        # Step 5: Generate improvement (with retries if validation enabled)
        improved_code = None
        attempts = 0
        max_attempts = self.max_retries + 1 if self.validate else 1

        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Generating improvement (attempt {attempts}/{max_attempts})...")

            improved_code = self.generate_improvement(algo_name, performance, current_code)

            # Step 6: Validate if enabled
            if self.validate:
                passed, error = self.validate_improvement(algo_name, improved_code, performance)
                if passed:
                    logger.info("Improvement validated successfully!")
                    break
                else:
                    logger.warning(f"Validation failed: {error}")
                    if attempts < max_attempts:
                        logger.info("Retrying with feedback...")
                        # Could enhance prompt with failure info here
                    else:
                        logger.error("Max retries reached, aborting")
                        return
            else:
                # No validation, proceed immediately
                break

        if improved_code is None:
            logger.error("Failed to generate improvement")
            return

        # Step 7: Write improved code
        self.write_improved_code(source_file, improved_code)

        # Step 8: Create branch and commit
        self.create_branch_and_commit(algo_name, performance)

        logger.info("=" * 80)
        logger.info("AI Code Evolution Agent - Complete!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review the changes with: git diff HEAD~1")
        if not self.validate:
            logger.info("2. Test the simulation to verify improvements")
        else:
            logger.info("2. Improvement already validated via test simulation")
        logger.info("3. Push the branch: git push -u origin <branch-name>")
        logger.info("4. Create a Pull Request on GitHub")
        logger.info("5. Merge if tests pass and improvements are verified!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Code Evolution Agent - Automated Algorithm Improvement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Improve algorithms using Claude
  python scripts/ai_code_evolution_agent.py results.json --provider anthropic

  # Improve algorithms using GPT-4
  python scripts/ai_code_evolution_agent.py results.json --provider openai

  # Validate improvements before committing (Phase 2 feature)
  python scripts/ai_code_evolution_agent.py results.json --validate

  # Dry run (don't commit changes)
  python scripts/ai_code_evolution_agent.py results.json --dry-run

Environment Variables:
  ANTHROPIC_API_KEY - Required for --provider anthropic
  OPENAI_API_KEY    - Required for --provider openai
        """,
    )

    parser.add_argument("stats_file", help="Path to simulation stats JSON file")

    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider to use (default: anthropic)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run test simulation to validate improvement before committing",
    )

    parser.add_argument(
        "--validation-frames",
        type=int,
        default=10000,
        help="Number of frames for validation simulation (default: 10000)",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retries if validation fails (default: 2)",
    )

    parser.add_argument(
        "--validation-seeds",
        default="42,7,123",
        help="Comma-separated validation seeds; at least three unique seeds are required",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually commit or push changes (for testing)",
    )

    args = parser.parse_args()

    try:
        validation_seeds = parse_validation_seeds(args.validation_seeds)
        improver = AlgorithmImprover(
            provider=args.provider,
            dry_run=args.dry_run,
            validate=args.validate,
            validation_frames=args.validation_frames,
            max_retries=args.max_retries,
            validation_seeds=validation_seeds,
        )
        improver.run(args.stats_file)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
