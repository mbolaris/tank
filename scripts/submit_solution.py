#!/usr/bin/env python3
"""CLI tool for submitting and managing TankWorld solutions.

Usage:
    python scripts/submit_solution.py submit --name "My Strategy" --author "username"
    python scripts/submit_solution.py list
    python scripts/submit_solution.py evaluate <solution_id>
    python scripts/submit_solution.py compare
    python scripts/submit_solution.py report
"""

import argparse
import json
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.solutions import (
    SolutionTracker,
    SolutionBenchmark,
    SolutionRecord,
)
from core.solutions.benchmark import SolutionBenchmarkConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_submit(args):
    """Submit a new solution from the current simulation's best performer."""
    tracker = SolutionTracker()

    # If we have a solution file, load and submit it
    if args.file:
        solution = SolutionRecord.load(args.file)
        if args.name:
            solution.metadata.name = args.name
        if args.author:
            solution.metadata.author = args.author
        if args.description:
            solution.metadata.description = args.description
    else:
        # Create a placeholder solution for manual specification
        # In practice, this would capture from a running simulation
        from datetime import datetime
        from core.solutions.models import SolutionMetadata

        now = datetime.utcnow()
        solution_id = f"manual_{now.strftime('%Y%m%d_%H%M%S')}"

        metadata = SolutionMetadata(
            solution_id=solution_id,
            name=args.name or "Manual Solution",
            description=args.description or "Manually submitted solution",
            author=args.author or os.environ.get("USER", "anonymous"),
            submitted_at=now.isoformat(),
        )

        solution = SolutionRecord(metadata=metadata)
        print("Note: Created placeholder solution. For real submissions,")
        print("use --file to specify a solution JSON file from simulation capture.")

    # Evaluate the solution
    if args.evaluate:
        print(f"\nEvaluating solution against benchmark opponents...")
        benchmark = SolutionBenchmark()
        result = benchmark.evaluate_solution(solution, verbose=True)
        solution.benchmark_result = result
        print(f"\nResults:")
        print(f"  Elo Rating: {result.elo_rating:.0f}")
        print(f"  Skill Tier: {result.skill_tier}")
        print(f"  bb/100: {result.weighted_bb_per_100:+.2f}")

    # Save the solution
    filepath = tracker.save_solution(solution)
    print(f"\nSolution saved to: {filepath}")

    # Submit to git if requested
    if args.push:
        print("\nSubmitting to git...")
        success = tracker.submit_to_git(solution, push=True)
        if success:
            print("Successfully submitted to git!")
        else:
            print("Failed to submit to git. Check error messages above.")

    print(f"\nSolution ID: {solution.metadata.solution_id}")


def cmd_list(args):
    """List all submitted solutions."""
    tracker = SolutionTracker()
    solutions = tracker.load_all_solutions()

    if not solutions:
        print("No solutions found in solutions/ directory.")
        return

    print(f"\nFound {len(solutions)} solutions:\n")
    print(f"{'Rank':<6} {'Name':<30} {'Author':<15} {'Elo':<8} {'Tier':<12}")
    print("-" * 75)

    # Sort by Elo if available
    solutions.sort(
        key=lambda s: s.benchmark_result.elo_rating if s.benchmark_result else 0,
        reverse=True,
    )

    for rank, solution in enumerate(solutions, 1):
        elo = "-"
        tier = "-"
        if solution.benchmark_result:
            elo = f"{solution.benchmark_result.elo_rating:.0f}"
            tier = solution.benchmark_result.skill_tier

        print(
            f"#{rank:<5} {solution.metadata.name:<30} "
            f"{solution.metadata.author:<15} {elo:<8} {tier:<12}"
        )

    print()


def cmd_evaluate(args):
    """Evaluate a specific solution or all solutions."""
    tracker = SolutionTracker()
    benchmark = SolutionBenchmark(
        SolutionBenchmarkConfig(
            hands_per_opponent=args.hands,
            num_duplicate_sets=args.duplicates,
        )
    )

    if args.solution_id:
        # Evaluate specific solution
        solutions = tracker.load_all_solutions()
        target = None
        for sol in solutions:
            if sol.metadata.solution_id.startswith(args.solution_id):
                target = sol
                break

        if target is None:
            print(f"Solution not found: {args.solution_id}")
            return

        print(f"Evaluating: {target.metadata.name}")
        result = benchmark.evaluate_solution(target, verbose=True)
        target.benchmark_result = result

        # Save updated solution
        tracker.save_solution(target)

        print(f"\nResults for {target.metadata.name}:")
        print(f"  Elo Rating: {result.elo_rating:.0f}")
        print(f"  Skill Tier: {result.skill_tier}")
        print(f"  bb/100: {result.weighted_bb_per_100:+.2f}")
        print(f"  Hands Played: {result.total_hands_played:,}")
        print("\n  Per-opponent results:")
        for opp, bb in sorted(result.per_opponent.items()):
            print(f"    {opp:<20}: {bb:+.2f} bb/100")
    else:
        # Evaluate all solutions
        solutions = tracker.load_all_solutions()
        if not solutions:
            print("No solutions found.")
            return

        print(f"Evaluating {len(solutions)} solutions...")
        results = benchmark.evaluate_all_solutions(solutions, verbose=True)

        # Save all solutions with updated results
        for sol in solutions:
            tracker.save_solution(sol)

        print("\nEvaluation complete!")


