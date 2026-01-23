from pathlib import Path

import pytest


def test_no_fish_aliases_in_codebase():
    """Ensure no FishMemorySystem our FishCommunicationSystem aliases remain."""

    # Root directory for checks
    root_dir = Path("c:/shared/bolaris/tank")

    # Files to check (or patterns)
    # We scan recursively but exclude hidden folders and pycache

    forbidden_terms = ["as FishMemorySystem", "as FishCommunicationSystem"]

    found_violations = []

    for path in root_dir.rglob("*.py"):
        if ".pytest_cache" in str(path) or "__pycache__" in str(path) or ".venv" in str(path):
            continue

        # Skip this test file itself to avoid self-flagging
        if path.name == "test_no_fish_aliases.py":
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for term in forbidden_terms:
                if term in content:
                    found_violations.append(f"{path}: Found '{term}'")
        except Exception as e:
            # Just skip files we can't read
            print(f"Skipping {path}: {e}")

    if found_violations:
        pytest.fail("Found forbidden aliases:\n" + "\n".join(found_violations))
