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
