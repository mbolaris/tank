import time

from backend.simulation_runner import SimulationRunner


def _wait_until(predicate, *, timeout_s: float = 2.0, poll_s: float = 0.01) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(poll_s)
    return False


def test_mode_switch_is_thread_safe_while_running():
    runner = SimulationRunner(world_type="tank", seed=42)
    runner.start(start_paused=False)

    try:
        assert _wait_until(lambda: runner.frame_count >= 2), "Runner did not advance frames"

        with runner.lock:
            entity_ids_before = {id(e) for e in runner.world.entities_list}
        assert entity_ids_before, "Expected at least one entity before mode switch"
        assert runner.world.is_paused is False

        runner.switch_world_type("petri")
        assert runner.running is True
        assert runner.thread is not None and runner.thread.is_alive()
        assert runner.world_type == "petri"
        assert runner.world.is_paused is False

        # Ensure pause state is preserved across switches too
        runner.world.set_paused(True)
        runner.switch_world_type("tank")
        assert runner.world_type == "tank"
        assert runner.world.is_paused is True

        with runner.lock:
            entity_ids_after = {id(e) for e in runner.world.entities_list}

        assert entity_ids_before == entity_ids_after, "Entity instances changed during mode switch"
    finally:
        runner.stop()
