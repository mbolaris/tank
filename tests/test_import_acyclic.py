"""Architecture fitness test: ``core/`` has an acyclic module-load import graph.

``core/`` historically leaned on hundreds of in-function imports to route around
circular dependencies. A measurement (ADR-008) showed the *module-level* graph
was already nearly a DAG -- the only cycles were three package/submodule pairs
where a submodule reached back into its own package facade. This test makes the
*absence* of module-load import cycles an enforced invariant rather than a happy
accident, so the graph stays acyclic as the codebase grows.

What "module-load" means
------------------------
The graph models only imports that execute the first time a module is imported.
Two kinds of imports are deliberately excluded because they do not participate
in module-load ordering:

* imports inside a function/method body (the explicit escape hatch for the rare
  genuine cycle), and
* imports under ``if TYPE_CHECKING:`` (type-only, never executed at runtime).

Pure-AST, no external dependencies -- consistent with ``test_import_boundaries``
and ``test_god_class_limits``.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

CORE = "core"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _module_name(path: Path, root: Path) -> str:
    """Dotted module name for a file, collapsing ``__init__`` to its package."""
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _iter_core_modules(root: Path) -> dict[str, Path]:
    core_dir = root / CORE
    return {
        _module_name(path, root): path
        for path in core_dir.rglob("*.py")
        if "__pycache__" not in path.parts
    }


def _is_type_checking(test: ast.expr) -> bool:
    """True for ``TYPE_CHECKING`` or ``typing.TYPE_CHECKING`` guards."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _module_load_imports(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    """Import statements that run at module load (not in functions / TYPE_CHECKING)."""
    found: list[ast.Import | ast.ImportFrom] = []

    def visit(node: ast.AST, in_func: bool, in_tc: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                if not in_func and not in_tc:
                    found.append(child)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, True, in_tc)
            elif isinstance(child, ast.If) and _is_type_checking(child.test):
                # Body is type-only; ``else:`` still runs at load time.
                for sub in child.body:
                    visit(sub, in_func, True)
                for sub in child.orelse:
                    visit(sub, in_func, in_tc)
            else:
                visit(child, in_func, in_tc)

    visit(tree, False, False)
    return found


def _relative_base(curmod: str, is_pkg: bool, level: int) -> str:
    """Resolve the anchor package for a relative import (``from . / .. import``)."""
    parts = curmod.split(".")
    if not is_pkg:
        parts = parts[:-1]  # a regular module anchors on its containing package
    drop = level - 1  # level 1 == current package; each extra dot climbs one more
    if drop > 0:
        parts = parts[:-drop] if drop <= len(parts) else []
    return ".".join(parts)


def _imported_targets(node: ast.Import | ast.ImportFrom, curmod: str, is_pkg: bool) -> set[str]:
    """Dotted names an import refers to (the module, plus each ``from`` name)."""
    targets: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.add(alias.name)
        return targets

    # ImportFrom
    if node.level:
        base = _relative_base(curmod, is_pkg, node.level)
        module = f"{base}.{node.module}" if node.module else base
    else:
        module = node.module or ""
    if module:
        targets.add(module)
        # ``from pkg import name`` may pull in a submodule named ``name``.
        for alias in node.names:
            targets.add(f"{module}.{alias.name}")
    return targets


def _longest_prefix(dotted: str, names: set[str]) -> str | None:
    """Map an import target onto the longest matching real module name."""
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in names:
            return cand
    return None


def _build_core_graph(mods: dict[str, Path]) -> dict[str, set[str]]:
    """Module-load import graph restricted to edges between core/ modules."""
    names = set(mods)
    graph: dict[str, set[str]] = {m: set() for m in names}
    for mod, path in mods.items():
        is_pkg = path.name == "__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in _module_load_imports(tree):
            for raw in _imported_targets(node, mod, is_pkg):
                if raw != CORE and not raw.startswith(CORE + "."):
                    continue
                dep = _longest_prefix(raw, names)
                if dep is not None and dep != mod:
                    graph[mod].add(dep)
    return graph


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    """Tarjan's algorithm; returns only components with a real cycle (size > 1)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: dict[str, bool] = {}
    stack: list[str] = []
    counter = [0]
    components: list[list[str]] = []

    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, 10000))
    try:

        def strong(v: str) -> None:
            index[v] = low[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack[v] = True
            for w in graph[v]:
                if w not in index:
                    strong(w)
                    low[v] = min(low[v], low[w])
                elif on_stack.get(w):
                    low[v] = min(low[v], index[w])
            if low[v] == index[v]:
                comp: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == v:
                        break
                components.append(comp)

        for node in graph:
            if node not in index:
                strong(node)
    finally:
        sys.setrecursionlimit(old_limit)

    return [c for c in components if len(c) > 1]


def test_core_module_graph_is_acyclic() -> None:
    """The core/ module-load import graph must be a DAG (ADR-008)."""
    mods = _iter_core_modules(_repo_root())
    graph = _build_core_graph(mods)
    cycles = _strongly_connected_components(graph)

    if cycles:
        lines = [
            "core/ module-load import graph must be acyclic (ADR-008), but found "
            f"{len(cycles)} cycle(s):",
            "",
        ]
        for comp in sorted(cycles, key=len, reverse=True):
            members = set(comp)
            lines.append(f"  cycle across {len(comp)} modules:")
            for m in sorted(comp):
                for dep in sorted(graph[m]):
                    if dep in members:
                        lines.append(f"    {m} -> {dep}")
        lines += [
            "",
            "Most cycles come from a submodule importing its own package facade,",
            "e.g. `from core.pkg import sibling_module`. Import the sibling module",
            "directly instead: `import core.pkg.sibling_module as sibling_module`.",
            "For a genuinely mutual dependency, defer one side with a function-local",
            "import (the documented escape hatch).",
        ]
        raise AssertionError("\n".join(lines))


def test_core_graph_is_connected_enough_to_be_meaningful() -> None:
    """Guard the analyzer itself: it must actually discover core/ import edges.

    A refactor that broke import parsing could make the acyclicity test pass
    vacuously. Assert the graph has a substantial number of edges so the
    invariant above keeps real teeth.
    """
    mods = _iter_core_modules(_repo_root())
    graph = _build_core_graph(mods)
    edge_count = sum(len(deps) for deps in graph.values())
    assert len(mods) > 100, f"expected to discover the core package, found {len(mods)} modules"
    assert edge_count > 200, f"import-graph analysis looks broken: only {edge_count} edges"
