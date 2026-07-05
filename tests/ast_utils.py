"""Shared utilities for walking Python files and caching AST parses in tests."""

from __future__ import annotations

import ast
import os
from pathlib import Path

# Thread-safe/global caches for ASTs and file content
_AST_CACHE: dict[Path, ast.AST] = {}
_CONTENT_CACHE: dict[Path, str] = {}
_FILES_CACHE: dict[Path, list[Path]] = {}

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "frontend",
    "dist",
    "build",
}


def walk_python_files(dir_path: Path) -> list[Path]:
    """Find all Python files under dir_path recursively, pruning excluded directories.

    This is extremely fast compared to rglob because it uses os.walk and prunes
    directories like .venv and .git in-place.
    """
    # Resolve to absolute path to ensure caching works correctly
    dir_path = dir_path.resolve()
    if dir_path in _FILES_CACHE:
        return _FILES_CACHE[dir_path]

    python_files: list[Path] = []
    for root, dirs, files in os.walk(dir_path):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    _FILES_CACHE[dir_path] = python_files
    return python_files


def get_file_content(path: Path) -> str:
    """Get the cached content of a Python file."""
    path = path.resolve()
    if path in _CONTENT_CACHE:
        return _CONTENT_CACHE[path]
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Fall back for binary or unreadable files in some test contexts
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = ""
    _CONTENT_CACHE[path] = content
    return content


def get_ast(path: Path) -> ast.AST | None:
    """Get the cached AST for a Python file."""
    path = path.resolve()
    if path in _AST_CACHE:
        return _AST_CACHE[path]

    content = get_file_content(path)
    if not content:
        return None

    try:
        tree = ast.parse(content, filename=str(path))
        _AST_CACHE[path] = tree
        return tree
    except SyntaxError:
        return None
