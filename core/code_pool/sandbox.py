"""Sandbox validation and restricted globals for code pool components."""

from __future__ import annotations

import ast
import math
from typing import Any, Optional

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
}

DISALLOWED_NODE_TYPES = (
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.DictComp,
    ast.For,
    ast.GeneratorExp,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.ListComp,
    ast.Nonlocal,
    ast.Raise,
    ast.SetComp,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)

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

DEFAULT_ALLOWED_MODULES: dict[str, Any] = {
    "math": math,
}


class ASTValidator(ast.NodeVisitor):
    """Validate code against the restricted sandbox rules."""

    def validate(self, tree: ast.AST) -> None:
        self.visit(tree)

    def _reject(self, node: ast.AST, reason: str) -> None:
        line = getattr(node, "lineno", "?")
        raise ValidationError(f"Disallowed syntax: {reason} (line {line})")

    def _validate_call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in DISALLOWED_CALL_NAMES or node.func.id.startswith("__"):
                self._reject(node, f"call to '{node.func.id}'")
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
        if isinstance(node, DISALLOWED_NODE_TYPES):
            self._reject(node, node.__class__.__name__)

        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                self._reject(node, f"dunder attribute '{node.attr}'")

        if isinstance(node, ast.Name):
            if node.id.startswith("__"):
                self._reject(node, f"dunder name '{node.id}'")
            if node.id in DISALLOWED_CALL_NAMES:
                self._reject(node, f"forbidden name '{node.id}'")

        if isinstance(node, ast.Call):
            self._validate_call(node)

        if isinstance(node, ast.FunctionDef):
            self._validate_function_def(node)

        if isinstance(node, ast.arg):
            self._validate_arg(node)

        super().generic_visit(node)


def parse_and_validate(
    source: str,
    *,
    max_source_length: Optional[int] = None,
    max_ast_nodes: Optional[int] = None,
    max_function_depth: Optional[int] = None,
) -> ast.AST:
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
        raise ValidationError(
            f"AST too complex: {node_count} nodes (max {max_ast_nodes})"
        )
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
    """Create restricted globals for exec of sandboxed code."""
    globals_dict: dict[str, Any] = {"__builtins__": ALLOWED_BUILTINS}
    globals_dict.update(DEFAULT_ALLOWED_MODULES)
    if extra_globals:
        globals_dict.update(extra_globals)
    return globals_dict
