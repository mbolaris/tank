from backend.simulation_runner import SimulationRunner
from core.entities.ball import Ball
from core.entities.goal_zone import GoalZone


class TestTankSoccerToggle:
    def test_toggle_adds_removes_entities(self):
        # Create runner (it creates the world internally)
        runner = SimulationRunner(seed=42, world_type="tank")
        adapter = runner.world
        # Adapter is already reset by runner.__init__ -> create_world -> reset

        # Ensure initial state has no soccer elements (assuming standard config)
        # Note: If TankPack default adds them, this check verifies they exist/don't exist
        # But we'll force disable first to be sure
        runner._cmd_set_tank_soccer_enabled({"enabled": False})

        # FORCE MUTATIONS to clear initial state
        adapter.engine._apply_entity_mutations("test_force_initial_clear")

        balls = [e for e in adapter.engine.entities_list if isinstance(e, Ball)]
        goals = [e for e in adapter.engine.entities_list if isinstance(e, GoalZone)]
        assert len(balls) == 0
        assert len(goals) == 0

        # ENABLE
        resp = runner._cmd_set_tank_soccer_enabled({"enabled": True})
        assert resp["success"] is True
        assert resp["enabled"] is True

        # FORCE MUTATIONS (spawns are queued)
        adapter.engine._apply_entity_mutations("test_force_enable")

        # Verify entities added
        balls = [e for e in adapter.engine.entities_list if isinstance(e, Ball)]
        goals = [e for e in adapter.engine.entities_list if isinstance(e, GoalZone)]
        assert len(balls) == 1
        assert len(goals) == 2

        # Verify environment references
        assert adapter.engine.environment.ball is not None
        assert adapter.engine.environment.goal_manager is not None
        assert adapter.engine.soccer_system.enabled is True

        # DISABLE
        resp = runner._cmd_set_tank_soccer_enabled({"enabled": False})
        assert resp["success"] is True
        assert resp["enabled"] is False

        # FORCE MUTATIONS (removals are queued)
        adapter.engine._apply_entity_mutations("test_force_disable")

        balls = [e for e in adapter.engine.entities_list if isinstance(e, Ball)]
        goals = [e for e in adapter.engine.entities_list if isinstance(e, GoalZone)]
        assert len(balls) == 0
        assert len(goals) == 0

        # Verify environment references cleared
        assert adapter.engine.environment.ball is None
        assert adapter.engine.environment.goal_manager is None
        assert adapter.engine.soccer_system.enabled is False
