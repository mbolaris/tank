"""Architecture test: Enforce protocol-based design over isinstance(Fish) checks.

This test scans the codebase to ensure we use capability protocols (EnergyHolder,
Reproducible, LifecycleAware, etc.) instead of isinstance checks for concrete types.

The goal is to maintain loose coupling between systems and entity types, making
it easy to add new entity types without modifying existing systems.

See: docs/ARCHITECTURE.md - Protocol-Based Architecture section
"""

import ast
from pathlib import Path

# Paths that are allowed to use isinstance(_, Fish) checks
# These are either test files or entity-specific modules where type checks are expected
ALLOWED_PATHS = {
    # Entity module files can check their own types
    "core/entities/fish.py",
    "core/entities/plant.py",
    # Fish-specific component modules
    "core/fish/",
    # Plant-specific modules
    "core/plant/",
    # Test files can use isinstance for verification
    "tests/",
    # Migration/snapshot modules may need type checks for serialization
    "core/transfer/",
    "backend/migration",
    # Cache manager needs to filter by type currently
    "core/cache_manager.py",
}

# Files that currently have legacy isinstance checks.
# As we refactor these, remove them from the list.
# New files should NOT be added without justification.
#
# UPDATE: All legacy files have been refactored to use snapshot_type!
LEGACY_VIOLATIONS: set[str] = set()  # Empty - all refactored!

# Directories to scan (relative to repo root)
SCAN_DIRS = [
    "core/systems",
    "core/simulation",
    "core/minigames",
]


def _is_allowed_path(file_path: Path, repo_root: Path) -> bool:
    """Check if a file path is allowed to have isinstance(Fish) checks."""
    rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
    return any(rel_path.startswith(allowed) for allowed in ALLOWED_PATHS)


def _find_isinstance_fish_calls(file_path: Path) -> list[tuple[int, str]]:
    """Find isinstance(x, Fish) calls in a Python file.

    Returns list of (line_number, line_content) tuples.
    """
    violations: list[tuple[int, str]] = []
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError):
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for isinstance(something, Fish) or isinstance(something, Plant)
            if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                if len(node.args) >= 2:
                    type_arg = node.args[1]
                    # Could be a Name, Tuple, or other
                    type_names = []
                    if isinstance(type_arg, ast.Name):
                        type_names = [type_arg.id]
                    elif isinstance(type_arg, ast.Tuple):
                        for elt in type_arg.elts:
                            if isinstance(elt, ast.Name):
                                type_names.append(elt.id)

                    # Check for concrete entity types
                    concrete_types = {"Fish", "Plant", "Crab", "Food"}
                    for name in type_names:
                        if name in concrete_types:
                            line = source.splitlines()[node.lineno - 1].strip()
                            violations.append((node.lineno, line))
                            break

    return violations


def _is_legacy_violation(file_path: Path, repo_root: Path) -> bool:
    """Check if a file is in the legacy violations list."""
    rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
    return rel_path in LEGACY_VIOLATIONS


def test_no_new_isinstance_concrete_entity_checks():
    """New files should not check isinstance(entity, Fish/Plant/etc).

    Use capability protocols instead:
    - EnergyHolder for energy operations
    - Reproducible for reproduction checks
    - LifecycleAware for lifecycle state
    - Mortal for death/alive checks
    - Movable for movement

    Existing violations are grandfathered in LEGACY_VIOLATIONS.
    This test prevents NEW violations from being added.
    """
    repo_root = Path(__file__).resolve().parents[1]

    all_violations: list[tuple[str, int, str]] = []

    for scan_dir in SCAN_DIRS:
        dir_path = repo_root / scan_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            if _is_allowed_path(py_file, repo_root):
                continue
            # Skip legacy files - they're tracked separately
            if _is_legacy_violation(py_file, repo_root):
                continue

            violations = _find_isinstance_fish_calls(py_file)
            for line_no, line_content in violations:
                rel_path = py_file.relative_to(repo_root)
                all_violations.append((str(rel_path), line_no, line_content))

    if all_violations:
        msg_lines = ["NEW isinstance checks for concrete entity types found:"]
        msg_lines.append("")
        for file_path, line_no, content in all_violations:
            msg_lines.append(f"  {file_path}:{line_no}: {content}")
        msg_lines.append("")
        msg_lines.append("Use capability protocols instead (see core/protocols.py)")

        raise AssertionError("\n".join(msg_lines))


def test_legacy_violations_not_growing():
    """Track that we're reducing legacy violations, not adding new ones.

    Update EXPECTED_COUNT when you refactor files.
    """
    EXPECTED_COUNT = 0  # All legacy files refactored!

    actual_count = len(LEGACY_VIOLATIONS)

    # Allow shrinking (good!) but not growing
    if actual_count > EXPECTED_COUNT:
        raise AssertionError(
            f"LEGACY_VIOLATIONS grew from {EXPECTED_COUNT} to {actual_count}.\n"
            f"Adding new files to the legacy list is discouraged.\n"
            f"Consider using capability protocols instead."
        )


def test_scan_covers_critical_directories():
    """Verify that SCAN_DIRS covers the critical system directories."""
    repo_root = Path(__file__).resolve().parents[1]

    for scan_dir in SCAN_DIRS:
        dir_path = repo_root / scan_dir
        assert dir_path.exists(), f"SCAN_DIR '{scan_dir}' does not exist"


if __name__ == "__main__":
    # Run as script for quick debugging
    test_no_new_isinstance_concrete_entity_checks()
    print("✓ No NEW isinstance(Fish/Plant/...) violations found")
