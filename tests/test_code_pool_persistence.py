"""Tests for CodePool persistence across tank snapshot save/load cycles."""

from __future__ import annotations

import random

import pytest

from core.code_pool import (
    BUILTIN_SEEK_NEAREST_FOOD_ID,
    CodePool,
    ValidationError,
    seek_nearest_food_policy,
)


def test_round_trip_with_custom_component():
    """Test that custom code components survive serialization."""
    pool = CodePool()
    
    # Register builtin
    pool.register(BUILTIN_SEEK_NEAREST_FOOD_ID, seek_nearest_food_policy)
    
    # Add a custom component
    component_id = pool.add_component(
        kind="movement_policy",
        name="Custom Policy",
        source="def policy(obs, rng):\n    return (0.5, 0.5)\n",
        entrypoint="policy",
    )
    
    # Serialize
    data = pool.to_dict()
    
    # Restore
    restored = CodePool.from_dict(data)
    
    # Re-register builtin (these are not serialized)
    restored.register(BUILTIN_SEEK_NEAREST_FOOD_ID, seek_nearest_food_policy)
    
    # Verify builtin works
    builtin_func = restored.get_callable(BUILTIN_SEEK_NEAREST_FOOD_ID)
    assert builtin_func is not None
    
    # Verify custom component works
    custom_func = restored.get_callable(component_id)
    assert custom_func is not None
    assert custom_func({}, None) == (0.5, 0.5)


def test_get_callable_returns_none_for_missing():
    """Test that get_callable returns None for missing components."""
    pool = CodePool()
    result = pool.get_callable("nonexistent_id")
    assert result is None


def test_builtin_not_serialized():
    """Test that builtin policies are not serialized but still work."""
    pool = CodePool()
    pool.register(BUILTIN_SEEK_NEAREST_FOOD_ID, seek_nearest_food_policy)
    
    # Serialize
    data = pool.to_dict()
    
    # Builtins should not appear in components list
    assert len(data["components"]) == 0
    
    # But get_callable should still work
    func = pool.get_callable(BUILTIN_SEEK_NEAREST_FOOD_ID)
    assert func is not None


def test_fallback_when_component_compilation_fails():
    """Test graceful handling of broken components."""
    pool = CodePool()
    
    # Add a component that will fail validation when compiled due to loop
    component_id = pool.add_component(
        kind="movement_policy",
        name="Broken Policy",
        source="def policy(obs, rng):\n    for i in range(10):\n        pass\n    return (0.0, 0.0)\n",
        entrypoint="policy",
    )
    
    # Compile should raise ValidationError
    with pytest.raises(ValidationError):
        pool.get_callable(component_id)


def test_determinism_compilation_no_global_state():
    """Test that compilation doesn't mutate global random state."""
    # Save global random state
    global_state_before = random.getstate()
    
    pool = CodePool()
    component_id = pool.add_component(
        kind="test",
        name="Test",
        source="def policy(obs, rng):\n    return (1.0, 0.0)\n",
        entrypoint="policy",
    )
    
    # Compile
    pool.compile(component_id)
    
    # Global random state should be unchanged
    global_state_after = random.getstate()
    assert global_state_before == global_state_after


def test_register_overwrites_previous():
    """Test that re-registering a builtin replaces the old one."""
    pool = CodePool()
    
    # Register twice with different functions
    pool.register("test_id", lambda obs, rng: (0.0, 0.0))
    pool.register("test_id", lambda obs, rng: (1.0, 1.0))
    
    # Should use the second one
    func = pool.get_callable("test_id")
    assert func({}, None) == (1.0, 1.0)
