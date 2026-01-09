"""Architecture guard: legacy soccer world imports are forbidden."""

from __future__ import annotations

import ast
from pathlib import Path


def test_no_core_worlds_soccer_imports() -> None:
    """Ensure nothing imports core.worlds.soccer.* anymore."""
    repo_root = Path(__file__).resolve().parents[1]
    excluded = {
        ".git",
        ".venv",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        "node_modules",
        "frontend",
        "dist",
        "build",
    }

    offenders: list[str] = []

    for path in repo_root.rglob("*.py"):
        if any(part in excluded for part in path.parts):
            continue

        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise AssertionError(f"Failed to parse {path}") from exc

        bad_imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "core.worlds.soccer" or name.startswith("core.worlds.soccer."):
                        bad_imports.append(name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "core.worlds.soccer" or module.startswith("core.worlds.soccer."):
                    bad_imports.append(module)
                elif module == "core.worlds":
                    for alias in node.names:
                        if alias.name == "soccer":
                            bad_imports.append(f"{module}.{alias.name}")

        if bad_imports:
            rel = path.relative_to(repo_root)
            offenders.append(f"{rel}: {sorted(set(bad_imports))}")

    assert not offenders, "Legacy soccer world imports found:\n" + "\n".join(offenders)
