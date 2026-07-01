"""Contracts that keep contributor validation tiers cheap and explicit."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_VALIDATION_MARKERS = {"slow", "integration", "manual"}
LONG_FRAME_LIMIT = 500
LONG_SLEEP_SECONDS = 0.25


def _marker_names_from_decorator(decorator: ast.expr) -> set[str]:
    curr: ast.expr = decorator
    if isinstance(curr, ast.Call):
        curr = curr.func

    parts = []
    while isinstance(curr, ast.Attribute):
        parts.append(curr.attr)
        curr = curr.value
    if isinstance(curr, ast.Name):
        parts.append(curr.id)
    parts.reverse()

    # Match pytest.mark.slow, pytest.mark.integration, pytest.mark.manual.
    if len(parts) >= 3 and parts[0] == "pytest" and parts[1] == "mark":
        return {parts[2]}
    return set()


def _has_exclusion_decorator(node: ast.AST) -> bool:
    decorators = getattr(node, "decorator_list", [])
    return any(
        _marker_names_from_decorator(dec) & EXCLUDED_VALIDATION_MARKERS for dec in decorators
    )


def _has_module_level_exclusion(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    value_str = ast.dump(node.value)
                    if any(marker in value_str for marker in EXCLUDED_VALIDATION_MARKERS):
                        return True
    return False


def _literal_number(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    return None


def _range_limit(call_node: ast.AST) -> int | None:
    if not isinstance(call_node, ast.Call):
        return None
    if not (isinstance(call_node.func, ast.Name) and call_node.func.id == "range"):
        return None
    args = call_node.args
    stop_node = None
    if len(args) == 1:
        stop_node = args[0]
    elif len(args) in (2, 3):
        stop_node = args[1]

    value = _literal_number(stop_node) if stop_node is not None else None
    return int(value) if value is not None else None


def _call_name(call_node: ast.Call) -> str:
    func = call_node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _has_simulation_tick_call(body_nodes: list[ast.stmt]) -> bool:
    tick_calls = {"step", "update", "run_collect_stats"}
    for node in body_nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and _call_name(child) in tick_calls:
                return True
    return False


def _long_frame_call(call_node: ast.Call) -> int | None:
    for kw in call_node.keywords:
        if kw.arg in {"frames", "max_frames"}:
            value = _literal_number(kw.value)
            if value is not None and value > LONG_FRAME_LIMIT:
                return int(value)
    return None


def _long_sleep_call(call_node: ast.Call) -> float | None:
    if _call_name(call_node) != "sleep" or not call_node.args:
        return None
    value = _literal_number(call_node.args[0])
    if value is not None and value > LONG_SLEEP_SECONDS:
        return value
    return None


def _is_subprocess_run_call(call_node: ast.Call) -> bool:
    func = call_node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "run"
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _contains_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node))


def _string_literals(node: ast.AST) -> list[str]:
    return [
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


def _iter_unexcluded_test_functions(tree: ast.Module):
    function_types = (ast.FunctionDef, ast.AsyncFunctionDef)
    if _has_module_level_exclusion(tree):
        return

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_excluded = _has_exclusion_decorator(node)
            for subnode in node.body:
                if isinstance(subnode, function_types) and subnode.name.startswith("test_"):
                    if not class_excluded and not _has_exclusion_decorator(subnode):
                        yield f"{node.name}.{subnode.name}", subnode
        elif isinstance(node, function_types) and node.name.startswith("test_"):
            if not _has_exclusion_decorator(node):
                yield node.name, node


def test_run_bench_contract_tests_do_not_import_real_benchmarks():
    source = (ROOT / "tests" / "test_run_bench.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any(
        module == "benchmarks" or module.startswith("benchmarks.") for module in imported_modules
    )
    assert "benchmarks/tank/" not in source.replace("\\", "/")
    assert "benchmarks/soccer/" not in source.replace("\\", "/")


def test_pre_pr_gate_composes_smoke_gate_and_excludes_expensive_markers():
    source = (ROOT / "tools" / "pre_pr_gate.py").read_text(encoding="utf-8")

    assert "tools/smoke_gate.py" in source
    assert "not slow and not integration and not manual" in source


def test_pre_pr_gate_reports_collection_and_module_diagnostics():
    """The broad suite must stay diagnosable: exact collected/deselected counts
    (which `-n auto` does not print on its own) and a slowest-modules breakdown.
    """
    source = (ROOT / "tools" / "pre_pr_gate.py").read_text(encoding="utf-8")
    assert "run_pytest_with_diagnostics" in source
    assert "collect_only_args" in source

    gate_common_source = (ROOT / "tools" / "gate_common.py").read_text(encoding="utf-8")
    assert "def run_pytest_with_diagnostics(" in gate_common_source
    assert "def collect_only_counts(" in gate_common_source


def test_agent_gate_composes_smoke_gate_and_uses_curated_tests():
    source = (ROOT / "tools" / "agent_gate.py").read_text(encoding="utf-8")

    assert "tools/smoke_gate.py" in source
    assert "_AGENT_CURATED_TESTS" in source
    assert "tests/test_determinism.py" in source
    assert "not slow and not integration and not manual" in source


def test_no_unmarked_expensive_simulation_loops():
    """Ensure ordinary tests cannot accidentally grow into real simulations.

    The pre-PR gate should include cheap unit and contract coverage. Tests that run
    long simulation loops, invoke real benchmarks in subprocesses, sleep for long
    periods, or run headless commands with large frame counts belong behind the
    slow/integration/manual markers.
    """

    tests_dir = ROOT / "tests"
    violations = []

    for path in tests_dir.rglob("test_*.py"):
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            continue

        for test_name, node in _iter_unexcluded_test_functions(tree):
            for child in ast.walk(node):
                if isinstance(child, ast.For):
                    limit = _range_limit(child.iter)
                    if (
                        limit is not None
                        and limit > LONG_FRAME_LIMIT
                        and _has_simulation_tick_call(child.body)
                    ):
                        violations.append(
                            f"File: {path.relative_to(ROOT)}\n"
                            f"Test: {test_name}\n"
                            f"Range limit: {limit} with simulation tick call."
                        )
                elif isinstance(child, ast.Call):
                    frame_count = _long_frame_call(child)
                    if frame_count is not None:
                        violations.append(
                            f"File: {path.relative_to(ROOT)}\n"
                            f"Test: {test_name}\n"
                            f"Long frame-count argument: {frame_count}."
                        )

                    sleep_seconds = _long_sleep_call(child)
                    if sleep_seconds is not None:
                        violations.append(
                            f"File: {path.relative_to(ROOT)}\n"
                            f"Test: {test_name}\n"
                            f"Long sleep: {sleep_seconds:g}s."
                        )
                    if _is_subprocess_run_call(child):
                        strings = [
                            literal.replace("\\", "/") for literal in _string_literals(child)
                        ]
                        if _contains_name(child, "RUN_BENCH") and any(
                            "benchmarks/" in literal for literal in strings
                        ):
                            violations.append(
                                f"File: {path.relative_to(ROOT)}\n"
                                f"Test: {test_name}\n"
                                "Real benchmark subprocess call belongs in a slow/integration/manual test."
                            )

    if violations:
        msg = "\n\n".join(violations)
        raise AssertionError(
            f"Found unmarked expensive work in ordinary tests:\n\n{msg}\n\n"
            f"Please mark these tests with @pytest.mark.slow, @pytest.mark.integration, or @pytest.mark.manual."
        )
