"""Selection decisions use the registered contrast and practical threshold."""

import pytest

from tools.study_provenance import apply_selection_protocol, selection_decision, study_provenance


@pytest.mark.parametrize(
    "low,high,expected",
    [
        (0.02, 0.04, "positive"),
        (-0.04, -0.01, "negative"),
        (0.005, 0.02, "inconclusive"),
        (-0.01, 0.02, "inconclusive"),
    ],
)
def test_primary_selection_decision(low, high, expected):
    report = {
        "aggregate": {
            "effects": {
                "source_learning": {"ci95_low": 0.01},
                "transfer_vs_neutral": {"ci95_low": low, "ci95_high": high},
                "transfer_vs_founders": {"ci95_low": 0.3, "ci95_high": 0.5},
            }
        }
    }
    result = selection_decision(report)
    assert result["verdict"] == expected
    assert result["primary_effect"] == "transfer_vs_neutral"
    assert result["confirmation"] is False
    report["aggregate"]["effects"]["source_learning"]["ci95_low"] = -0.01
    assert selection_decision(report)["next_action"] == "stop_source_not_learnable"


def test_provenance_records_content_and_config_identity():
    first = study_provenance({"budget": 1})
    second = study_provenance({"budget": 2})
    assert first["source_identities"] == second["source_identities"]
    assert first["config_identity"] != second["config_identity"]
    assert first["code_revision"] != "unknown"
    assert first["preregistration_identity"]


def test_registered_primary_cannot_be_replaced_by_default_comparison():
    report = {
        "study": {},
        "aggregate": {
            "effects": {
                "source_learning": {"ci95_low": 0.02},
                "transfer_vs_neutral": {"ci95_low": 0.005, "ci95_high": 0.02},
                "transfer_vs_disjoint": {"verdict": "positive"},
            }
        },
    }
    apply_selection_protocol(report)
    assert report["study"]["primary_effect"] == "transfer_vs_neutral"
    assert report["aggregate"]["overall_verdict"] == "inconclusive"
