#!/usr/bin/env python3
"""Evolution health report CLI driver for a long-running Tank World simulation.

This script parses command-line arguments, executes IO (attaching to live servers,
loading stats/history files, or running headless probes), and outputs the formatted
report or structured JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, cast
from urllib.request import urlopen

# Import all constants and core functions from the helper modules
from tools.evolution_report_analyzer import (
    DIVERSITY_LOW,
    GEN_RATE_HEALTHY_PER_10K,
    GEN_RATE_SLOW_PER_10K,
    MIN_SAMPLES_FOR_TREND,
    POP_CV_UNSTABLE,
    POP_STABLE_MIN,
    STARVATION_BROKEN,
    STARVATION_STRAINED,
    TRAIT_BOUNDS,
    TRAIT_DRIFT_SELECTION_PCT,
    _boot_ids,
    _local_cv,
    _range_normalized_drift,
    _roll_up,
    _selection_quality,
    _stable_samples,
    _trait_drift,
    _unwrap_snapshot,
    analyze_history,
    analyze_stats,
    assess,
    build_report,
    extract_history_samples,
    extract_stats,
    population_value,
    starvation_fraction,
)
from tools.evolution_report_display import format_human, recommend

__all__ = [
    "TRAIT_BOUNDS",
    "TRAIT_DRIFT_SELECTION_PCT",
    "GEN_RATE_HEALTHY_PER_10K",
    "GEN_RATE_SLOW_PER_10K",
    "STARVATION_STRAINED",
    "STARVATION_BROKEN",
    "POP_STABLE_MIN",
    "POP_CV_UNSTABLE",
    "DIVERSITY_LOW",
    "MIN_SAMPLES_FOR_TREND",
    "_unwrap_snapshot",
    "extract_history_samples",
    "extract_stats",
    "starvation_fraction",
    "population_value",
    "analyze_history",
    "_trait_drift",
    "_local_cv",
    "_stable_samples",
    "_boot_ids",
    "_range_normalized_drift",
    "_selection_quality",
    "analyze_stats",
    "assess",
    "_roll_up",
    "build_report",
    "recommend",
    "format_human",
]


# ---------------------------------------------------------------------------
# IO: live server, files, probe, watch
# ---------------------------------------------------------------------------
def _http_get_json(url: str, timeout: float = 10.0) -> Any:
    # Trusted, user-supplied local/LAN URL pointing at their own simulation server.
    with urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def resolve_world_id(base_url: str, world_id: str | None) -> str:
    if world_id:
        return world_id
    data = _http_get_json(f"{base_url}/api/worlds/default/id")
    wid: str = data["world_id"]
    return wid


def fetch_live(base_url: str, world_id: str | None) -> tuple[list[dict], dict, str]:
    """Fetch samples + current stats from a running server.

    Prefers the snapshot endpoint (stats + metrics_history in one call); falls
    back to the metrics-history endpoint alone.
    """
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    try:
        snap = _http_get_json(f"{base_url}/api/worlds/{wid}/snapshot")
        samples = extract_history_samples(snap)
        stats = extract_stats(snap)
        if samples or stats:
            return samples, stats, f"live:{base_url} world={wid} (snapshot)"
    except Exception:
        pass
    payload = _http_get_json(f"{base_url}/api/world/{wid}/metrics/history")
    return extract_history_samples(payload), {}, f"live:{base_url} world={wid} (metrics/history)"


def load_history_file(path: str) -> list[dict]:
    """Load a metrics-history payload (JSON) or a watch-journal (JSONL)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        payload = json.loads(text)
        return extract_history_samples(payload)
    except json.JSONDecodeError:
        samples: list[dict] = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                samples.append(json.loads(line))
        return samples


def run_probe(frames: int, seed: int, interval: int) -> tuple[list[dict], dict, str]:
    """Run a fresh, deterministic headless sim, sampling trait means as we go."""
    import os

    sys.path.insert(0, os.getcwd())
    from core.entities import Fish
    from core.services.stats.trait_trends import compute_trait_means
    from core.worlds import WorldRegistry

    config: dict[str, object] = {
        "headless": True,
        "screen_width": 2000,
        "screen_height": 2000,
        "max_population": 60,
        "max_fish": 40,
        "soccer_enabled": False,
        "plants_enabled": False,
        "poker_activity_enabled": False,
        "auto_food_spawn_rate": 9,
    }
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)

    samples: list[dict] = []
    for i in range(frames):
        world.step()
        if (i + 1) % interval == 0:
            stats = world.get_stats(include_distributions=False)
            living = [e for e in world.entities_list if isinstance(e, Fish) and not e.is_dead()]
            div = cast(dict[str, object], stats.get("diversity_stats", {}))
            samples.append(
                {
                    "frame": i + 1,
                    "max_generation": stats.get("max_generation", 0),
                    "population": stats.get("fish_count", 0),
                    "births_total": stats.get("total_births", stats.get("births", 0)),
                    "deaths_total": stats.get("total_deaths", stats.get("deaths", 0)),
                    "diversity_score": div.get("diversity_score", 0.0),
                    "traits": compute_trait_means(living),
                }
            )
    final = world.get_current_metrics(include_distributions=True)
    return samples, extract_stats(final), f"probe frames={frames} seed={seed} interval={interval}"


