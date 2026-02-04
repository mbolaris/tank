from __future__ import annotations

import random

import pytest

from core.code_pool import CodePool, ValidationError


def _make_component(source: str) -> tuple[CodePool, str]:
    pool = CodePool()
    component_id = pool.add_component(
        kind="test_policy",
        name="Test Policy",
        source=source,
        entrypoint="policy",
    )
    return pool, component_id


@pytest.mark.parametrize(
    "source",
    [
        "import os\n\ndef policy(obs, rng):\n    return (1.0, 0.0)\n",
        "def policy(obs, rng):\n    return open('x', 'w')\n",
        "def policy(obs, rng):\n    return eval('1 + 1')\n",
        "def policy(obs, rng):\n    exec('x = 1')\n    return (1.0, 0.0)\n",
        "def policy(obs, rng):\n    return globals()\n",
        "def policy(obs, rng):\n    return (1).__class__\n",
        "def policy(obs, rng):\n    return __import__('os')\n",
    ],
)
def test_rejects_imports_exec_eval_open_and_dunder(source: str) -> None:
    """Test that dangerous code is rejected at add_component time."""
    pool = CodePool()
    with pytest.raises(ValidationError):
        pool.add_component(
            kind="test_policy",
            name="Test Policy",
            source=source,
            entrypoint="policy",
        )


@pytest.mark.parametrize(
    "source",
    [
        "def policy(obs, rng):\n    for i in (1, 2):\n        return (1.0, 0.0)\n",
        "def policy(obs, rng):\n    while False:\n        return (1.0, 0.0)\n",
        "def policy(obs, rng):\n    return [x for x in (1, 2)]\n",
        "def policy(obs, rng):\n    return {x: x for x in (1, 2)}\n",
    ],
)
def test_rejects_loops_and_comprehensions(source: str) -> None:
    """Test that loops and comprehensions are rejected at add_component time."""
    pool = CodePool()
    with pytest.raises(ValidationError):
        pool.add_component(
            kind="test_policy",
            name="Test Policy",
            source=source,
            entrypoint="policy",
        )


def test_allows_basic_policy() -> None:
    pool, component_id = _make_component("def policy(obs, rng):\n    return (1.0, 0.0)\n")
    func = pool.get_callable(component_id)
    assert func is not None
    assert func({}, None) == (1.0, 0.0)


def test_determinism_with_seeded_rng() -> None:
    pool, component_id = _make_component(
        "def policy(obs, rng):\n    return (rng.random(), rng.random())\n"
    )
    func = pool.get_callable(component_id)
    assert func is not None
    rng_a = random.Random(123)
    rng_b = random.Random(123)
    assert func(None, rng_a) == func(None, rng_b)


def test_compile_cache_per_version() -> None:
    pool, component_id = _make_component("def policy(obs, rng):\n    return (1.0, 0.0)\n")
    calls = 0
    original = pool._compile_component

    def counting(component):
        nonlocal calls
        calls += 1
        return original(component)

    pool._compile_component = counting
    pool.compile(component_id)
    pool.compile(component_id)
    assert calls == 1


def test_round_trip_serialization_preserves_ids_and_versions() -> None:
    pool, component_id = _make_component("def policy(obs, rng):\n    return (1.0, 0.0)\n")
    data = pool.to_dict()
    restored = CodePool.from_dict(data)
    component = restored.get_component(component_id)
    assert component.component_id == component_id
    assert component.version == 1
    assert component.source == "def policy(obs, rng):\n    return (1.0, 0.0)\n"
