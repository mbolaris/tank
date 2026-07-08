#!/usr/bin/env python3
"""Summarize skill-ladder standings across all domains.

Reads the champion registry (``champions/**/*.json``) and prints, for every
benchmark that emits a skill-ladder summary (see ``core/skill/ladder.py``), the
normalized skill index, how many frozen rungs the substrate beats, and the
per-rung margins. This is the "how good are the agents, absolutely and vs the
ceiling" view in one place.

Usage:
    python tools/skill_status.py                # human-readable table
    python tools/skill_status.py --json         # machine-readable
    python tools/skill_status.py --domain poker # filter to one domain
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.skill import SkillLadderSummary, load_ladder_summaries


def _format_rung(rung: Any) -> str:
    mark = "beat" if rung.beaten else "----"
    ci = ""
    if rung.ci_95 is not None:
        ci = f"  [{rung.ci_95[0]:.1f}, {rung.ci_95[1]:.1f}]"
    return f"    {rung.rung} {rung.rung_id:<20} {rung.metric:+10.2f}  {mark}{ci}"


def render_text(summaries: list[SkillLadderSummary]) -> str:
    if not summaries:
        return "No skill-ladder summaries found in the champion registry."

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("SKILL LADDER STATUS (frozen-ruler standings)")
    lines.append("=" * 70)
    for summary in sorted(summaries, key=lambda s: s.domain):
        lines.append("")
        lines.append(
            f"{summary.domain.upper()}  ({summary.benchmark_id})  "
            f"skill_index={summary.skill_index:.1f}  "
            f"rungs_beaten={summary.rungs_beaten}/{summary.total_rungs}"
        )
        lines.append(f"  metric: {summary.metric_name}")
        for rung in summary.rungs:
            lines.append(_format_rung(rung))
        if summary.notes:
            lines.append(f"  note: {summary.notes}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize skill-ladder standings")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    parser.add_argument("--domain", help="Filter to a single domain (e.g. poker)")
    parser.add_argument(
        "--champions-dir",
        default=str(ROOT / "champions"),
        help="Champion registry directory (default: ./champions)",
    )
    args = parser.parse_args()

    summaries = load_ladder_summaries(args.champions_dir)
    if args.domain:
        summaries = [s for s in summaries if s.domain == args.domain]

    if args.json:
        print(json.dumps([s.to_dict() for s in summaries], indent=2))
    else:
        print(render_text(summaries))


if __name__ == "__main__":
    main()
