def test_no_legacy_code():
    """Guardrail test to ensure no legacy terms exist in production code."""
    import os

    # Terms that should not appear in the codebase
    FORBIDDEN_TERMS = [
        "legacy endpoint",
        "backward compat",
        "compatibility shim",
        "tank_registry",
        "simulation_manager",
        "tank_world_adapter",
        "/api/tanks",
        "/ws/tank",
    ]

    # Directories to search (exclude tests, docs, and hidden dirs)
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SEARCH_DIRS = ["backend", "core", "frontend/src"]

    violations = []

    for search_dir in SEARCH_DIRS:
        abs_search_dir = os.path.join(ROOT_DIR, search_dir)
        if not os.path.exists(abs_search_dir):
            continue

        for root, dirs, files in os.walk(abs_search_dir):
            # Skip caches and tests
            if "__pycache__" in root or "tests" in root or "node_modules" in root:
                continue

            for file in files:
                if not (file.endswith(".py") or file.endswith(".ts") or file.endswith(".tsx")):
                    continue

                # Skip this test file itself if it were in the search path (it's in tests/ so it's skipped)
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    for term in FORBIDDEN_TERMS:
                        if term in content:
                            # Allow "legacy" if it's just the word "legacy" without "endpoint" context,
                            # but here we search for specific phrases.
                            # Exception: comments might reference legacy, but we want a clean cut.
                            # Let's flag it.
                            violations.append(f"{file_path}: Found '{term}'")
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")

    assert not violations, "Found legacy code violations:\n" + "\n".join(violations)


def test_no_tank_id_in_world_agnostic_code():
    """Ensure tank_id doesn't appear outside Tank-mode-specific paths."""
    import os
    import re

    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Directories/files that ARE allowed to use tank_id
    # We include tests/ because tests often mock or check legacy behavior
    ALLOWED_PATHS = [
        "core/worlds/tank/",
        "backend/world_persistence.py",  # read-fallback only
        "backend/README.md",  # documentation might reference back-compat
        "tests/",
        "frontend/src/config.ts",  # deprecated function
    ]

    # Forbidden term
    TERM = "tank_id"
    # Regex to find whole word 'tank_id'
    tank_id_pattern = re.compile(r"\btank_id\b", re.IGNORECASE)

    SEARCH_DIRS = ["backend", "core", "frontend/src"]
    violations = []

    for search_dir in SEARCH_DIRS:
        abs_search_dir = os.path.join(ROOT_DIR, search_dir)
        if not os.path.exists(abs_search_dir):
            continue

        for root, dirs, files in os.walk(abs_search_dir):
            if "__pycache__" in root or "node_modules" in root:
                continue

            for file in files:
                if not (file.endswith(".py") or file.endswith(".ts") or file.endswith(".tsx")):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, ROOT_DIR)

                # Skip allowed paths
                if any(allowed in rel_path for allowed in ALLOWED_PATHS):
                    continue

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    if tank_id_pattern.search(content):
                        violations.append(f"{rel_path}: Contains '{TERM}'")
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")

    assert not violations, "Found tank_id in world-agnostic code:\n" + "\n".join(violations)
