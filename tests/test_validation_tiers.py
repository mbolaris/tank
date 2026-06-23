"""Contracts that keep contributor validation tiers cheap and explicit."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def test_fast_gate_composes_smoke_gate_and_excludes_expensive_markers():
    source = (ROOT / "tools" / "fast_gate.py").read_text(encoding="utf-8")

    assert "tools/smoke_gate.py" in source
    assert "not slow and not integration and not manual" in source


def test_agent_gate_composes_smoke_gate_and_uses_curated_tests():
    source = (ROOT / "tools" / "agent_gate.py").read_text(encoding="utf-8")

    assert "tools/smoke_gate.py" in source
    assert "_AGENT_CURATED_TESTS" in source
    assert "tests/test_determinism.py" in source
    assert "not slow and not integration and not manual" in source


def test_no_unmarked_expensive_simulation_loops():
    """Ensure that no test function contains a large simulation loop (e.g. range > 100
    with world.step() or equivalent) unless marked as slow, integration, or manual.
    """
    import ast

    tests_dir = ROOT / "tests"

    def get_range_limit(call_node):
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

        if stop_node is not None:
            if isinstance(stop_node, ast.Constant) and isinstance(stop_node.value, int):
                return stop_node.value
        return None

    def has_step_call(body_nodes):
        for node in body_nodes:
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if (isinstance(func, ast.Attribute) and func.attr == "step") or (
                        isinstance(func, ast.Name) and func.id == "step"
                    ):
                        return True
        return False

    def has_exclusion_decorator(node):
        if not hasattr(node, "decorator_list"):
            return False
        for dec in node.decorator_list:
            curr = dec
            if isinstance(curr, ast.Call):
                curr = curr.func

            parts = []
            while isinstance(curr, ast.Attribute):
                parts.append(curr.attr)
                curr = curr.value
            if isinstance(curr, ast.Name):
                parts.append(curr.id)
            parts.reverse()

            # Match pytest.mark.slow, pytest.mark.integration, pytest.mark.manual
            if (
                len(parts) >= 3
                and parts[0] == "pytest"
                and parts[1] == "mark"
                and parts[2] in ("slow", "integration", "manual")
            ):
                return True
        return False

    def has_module_level_exclusion(tree):
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "pytestmark":
                        value_str = ast.dump(node.value)
                        if any(marker in value_str for marker in ("slow", "integration", "manual")):
                            return True
        return False

    violations = []

    for path in tests_dir.rglob("test_*.py"):
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except Exception:
            continue

        if has_module_level_exclusion(tree):
            continue

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_excluded = has_exclusion_decorator(node)
                for subnode in node.body:
                    if isinstance(subnode, ast.FunctionDef) and subnode.name.startswith("test_"):
                        if class_excluded or has_exclusion_decorator(subnode):
                            continue
                        for child in ast.walk(subnode):
                            if isinstance(child, ast.For):
                                limit = get_range_limit(child.iter)
                                if limit is not None and limit > 100:
                                    if has_step_call(child.body):
                                        violations.append(
                                            f"File: {path.relative_to(ROOT)}\n"
                                            f"Test: {node.name}.{subnode.name}\n"
                                            f"Range limit: {limit} with step() call."
                                        )
            elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                if has_exclusion_decorator(node):
                    continue
                for child in ast.walk(node):
                    if isinstance(child, ast.For):
                        limit = get_range_limit(child.iter)
                        if limit is not None and limit > 100:
                            if has_step_call(child.body):
                                violations.append(
                                    f"File: {path.relative_to(ROOT)}\n"
                                    f"Test: {node.name}\n"
                                    f"Range limit: {limit} with step() call."
                                )

    if violations:
        msg = "\n\n".join(violations)
        raise AssertionError(
            f"Found unmarked expensive simulation loops in ordinary tests:\n\n{msg}\n\n"
            f"Please mark these tests with @pytest.mark.slow, @pytest.mark.integration, or @pytest.mark.manual."
        )
