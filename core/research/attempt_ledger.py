"""Attempt ledger module for tracking research experiments and runs.

Logs every evaluation attempt to research/attempts.jsonl.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


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
        logger.debug("git context collection failed; recording partial context", exc_info=True)

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
    attempt_id: str | None = None,
    parent_attempt_id: str | None = None,
    base_commit: str | None = None,
    agent_model: str | None = None,
    prompt_template_id: str | None = None,
    files_changed: list[str] | None = None,
    patch_type: str | None = None,
    tests_run: list[str] | str | None = None,
    benchmark_command: str | None = None,
    duration: float | None = None,
    exit_code: int | None = None,
    failure_reason: str | None = None,
    accepted_by_gate: bool | None = None,
    champion_updated: bool | None = None,
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
        attempt_id: A generated UUID string or similar unique identifier.
        parent_attempt_id: UUID of the parent attempt this build inherits from.
        base_commit: Git commit hash of base commit before modification.
        patch_type: The taxonomy category of the change (e.g., 'parameter-tuning', 'logic-change').
        agent_model: Specific LLM/model descriptor used.
        prompt_template_id: Specific template or version of the prompt/system message.
        files_changed: List of files modified in this attempt.
        tests_run: List/string of tests executed.
        benchmark_command: Exact CLI command run for benchmark.
        duration: Elapsed wall-clock execution time for this attempt.
        exit_code: Final return code of run.
        failure_reason: Error/failure description if candidate errored.
        accepted_by_gate: Whether local/CI gates passed.
        champion_updated: Whether this attempt successfully became the new champion.
    """
    if timestamp is None:
        timestamp = time.time()

    # Generate attempt ID if not provided
    if attempt_id is None:
        attempt_id = str(uuid.uuid4())

    # Detect base commit
    if base_commit is None:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD~1"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                base_commit = res.stdout.strip()
        except Exception:
            logger.debug("base commit detection failed; leaving unset", exc_info=True)

    # Detect files changed
    if files_changed is None:
        try:
            files = []
            # Modified and staged changes
            res_diff = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res_diff.returncode == 0 and res_diff.stdout.strip():
                files.extend(res_diff.stdout.strip().splitlines())

            res_cached = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res_cached.returncode == 0 and res_cached.stdout.strip():
                files.extend(res_cached.stdout.strip().splitlines())

            # Untracked files
            res_status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res_status.returncode == 0 and res_status.stdout.strip():
                for line in res_status.stdout.strip().splitlines():
                    if line.startswith("?? "):
                        files.append(line[3:])
            files_changed = sorted(set(files))
        except Exception:
            logger.debug("changed-files detection failed; leaving unset", exc_info=True)

    # Detect patch_type
    if patch_type is None:
        try:
            project_root_str = str(Path(__file__).resolve().parents[2])
            if project_root_str not in sys.path:
                sys.path.insert(0, project_root_str)
            from tools.classify_patch import classify_diff, get_current_workspace_changes

            diff_text, detected_files = get_current_workspace_changes()
            if not files_changed:
                files_changed = detected_files
            patch_type = classify_diff(diff_text, files_changed or [])
        except Exception:
            patch_type = "logic-change"

    # Detect model
    if not agent_model:
        agent_model = os.environ.get("AGENT_MODEL") or os.environ.get("MODEL_NAME")

    # Detect prompt template ID
    if not prompt_template_id:
        prompt_template_id = os.environ.get("PROMPT_TEMPLATE_ID") or os.environ.get(
            "SYSTEM_PROMPT_VERSION"
        )

    # Detect benchmark command
    if not benchmark_command:
        benchmark_command = " ".join(sys.argv)

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
            logger.debug("description detection from git log failed", exc_info=True)
        if not description:
            description = "No description provided"

    record = {
        "timestamp": timestamp,
        "timestamp_iso": datetime.datetime.fromtimestamp(
            timestamp, tz=datetime.timezone.utc
        ).isoformat(),
        "attempt_id": attempt_id,
        "parent_attempt_id": parent_attempt_id,
        "base_commit": base_commit,
        "agent_id": agent_id,
        "agent_model": agent_model,
        "prompt_template_id": prompt_template_id,
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
        "files_changed": files_changed,
        "patch_type": patch_type,
        "tests_run": tests_run,
        "benchmark_command": benchmark_command,
        "duration": duration,
        "exit_code": exit_code,
        "failure_reason": failure_reason,
        "accepted_by_gate": accepted_by_gate,
        "champion_updated": champion_updated,
    }

    if ledger_path is None:
        env_path = os.environ.get("ATTEMPT_LEDGER_PATH")
        if env_path:
            final_ledger_path = Path(env_path)
            if final_ledger_path.parent:
                final_ledger_path.parent.mkdir(exist_ok=True, parents=True)
        else:
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
