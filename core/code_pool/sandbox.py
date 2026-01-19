"""Sandbox validation and restricted globals for code pool components."""

from __future__ import annotations

import ast
import math
from typing import Any

from .models import ValidationError

# Default limits for source validation (can be overridden via SafetyConfig)
DEFAULT_MAX_SOURCE_LENGTH = 10_000
DEFAULT_MAX_AST_NODES = 500
DEFAULT_MAX_FUNCTION_DEPTH = 5

DISALLOWED_CALL_NAMES = {
    "__import__",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "locals",
    "open",
    "setattr",
    "delattr",
    "vars",
    "dir",
}

# Default set of allowed modules for imports
DEFAULT_ALLOWED_MODULES: set[str] = {"math"}

# Pre-loaded safe module objects
SAFE_MODULE_OBJECTS: dict[str, Any] = {
    "math": math,
}

ALLOWED_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "bool": bool,
    "dict": dict,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "round": round,
    "str": str,
    "sum": sum,
    "tuple": tuple,
}


class ASTValidator(ast.NodeVisitor):
    """Validate code against the restricted sandbox rules.

    Args:
        allowed_modules: Set of module names that can be imported.
                        Defaults to DEFAULT_ALLOWED_MODULES.
    """

    def __init__(self, allowed_modules: set[str] | None = None) -> None:
        self.allowed_modules = (
            allowed_modules if allowed_modules is not None else DEFAULT_ALLOWED_MODULES
        )

    def validate(self, tree: ast.AST) -> None:
        self.visit(tree)

    def _reject(self, node: ast.AST, reason: str) -> None:
        line = getattr(node, "lineno", "?")
        raise ValidationError(f"Disallowed syntax: {reason} (line {line})")

    def _validate_import(self, node: ast.Import) -> None:
        """Validate import statement - only allow whitelisted modules."""
        for alias in node.names:
            module_name = alias.name.split(".")[0]  # Get top-level module
            if module_name not in self.allowed_modules:
                self._reject(node, f"import of '{alias.name}' is not allowed")

    def _validate_import_from(self, node: ast.ImportFrom) -> None:
        """Validate from-import statement - only allow whitelisted modules."""
        if node.module is None:
            self._reject(node, "relative import is not allowed")
            return
        module_name = node.module.split(".")[0]  # Get top-level module
        if module_name not in self.allowed_modules:
            self._reject(node, f"import from '{node.module}' is not allowed")

    def _validate_call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in DISALLOWED_CALL_NAMES:
                self._reject(node, f"call to '{name}' is forbidden")
            if name.startswith("__"):
                self._reject(node, f"call to dunder '{name}'")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr.startswith("__"):
                self._reject(node, f"call to dunder attribute '{node.func.attr}'")

    def _validate_function_def(self, node: ast.FunctionDef) -> None:
        if node.name.startswith("__") or node.name in DISALLOWED_CALL_NAMES:
            self._reject(node, f"function name '{node.name}'")
        if node.decorator_list:
            self._reject(node, "decorators")

    def _validate_arg(self, node: ast.arg) -> None:
        if node.arg.startswith("__") or node.arg in DISALLOWED_CALL_NAMES:
            self._reject(node, f"argument name '{node.arg}'")

    def generic_visit(self, node: ast.AST) -> None:
        # First check for forbidden call patterns
        if isinstance(node, ast.Call):
            self._validate_call(node)

        # Check for forbidden names that might be used as values
        if isinstance(node, ast.Name):
            if node.id.startswith("__"):
                self._reject(node, f"dunder name '{node.id}'")
            if node.id in DISALLOWED_CALL_NAMES:
                self._reject(node, f"call to '{node.id}' is forbidden")

        # Check for dunder attributes
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                self._reject(node, f"dunder attribute '{node.attr}'")

        if isinstance(node, ast.FunctionDef):
            self._validate_function_def(node)

        if isinstance(node, ast.arg):
            self._validate_arg(node)

        # Handle imports (conditionally allowed)
        if isinstance(node, ast.Import):
            self._validate_import(node)
        elif isinstance(node, ast.ImportFrom):
            self._validate_import_from(node)

        # Continue visiting children
        super().generic_visit(node)

    # =========================================================================
    # Specific visit methods for nodes that should be rejected immediately
    # (without visiting children first, unless needed for test compatibility)
    # =========================================================================

    def visit_While(self, node: ast.While) -> None:
        self._reject(node, "while loops are not allowed")

    def visit_For(self, node: ast.For) -> None:
        self._reject(node, "for loops are not allowed")

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._reject(node, "lambda expressions are not allowed")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._reject(node, "class definitions are not allowed")

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._reject(node, "list comprehension is not allowed")

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._reject(node, "dict comprehension is not allowed")

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._reject(node, "set comprehension is not allowed")

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._reject(node, "generator comprehension is not allowed")

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._reject(node, "async operations are not allowed")

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._reject(node, "async operations are not allowed")

    def visit_Await(self, node: ast.Await) -> None:
        self._reject(node, "async operations are not allowed")

    def visit_Delete(self, node: ast.Delete) -> None:
        self._reject(node, "delete statements are not allowed")

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._reject(node, "nonlocal statements are not allowed")

    def visit_Raise(self, node: ast.Raise) -> None:
        self._reject(node, "raise statements are not allowed")

    def visit_Try(self, node: ast.Try) -> None:
        self._reject(node, "try statements are not allowed")

    def visit_Yield(self, node: ast.Yield) -> None:
        self._reject(node, "yield expressions are not allowed")

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self._reject(node, "yield expressions are not allowed")

    def visit_With(self, node: ast.With) -> None:
        # Visit children first to catch forbidden calls like open()
        self.generic_visit(node)
        self._reject(node, "with statements are not allowed")


