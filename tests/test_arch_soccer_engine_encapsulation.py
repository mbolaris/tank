"""Architecture guardrail for soccer engine encapsulation."""

from __future__ import annotations

import re
from pathlib import Path
from re import Pattern

PRIVATE_FIELD_PATTERNS: list[tuple[str, Pattern[str]]] = [
    (
        "_players",
        re.compile(r"(?P<object>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\._players\b"),
    ),
    (
        "_last_touch",
        re.compile(
            r"(?P<object>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\._last_touch_[A-Za-z0-9_]*"
        ),
    ),
    (
        "_prev_touch",
        re.compile(
            r"(?P<object>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\._prev_touch_[A-Za-z0-9_]*"
        ),
    ),
    (
        "_cycle",
        re.compile(r"(?P<object>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\._cycle\b"),
    ),
]


def _looks_like_soccer_engine_accessor(obj_path: str) -> bool:
    """Only enforce accesses through engine-like attributes."""
    return "engine" in obj_path.lower()


def test_soccer_engine_private_state_remains_encapsulated():
    """Surface any soccer module accessing RCSSLiteEngine private fields."""
    root = Path("core/minigames/soccer")
    violations: list[str] = []

    for path in sorted(root.rglob("*.py")):
        if path.name == "engine.py":
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(lines, start=1):
            for field_name, pattern in PRIVATE_FIELD_PATTERNS:
                for match in pattern.finditer(line):
                    obj_path = match.group("object")
                    if not _looks_like_soccer_engine_accessor(obj_path):
                        continue

                    violations.append(
                        f"{path.as_posix()}:{line_no}: {obj_path}.{field_name} -> {line.strip()}"
                    )

    assert not violations, (
        "Found soccer code reaching into RCSSLiteEngine private state.\n"
        "Use the public players()/iter_players()/last_touch_info()/cycle properties instead.\n"
        + "\n".join(violations)
    )
