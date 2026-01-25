from pathlib import Path
from typing import List

import pytest


def test_no_external_lifecycle_component_usage():
    """Ensure only the Fish entity touches its lifecycle component directly."""
    repo_root = Path(__file__).resolve().parents[1]
    core_dir = repo_root / "core"
    fish_file = (core_dir / "entities" / "fish.py").resolve()

    offenders: List[Path] = []
    for path in core_dir.rglob("*.py"):
        if path.resolve() == fish_file:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "_lifecycle_component" in text:
            offenders.append(path.relative_to(repo_root))

    if offenders:
        pytest.fail(
            "Found direct lifecycle component access outside Fish:\n"
            + "\n".join(str(p) for p in sorted(offenders))
        )
