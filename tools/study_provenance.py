"""Record reproducible study identities without inventing historical provenance."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

SELECTION_RULE = (
    "positive only when the 95% bootstrap CI lower bound exceeds 0.01; "
    "negative when the upper bound is below zero; otherwise inconclusive"
)


def study_provenance(config: dict) -> dict:
    root = Path(__file__).resolve().parents[1]
    sources = [
        *root.joinpath("core/behavior").glob("target_memory*.py"),
        root / "core/math_utils.py",
    ]
    identities = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(sources)
    }
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    diff = subprocess.check_output(
        ["git", "diff", "HEAD", "--", "core/behavior", "core/math_utils.py"], cwd=root
    )
    return {
        "code_revision": revision,
        "working_diff_identity": hashlib.sha256(diff).hexdigest(),
        "source_identities": identities,
        "config_identity": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "preregistration_identity": hashlib.sha256(
            (
                root / "research/target_memory_transfer/selection_transfer_preregistration.md"
            ).read_bytes()
        ).hexdigest(),
    }


def selection_decision(report: dict) -> dict:
    effects = report["aggregate"]["effects"]
    source = effects["source_learning"]["ci95_low"] > 0
    primary = effects["transfer_vs_neutral"]
    verdict = (
        "positive"
        if primary["ci95_low"] > 0.01
        else "negative" if primary["ci95_high"] < 0 else "inconclusive"
    )
    return {
        "primary_effect": "transfer_vs_neutral",
        "practical_threshold": 0.01,
        "verdict": verdict,
        "source_learning_established": source,
        "next_action": (
            "stop_source_not_learnable"
            if not source
            else (
                "test_bounded_mechanism"
                if verdict != "positive"
                else "preregister_independent_confirmation"
            )
        ),
        "confirmation": False,
    }


def apply_selection_protocol(report: dict) -> None:
    """Publish the preregistered contrast as the new replication's headline."""
    decision = selection_decision(report)
    report["selection_decision"] = decision
    report["study"]["primary_effect"] = decision["primary_effect"]
    report["study"]["decision_rule"] = SELECTION_RULE
    report["study"]["preregistration_applied"] = True
    report["aggregate"]["overall_verdict"] = decision["verdict"]
