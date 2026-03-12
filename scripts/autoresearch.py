#!/usr/bin/env python3
"""Autoresearch: Autonomous experiment loop for Tank World.

Inspired by Karpathy's autoresearch pattern. An AI agent (or human) modifies
algorithm code, the loop runs a fixed-budget benchmark, keeps or discards the
change based on a single score, and logs every experiment to results.tsv.

The loop runs indefinitely. ~12 experiments/hour at 5-min budget.

Design principles (from Karpathy):
    - Fixed time/frame budget per experiment: makes results comparable
    - Single metric for keep/discard: ecosystem_health score
    - Git commit per experiment: full traceability
    - results.tsv: cumulative append-only experiment log
    - Never stops: runs until manually interrupted

Usage:
    # Autonomous mode (AI generates improvements, runs forever)
    python scripts/autoresearch.py --provider anthropic

    # Manual mode (you edit code, script benchmarks + logs)
    python scripts/autoresearch.py --manual

    # Custom benchmark and budget
    python scripts/autoresearch.py --benchmark benchmarks/tank/survival_5k.py --seed 42

    # Limit iterations (default: infinite)
    python scripts/autoresearch.py --max-iterations 20
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add repo root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("autoresearch")

# ── Constants ──────────────────────────────────────────────────────────────

DEFAULT_BENCHMARK = "benchmarks/tank/ecosystem_health_10k.py"
DEFAULT_SEED = 42
RESULTS_TSV = "results.tsv"
TSV_HEADERS = [
    "exp_id",
    "timestamp",
    "commit",
    "score",
    "prev_score",
    "delta",
    "status",
    "algo_changed",
    "description",
    "runtime_s",
]

# Files the agent is allowed to modify (Karpathy pattern: constrained scope)
EDITABLE_PATHS = [
    "core/algorithms/composable/definitions.py",
    "core/algorithms/composable/behavior.py",
    "core/algorithms/composable/actions.py",
    "core/config/fish.py",
    "core/config/food.py",
]

# ── Graceful shutdown ──────────────────────────────────────────────────────

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Shutdown requested (Ctrl+C). Finishing current experiment...")
    _shutdown = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)

# ── Benchmark runner ──────────────────────────────────────────────────────


def load_benchmark(path: str):
    """Dynamically load a benchmark module."""
    spec = importlib.util.spec_from_file_location("bench", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load benchmark: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_benchmark(bench_path: str, seed: int) -> dict[str, Any]:
    """Run a benchmark and return its result dict."""
    mod = load_benchmark(bench_path)
    return mod.run(seed)


# ── Results TSV ───────────────────────────────────────────────────────────


def init_results_tsv(path: str) -> None:
    """Create results.tsv with headers if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(TSV_HEADERS)
        logger.info(f"Created {path}")


