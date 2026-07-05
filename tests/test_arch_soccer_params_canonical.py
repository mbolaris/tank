"""Guardrail to keep soccer code on canonical RCSS params."""

from pathlib import Path

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
    from tests.ast_utils import get_file_content, walk_python_files

    repo_root = Path(__file__).resolve().parents[1]
    violations: list[str] = []

    for path in sorted(walk_python_files(repo_root)):
        rel_path = path.relative_to(repo_root).as_posix()
        if _is_allowed_path(rel_path):
            continue

        content = get_file_content(path)
        if "DEFAULT_RCSS_PARAMS" in content:
            violations.append(rel_path)

    assert not violations, (
        "DEFAULT_RCSS_PARAMS is now restricted to core/minigames/soccer/params.py and tests.\n"
        "Use SOCCER_CANONICAL_PARAMS when you need the canonical RCSS parameters.\n"
        + "\n".join(violations)
    )
