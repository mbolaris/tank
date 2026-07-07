#!/usr/bin/env python3
"""Patch classification tool for the Tank World ecosystem.

Given a git diff/commit range, this tool analyzes the changed files and the
diff hunks to classify the changes into one of the following categories:
- docs: only documentation files changed
- benchmark-or-meta: only benchmarks, CI/CD, tests, or scripts/tools changed
- new-algorithm: added a new algorithm to core/algorithms/
- parameter-tuning: only literal value/constant changes in config files or code
- refactor: only type hint annotations, imports, comments, docstrings, formatting, or renames
- logic-change: modification to control flow, equations, algorithms in core modules
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def classify_diff(diff_text: str, changed_files: list[str]) -> str:
    """Classify the patch based on the diff content and files changed.

    Args:
        diff_text: Full text of the git diff.
        changed_files: List of file paths modified/added/removed.

    Returns:
        One of: 'docs', 'benchmark-or-meta', 'new-algorithm', 'parameter-tuning',
                'refactor', 'logic-change'.
    """
    # 1. Clean changed files list
    changed_files = [f.strip().replace("\\", "/") for f in changed_files if f.strip()]
    if not changed_files:
        return "refactor"

    # 2. Check if all files are docs
    def is_doc(f: str) -> bool:
        return (
            f.startswith("docs/") or f.endswith(".md") or f.endswith(".txt") or f.endswith(".rst")
        )

    if all(is_doc(f) for f in changed_files):
        return "docs"

    # 3. Check if all files are meta/benchmark-or-meta
    meta_prefixes = [
        "tests/",
        "tools/",
        "benchmarks/",
        "backend/",
        "research/",
        "scripts/",
        ".github/",
    ]
    meta_files = [
        ".gitignore",
        "pyproject.toml",
        "uv.lock",
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "SETUP.md",
        "Dockerfile",
        "docker-compose.yml",
        "start.ps1",
        "start.py",
    ]

    def is_meta(f: str) -> bool:
        return (
            any(f.startswith(p) for p in meta_prefixes)
            or f in meta_files
            or os.path.basename(f) in meta_files
        )

    if all(is_meta(f) for f in changed_files):
        return "benchmark-or-meta"

    # 4. Check for new algorithm files
    new_algo = False
    for f in changed_files:
        if (
            f.startswith("core/algorithms/")
            and not f.endswith("registry.py")
            and not f.endswith("base.py")
        ):
            # Check if it's a new file.
            null_pattern = rf"--- /dev/null\n\+\+\+ b/{re.escape(f)}"
            if re.search(null_pattern, diff_text):
                new_algo = True
                break

    if new_algo:
        return "new-algorithm"

    # 5. Analyze python/code changes in core/
    core_files = [f for f in changed_files if f.startswith("core/") and not is_meta(f)]
    if not core_files:
        # Modified files are not strictly docs, not strictly meta, but nothing in core.
        return "benchmark-or-meta"

    # If only config/parameter files are changed in core/
    def is_config_file(f: str) -> bool:
        return (
            f.startswith("core/config/")
            or f.startswith("core/parameters/")
            or "config" in f
            or "parameter" in f
        )

    if all(is_config_file(f) for f in core_files):
        return "parameter-tuning"

    # Extract changed lines from the diff for core_files
    added_lines = []
    removed_lines = []

    # Split the diff_text into individual file diff sections
    file_diffs = re.split(r"^diff --git ", diff_text, flags=re.MULTILINE)

    for file_diff in file_diffs:
        # Find which file this diff is for
        # E.g. a/core/algorithms/composable/behavior.py b/core/algorithms/composable/behavior.py
        match = re.match(r"^a/(\S+) b/\S+", file_diff)
        if not match:
            # Try to match untracked / new files headers
            match = re.search(r"\+\+\+ b/(\S+)", file_diff)
            if not match:
                continue
        fname = match.group(1).replace("\\", "/")
        if fname not in core_files:
            continue

        # Extract the added and removed lines from the hunks of this file
        for line in file_diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                removed_lines.append(line[1:])

    # Clean code lines to filter out comments, docstrings, imports, formatting, and type annotations
    def clean_code_lines(lines: list[str]) -> list[str]:
        cleaned = []
        in_multiline_comment = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Handle triple-quote docstrings/comments
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if (stripped.endswith('"""') or stripped.endswith("'''")) and len(stripped) > 3:
                    continue  # Single line triple quote
                in_multiline_comment = not in_multiline_comment
                continue
            if in_multiline_comment:
                if stripped.endswith('"""') or stripped.endswith("'''"):
                    in_multiline_comment = False
                continue

            # Skip single-line comments and imports
            if stripped.startswith("#"):
                continue
            if stripped.startswith("import ") or (
                stripped.startswith("from ") and " import " in stripped
            ):
                continue

            if stripped == "pass":
                continue

            # Remove type annotations to inspect remaining code structure
            # Variable annotations: x: int = 5 -> x = 5
            # Function annotations: def foo(x: int) -> None -> def foo(x):
            # We match and remove annotations like : int, : List[str], -> None, etc.
            no_ann = re.sub(r":\s*[a-zA-Z0-9_|\[\], \'\"]+(?=\s*=|\s*\))", "", stripped)
            no_ann = re.sub(r"->\s*[a-zA-Z0-9_|\[\], \'\"]+:", ":", no_ann)

            # If it's a variable declaration with only type hint and no assignment, e.g. "x: int"
            if re.match(r"^[a-zA-Z0-9_]+\s*:\s*[a-zA-Z0-9_|\[\], \'\"]+$", stripped):
                continue

            # Normalize whitespace: replace multiple spaces with single space
            no_ann = re.sub(r"\s+", " ", no_ann).strip()
            # Remove spaces around punctuation to normalize formatting
            no_ann = re.sub(r"\s*([:=,\(\)])\s*", r"\1", no_ann)

            cleaned.append(no_ann)
        return cleaned

    cleaned_added = clean_code_lines(added_lines)
    cleaned_removed = clean_code_lines(removed_lines)

    # Filter out identical logic lines that only differed in annotations or formatting
    added_unique = []
    removed_unique = list(cleaned_removed)
    for item in cleaned_added:
        if item in removed_unique:
            removed_unique.remove(item)
        else:
            added_unique.append(item)

    cleaned_added = added_unique
    cleaned_removed = removed_unique

    # If there are no active code line changes, it's a refactor
    if not cleaned_added and not cleaned_removed:
        return "refactor"

    # using ast.literal_eval for robust detection.
    def is_param_line(line_str: str) -> bool:
        import ast

        # 1. Match var=value
        match = re.match(r"^([a-zA-Z0-9_]+)=(.*)$", line_str)
        if match:
            val = match.group(2)
            try:
                ast.literal_eval(val)
                return True
            except Exception:
                pass
        # 2. Match "key":value or 'key':value
        match = re.match(r"^['\"][a-zA-Z0-9_-]+['\"]:(.*)$", line_str)
        if match:
            val = match.group(1).rstrip(",")
            try:
                ast.literal_eval(val)
                return True
            except Exception:
                pass
        return False

    all_added_are_params = all(is_param_line(line_val) for line_val in cleaned_added)
    all_removed_are_params = all(is_param_line(line_val) for line_val in cleaned_removed)

    if all_added_are_params and all_removed_are_params:
        return "parameter-tuning"

    return "logic-change"


