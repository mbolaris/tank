from __future__ import annotations

import subprocess
import sys

from scripts import diagnose


def test_run_checks_keeps_going_after_failure():
    calls: list[str] = []

    def fail():
        calls.append("fail")
        return diagnose.CheckResult("first", False, "broken", "fix it")

    def pass_():
        calls.append("pass")
        return diagnose.CheckResult("second", True, "ok")

    results = diagnose.run_checks([fail, pass_])

    assert calls == ["fail", "pass"]
    assert [result.passed for result in results] == [False, True]


def test_dev_tool_check_reports_missing_module_with_remedy():
    def runner(args):
        assert args == [sys.executable, "-m", "mypy", "--version"]
        return subprocess.CompletedProcess(args, 1, "No module named mypy\n")

    result = diagnose._dev_tool_check("mypy", runner=runner)()

    assert not result.passed
    assert "No module named mypy" in result.detail
    assert result.remedy == "Install developer dependencies with `pip install -e .[dev]`."


def test_frontend_deps_check_reports_install_command(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnose, "REPO_ROOT", tmp_path)

    result = diagnose._frontend_deps_check()

    assert not result.passed
    assert result.remedy == "Run `cd frontend && npm install`."
