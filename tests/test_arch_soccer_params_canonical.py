"""Guardrail to keep soccer code on canonical RCSS params."""

from pathlib import Path
from typing import List

ALLOWED_PATHS = {
    "core/minigames/soccer/params.py",
    "core/minigames/soccer/__init__.py",
}
ALLOWED_PREFIXES = ("tests/",)


def _is_allowed_path(rel_path: str) -> bool:
    """Return True if DEFAULT_RCSS_PARAMS is permitted in this path."""
    if rel_path in ALLOWED_PATHS:
        return True
    return rel_path.startswith(ALLOWED_PREFIXES)


def test_soccer_only_uses_canonical_params():
    """Ensure only params.py/tests mention DEFAULT_RCSS_PARAMS."""
    violations: List[str] = []

    for path in sorted(Path(".").rglob("*.py")):
        if any(part.startswith(".") for part in path.parts):
            continue

        rel_path = path.as_posix()
        if _is_allowed_path(rel_path):
            continue

        content = path.read_text(encoding="utf-8")
        if "DEFAULT_RCSS_PARAMS" in content:
            violations.append(rel_path)

    assert not violations, (
        "DEFAULT_RCSS_PARAMS is now restricted to core/minigames/soccer/params.py and tests.\n"
        "Use SOCCER_CANONICAL_PARAMS when you need the canonical RCSS parameters.\n"
        + "\n".join(violations)
    )
