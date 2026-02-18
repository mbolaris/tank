import ast
from pathlib import Path
from typing import Optional

ALLOWED_RANDOM_ATTRS = {"Random", "SystemRandom"}


def _iter_core_files() -> list[Path]:
    core_root = Path(__file__).resolve().parents[1] / "core"
    return [path for path in core_root.rglob("*.py") if "__pycache__" not in path.parts]


def _collect_random_aliases(tree: ast.AST) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random":
                    aliases.add(alias.asname or "random")
    return aliases


class _RandomUsageVisitor(ast.NodeVisitor):
    def __init__(self, random_aliases: set[str]) -> None:
        self._aliases = random_aliases
        self._stack: list[ast.AST] = []
        self.violations: list[tuple[int, str]] = []

    def visit(self, node: ast.AST) -> None:
        self._stack.append(node)
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        visitor(node)
        self._stack.pop()

    def _parent(self) -> Optional[ast.AST]:
        if len(self._stack) < 2:
            return None
        return self._stack[-2]

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "random":
            for alias in node.names:
                if alias.name not in ALLOWED_RANDOM_ATTRS:
                    self.violations.append((node.lineno, f"from random import {alias.name}"))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id in self._aliases:
            if node.attr not in ALLOWED_RANDOM_ATTRS:
                self.violations.append((node.lineno, f"{node.value.id}.{node.attr}"))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self._aliases:
            parent = self._parent()
            if isinstance(parent, ast.Attribute) and parent.value is node:
                return
            self.violations.append((node.lineno, node.id))
        self.generic_visit(node)


def test_no_global_random_usage_in_core() -> None:
    """Core simulation should avoid global random module usage."""
    violations: list[str] = []
    for path in _iter_core_files():
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
        aliases = _collect_random_aliases(tree)
        visitor = _RandomUsageVisitor(aliases)
        visitor.visit(tree)
        for line, detail in visitor.violations:
            violations.append(f"{path}:{line}: {detail}")

    assert not violations, "Global random usage detected:\n" + "\n".join(sorted(violations))


class _UnseededRandomFinder(ast.NodeVisitor):
    """AST visitor that finds calls to random.Random() with no seed arguments."""

    def __init__(self, random_aliases: set[str]) -> None:
        self._aliases = random_aliases
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check if this is a call to random.Random() with no args (unseeded)."""
        is_random_random = False

        # Case 1: random.Random() or pyrandom.Random()
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "Random":
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in self._aliases:
                        is_random_random = True

        if is_random_random:
            # Check if called with no arguments (unseeded = non-deterministic)
            if not node.args and not node.keywords:
                self.violations.append((node.lineno, "random.Random() called with no seed"))

        self.generic_visit(node)


def test_no_unseeded_random_in_core() -> None:
    """Core simulation should not use unseeded random.Random() fallbacks.

    This catches patterns like:
        rng = rng if rng is not None else random.Random()
    or:
        rng = rng or random.Random()

    These work fine if callers always pass rng, but are landmines that
    silently cause non-deterministic behavior if a call site is missed.

    For simulation code, use require_rng() from core.util.rng which
    fails loudly when an RNG is not available.
    """
    # Files that are explicitly allowed to create RNGs (engine/world level, or utility)
    # These are the ONLY places that should create random.Random(seed)
    allowlist_files = {
        "rng.py",  # The utility module itself (documents the pattern)
        "engine.py",  # SimulationEngine creates the master RNG with seed
        "tank_world.py",  # TankWorld may need RNG for standalone usage
    }

    # Paths within core/ that are allowed (e.g., non-simulation utilities)
    allowlist_paths = {
        "core/poker/simulation/",  # Poker simulation has its own engine
        "core/poker/evaluation/",  # Benchmark tools
        "core/skills/games/",  # Mini-game utilities (not core sim)
        "core/human_poker_game.py",  # Human-facing game
    }

    violations: list[str] = []
    for path in _iter_core_files():
        # Check file allowlist
        if path.name in allowlist_files:
            continue

        # Check path allowlist
        path_str = str(path).replace("\\", "/")
        if any(allowed in path_str for allowed in allowlist_paths):
            continue

        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
        aliases = _collect_random_aliases(tree)
        # Also check for "pyrandom" which is a common alias in this codebase
        aliases.add("pyrandom")

        visitor = _UnseededRandomFinder(aliases)
        visitor.visit(tree)

        for line, detail in visitor.violations:
            violations.append(f"{path}:{line}: {detail}")

    # STRICT MODE: This test now fails if there are violations in core simulation paths
    # If you get failures, either:
    # 1. Fix the code to use require_rng() or require_rng_param()
    # 2. Add the file to allowlist_files if it's a legitimate engine/world-level RNG creator
    # 3. Add the path to allowlist_paths if it's a non-simulation utility
    assert not violations, (
        f"Found {len(violations)} unseeded random.Random() calls in core/ (determinism risk):\n"
        + "\n".join(sorted(violations)[:30])
        + ("\n..." if len(violations) > 30 else "")
        + "\nFix by using require_rng_param() or adding to allowlist if legitimately top-level."
    )
