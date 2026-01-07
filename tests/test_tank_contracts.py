"""Tests for tank action/observation contracts.

These tests verify the core contracts and tank-specific adapters work correctly.
"""

import random

import pytest

from core.brains.contracts import BrainAction, BrainObservation, WorldTickResult

# Use the canonical names in tests (backward-compat aliases still work)
Action = BrainAction
Observation = BrainObservation
from core.worlds.tank import TankWorldBackendAdapter


class TestContracts:
    """Test core contract dataclasses."""

    def test_observation_has_required_fields(self):
        """Observation should have all required fields."""
        obs = Observation(
            entity_id="fish_1",
            position=(100.0, 200.0),
            velocity=(1.0, 2.0),
            energy=50.0,
            max_energy=100.0,
            age=100,
            frame=42,
        )

        assert obs.entity_id == "fish_1"
        assert obs.position == (100.0, 200.0)
        assert obs.velocity == (1.0, 2.0)
        assert obs.energy == 50.0
        assert obs.max_energy == 100.0
        assert obs.age == 100
        assert obs.frame == 42
        assert obs.nearby_food == []
        assert obs.nearby_fish == []
        assert obs.nearby_threats == []
        assert obs.extra == {}

    def test_observation_is_immutable(self):
        """Observation should be frozen (immutable)."""
        obs = Observation(
            entity_id="fish_1",
            position=(100.0, 200.0),
            velocity=(1.0, 2.0),
            energy=50.0,
            max_energy=100.0,
            age=100,
        )

        with pytest.raises(AttributeError):
            obs.energy = 75.0  # type: ignore

    def test_action_has_required_fields(self):
        """Action should have all required fields."""
        action = Action(
            entity_id="fish_1",
            target_velocity=(1.5, -0.5),
        )

        assert action.entity_id == "fish_1"
        assert action.target_velocity == (1.5, -0.5)
        assert action.extra == {}

    def test_action_is_immutable(self):
        """Action should be frozen (immutable)."""
        action = Action(entity_id="fish_1")

        with pytest.raises(AttributeError):
            action.entity_id = "fish_2"  # type: ignore

    def test_world_tick_result_is_mutable(self):
        """WorldTickResult should be mutable for building results."""
        result = WorldTickResult()
        result.events.append({"type": "test"})
        result.metrics["count"] = 5
        result.info["frame"] = 1

        assert len(result.events) == 1
        assert result.metrics["count"] == 5
        assert result.info["frame"] == 1


class TestObservationBuilder:
    """Test observation builder for Tank world."""

    def test_observation_builder_produces_stable_fields(self):
        """Observation builder should produce observations with all fields."""
        from core.worlds.tank.observation_builder import build_tank_observations

        adapter = TankWorldBackendAdapter(seed=42)
        adapter.reset(seed=42)

        # Let a few ticks run to ensure fish are active
        for _ in range(10):
            adapter.step()

        # The adapter itself is the world interface now
        observations = build_tank_observations(adapter)

        # Should have at least one fish observation
        assert len(observations) > 0

        # Check first observation has all required fields
        first_obs = next(iter(observations.values()))
        assert first_obs.entity_id is not None
        assert isinstance(first_obs.position, tuple)
        assert len(first_obs.position) == 2
        assert isinstance(first_obs.velocity, tuple)
        assert len(first_obs.velocity) == 2
        assert first_obs.energy >= 0
        assert first_obs.max_energy > 0
        assert first_obs.age >= 0
        assert first_obs.frame >= 0
        assert isinstance(first_obs.nearby_food, list)
        assert isinstance(first_obs.nearby_fish, list)
        assert isinstance(first_obs.nearby_threats, list)


class TestActionBridge:
    """Test action bridge adapter."""

    def test_action_bridge_produces_actions_for_fish(self):
        """Action bridge should produce actions for each fish in observations."""
        from core.worlds.tank.action_bridge import decide_actions
        from core.worlds.tank.observation_builder import build_tank_observations

        adapter = TankWorldBackendAdapter(seed=42)
        adapter.reset(seed=42)

        # Run some ticks to let fish make decisions
        for _ in range(10):
            adapter.step()

        # The adapter itself is the world interface now
        observations = build_tank_observations(adapter)
        actions = decide_actions(observations, adapter, rng=random.Random(42))

        # Should have an action for each observation
        assert len(actions) == len(observations)

        # Each action should match an observation
        for entity_id, action in actions.items():
            assert entity_id in observations
            assert action.entity_id == entity_id
            assert isinstance(action.target_velocity, tuple)
            assert len(action.target_velocity) == 2

    def test_action_velocities_match_fish_velocities(self):
        """Action velocities should match actual fish velocities."""
        from core.entities import Fish
        from core.worlds.tank.action_bridge import decide_actions
        from core.worlds.tank.observation_builder import build_tank_observations

        adapter = TankWorldBackendAdapter(seed=42)
        adapter.reset(seed=42)

        # Run simulation
        for _ in range(20):
            adapter.step()

        # The adapter itself is the world interface now
        observations = build_tank_observations(adapter)
        actions = decide_actions(observations, adapter, rng=random.Random(42))

        # Build fish lookup
        fish_by_id = {}
        for entity in adapter.entities_list:
            if isinstance(entity, Fish):
                fish_by_id[str(entity.fish_id)] = entity

        # Verify velocities match
        for entity_id, action in actions.items():
            fish = fish_by_id.get(entity_id)
            assert fish is not None
            assert action.target_velocity[0] == fish.vel.x
            assert action.target_velocity[1] == fish.vel.y
