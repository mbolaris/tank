"""Smoke tests for the one-command launcher (start.py).

These intentionally do NOT spawn the servers — they only exercise the pure
helper logic so CI stays fast and side-effect free.
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
START_PATH = REPO_ROOT / "start.py"


def _load_start():
    spec = importlib.util.spec_from_file_location("start_launcher", START_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def start():
    return _load_start()


def test_urls_and_paths_are_sane(start):
    assert start.BACKEND_URL.endswith(":8000")
    assert start.FRONTEND_URL.endswith(":3000")
    assert start.FRONTEND_DIR.name == "frontend"
    assert start.REPO_ROOT == REPO_ROOT


def test_backend_only_preflight_always_ok(start):
    """--backend-only must never be blocked by missing Node tooling."""
    assert start._preflight(backend_only=True) is True


def test_color_helper_respects_toggle(start, monkeypatch):
    # When color is disabled, text passes through unchanged.
    monkeypatch.setattr(start, "_COLOR", False)
    assert start._c("32", "hello") == "hello"
    # When enabled, it wraps in ANSI codes.
    monkeypatch.setattr(start, "_COLOR", True)
    assert "\033[32m" in start._c("32", "hello")
