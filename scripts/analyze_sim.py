#!/usr/bin/env python3
"""Quick analyzer for the running Tank World simulation.

This script fetches `/api/evaluation-history` and `/api/lineage` from the
local backend and prints a short report: top performers over time and
lineage/clade stats for poker-related algorithms.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Counter as CounterType
from urllib.request import urlopen

BASE = "http://localhost:8000"


def fetch(path):
    with urlopen(BASE + path) as f:
        return json.load(f)


def top_leaderboard(history, top_n=5):
    # Use the last snapshot as latest leaderboard
    if not history:
        return []
    last = history[-1]
    players = last.get("players", [])
    # Sort by net_energy or bb_per_100 if available
    players_sorted = sorted(
        players, key=lambda p: p.get("net_energy", p.get("bb_per_100", 0)), reverse=True
    )
    return players_sorted[:top_n]


def poker_clade_stats(lineage):
    # Count entries per algorithm and find algorithms with 'Poker' or 'poker' in name
    alg_counter: CounterType[str] = Counter()
    poker_members = []
    for rec in lineage:
        alg = rec.get("algorithm", "unknown")
        alg_counter[alg] += 1
        if "poker" in alg.lower() or alg.lower().startswith("poker"):
            poker_members.append(rec)
    # Group by algorithm
    poker_by_alg = defaultdict(list)
    for rec in poker_members:
        poker_by_alg[rec.get("algorithm", "unknown")].append(rec)
    return alg_counter, poker_by_alg


def poker_lifespan_csv(poker_by_alg, out_path="scripts/poker_clades.csv"):
    rows = []
    for alg, members in poker_by_alg.items():
        birth_times = [
            m.get("birth_time", 0)
            for m in members
            if isinstance(m.get("birth_time", None), (int, float))
        ]
        if birth_times:
            first = min(birth_times)
            last = max(birth_times)
            lifespan = last - first
        else:
            first = last = lifespan = 0
        alive = sum(1 for m in members if m.get("is_alive"))
        rows.append(
            {
                "algorithm": alg,
                "members": len(members),
                "alive": alive,
                "first_birth": first,
                "last_birth": last,
                "span": lifespan,
            }
        )

    outp = Path(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["algorithm", "members", "alive", "first_birth", "last_birth", "span"]
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return outp


def main():
    try:
        history = fetch("/api/evaluation-history")
    except Exception as e:
        print("Could not fetch evaluation history:", e)
        sys.exit(1)

    try:
        lineage = fetch("/api/lineage")
    except Exception as e:
        print("Could not fetch lineage:", e)
        sys.exit(1)

    print("Evaluation snapshots:", len(history))
    top = top_leaderboard(history, top_n=8)
    print("Top performers (latest snapshot):")
    for p in top:
        print(
            f" - {p.get('player_id')} ({p.get('name')}): net_energy={p.get('net_energy')}, bb_per_100={p.get('bb_per_100')}, win_rate={p.get('win_rate')}"
        )

    alg_counter, poker_by_alg = poker_clade_stats(lineage)
    print("\nMost common algorithms (top 10):")
    for alg, cnt in alg_counter.most_common(10):
        print(f" - {alg}: {cnt}")

    print("\nPoker-related clades found:")
    if not poker_by_alg:
        print(" - None detected")
    else:
        for alg, members in poker_by_alg.items():
            alive = sum(1 for m in members if m.get("is_alive"))
            print(f" - {alg}: members={len(members)}, alive={alive}")

    # Quick interesting-fact heuristics
    # 1) Check if any evolved agent overtook the 'standard' by net_energy
    last_snapshot = history[-1] if history else None
    if last_snapshot:
        std = None
        best = None
        for p in last_snapshot.get("players", []):
            if p.get("is_standard"):
                std = p
            if best is None or p.get("net_energy", 0) > best.get("net_energy", 0):
                best = p
        if std and best and best.get("player_id") != std.get("player_id"):
            print(
                f"\nInteresting: top net energy is {best.get('player_id')} ({best.get('name')}) vs standard {std.get('player_id')} ({std.get('name')})"
            )

    # Write poker-clade lifespan CSV for offline analysis and print path
    try:
        csv_path = poker_lifespan_csv(poker_by_alg)
        print(f"\nWrote poker clade lifespans to: {csv_path.resolve()}")
    except Exception as e:
        print("Could not write poker clade CSV:", e)


if __name__ == "__main__":
    main()
