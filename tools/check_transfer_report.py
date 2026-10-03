"""Offline freshness and decision-rule check for a maintained transfer report."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.behavior.target_memory_transfer_study import aggregate_rows, render_markdown


def _same_aggregate(saved: object, recomputed: object) -> bool:
    """Compare JSON-derived summaries across Python versions without float noise."""
    if isinstance(saved, bool) or isinstance(recomputed, bool):
        return type(saved) is type(recomputed) and saved == recomputed
    if isinstance(saved, (float, int)) and isinstance(recomputed, (float, int)):
        if isinstance(saved, float) or isinstance(recomputed, float):
            return math.isclose(float(saved), float(recomputed), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(saved, dict) and isinstance(recomputed, dict):
        return saved.keys() == recomputed.keys() and all(
            _same_aggregate(saved[key], recomputed[key]) for key in saved
        )
    if isinstance(saved, list) and isinstance(recomputed, list):
        return len(saved) == len(recomputed) and all(
            _same_aggregate(left, right) for left, right in zip(saved, recomputed, strict=True)
        )
    return saved == recomputed


def check_report(report: dict, markdown: str) -> None:
    """Reject inconsistent evidence before accepting its rendered presentation."""
    study = report["study"]
    primary = study["primary_effect"]
    seeds = [row["seed"] for row in report["per_seed"]]
    if study["seeds"] != sorted(seeds) or len(seeds) != len(set(seeds)):
        raise ValueError("Declared seeds disagree with retained independent rows")
    expected_rule = (
        "verdict is positive/negative only when the 95% bootstrap CI "
        "of the mean effect excludes zero; otherwise inconclusive"
    )
    if primary == "transfer_vs_neutral":
        from tools.study_provenance import SELECTION_RULE

        expected_rule = SELECTION_RULE
    elif primary != "transfer_vs_disjoint":
        raise ValueError("Unknown primary effect")
    if study["decision_rule"] != expected_rule:
        raise ValueError("Unknown primary effect or decision rule")
    effects = aggregate_rows(report["per_seed"])["effects"]
    if not _same_aggregate(report["aggregate"]["effects"], effects):
        raise ValueError("Saved effects disagree with retained rows; review correction separately")
    expected_verdict = effects[primary]["verdict"]
    if primary == "transfer_vs_neutral":
        from tools.study_provenance import selection_decision

        expected_verdict = selection_decision(report)["verdict"]
    if report["aggregate"]["overall_verdict"] != expected_verdict:
        raise ValueError("Overall verdict disagrees with primary effect")
    if "selection_decision" in report:
        from tools.study_provenance import selection_decision

        if report["selection_decision"] != selection_decision(report):
            raise ValueError("Selection-specific decision disagrees with its registered rule")
    if markdown != render_markdown(report):
        raise ValueError("Markdown is stale; regenerate with the existing renderer")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=Path("research/target_memory_transfer/study_v4.json"),
    )
    args = parser.parse_args()
    check_report(
        json.loads(args.report.read_text(encoding="utf-8")),
        args.report.with_suffix(".md").read_text(encoding="utf-8"),
    )
    print("Transfer report is fresh and agrees with its primary decision rule")


if __name__ == "__main__":
    main()
