#!/usr/bin/env python3
"""AI Code Evolution Agent - Automated Algorithm Improvement Bot

This script implements a "Coding Agent" that:
1. Reads simulation statistics from JSON export
2. Identifies underperforming algorithms
3. Uses an LLM (Claude/GPT) to generate code improvements
4. Creates a git branch and commits the changes
5. Pushes the branch for pull request creation

This enables a Continuous Improvement (CI) Loop where the AI acts as a
"Junior Developer" that proposes improvements based on simulation results.

Usage:
    python scripts/ai_code_evolution_agent.py results.json --provider anthropic
    python scripts/ai_code_evolution_agent.py results.json --provider openai
    python scripts/ai_code_evolution_agent.py results.json --dry-run  # Don't commit/push

Environment Variables:
    ANTHROPIC_API_KEY: For Claude API access
    OPENAI_API_KEY: For GPT API access
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class AlgorithmImprover:
    """AI-powered algorithm improvement agent."""

    def __init__(self, provider: str = "anthropic", dry_run: bool = False):
        """Initialize the improver.

        Args:
            provider: LLM provider ("anthropic" or "openai")
            dry_run: If True, don't commit or push changes
        """
        self.provider = provider
        self.dry_run = dry_run

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

    def load_stats(self, stats_file: str) -> Dict:
        """Load simulation statistics from JSON file.

        Args:
            stats_file: Path to stats JSON file

        Returns:
            Dictionary with stats data
        """
        logger.info(f"Loading stats from: {stats_file}")
        with open(stats_file) as f:
            return json.load(f)

    def identify_worst_performer(self, stats: Dict) -> Optional[Tuple[str, Dict]]:
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

    def generate_improvement(self, algo_name: str, performance: Dict, source_code: str) -> str:
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

    def _build_improvement_prompt(self, algo_name: str, performance: Dict, source_code: str) -> str:
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
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text

    def _call_gpt(self, prompt: str) -> str:
        """Call OpenAI GPT API for code generation.

        Args:
            prompt: The improvement prompt

        Returns:
            Generated code
        """
        try:
            import openai
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

        client = openai.OpenAI(api_key=self.api_key)

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096,
        )

        return response.choices[0].message.content

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

    def create_branch_and_commit(self, algo_name: str, performance: Dict) -> None:
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

    def run(self, stats_file: str) -> None:
        """Run the full improvement workflow.

        Args:
            stats_file: Path to simulation stats JSON
        """
        logger.info("=" * 80)
        logger.info("AI Code Evolution Agent - Starting")
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

        # Step 5: Generate improvement
        improved_code = self.generate_improvement(algo_name, performance, current_code)

        # Step 6: Write improved code
        self.write_improved_code(source_file, improved_code)

        # Step 7: Create branch and commit
        self.create_branch_and_commit(algo_name, performance)

        logger.info("=" * 80)
        logger.info("AI Code Evolution Agent - Complete!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review the changes with: git diff HEAD~1")
        logger.info("2. Test the simulation to verify improvements")
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
        "--dry-run",
        action="store_true",
        help="Don't actually commit or push changes (for testing)",
    )

    args = parser.parse_args()

    try:
        improver = AlgorithmImprover(provider=args.provider, dry_run=args.dry_run)
        improver.run(args.stats_file)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
