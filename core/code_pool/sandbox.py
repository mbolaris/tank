"""Sandbox validation and restricted globals for code pool components."""

from __future__ import annotations

import ast
import math
from typing import Any

from .models import ValidationError


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


def parse_and_validate(source: str) -> ast.AST:
    """Parse and validate Python source for the restricted sandbox."""
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError as exc:
        raise ValidationError(f"Syntax error: {exc.msg}") from exc

    ASTValidator().validate(tree)
    return tree


def build_restricted_globals(extra_globals: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create restricted globals for exec of sandboxed code."""
    globals_dict: dict[str, Any] = {"__builtins__": ALLOWED_BUILTINS}
    globals_dict.update(DEFAULT_ALLOWED_MODULES)
    if extra_globals:
        globals_dict.update(extra_globals)
    return globals_dict
