"""Guardrail test: Ensure no direct imports of core.tank_world outside legacy.

This test enforces that new code uses the canonical WorldRegistry path
instead of directly importing from core.tank_world.
"""

from __future__ import annotations

from pathlib import Path


def test_no_direct_tank_world_imports():
    """Ensure production code doesn't import core.tank_world directly."""
    project_root = Path(__file__).resolve().parents[1]

    # Find all .py files that import from core.tank_world using Python (cross-platform)
    pattern = "from core.tank_world import"
    lines = []

    for py_file in project_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
            if pattern in content:
                rel_path = py_file.relative_to(project_root)
                for i, line in enumerate(content.splitlines(), 1):
                    if pattern in line:
                        lines.append(f"./{rel_path}:{i}: {line.strip()}")
        except Exception:
            pass

    # Filter out acceptable usages
    violations = []
    for line in lines:
        if not line:
            continue
        # Acceptable: core/legacy/ (backward compat)
        if "core/legacy/" in line or "core\\legacy\\" in line:
            continue
        # Acceptable: this test file
        if "test_no_tank_world_imports" in line:
            continue
        # Acceptable: __pycache__
        if "__pycache__" in line:
            continue
        # Acceptable: archive directories (legacy scripts)
        if "/archive/" in line or "\\archive\\" in line:
            continue
        # Acceptable: scripts directory (can use deprecated API for now)
        if "scripts/" in line or "scripts\\" in line:
            continue
        # Acceptable: tools directory (can use deprecated API for now)
        if "tools/" in line or "tools\\" in line:
            continue

        violations.append(line)

    assert not violations, (
        f"Found {len(violations)} direct imports of core.tank_world. "
        f"Use core.worlds.WorldRegistry instead:\n" + "\n".join(violations)
    )


def test_legacy_module_emits_deprecation_warning():
    """Verify that importing from core.legacy emits DeprecationWarning."""
    import subprocess
    import sys

    # Use subprocess to get a fresh Python interpreter that hasn't cached the import
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "always::DeprecationWarning",
            "-c",
            "import warnings; warnings.filterwarnings('error', category=DeprecationWarning); "
            "from core.legacy import tank_world",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    # We expect the import to fail due to DeprecationWarning being raised as error
    # OR to emit the warning to stderr
    assert result.returncode != 0 or "DeprecationWarning" in result.stderr, (
        f"Expected DeprecationWarning when importing core.legacy.tank_world. "
        f"stderr: {result.stderr}, stdout: {result.stdout}"
    )
