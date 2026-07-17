#!/usr/bin/env python3
"""Summary tool for the attempt ledger.

Reads research/attempts.jsonl and outputs a breakdown of results and stats.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path


def main() -> None:
    # 1. Locate attempts ledger
    env_path = os.environ.get("ATTEMPT_LEDGER_PATH")
    if env_path:
        ledger_path = Path(env_path)
    else:
        project_root = Path(__file__).resolve().parents[1]
        ledger_path = project_root / "research" / "attempts.jsonl"

    if not ledger_path.exists():
        print(f"No attempts ledger found at: {ledger_path}")
        print("Run benchmarks first to generate attempt logs.")
        sys.exit(0)

    # 2. Parse entries
    entries = []
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception as e:
                print(f"Warning: skipped invalid JSON line: {e}")

    if not entries:
        print("The attempts ledger is empty.")
        sys.exit(0)

    # 3. Analyze stats
    total_attempts = len(entries)
    verdicts = Counter(e.get("verdict") for e in entries)
    agents = Counter(e.get("agent_id") for e in entries)
    benchmarks = Counter(e.get("benchmark_id") for e in entries)
    patch_types = Counter(e.get("patch_type", "unknown") for e in entries)

    durations = [e["duration"] for e in entries if e.get("duration") is not None]
    total_duration = sum(durations)
    avg_duration = total_duration / len(durations) if durations else 0.0

    print("=" * 60)
    print("           TANK WORLD ATTEMPT LEDGER SUMMARY")
    print("=" * 60)
    print(f"Total Attempts Recorded: {total_attempts}")
    print(f"Ledger File:             {ledger_path}")
    print("-" * 60)

    print("Verdict Breakdown:")
    for verdict, count in sorted(verdicts.items()):
        pct = (count / total_attempts) * 100
        print(f"  - {verdict:<12}: {count:3} ({pct:5.1f}%)")
    print("-" * 60)

    print("Patch / Mutation Type Breakdown:")
    for patch_type, count in sorted(patch_types.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_attempts) * 100
        print(f"  - {patch_type!s:<25}: {count:3} ({pct:5.1f}%)")
    print("-" * 60)

    print("Agent / Model Activity:")
    for agent, count in sorted(agents.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {agent!s:<25}: {count:3}")
    print("-" * 60)

    print("Benchmark Activity:")
    for bench, count in sorted(benchmarks.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {bench!s:<40}: {count:3}")
    print("-" * 60)

    if durations:
        print("Duration Stats:")
        print(f"  - Total time:   {total_duration:8.2f}s")
        print(f"  - Mean time:    {avg_duration:8.2f}s")
        print(f"  - Max time:     {max(durations):8.2f}s")
        print(f"  - Min time:     {min(durations):8.2f}s")
        print("-" * 60)

    print("Recent Attempts (Last 5):")
    recent = entries[-5:]
    for entry in reversed(recent):
        ts = entry.get("timestamp_iso", "Unknown time")
        agent = entry.get("agent_id", "unknown")
        verdict = entry.get("verdict", "unknown")
        bench = entry.get("benchmark_id", "unknown")
        desc = entry.get("description", "No description")
        patch_type = entry.get("patch_type", "unknown")

        # Handle score delta
        cand = entry.get("candidate_score")
        chmp = entry.get("champion_score")
        score_info = ""
        if cand is not None and chmp is not None:
            score_info = f" (cand={cand}, chmp={chmp})"

        print(f"[{ts}] {agent} -> {verdict.upper()} on {bench} ({patch_type}){score_info}")
        print(f"  Description: {desc}")
        print("-" * 60)


if __name__ == "__main__":
    main()
