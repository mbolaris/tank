import ast
from pathlib import Path
from typing import List, Optional, Set, Tuple


ALLOWED_RANDOM_ATTRS = {"Random", "SystemRandom"}


def _iter_core_files() -> List[Path]:
    core_root = Path(__file__).resolve().parents[1] / "core"
    return [path for path in core_root.rglob("*.py") if "__pycache__" not in path.parts]


def _collect_random_aliases(tree: ast.AST) -> Set[str]:
    aliases: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random":
                    aliases.add(alias.asname or "random")
    return aliases


class _RandomUsageVisitor(ast.NodeVisitor):
    def __init__(self, random_aliases: Set[str]) -> None:
        self._aliases = random_aliases
        self._stack: List[ast.AST] = []
        self.violations: List[Tuple[int, str]] = []

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
    violations: List[str] = []
    for path in _iter_core_files():
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
        aliases = _collect_random_aliases(tree)
        visitor = _RandomUsageVisitor(aliases)
        visitor.visit(tree)
        for line, detail in visitor.violations:
            violations.append(f"{path}:{line}: {detail}")

    assert not violations, "Global random usage detected:\n" + "\n".join(sorted(violations))
