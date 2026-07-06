"""Attempt ledger module for tracking research experiments and runs.

Logs every evaluation attempt to research/attempts.jsonl.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import time
from pathlib import Path


def _get_git_info() -> dict[str, str | None]:
    """Retrieve current Git branch, commit, and diff stat if available."""
    branch = None
    commit = None
    diff_stat = None

    try:
        # Get branch
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            branch = res.stdout.strip()

        # Get commit
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            commit = res.stdout.strip()

        # Get diff stat
        res = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            diff_stat = res.stdout.strip()
    except Exception:
        pass

    return {"branch": branch, "commit": commit, "diff_stat": diff_stat}


def log_attempt(
    benchmark_id: str,
    verdict: str,
    candidate_score: float | None,
    champion_score: float | None,
    seed: int | list[int] | None = None,
    config_hash: str | None = None,
    agent_id: str | None = None,
    description: str | None = None,
    timestamp: float | None = None,
    ledger_path: str | Path | None = None,
) -> None:
    """Log an evaluation attempt to the append-only ledger research/attempts.jsonl.

    Args:
        benchmark_id: The ID of the benchmark being run.
        verdict: 'accepted', 'rejected', or 'error'.
        candidate_score: Score of the candidate.
        champion_score: Score of the champion at the time of comparison.
        seed: Seed or list of seeds used.
        config_hash: Hash of the simulation configuration.
        agent_id: Identifier of the agent/model making the change (e.g. 'anthropic', 'openai', 'manual').
        description: Description of the change/attempt.
        timestamp: Unix timestamp for the log.
        ledger_path: Custom path to write the ledger. Defaults to research/attempts.jsonl under project root.
    """
    if timestamp is None:
        timestamp = time.time()

    # Attempt to auto-detect agent_id if not provided
    if not agent_id:
        agent_id = os.environ.get("AGENT_ID") or os.environ.get("MODEL_NAME")
        if not agent_id:
            # Fall back to "ci" or "manual"
            if os.environ.get("CI"):
                agent_id = "ci"
            else:
                # Can we find git author?
                try:
                    res = subprocess.run(
                        ["git", "config", "user.name"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if res.returncode == 0 and res.stdout.strip():
                        agent_id = f"manual-{res.stdout.strip()}"
                    else:
                        agent_id = "manual"
                except Exception:
                    agent_id = "manual"

    git_info = _get_git_info()

    # Get one-line description from recent git commit if not provided
    if not description:
        try:
            res = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%s"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and res.stdout.strip():
                description = res.stdout.strip()
        except Exception:
            pass
        if not description:
            description = "No description provided"

    record = {
        "timestamp": timestamp,
        "timestamp_iso": datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.timezone.utc
        ).isoformat(),
        "agent_id": agent_id,
        "benchmark_id": benchmark_id,
        "seed": seed,
        "candidate_score": candidate_score,
        "champion_score": champion_score,
        "config_hash": config_hash,
        "verdict": verdict,
        "description": description,
        "branch": git_info["branch"],
        "commit": git_info["commit"],
        "diff_stat": git_info["diff_stat"],
    }

    if ledger_path is None:
        project_root = Path(__file__).resolve().parents[2]
        research_dir = project_root / "research"
        research_dir.mkdir(exist_ok=True)
        final_ledger_path = research_dir / "attempts.jsonl"
    else:
        final_ledger_path = Path(ledger_path)
        if final_ledger_path.parent:
            final_ledger_path.parent.mkdir(exist_ok=True, parents=True)

    # Append to JSONL ledger
    with open(final_ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
