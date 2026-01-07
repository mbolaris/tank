import pathlib
import sys


def main():
    root = pathlib.Path(".")
    exclude_dirs = {
        ".venv",
        "venv",
        "node_modules",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
    }

    artifacts = []
    # Use rglob but filter out excluded directories early
    for path in root.rglob("*"):
        # Skip if any part of the path is in exclude_dirs
        if any(part in exclude_dirs for part in path.parts):
            continue

        if (path.name == "__pycache__" and path.is_dir()) or path.suffix == ".pyc":
            artifacts.append(path)

    if artifacts:
        for art in artifacts:
            print(f"ERROR: Found artifact {art}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
