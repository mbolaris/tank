"""Import boundary tests to prevent architectural re-tangling.

These tests verify that module boundaries are respected:
- core/worlds/* must not import backend/* or frontend/*
- backend/* can import core/worlds/interfaces.py but not core/worlds/tank/* directly

Uses AST-based import analysis with no external dependencies.
"""

import ast
import os
from pathlib import Path
from typing import List, Set, Tuple

import pytest


def get_repo_root() -> Path:
    """Get repository root directory."""
    return Path(__file__).parent.parent


def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in a directory recursively."""
    return list(directory.rglob("*.py"))


def extract_imports(file_path: Path) -> Set[str]:
    """Extract all import module names from a Python file.

    Returns set of module names (e.g., 'backend.world_registry', 'core.worlds.interfaces').
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return set()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return set()

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
                # Also add the full path for "from X import Y" cases
                for alias in node.names:
                    imports.add(f"{node.module}.{alias.name}")

    return imports


def check_forbidden_imports(
    source_dir: Path, forbidden_patterns: List[str], allowed_exceptions: List[str] = None
) -> List[Tuple[Path, str]]:
    """Check for forbidden imports in a directory.

    Args:
        source_dir: Directory to scan for Python files
        forbidden_patterns: List of import prefixes that are forbidden
        allowed_exceptions: List of specific imports that are allowed despite matching forbidden patterns

    Returns:
        List of (file_path, forbidden_import) tuples for violations
    """
    allowed = set(allowed_exceptions or [])
    violations = []

    for py_file in find_python_files(source_dir):
        imports = extract_imports(py_file)

        for imp in imports:
            for pattern in forbidden_patterns:
                if imp.startswith(pattern):
                    # Check if this specific import is allowed
                    if imp not in allowed and not any(imp.startswith(a) for a in allowed):
                        violations.append((py_file, imp))
                        break

    return violations


class TestCoreWorldsBoundaries:
    """Verify core/worlds does not import backend or frontend."""

    def test_no_backend_imports(self):
        """core/worlds/* must not import backend/*."""
        repo_root = get_repo_root()
        core_worlds_dir = repo_root / "core" / "worlds"

        if not core_worlds_dir.exists():
            pytest.skip("core/worlds directory not found")

        violations = check_forbidden_imports(core_worlds_dir, forbidden_patterns=["backend"])

        if violations:
            msg = "core/worlds must not import backend:\n"
            for path, imp in violations:
                rel_path = path.relative_to(repo_root)
                msg += f"  {rel_path}: imports '{imp}'\n"
            pytest.fail(msg)

    def test_no_frontend_imports(self):
        """core/worlds/* must not import frontend/*."""
        repo_root = get_repo_root()
        core_worlds_dir = repo_root / "core" / "worlds"

        if not core_worlds_dir.exists():
            pytest.skip("core/worlds directory not found")

        violations = check_forbidden_imports(core_worlds_dir, forbidden_patterns=["frontend"])

        if violations:
            msg = "core/worlds must not import frontend:\n"
            for path, imp in violations:
                rel_path = path.relative_to(repo_root)
                msg += f"  {rel_path}: imports '{imp}'\n"
            pytest.fail(msg)


class TestBackendBoundaries:
    """Verify backend respects the registry pattern for world access."""

    def test_no_direct_tank_world_imports(self):
        """backend/* should not import core/worlds/tank/* directly.

        Backend should access worlds through the registry pattern,
        not by directly importing implementation details.
        """
        repo_root = get_repo_root()
        backend_dir = repo_root / "backend"

        if not backend_dir.exists():
            pytest.skip("backend directory not found")

        # backend/world_registry.py is the exception - it MUST import tank to register it
        violations = check_forbidden_imports(
            backend_dir,
            forbidden_patterns=["core.worlds.tank"],
            allowed_exceptions=[
                # world_registry.py is allowed to import tank to register it
                # This is checked via file path below
            ],
        )

        # Filter out world_registry.py - it's the designated place for tank imports
        filtered_violations = [
            (path, imp) for path, imp in violations if path.name != "world_registry.py"
        ]

        if filtered_violations:
            msg = "backend should use registry instead of direct core/worlds/tank imports:\n"
            for path, imp in filtered_violations:
                rel_path = path.relative_to(repo_root)
                msg += f"  {rel_path}: imports '{imp}'\n"
            msg += "\nUse create_world() from backend.world_registry instead."
            pytest.fail(msg)

    def test_allowed_interface_imports(self):
        """backend/* CAN import core/worlds/interfaces.py - this is expected."""
        # This is a documentation test - we're verifying the allowed pattern exists
        repo_root = get_repo_root()
        interfaces_path = repo_root / "core" / "worlds" / "interfaces.py"

        assert interfaces_path.exists(), "core/worlds/interfaces.py should exist as the public API"


class TestCoreInterfacesBoundaries:
    """Verify core/interfaces.py is clean of circular dependencies."""

    def test_no_backend_imports_in_interfaces(self):
        """core/interfaces.py must not import backend."""
        repo_root = get_repo_root()
        interfaces_file = repo_root / "core" / "interfaces.py"

        if not interfaces_file.exists():
            pytest.skip("core/interfaces.py not found")

        imports = extract_imports(interfaces_file)
        backend_imports = [imp for imp in imports if imp.startswith("backend")]

        if backend_imports:
            pytest.fail(f"core/interfaces.py must not import backend: {backend_imports}")


# Utility function for local testing
def main():
    """Run boundary checks and report violations."""
    repo_root = get_repo_root()

    print("Checking import boundaries...")
    print()

    # Check core/worlds -> backend
    core_worlds_dir = repo_root / "core" / "worlds"
    if core_worlds_dir.exists():
        violations = check_forbidden_imports(core_worlds_dir, ["backend", "frontend"])
        if violations:
            print("❌ core/worlds has forbidden imports:")
            for path, imp in violations:
                print(f"   {path.relative_to(repo_root)}: {imp}")
        else:
            print("✅ core/worlds: clean (no backend/frontend imports)")

    # Check backend -> core/worlds/tank
    backend_dir = repo_root / "backend"
    if backend_dir.exists():
        violations = check_forbidden_imports(backend_dir, ["core.worlds.tank"])
        filtered = [(p, i) for p, i in violations if p.name != "world_registry.py"]
        if filtered:
            print("❌ backend has direct tank imports (should use registry):")
            for path, imp in filtered:
                print(f"   {path.relative_to(repo_root)}: {imp}")
        else:
            print("✅ backend: clean (uses registry for tank access)")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
