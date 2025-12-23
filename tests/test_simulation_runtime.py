import random
from typing import List, Tuple

from core.simulation_engine import SimulationEngine
from core.simulation_runtime import SimulationRuntime, SimulationRuntimeConfig, SystemRegistry
from core.systems.base import BaseSystem, SystemResult


class RecordingSystem(BaseSystem):
    def __init__(self, engine, name: str, log: List[Tuple[int, str]]):
        super().__init__(engine, name)
        self._log = log

    def _do_update(self, frame: int) -> SystemResult:
        self._log.append((frame, self.name))
        return SystemResult.empty()


class StubRegistry(SystemRegistry):
    def __init__(self, engine, context, config, log):
        super().__init__(engine, context, config)
        self._log = log
        self.build_default_systems()

    @property
    def should_run_registered_systems(self) -> bool:
        return True

    def build_default_systems(self) -> None:
        self.systems = [
            RecordingSystem(self.engine, "alpha", self._log),
            RecordingSystem(self.engine, "beta", self._log),
            RecordingSystem(self.engine, "gamma", self._log),
        ]


def test_registered_systems_run_in_order():
    log: List[Tuple[int, str]] = []

    def factory(engine, context, config):
        return StubRegistry(engine, context, config, log)

    runtime = SimulationRuntime(
        SimulationRuntimeConfig(seed=123, headless=True, rng=random.Random(5)),
        registry_factory=factory,
    )
    engine = SimulationEngine(runtime=runtime)
    engine.setup()

    engine.update()
    engine.update()

    assert log == [
        (1, "alpha"),
        (1, "beta"),
        (1, "gamma"),
        (2, "alpha"),
        (2, "beta"),
        (2, "gamma"),
    ]
