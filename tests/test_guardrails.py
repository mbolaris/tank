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
