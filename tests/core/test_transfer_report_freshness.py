"""Maintained evidence must agree with its retained data and presentation."""

import copy
import json
from pathlib import Path

import pytest

from core.behavior.target_memory_transfer_study import render_markdown
from tools.check_transfer_report import check_report

REPORT = Path(__file__).resolve().parents[2] / "research/target_memory_transfer/study_v4.json"


def test_maintained_transfer_report_is_fresh():
    check_report(
        json.loads(REPORT.read_text()), REPORT.with_suffix(".md").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("fault", ["headline", "secondary", "interval", "rule"])
def test_check_rejects_drift(fault):
    report = copy.deepcopy(json.loads(REPORT.read_text()))
    markdown = render_markdown(report)
    if fault == "headline":
        markdown = markdown.replace("NEGATIVE", "POSITIVE")
    elif fault == "secondary":
        report["aggregate"]["overall_verdict"] = report["aggregate"]["effects"][
            "transfer_vs_founders"
        ]["verdict"]
    elif fault == "interval":
        report["aggregate"]["effects"]["transfer_vs_disjoint"]["ci95_low"] = 0.1
    else:
        report["study"]["decision_rule"] = "Use founders instead"
    with pytest.raises(ValueError):
        check_report(report, markdown)


def test_old_provenance_is_unknown():
    assert "Code provenance: `unknown`" in render_markdown(json.loads(REPORT.read_text()))


def test_selection_replication_is_fresh_and_uses_registered_primary():
    path = REPORT.with_name("selection_replication.json")
    report = json.loads(path.read_text(encoding="utf-8"))
    check_report(report, path.with_suffix(".md").read_text(encoding="utf-8"))
    assert report["study"]["primary_effect"] == "transfer_vs_neutral"
    assert report["aggregate"]["overall_verdict"] == "inconclusive"
    report["aggregate"]["overall_verdict"] = "positive"
    with pytest.raises(ValueError):
        check_report(report, render_markdown(report))
