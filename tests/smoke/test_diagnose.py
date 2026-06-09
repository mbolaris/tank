"""Smoke tests for the environment diagnostic tool (scripts/diagnose.py)."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DIAGNOSE_PATH = REPO_ROOT / "scripts" / "diagnose.py"


def _load_diagnose():
    spec = importlib.util.spec_from_file_location("diagnose", DIAGNOSE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve the module by name.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def diagnose():
    return _load_diagnose()


def test_core_checks_pass_in_dev_env(diagnose):
    """The checks that must hold in any working install should report OK."""
    required_checks = [
        diagnose.check_python_version,
        diagnose.check_dependencies,
        diagnose.check_core_imports,
        diagnose.check_algorithm_registry,
        diagnose.check_simulation_smoke,
    ]
    for check in required_checks:
        result = check()
        assert result.status in (
            diagnose.OK,
            diagnose.WARN,
        ), f"{check.__name__} unexpectedly failed: {result.detail}"
        assert result.title
        assert result.status != diagnose.FAIL


def test_simulation_smoke_reports_live_fish(diagnose):
    result = diagnose.check_simulation_smoke(frames=10)
    assert result.status == diagnose.OK
    assert "fish alive" in result.detail


def test_runner_returns_zero_when_core_healthy(diagnose):
    """The full runner should exit 0 (warnings are non-fatal)."""
    style = diagnose.Style(enabled=False)
    assert diagnose.run_diagnostics(style) == 0


def test_every_check_is_resilient(diagnose):
    """No check should raise; each must return a Result."""
    for check in diagnose.CHECKS:
        result = check()
        assert isinstance(result, diagnose.Result)
        assert result.status in (diagnose.OK, diagnose.WARN, diagnose.FAIL)
