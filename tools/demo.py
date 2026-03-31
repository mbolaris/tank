"""One-command demo bundle generator for Tank World.

This script creates a timestamped run directory with a short tank simulation,
one soccer episode, and one benchmark result. The output is designed to be
easy to inspect or attach to a PR/comment without digging through console logs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class DemoConfig:
    seed: int
    output_root: Path
    tank_frames: int
    tank_stats_interval: int
    replay_frames: int
    replay_every: int
    soccer_frames: int
    soccer_team_size: int
    benchmark_path: Path


def _json_default(value: Any) -> Any:
    """Best-effort JSON serializer for dataclass-like values."""
    if hasattr(value, "__dict__"):
        return value.__dict__
    return str(value)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _append_log(path: Path, message: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{message}\n")


def _iso_now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_slug() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def _safe_git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def _git_metadata() -> dict[str, Any]:
    status = _safe_git("status", "--short")
    return {
        "commit": _safe_git("rev-parse", "HEAD"),
        "branch": _safe_git("branch", "--show-current"),
        "is_dirty": bool(status),
    }


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _tank_summary(stats: dict[str, Any]) -> dict[str, Any]:
    death_causes = stats.get("death_causes", {})
    return {
        "population": stats.get("total_population", stats.get("population")),
        "max_generation": stats.get("max_generation"),
        "total_births": stats.get("total_births"),
        "total_deaths": stats.get("total_deaths"),
        "starvation_deaths": death_causes.get("starvation", 0),
        "predation_deaths": death_causes.get("predation", 0),
        "old_age_deaths": death_causes.get("old_age", 0),
        "total_energy": stats.get("total_energy"),
    }


def _soccer_summary(episode: dict[str, Any]) -> dict[str, Any]:
    return {
        "winner": episode.get("winner"),
        "score_left": episode.get("score_left"),
        "score_right": episode.get("score_right"),
        "total_goals": episode.get("score_left", 0) + episode.get("score_right", 0),
        "average_fitness": episode.get("average_fitness"),
        "best_agent": episode.get("best_agent"),
    }


def _benchmark_summary(result: dict[str, Any]) -> dict[str, Any]:
    metadata = result.get("metadata", {})
    return {
        "benchmark_id": result.get("benchmark_id"),
        "score": result.get("score"),
        "runtime_seconds": result.get("runtime_seconds"),
        "frames": metadata.get("frames"),
        "team_size": metadata.get("team_size"),
        "n_seeds": metadata.get("n_seeds"),
    }


def run_tank_simulation(config: DemoConfig, run_dir: Path) -> dict[str, Any]:
    """Run the short headless tank simulation and write stats JSON."""
    from main import run_headless

    stats_path = run_dir / "tank_results.json"
    run_headless(
        config.tank_frames,
        config.tank_stats_interval,
        seed=config.seed,
        export_stats=str(stats_path),
        trace_output=None,
    )
    return json.loads(stats_path.read_text(encoding="utf-8"))


def record_tank_replay(config: DemoConfig, run_dir: Path) -> Path:
    """Record a deterministic replay artifact for the tank slice."""
    from backend.replay import record_file

    replay_path = run_dir / "tank.replay.jsonl"
    record_file(
        replay_path,
        seed=config.seed,
        initial_mode="tank",
        steps=config.replay_frames,
        record_every=config.replay_every,
    )
    return replay_path


def _create_default_soccer_population(seed: int, team_size: int) -> list[Any]:
    import random

    from core.code_pool import create_default_genome_code_pool
    from core.genetics import Genome
    from core.genetics.trait import GeneticTrait

    genome_code_pool = create_default_genome_code_pool()
    default_id = genome_code_pool.get_default("soccer_policy")
    rng = random.Random(seed)

    population: list[Genome] = []
    for _ in range(team_size * 2):
        genome = Genome.random(use_algorithm=False, rng=rng)
        if default_id:
            genome.behavioral.soccer_policy_id = GeneticTrait(default_id)
        population.append(genome)
    return population


def run_soccer_episode(config: DemoConfig, run_dir: Path) -> dict[str, Any]:
    """Run a single soccer training episode and persist the result."""
    from core.code_pool import create_default_genome_code_pool
    from core.minigames.soccer import SoccerMatchRunner

    population = _create_default_soccer_population(config.seed, config.soccer_team_size)
    runner = SoccerMatchRunner(
        team_size=config.soccer_team_size,
        genome_code_pool=create_default_genome_code_pool(),
    )
    episode_result, agent_results = runner.run_episode(
        genomes=population,
        seed=config.seed,
        frames=config.soccer_frames,
        goal_weight=100.0,
    )

    serialized_agents: list[dict[str, Any]] = []
    for result in agent_results:
        serialized_agents.append(
            {
                "player_id": result.player_id,
                "team": result.team,
                "goals": result.goals,
                "fitness": result.fitness,
            }
        )

    average_fitness = (
        sum(item["fitness"] for item in serialized_agents) / len(serialized_agents)
        if serialized_agents
        else 0.0
    )
    best_agent = max(serialized_agents, key=lambda item: item["fitness"], default=None)

    payload = {
        "seed": episode_result.seed,
        "frames": episode_result.frames,
        "team_size": config.soccer_team_size,
        "score_left": episode_result.score_left,
        "score_right": episode_result.score_right,
        "winner": episode_result.winner,
        "average_fitness": average_fitness,
        "best_agent": best_agent,
        "player_stats": {
            player_id: {
                "team": stats.team,
                "goals": stats.goals,
                "assists": stats.assists,
                "possessions": stats.possessions,
                "kicks": stats.kicks,
                "total_reward": stats.total_reward,
            }
            for player_id, stats in sorted(episode_result.player_stats.items())
        },
        "agent_results": serialized_agents,
    }
    _write_json(run_dir / "soccer_episode.json", payload)
    return payload


def run_benchmark(config: DemoConfig, run_dir: Path) -> dict[str, Any]:
    """Run the selected benchmark and persist the result JSON."""
    from tools.run_bench import load_benchmark_module

    module = load_benchmark_module(str(config.benchmark_path))
    result = module.run(config.seed)
    result["timestamp"] = time.time()
    _write_json(run_dir / "benchmark_result.json", result)
    return result


def render_summary(
    *,
    run_dir: Path,
    created_at: str,
    config: DemoConfig,
    git_info: dict[str, Any],
    tank_stats: dict[str, Any],
    soccer_episode: dict[str, Any],
    benchmark_result: dict[str, Any],
) -> str:
    """Create the human-readable markdown summary for the run bundle."""
    tank = _tank_summary(tank_stats)
    soccer = _soccer_summary(soccer_episode)
    benchmark = _benchmark_summary(benchmark_result)
    benchmark_rel = config.benchmark_path.relative_to(ROOT).as_posix()

    commit = git_info.get("commit") or "unknown"
    branch = git_info.get("branch") or "unknown"
    dirty = "dirty" if git_info.get("is_dirty") else "clean"

    lines = [
        "# Tank World Demo",
        "",
        f"- Created: `{created_at}`",
        f"- Output: `{_display_path(run_dir)}`",
        f"- Seed: `{config.seed}`",
        f"- Git: `{commit}` on `{branch}` ({dirty})",
        "",
        "## What Ran",
        "",
        f"- Tank headless sim: `{config.tank_frames}` frames, stats every `{config.tank_stats_interval}` frames",
        f"- Tank replay capture: `{config.replay_frames}` frames, every `{config.replay_every}` frames",
        f"- Soccer episode: `{config.soccer_team_size}v{config.soccer_team_size}` for `{config.soccer_frames}` frames",
        f"- Benchmark: `{benchmark_rel}`",
        "",
        "## Highlights",
        "",
        f"- Tank population: `{tank.get('population')}` with `{tank.get('max_generation')}` max generation",
        f"- Tank births/deaths: `{tank.get('total_births')}` / `{tank.get('total_deaths')}`",
        f"- Tank starvation/predation/old-age: `{tank.get('starvation_deaths')}` / `{tank.get('predation_deaths')}` / `{tank.get('old_age_deaths')}`",
        f"- Soccer scoreline: `{soccer.get('score_left')}-{soccer.get('score_right')}` winner `{soccer.get('winner')}`",
        f"- Soccer average fitness: `{soccer.get('average_fitness'):.3f}`",
        f"- Benchmark `{benchmark.get('benchmark_id')}` score: `{benchmark.get('score'):.6f}`",
        "",
        "## Artifacts",
        "",
        "- `manifest.json`",
        "- `demo.log`",
        "- `summary.md`",
        "- `tank_results.json`",
        "- `tank.replay.jsonl`",
        "- `soccer_episode.json`",
        "- `benchmark_result.json`",
        "",
        "## Run Again",
        "",
        "```bash",
        f"python tools/demo.py --seed {config.seed}",
        "```",
    ]
    return "\n".join(lines) + "\n"


def run_demo(config: DemoConfig) -> Path:
    """Run the demo workflow and return the output directory."""
    created_at = _iso_now()
    run_dir = config.output_root / f"demo_{_timestamp_slug()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "demo.log"

    start = time.time()
    git_info = _git_metadata()
    _append_log(log_path, f"[{created_at}] Demo started (seed={config.seed})")
    tank_stats = run_tank_simulation(config, run_dir)
    _append_log(log_path, "Tank simulation completed -> tank_results.json")
    replay_path = record_tank_replay(config, run_dir)
    _append_log(log_path, f"Tank replay recorded -> {replay_path.name}")
    soccer_episode = run_soccer_episode(config, run_dir)
    _append_log(log_path, "Soccer episode completed -> soccer_episode.json")
    benchmark_result = run_benchmark(config, run_dir)
    _append_log(log_path, "Benchmark completed -> benchmark_result.json")
    runtime_seconds = time.time() - start
    _append_log(log_path, f"Demo finished in {runtime_seconds:.2f}s")

    summary = render_summary(
        run_dir=run_dir,
        created_at=created_at,
        config=config,
        git_info=git_info,
        tank_stats=tank_stats,
        soccer_episode=soccer_episode,
        benchmark_result=benchmark_result,
    )
    (run_dir / "summary.md").write_text(summary, encoding="utf-8")

    manifest = {
        "demo_version": 1,
        "created_at": created_at,
        "runtime_seconds": runtime_seconds,
        "seed": config.seed,
        "git": git_info,
        "parameters": {
            "tank_frames": config.tank_frames,
            "tank_stats_interval": config.tank_stats_interval,
            "replay_frames": config.replay_frames,
            "replay_every": config.replay_every,
            "soccer_frames": config.soccer_frames,
            "soccer_team_size": config.soccer_team_size,
            "benchmark_path": config.benchmark_path.relative_to(ROOT).as_posix(),
        },
        "artifacts": {
            "log": "demo.log",
            "summary": "summary.md",
            "tank_stats": "tank_results.json",
            "tank_replay": replay_path.name,
            "soccer_episode": "soccer_episode.json",
            "benchmark_result": "benchmark_result.json",
        },
        "scores": {
            "tank": _tank_summary(tank_stats),
            "soccer_episode": _soccer_summary(soccer_episode),
            "benchmark": _benchmark_summary(benchmark_result),
        },
    }
    _write_json(run_dir / "manifest.json", manifest)
    return run_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a one-command Tank World demo bundle")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic seed (default: 42)")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "runs",
        help="Directory where demo_<timestamp> bundles will be created",
    )
    parser.add_argument(
        "--tank-frames",
        type=int,
        default=1500,
        help="Frames for the short tank headless simulation",
    )
    parser.add_argument(
        "--tank-stats-interval",
        type=int,
        default=500,
        help="Stats interval for the tank headless simulation",
    )
    parser.add_argument(
        "--replay-frames",
        type=int,
        default=300,
        help="Frames to record for the tank replay artifact",
    )
    parser.add_argument(
        "--replay-every",
        type=int,
        default=10,
        help="Fingerprint sampling interval for the replay artifact",
    )
    parser.add_argument(
        "--soccer-frames",
        type=int,
        default=600,
        help="Frames for the soccer episode",
    )
    parser.add_argument(
        "--soccer-team-size",
        type=int,
        default=3,
        help="Players per team for the soccer episode",
    )
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=ROOT / "benchmarks" / "soccer" / "training_3k.py",
        help="Benchmark file to run (default: benchmarks/soccer/training_3k.py)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    benchmark_path = args.benchmark
    if not benchmark_path.is_absolute():
        benchmark_path = (ROOT / benchmark_path).resolve()

    config = DemoConfig(
        seed=args.seed,
        output_root=args.output_root,
        tank_frames=args.tank_frames,
        tank_stats_interval=args.tank_stats_interval,
        replay_frames=args.replay_frames,
        replay_every=args.replay_every,
        soccer_frames=args.soccer_frames,
        soccer_team_size=args.soccer_team_size,
        benchmark_path=benchmark_path,
    )

    run_dir = run_demo(config)
    print(f"Demo bundle created at {run_dir}")
    print(f"Summary: {run_dir / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