def cmd_compare(args):
    """Compare all solutions against each other."""
    tracker = SolutionTracker()
    benchmark = SolutionBenchmark()

    solutions = tracker.load_all_solutions()
    if len(solutions) < 2:
        print("Need at least 2 solutions to compare.")
        return

    print(f"Comparing {len(solutions)} solutions...")

    # Ensure all are evaluated
    for sol in solutions:
        if sol.benchmark_result is None:
            print(f"Evaluating {sol.metadata.name}...")
            sol.benchmark_result = benchmark.evaluate_solution(sol)

    # Run comparison
    comparison = benchmark.compare_solutions(solutions, verbose=True)

    print("\n" + comparison.get_summary())

    # Save comparison results
    comparison_path = "solutions/comparison_results.json"
    with open(comparison_path, "w") as f:
        json.dump(comparison.to_dict(), f, indent=2)
    print(f"\nComparison saved to: {comparison_path}")


def cmd_report(args):
    """Generate a comprehensive benchmark report."""
    tracker = SolutionTracker()
    benchmark = SolutionBenchmark()

    solutions = tracker.load_all_solutions()
    if not solutions:
        print("No solutions found.")
        return

    print(f"Generating report for {len(solutions)} solutions...")

    # Ensure all are evaluated
    unevaluated = [s for s in solutions if s.benchmark_result is None]
    if unevaluated:
        print(f"Evaluating {len(unevaluated)} solutions first...")
        benchmark.evaluate_all_solutions(unevaluated, verbose=True)
        for sol in unevaluated:
            tracker.save_solution(sol)

    # Generate report
    output_path = args.output or "solutions/benchmark_report.txt"
    report = benchmark.generate_report(solutions, output_path)

    print(f"\nReport saved to: {output_path}")
    if args.print_report:
        print("\n" + report)


def cmd_capture(args):
    """Capture best solution from a running or recent simulation."""
    # This requires integration with the simulation
    print("Capture from simulation not yet implemented.")
    print("Use --file with submit command to submit a previously saved solution.")


def main():
    parser = argparse.ArgumentParser(
        description="TankWorld Solution Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Submit a solution from file:
    python scripts/submit_solution.py submit --file solution.json --push

  List all solutions:
    python scripts/submit_solution.py list

  Evaluate a specific solution:
    python scripts/submit_solution.py evaluate abc123

  Compare all solutions:
    python scripts/submit_solution.py compare

  Generate benchmark report:
    python scripts/submit_solution.py report --print
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit a new solution")
    submit_parser.add_argument("--file", "-f", help="Solution JSON file to submit")
    submit_parser.add_argument("--name", "-n", help="Name for the solution")
    submit_parser.add_argument("--author", "-a", help="Author name")
    submit_parser.add_argument("--description", "-d", help="Description")
    submit_parser.add_argument(
        "--evaluate", "-e", action="store_true",
        help="Evaluate against benchmarks before submitting"
    )
    submit_parser.add_argument(
        "--push", "-p", action="store_true",
        help="Push to git after saving"
    )
    submit_parser.set_defaults(func=cmd_submit)

    # List command
    list_parser = subparsers.add_parser("list", help="List all solutions")
    list_parser.set_defaults(func=cmd_list)

    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate solution(s)")
    eval_parser.add_argument(
        "solution_id", nargs="?",
        help="Solution ID to evaluate (evaluates all if not specified)"
    )
    eval_parser.add_argument(
        "--hands", "-n", type=int, default=500,
        help="Hands per opponent (default: 500)"
    )
    eval_parser.add_argument(
        "--duplicates", "-d", type=int, default=25,
        help="Duplicate sets per opponent (default: 25)"
    )
    eval_parser.set_defaults(func=cmd_evaluate)

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare all solutions")
    compare_parser.set_defaults(func=cmd_compare)

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate benchmark report")
    report_parser.add_argument("--output", "-o", help="Output file path")
    report_parser.add_argument(
        "--print", dest="print_report", action="store_true",
        help="Print report to console"
    )
    report_parser.set_defaults(func=cmd_report)

    # Capture command
    capture_parser = subparsers.add_parser(
        "capture", help="Capture best from simulation"
    )
    capture_parser.set_defaults(func=cmd_capture)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