def _new_samples_since(last_frame: int, samples: list[dict]) -> list[dict]:
    """Samples strictly newer than last_frame (for incremental journaling)."""
    return [s for s in samples if isinstance(s.get("frame"), int) and s["frame"] > last_frame]


def watch(base_url: str, world_id: str | None, interval: float, journal: str | None) -> None:
    """Poll the running server and stream new samples to an append-only journal.

    Runs until interrupted. This is how multi-day trends survive the in-memory
    history buffer (which wraps after max_samples) - the journal is unbounded.
    """
    base_url = base_url.rstrip("/")
    wid = resolve_world_id(base_url, world_id)
    last_frame = -1
    print(
        f"[watch] world={wid} interval={interval}s journal={journal or '(none)'} - Ctrl-C to stop",
        flush=True,
    )
    while True:
        try:
            payload = _http_get_json(f"{base_url}/api/world/{wid}/metrics/history")
            samples = extract_history_samples(payload)
            fresh = _new_samples_since(last_frame, samples)
            if fresh:
                last_frame = fresh[-1]["frame"]
                if journal:
                    with open(journal, "a", encoding="utf-8") as jf:
                        for s in fresh:
                            jf.write(json.dumps(s) + "\n")
                latest = fresh[-1]
                drift = _trait_drift(samples)
                top = ""
                if drift:
                    key = max(drift, key=lambda k: abs(cast(float, drift[k]["pct"])))
                    top = f" topdrift={key}{cast(float, drift[key]['pct']):+.1f}%"
                print(
                    f"[watch] frame={latest.get('frame')} gen={latest.get('max_generation')} "
                    f"pop={latest.get('population')} div={latest.get('diversity_score')}{top}",
                    flush=True,
                )
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # transient server hiccups should not kill the watch
            print(f"[watch] poll failed: {exc}", flush=True)
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[watch] stopped.", flush=True)
            return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evolution health report CLI driver for a long-running Tank World simulation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--url", help="Base URL of a running simulation (e.g. http://127.0.0.1:8000)")
    src.add_argument("--stats", help="Path to an exported stats JSON (main.py --export-stats)")
    src.add_argument(
        "--history", help="Path to a metrics-history payload (JSON) or journal (JSONL)"
    )
    src.add_argument("--probe", action="store_true", help="Run a fresh headless probe simulation")
    parser.add_argument("--world", help="World id (defaults to the server's default world)")
    parser.add_argument("--frames", type=int, default=20000, help="Probe length in frames")
    parser.add_argument("--seed", type=int, default=42, help="Probe seed")
    parser.add_argument("--interval", type=int, default=1000, help="Probe sampling interval frames")
    parser.add_argument(
        "--watch", action="store_true", help="Stream samples to a journal (long runs)"
    )
    parser.add_argument("--watch-interval", type=float, default=300.0, help="Watch poll seconds")
    parser.add_argument("--journal", help="Append-only JSONL journal path for --watch")
    parser.add_argument("--json", action="store_true", help="Emit the structured report as JSON")
    parser.add_argument("--out", help="Write the structured report JSON to this file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.watch:
        base = args.url or "http://127.0.0.1:8000"
        try:
            watch(base, args.world, args.watch_interval, args.journal)
        except KeyboardInterrupt:
            print("\n[watch] stopped.", flush=True)
        return 0

    try:
        if args.stats:
            with open(args.stats, encoding="utf-8") as f:
                blob = json.load(f)
            samples = extract_history_samples(blob)
            stats = extract_stats(blob)
            source = f"stats:{args.stats}"
        elif args.history:
            samples = load_history_file(args.history)
            stats = {}
            source = f"history:{args.history}"
        elif args.probe:
            samples, stats, source = run_probe(args.frames, args.seed, args.interval)
        else:
            base = args.url or "http://127.0.0.1:8000"
            samples, stats, source = fetch_live(base, args.world)
    except Exception as exc:
        print(f"error: could not load simulation data: {exc}", file=sys.stderr)
        if not (args.stats or args.history or args.probe):
            print(
                "hint: is the simulation running? start it with `python main.py`, or analyse an "
                "export with --stats / run a fresh probe with --probe.",
                file=sys.stderr,
            )
        return 2

    report = build_report(samples, stats, source)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(format_human(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
