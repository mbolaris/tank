from pathlib import Path

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

    from tests.ast_utils import get_file_content, walk_python_files

    offenders: list[Path] = []
    for path in walk_python_files(core_dir):
        if path.resolve() in allowed_paths:
            continue
        text = get_file_content(path)
        if "_lifecycle_component" in text:
            offenders.append(path.relative_to(repo_root))

    if offenders:
        pytest.fail(
            "Found direct lifecycle component access outside Fish:\n"
            + "\n".join(str(p) for p in sorted(offenders))
        )