def get_current_workspace_changes() -> tuple[str, list[str]]:
    """Get the current unstaged/staged changes and untracked files."""
    changed_files = []
    diff_text = ""

    # Modified and staged changes
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            diff_text = res.stdout
    except Exception:
        pass

    # Find modified, staged and untracked files
    try:
        res_diff = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res_diff.returncode == 0 and res_diff.stdout.strip():
            changed_files.extend(res_diff.stdout.strip().splitlines())

        res_cached = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res_cached.returncode == 0 and res_cached.stdout.strip():
            changed_files.extend(res_cached.stdout.strip().splitlines())

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
                    filepath = line[3:]
                    changed_files.append(filepath)
                    # For untracked files, we read their content and simulate addition diff
                    try:
                        fpath = Path(filepath)
                        if fpath.is_file():
                            content = fpath.read_text(encoding="utf-8", errors="ignore")
                            fake_diff = f"diff --git a/{filepath} b/{filepath}\nnew file mode 100644\n--- /dev/null\n+++ b/{filepath}\n"
                            for cline in content.splitlines():
                                fake_diff += f"+{cline}\n"
                            diff_text += "\n" + fake_diff
                    except Exception:
                        pass
    except Exception:
        pass

    return diff_text, sorted(set(changed_files))


def get_commit_changes(commit_range: str) -> tuple[str, list[str]]:
    """Get diff and changed files for a commit range/hash."""
    changed_files = []
    diff_text = ""

    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", commit_range],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            changed_files = res.stdout.strip().splitlines()

        res_diff = subprocess.run(
            ["git", "diff", commit_range],
            capture_output=True,
            text=True,
            check=False,
        )
        if res_diff.returncode == 0:
            diff_text = res.stdout
    except Exception as e:
        print(f"Error executing git command: {e}", file=sys.stderr)

    return diff_text, changed_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify code change patch.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--commit-range", help="Git commit range or hash (e.g. HEAD~1..HEAD or commit_hash)"
    )
    group.add_argument("--diff-file", help="Path to a file containing raw diff text")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")

    args = parser.parse_args()

    if args.diff_file:
        try:
            diff_text = Path(args.diff_file).read_text(encoding="utf-8")
            # Parse filenames from diff text
            changed_files = []
            for line in diff_text.splitlines():
                if line.startswith("+++ b/"):
                    changed_files.append(line[6:])
        except Exception as e:
            print(f"Error reading diff file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.commit_range:
        diff_text, changed_files = get_commit_changes(args.commit_range)
    else:
        diff_text, changed_files = get_current_workspace_changes()

    category = classify_diff(diff_text, changed_files)

    if args.json:
        result = {
            "patch_type": category,
            "changed_files_count": len(changed_files),
            "files": changed_files,
        }
        print(json.dumps(result, indent=2))
    else:
        print(category)


if __name__ == "__main__":
    main()
