"""Algorithm Validator - Tests AI-generated improvements before merging.

This module provides validation infrastructure for the AI Code Evolution workflow.
It runs test simulations to verify that AI-generated algorithm changes actually
improve fitness metrics before committing them.

Usage:
    from core.algorithm_validator import AlgorithmValidator, ValidationResult

    validator = AlgorithmValidator()
    result = validator.validate_improvement(
        algorithm_id="greedy_food_seeker",
        new_code=improved_source_code,
        baseline_metrics={"reproduction_rate": 0.12, "survival_rate": 0.15},
        seed=42
    )

    if result.passed:
        # Safe to commit
        write_improved_code(...)
    else:
        # Reject or retry
        logger.warning(f"Validation failed: {result.reason}")
"""

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating an algorithm improvement."""

    passed: bool
    algorithm_id: str
    reason: str = ""

    # Baseline metrics (before improvement)
    baseline_reproduction_rate: float = 0.0
    baseline_survival_rate: float = 0.0
    baseline_avg_lifespan: float = 0.0

    # New metrics (after improvement)
    new_reproduction_rate: float = 0.0
    new_survival_rate: float = 0.0
    new_avg_lifespan: float = 0.0

    # Improvement percentages
    improvement_reproduction: float = 0.0
    improvement_survival: float = 0.0
    improvement_lifespan: float = 0.0

    # Detailed results
    metrics_improved: dict[str, bool] = field(default_factory=dict)
    simulation_error: Optional[str] = None


class AlgorithmValidator:
    """Validates AI-generated algorithm improvements by running test simulations."""

    def __init__(
        self,
        test_frames: int = 10000,
        min_improvement_threshold: float = 0.0,
        require_all_metrics: bool = False,
    ):
        """Initialize the validator.

        Args:
            test_frames: Number of frames to run test simulation
            min_improvement_threshold: Minimum improvement required (0.0 = any improvement)
            require_all_metrics: If True, all metrics must improve; if False, at least one
        """
        self.test_frames = test_frames
        self.min_improvement_threshold = min_improvement_threshold
        self.require_all_metrics = require_all_metrics

    def validate_improvement(
        self,
        algorithm_id: str,
        new_code: str,
        baseline_metrics: dict[str, float],
        seed: int = 42,
    ) -> ValidationResult:
        """Validate that improved algorithm code performs better than baseline.

        Args:
            algorithm_id: The algorithm being improved (e.g., "greedy_food_seeker")
            new_code: The improved source code
            baseline_metrics: Metrics from the original algorithm
            seed: Random seed for reproducible testing

        Returns:
            ValidationResult with pass/fail status and details
        """
        logger.info(f"Validating improvement for: {algorithm_id}")
        logger.info(f"  Test frames: {self.test_frames}")
        logger.info(f"  Seed: {seed}")

        # Extract baseline values
        baseline_repro = baseline_metrics.get("reproduction_rate", 0.0)
        baseline_survival = baseline_metrics.get("survival_rate", 0.0)
        baseline_lifespan = baseline_metrics.get("avg_lifespan_frames", 0.0)

        logger.info(f"  Baseline reproduction rate: {baseline_repro:.2%}")
        logger.info(f"  Baseline survival rate: {baseline_survival:.2%}")
        logger.info(f"  Baseline avg lifespan: {baseline_lifespan:.0f} frames")

        # Run test simulation with improved code
        try:
            new_metrics = self._run_test_simulation(algorithm_id, new_code, seed)
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return ValidationResult(
                passed=False,
                algorithm_id=algorithm_id,
                reason=f"Simulation error: {e!s}",
                baseline_reproduction_rate=baseline_repro,
                baseline_survival_rate=baseline_survival,
                baseline_avg_lifespan=baseline_lifespan,
                simulation_error=str(e),
            )

        # Extract new metrics
        new_repro = new_metrics.get("reproduction_rate", 0.0)
        new_survival = new_metrics.get("survival_rate", 0.0)
        new_lifespan = new_metrics.get("avg_lifespan_frames", 0.0)

        logger.info(f"  New reproduction rate: {new_repro:.2%}")
        logger.info(f"  New survival rate: {new_survival:.2%}")
        logger.info(f"  New avg lifespan: {new_lifespan:.0f} frames")

        # Calculate improvements
        def calc_improvement(new_val: float, old_val: float) -> float:
            if old_val == 0:
                return 1.0 if new_val > 0 else 0.0
            return (new_val - old_val) / old_val

        improvement_repro = calc_improvement(new_repro, baseline_repro)
        improvement_survival = calc_improvement(new_survival, baseline_survival)
        improvement_lifespan = calc_improvement(new_lifespan, baseline_lifespan)

        # Determine which metrics improved
        metrics_improved = {
            "reproduction_rate": improvement_repro > self.min_improvement_threshold,
            "survival_rate": improvement_survival > self.min_improvement_threshold,
            "avg_lifespan": improvement_lifespan > self.min_improvement_threshold,
        }

        # Determine pass/fail
        if self.require_all_metrics:
            passed = all(metrics_improved.values())
            if not passed:
                failed_metrics = [k for k, v in metrics_improved.items() if not v]
                reason = f"Metrics did not improve: {', '.join(failed_metrics)}"
            else:
                reason = "All metrics improved"
        else:
            passed = any(metrics_improved.values())
            if not passed:
                reason = "No metrics improved"
            else:
                improved_metrics = [k for k, v in metrics_improved.items() if v]
                reason = f"Improved metrics: {', '.join(improved_metrics)}"

        logger.info(f"  Validation {'PASSED' if passed else 'FAILED'}: {reason}")

        return ValidationResult(
            passed=passed,
            algorithm_id=algorithm_id,
            reason=reason,
            baseline_reproduction_rate=baseline_repro,
            baseline_survival_rate=baseline_survival,
            baseline_avg_lifespan=baseline_lifespan,
            new_reproduction_rate=new_repro,
            new_survival_rate=new_survival,
            new_avg_lifespan=new_lifespan,
            improvement_reproduction=improvement_repro,
            improvement_survival=improvement_survival,
            improvement_lifespan=improvement_lifespan,
            metrics_improved=metrics_improved,
        )

    def _run_test_simulation(
        self,
        algorithm_id: str,
        new_code: str,
        seed: int,
    ) -> dict[str, float]:
        """Run a test simulation with the improved algorithm.

        This method:
        1. Creates a temporary copy of the algorithm file
        2. Writes the new code to the original location
        3. Runs a headless simulation
        4. Restores the original file
        5. Returns the performance metrics

        Args:
            algorithm_id: Algorithm being tested
            new_code: Improved source code
            seed: Random seed

        Returns:
            Performance metrics for the algorithm
        """
        from core.registry import get_algorithm_metadata

        # Get the source file path
        metadata = get_algorithm_metadata()
        algo_meta = metadata.get(algorithm_id, {})
        source_file = algo_meta.get("source_file")

        if not source_file or not os.path.exists(source_file):
            raise FileNotFoundError(f"Source file not found for {algorithm_id}")

        # Create backup
        backup_file = None
        try:
            # Backup original file
            backup_file = tempfile.NamedTemporaryFile(  # noqa: SIM115
                mode="w", suffix=".py", delete=False
            )
            with open(source_file) as f:
                original_code = f.read()
            backup_file.write(original_code)
            backup_file.close()

            # Write new code
            with open(source_file, "w") as f:
                f.write(new_code)

            # Need to reload modules for changes to take effect
            self._reload_algorithm_modules()

            # Run simulation
            metrics = self._run_headless_simulation(algorithm_id, seed)

            return metrics

        finally:
            # Restore original file
            if backup_file and os.path.exists(backup_file.name):
                shutil.copy(backup_file.name, source_file)
                os.unlink(backup_file.name)
                # Reload again to restore original behavior
                self._reload_algorithm_modules()

    def _reload_algorithm_modules(self) -> None:
        """Reload algorithm modules to pick up code changes."""
        import importlib
        import sys

        # Modules that need reloading
        modules_to_reload = [
            "core.algorithms.food_seeking",
            "core.algorithms.predator_avoidance",
            "core.algorithms.schooling",
            "core.algorithms.energy_management",
            "core.algorithms.territory",
            "core.algorithms.poker_behavior",
            "core.algorithms",
        ]

        for module_name in modules_to_reload:
            if module_name in sys.modules:
                try:
                    importlib.reload(sys.modules[module_name])
                except Exception as e:
                    logger.warning(f"Failed to reload {module_name}: {e}")

    def _run_headless_simulation(
        self,
        algorithm_id: str,
        seed: int,
    ) -> dict[str, float]:
        """Run a headless simulation and return algorithm performance.

        Args:
            algorithm_id: Algorithm to track
            seed: Random seed

        Returns:
            Performance metrics dict
        """
        from core.worlds import WorldRegistry

        # Create simulation via WorldRegistry
        world = WorldRegistry.create_world("tank", seed=seed)
        world.reset(seed=seed)
        engine = world.engine

        # Run simulation
        logger.info(f"  Running {self.test_frames} frame simulation...")
        for _ in range(self.test_frames):
            engine.update()

        # Get algorithm performance
        ecosystem = engine.get_ecosystem()
        algorithm_performance = ecosystem.get_algorithm_performance_summary()

        # Find the target algorithm's metrics
        algo_metrics = algorithm_performance.get(algorithm_id, {})

        if not algo_metrics:
            # Algorithm may have gone extinct - return zeros
            logger.warning(f"  Algorithm {algorithm_id} not found in results (extinct?)")
            return {
                "reproduction_rate": 0.0,
                "survival_rate": 0.0,
                "avg_lifespan_frames": 0.0,
            }

        return {
            "reproduction_rate": algo_metrics.get("reproduction_rate", 0.0),
            "survival_rate": algo_metrics.get("survival_rate", 0.0),
            "avg_lifespan_frames": algo_metrics.get("avg_lifespan_frames", 0.0),
            "total_births": algo_metrics.get("total_births", 0),
            "total_deaths": algo_metrics.get("total_deaths", 0),
        }

    def validate_syntax(self, new_code: str) -> tuple[bool, str]:
        """Validate that the new code has valid Python syntax.

        Args:
            new_code: Source code to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            compile(new_code, "<string>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.msg}"


def quick_validate(
    algorithm_id: str,
    new_code: str,
    baseline_metrics: dict[str, float],
    test_frames: int = 5000,
    seed: int = 42,
) -> ValidationResult:
    """Convenience function for quick validation.

    Args:
        algorithm_id: Algorithm being improved
        new_code: Improved source code
        baseline_metrics: Original performance metrics
        test_frames: Frames for test simulation
        seed: Random seed

    Returns:
        ValidationResult
    """
    validator = AlgorithmValidator(test_frames=test_frames)
    return validator.validate_improvement(
        algorithm_id=algorithm_id,
        new_code=new_code,
        baseline_metrics=baseline_metrics,
        seed=seed,
    )
