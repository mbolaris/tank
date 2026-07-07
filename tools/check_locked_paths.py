#!/usr/bin/env python3
"""Check if any changed files are under locked paths.

Usage:
    python tools/check_locked_paths.py --locked benchmarks/heldout tools/paper_eval.py
"""

import argparse
import subprocess
import sys


def get_changed_files(base: str | None = None) -> list[str]:
    """Retrieve changed files from git.

    If base is provided, runs: git diff --name-only base
    Otherwise, aggregates local changes (unstaged, staged, untracked).
    """
    changed = set()
    try:
        if base:
            # Diff against base revision
            res = subprocess.run(
                ["git", "diff", "--name-only", base],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in res.stdout.strip().splitlines():
                if line.strip():
                    changed.add(line.strip())
        else:
            # Unstaged changes
            res = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in res.stdout.strip().splitlines():
                if line.strip():
                    changed.add(line.strip())

            # Staged changes
            res = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in res.stdout.strip().splitlines():
                if line.strip():
                    changed.add(line.strip())

            # Untracked files
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in res.stdout.strip().splitlines():
                if line.startswith("?? "):
                    filepath = line[3:].strip()
                    if filepath:
                        changed.add(filepath)
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e}", file=sys.stderr)
        sys.exit(1)

    return sorted(changed)


def is_path_locked(file_path: str, locked_paths: list[str]) -> bool:
    """Check if the given file_path is matched by any path in locked_paths."""
    norm_file = file_path.replace("\\", "/").strip().lstrip("/")
    for locked in locked_paths:
        norm_locked = locked.replace("\\", "/").strip().lstrip("/")
        if not norm_locked:
            continue
        # Exact match or directory prefix match
        if norm_file == norm_locked:
            return True
        if norm_file.startswith(norm_locked.rstrip("/") + "/"):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Check for changes to locked paths.")
    parser.add_argument(
        "--locked",
        nargs="+",
        required=True,
        help="List of locked paths (directories or files) to protect.",
    )
    parser.add_argument(
        "--base",
        type=str,
        help="Git revision to compare against (e.g. origin/master). If omitted, checks local changes.",
    )

    args = parser.parse_args()

    changed_files = get_changed_files(base=args.base)
    violations = []

    for filepath in changed_files:
        if is_path_locked(filepath, args.locked):
            violations.append(filepath)

    if violations:
        print("[FAIL] Found changes to locked paths!", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)

    print("[PASS] No changes to locked paths found.")
    sys.exit(0)


if __name__ == "__main__":
    main()
