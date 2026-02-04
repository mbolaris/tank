from pathlib import Path
from typing import List

import pytest


def test_no_external_lifecycle_component_usage():
    """Ensure only Fish and its mixins touch the lifecycle component directly."""
    repo_root = Path(__file__).resolve().parents[1]
    core_dir = repo_root / "core"

    # fish.py and its mixins are part of the Fish class hierarchy
    allowed_paths = {
        (core_dir / "entities" / "fish.py").resolve(),
        (core_dir / "entities" / "mixins" / "energy_mixin.py").resolve(),
        (core_dir / "entities" / "mixins" / "mortality_mixin.py").resolve(),
        (core_dir / "entities" / "mixins" / "reproduction_mixin.py").resolve(),
    }

    offenders: List[Path] = []
    for path in core_dir.rglob("*.py"):
        if path.resolve() in allowed_paths:
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