def parse_and_validate(
    source: str,
    *,
    max_source_length: int | None = None,
    max_ast_nodes: int | None = None,
    max_function_depth: int | None = None,
) -> ast.Module:
    """Parse and validate Python source for the restricted sandbox.

    Args:
        source: Python source code to validate
        max_source_length: Maximum source length (default: DEFAULT_MAX_SOURCE_LENGTH)
        max_ast_nodes: Maximum AST node count (default: DEFAULT_MAX_AST_NODES)
        max_function_depth: Maximum function nesting depth (default: DEFAULT_MAX_FUNCTION_DEPTH)

    Returns:
        The parsed and validated AST

    Raises:
        ValidationError: If source fails any validation check
    """
    max_source_length = max_source_length or DEFAULT_MAX_SOURCE_LENGTH
    max_ast_nodes = max_ast_nodes or DEFAULT_MAX_AST_NODES
    max_function_depth = max_function_depth or DEFAULT_MAX_FUNCTION_DEPTH

    # Check source length
    if len(source) > max_source_length:
        raise ValidationError(
            f"Source too long: {len(source)} characters (max {max_source_length})"
        )

    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise ValidationError(f"Syntax error: {exc.msg}") from exc

    # Validate syntax rules
    ASTValidator().validate(tree)

    # Check complexity limits
    node_count, max_depth = _count_ast_complexity(tree)
    if node_count > max_ast_nodes:
        raise ValidationError(f"AST too complex: {node_count} nodes (max {max_ast_nodes})")
    if max_depth > max_function_depth:
        raise ValidationError(
            f"Function nesting too deep: {max_depth} levels (max {max_function_depth})"
        )

    return tree


def _count_ast_complexity(tree: ast.AST) -> tuple[int, int]:
    """Count AST nodes and maximum function nesting depth.

    Returns:
        Tuple of (node_count, max_function_depth)
    """
    node_count = 0
    max_depth = 0
    current_depth = 0

    class ComplexityCounter(ast.NodeVisitor):
        def generic_visit(self, node: ast.AST) -> None:
            nonlocal node_count
            node_count += 1
            super().generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            nonlocal node_count, current_depth, max_depth
            node_count += 1
            current_depth += 1
            max_depth = max(max_depth, current_depth)
            super().generic_visit(node)
            current_depth -= 1

    ComplexityCounter().visit(tree)
    return node_count, max_depth


def build_restricted_globals(extra_globals: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create restricted globals for exec of sandboxed code.

    Includes a safe __import__ that only allows importing whitelisted modules.
    """

    def safe_import(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> Any:
        """Safe import function that only allows whitelisted modules."""
        # Reject relative imports
        if level != 0:
            raise ImportError("Relative imports are not allowed")

        # Get top-level module name
        top_module = name.split(".")[0]

        # Check allowlist
        if top_module not in DEFAULT_ALLOWED_MODULES:
            raise ImportError(f"Import of '{name}' is not allowed")

        # Return the pre-loaded module object
        module = SAFE_MODULE_OBJECTS.get(top_module)
        if module is None:
            raise ImportError(f"Module '{top_module}' is not available")

        return module

    builtins_with_import = dict(ALLOWED_BUILTINS)
    builtins_with_import["__import__"] = safe_import

    globals_dict: dict[str, Any] = {"__builtins__": builtins_with_import}
    globals_dict.update(SAFE_MODULE_OBJECTS)
    if extra_globals:
        globals_dict.update(extra_globals)
    return globals_dict