def append_result(
    path: str,
    exp_id: int,
    commit: str,
    score: float,
    prev_score: float,
    status: str,
    algo_changed: str,
    description: str,
    runtime: float,
) -> None:
    """Append one experiment row to results.tsv."""
    delta = score - prev_score
    with open(path, "a", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(
            [
                exp_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                commit[:7],
                f"{score:.6f}",
                f"{prev_score:.6f}",
                f"{delta:+.6f}",
                status,
                algo_changed,
                description,
                f"{runtime:.1f}",
            ]
        )


def get_best_score(path: str) -> float | None:
    """Read the best 'keep' score from results.tsv."""
    if not os.path.exists(path):
        return None
    best = None
    with open(path) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            if row.get("status") == "keep":
                s = float(row["score"])
                if best is None or s > best:
                    best = s
    return best


# ── Git helpers ───────────────────────────────────────────────────────────


def git_commit_hash() -> str:
    """Get current short commit hash."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def git_commit(message: str) -> str:
    """Stage editable files and commit. Returns new commit hash."""
    # Only stage the files the agent is allowed to touch
    for p in EDITABLE_PATHS:
        full = ROOT / p
        if full.exists():
            subprocess.run(["git", "add", str(full)], cwd=ROOT, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message, "--allow-empty"],
        cwd=ROOT,
        capture_output=True,
    )
    return git_commit_hash()


def git_reset_to(commit: str) -> None:
    """Hard-reset working tree to a specific commit (discard failed experiment)."""
    subprocess.run(
        ["git", "reset", "--hard", commit],
        cwd=ROOT,
        capture_output=True,
    )


def git_has_changes() -> bool:
    """Check if any editable files have uncommitted changes."""
    result = subprocess.run(
        ["git", "diff", "--name-only"] + [str(ROOT / p) for p in EDITABLE_PATHS],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


# ── AI improvement generator ─────────────────────────────────────────────


def generate_ai_improvement(
    provider: str,
    api_key: str,
    best_score: float,
    last_result: dict[str, Any] | None,
    experiment_history: list[dict],
) -> tuple[str, str]:
    """Ask an LLM to suggest one code change. Returns (file_changed, description).

    The LLM edits files in-place via tool use or by returning code.
    For simplicity, we use the existing ai_code_evolution_agent pattern:
    run a headless sim, identify worst algo, improve it.
    """
    # Run a quick sim to get current stats
    logger.info("Running stats collection simulation (5000 frames)...")
    stats_path = str(ROOT / ".autoresearch_stats.json")
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "main.py"),
            "--headless",
            "--max-frames",
            "5000",
            "--export-stats",
            stats_path,
            "--seed",
            "42",
        ],
        cwd=ROOT,
        capture_output=True,
    )

    if not os.path.exists(stats_path):
        return "none", "stats collection failed"

    with open(stats_path) as f:
        stats = json.load(f)

    # Identify worst performer
    algo_perf = stats.get("algorithm_performance", {})
    candidates = {
        name: perf for name, perf in algo_perf.items() if perf.get("total_births", 0) >= 3
    }

    if not candidates:
        return "none", "no algorithms with sufficient data"

    worst_name, worst_perf = min(
        candidates.items(),
        key=lambda x: x[1].get("reproduction_rate", 1.0),
    )

    # Read current source
    source_file = worst_perf.get("source_file", "")
    if not source_file or not os.path.exists(source_file):
        # Fallback: try the composable definitions
        source_file = str(ROOT / "core/algorithms/composable/definitions.py")

    with open(source_file) as f:
        current_code = f.read()

    # Build context-rich prompt with experiment history
    history_text = ""
    if experiment_history:
        recent = experiment_history[-10:]  # Last 10 experiments
        history_text = "\n\nRECENT EXPERIMENT HISTORY (learn from what worked/failed):\n"
        for h in recent:
            history_text += (
                f"  exp_{h['exp_id']}: score={h['score']:.4f} "
                f"delta={h['delta']:+.4f} status={h['status']} "
                f"desc={h['description']}\n"
            )

    death_breakdown = worst_perf.get("death_breakdown", {})
    main_death = (
        max(death_breakdown.items(), key=lambda x: x[1])[0] if death_breakdown else "unknown"
    )

    prompt = f"""You are an autonomous research agent improving fish behavior algorithms
in an evolutionary simulation. Your goal: maximize the ecosystem health benchmark score.

CURRENT BEST SCORE: {best_score:.6f}
TARGET ALGORITHM: {worst_name} (worst performer)
REPRODUCTION RATE: {worst_perf.get('reproduction_rate', 0):.2%}
MAIN DEATH CAUSE: {main_death}
{history_text}

CURRENT SOURCE ({source_file}):
```python
{current_code[:8000]}
```

RULES:
1. Make ONE focused change. Small, testable, reversible.
2. Prefer parameter tuning over structural changes.
3. If recent history shows parameter tuning plateaued, try structural changes.
4. Simpler is better. Code deletions that maintain score are wins.
5. Return ONLY the complete Python file content, no markdown fences.
"""

    # Call LLM
    improved_code = _call_llm(provider, api_key, prompt)

    # Write improved code
    with open(source_file, "w") as f:
        f.write(improved_code)

    description = f"improve {worst_name}: address {main_death} deaths"
    algo_changed = worst_name

    # Cleanup temp stats
    if os.path.exists(stats_path):
        os.remove(stats_path)

    return algo_changed, description


def _call_llm(provider: str, api_key: str, prompt: str) -> str:
    """Call Claude or GPT and return the response text."""
    if provider == "anthropic":
        anthropic = importlib.import_module("anthropic")
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        content = getattr(msg, "content", [])
        if isinstance(content, list) and content:
            text = getattr(content[0], "text", "")
            if isinstance(text, str):
                return text
        raise ValueError("Unexpected Anthropic response format")
    elif provider == "openai":
        openai = importlib.import_module("openai")
        client = openai.OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=8192,
        )
        text = resp.choices[0].message.content
        if isinstance(text, str):
            return text
        raise ValueError("Unexpected OpenAI response format")
    else:
        raise ValueError(f"Unknown provider: {provider}")


# ── Main loop ─────────────────────────────────────────────────────────────


def run_loop(args: argparse.Namespace) -> None:
    """The autonomous experiment loop. Runs until interrupted."""
    bench_path = str(ROOT / args.benchmark)
    tsv_path = str(ROOT / RESULTS_TSV)

    init_results_tsv(tsv_path)

    # Get API key if in autonomous mode
    api_key = None
    if not args.manual:
        if args.provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        elif args.provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error(f"Set {args.provider.upper()}_API_KEY or use --manual mode")
            sys.exit(1)

    # Establish baseline
    logger.info("=" * 70)
    logger.info("AUTORESEARCH: Tank World Autonomous Experiment Loop")
    logger.info(f"Benchmark: {args.benchmark}")
    logger.info(f"Seed: {args.seed}")
    logger.info(f"Mode: {'manual' if args.manual else f'autonomous ({args.provider})'}")
    logger.info("=" * 70)

    logger.info("Running baseline benchmark...")
    baseline_result = run_benchmark(bench_path, args.seed)
    baseline_score = baseline_result["score"]
    best_score = get_best_score(tsv_path) or baseline_score
    if baseline_score > best_score:
        best_score = baseline_score

    baseline_commit = git_commit_hash()
    logger.info(f"Baseline score: {baseline_score:.6f} (commit: {baseline_commit})")
    logger.info(f"Best known score: {best_score:.6f}")
    logger.info("")

    # Experiment history for AI context
    experiment_history: list[dict] = []

    exp_id = 0
    keeps = 0
    discards = 0
    crashes = 0

    while not _shutdown:
        exp_id += 1

        if 0 < args.max_iterations < exp_id:
            logger.info(f"Reached max iterations ({args.max_iterations}). Stopping.")
            break

        logger.info("─" * 70)
        logger.info(f"EXPERIMENT {exp_id}")
        logger.info("─" * 70)

        # Save state before experiment
        pre_commit = git_commit_hash()
        algo_changed = "manual"
        description = "manual edit"

        if args.manual:
            # Wait for user to make changes
            logger.info("Make your changes to the algorithm files, then press Enter...")
            try:
                input()
            except EOFError:
                break

            if not git_has_changes():
                logger.info("No changes detected. Skipping.")
                continue
            description = input("Brief description of change: ").strip() or "manual edit"
        else:
            # AI generates an improvement
            logger.info("AI generating improvement...")
            try:
                algo_changed, description = generate_ai_improvement(
                    provider=args.provider,
                    api_key=api_key,
                    best_score=best_score,
                    last_result=baseline_result,
                    experiment_history=experiment_history,
                )
            except Exception as e:
                logger.warning(f"AI generation failed: {e}")
                crashes += 1
                append_result(
                    tsv_path,
                    exp_id,
                    pre_commit,
                    0.0,
                    best_score,
                    "crash",
                    "none",
                    f"generation failed: {e}",
                    0.0,
                )
                experiment_history.append(
                    {
                        "exp_id": exp_id,
                        "score": 0.0,
                        "delta": -best_score,
                        "status": "crash",
                        "description": str(e),
                    }
                )
                continue

        # Commit the change
        commit_msg = f"exp_{exp_id}: {description}"
        new_commit = git_commit(commit_msg)
        logger.info(f"Committed: {new_commit} - {description}")

        # Run benchmark
        logger.info("Running benchmark...")
        exp_start = time.time()
        try:
            result = run_benchmark(bench_path, args.seed)
            score = result["score"]
            runtime = time.time() - exp_start
        except Exception as e:
            logger.warning(f"Benchmark crashed: {e}")
            runtime = time.time() - exp_start
            crashes += 1
            append_result(
                tsv_path,
                exp_id,
                new_commit,
                0.0,
                best_score,
                "crash",
                algo_changed,
                f"crash: {e}",
                runtime,
            )
            experiment_history.append(
                {
                    "exp_id": exp_id,
                    "score": 0.0,
                    "delta": -best_score,
                    "status": "crash",
                    "description": str(e),
                }
            )
            # Reset to last good state
            git_reset_to(pre_commit)
            continue

        # Keep or discard
        delta = score - best_score
        if score > best_score:
            status = "keep"
            keeps += 1
            best_score = score
            baseline_result = result
            logger.info(
                f"  KEEP: {score:.6f} (delta: {delta:+.6f}) "
                f"[{keeps} keeps / {discards} discards / {crashes} crashes]"
            )
        else:
            status = "discard"
            discards += 1
            logger.info(
                f"  DISCARD: {score:.6f} (delta: {delta:+.6f}) "
                f"[{keeps} keeps / {discards} discards / {crashes} crashes]"
            )
            # Reset to last good state
            git_reset_to(pre_commit)

        # Log to TSV
        append_result(
            tsv_path,
            exp_id,
            new_commit,
            score,
            best_score if status == "discard" else score - delta,
            status,
            algo_changed,
            description,
            runtime,
        )
        experiment_history.append(
            {
                "exp_id": exp_id,
                "score": score,
                "delta": delta,
                "status": status,
                "description": description,
            }
        )

        logger.info("")

    # Summary
    logger.info("=" * 70)
    logger.info("AUTORESEARCH SESSION COMPLETE")
    logger.info(f"  Experiments: {exp_id}")
    logger.info(f"  Keeps: {keeps}")
    logger.info(f"  Discards: {discards}")
    logger.info(f"  Crashes: {crashes}")
    logger.info(f"  Best score: {best_score:.6f}")
    logger.info(f"  Results: {tsv_path}")
    logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Autoresearch: Autonomous experiment loop for Tank World",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Inspired by Karpathy's autoresearch. The human writes the prompt (program.md),
the AI agent iterates on the code. Fixed budget per experiment, single metric
for keep/discard, git commit per experiment, results.tsv for tracking.

Examples:
  # Run autonomously with Claude
  python scripts/autoresearch.py --provider anthropic

  # Manual mode: you edit, script benchmarks
  python scripts/autoresearch.py --manual

  # Run 20 experiments then stop
  python scripts/autoresearch.py --max-iterations 20

  # Use survival benchmark instead
  python scripts/autoresearch.py --benchmark benchmarks/tank/survival_5k.py
""",
    )

    parser.add_argument(
        "--manual",
        action="store_true",
        help="Manual mode: wait for human edits between experiments",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider for autonomous mode (default: anthropic)",
    )
    parser.add_argument(
        "--benchmark",
        default=DEFAULT_BENCHMARK,
        help=f"Benchmark to use (default: {DEFAULT_BENCHMARK})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=0,
        help="Max experiments to run (0 = infinite, default: 0)",
    )

    args = parser.parse_args()
    run_loop(args)


if __name__ == "__main__":
    main()
