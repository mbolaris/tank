import pathlib
import subprocess


def _decode_paths_nul(data: bytes) -> list[str]:
    if not data:
        return []
    # Git uses UTF-8 paths; fall back safely on Windows oddities.
    text = data.decode("utf-8", errors="replace")
    parts = [p for p in text.split("\0") if p]
    return parts


def _git_paths(args: list[str]) -> list[str]:
    try:
        data = subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)
    except Exception:
        return []
    return _decode_paths_nul(data)


def _is_artifact(path_str: str) -> bool:
    # Git outputs forward slashes even on Windows.
    normalized = path_str.replace("\\", "/")
    if normalized.endswith(".pyc"):
        return True
    if "/__pycache__/" in normalized or normalized.endswith("/__pycache__"):
        return True
    return False


def main():
    # This hook is intended to prevent committing Python bytecode artifacts.
    # Developers may legitimately have local `__pycache__/` directories after
    # running tests; those should be gitignored and should not block commits.

    tracked = _git_paths(["ls-files", "-z"])
    staged = _git_paths(["diff", "--cached", "--name-only", "-z"])

    artifacts: list[str] = []
    for path_str in tracked + staged:
        if _is_artifact(path_str):
            artifacts.append(path_str)

    if artifacts:
        for art in sorted(set(artifacts)):
            print(f"ERROR: Found committed/staged artifact {art}")
        return 1

    # If git isn't available for some reason, fall back to a lightweight scan
    # of the current directory (best-effort, but do not block local workflows
    # just because bytecode exists on disk).
    if not tracked and not staged:
        root = pathlib.Path(".")
        for path in root.rglob("*.pyc"):
            print(f"ERROR: Found artifact {path}")
            return 1
        for path in root.rglob("__pycache__"):
            if path.is_dir():
                print(f"ERROR: Found artifact {path}")
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
