"""Tests for the EnginePipeline abstraction.

These tests verify that:
1. The default pipeline has the correct step names in canonical order
2. Executing the pipeline advances frame count as expected
3. Custom pipelines can be created and used
"""


def test_default_pipeline_step_names() -> None:
    """Assert that tank's pipeline step names match the canonical list."""
    from core.simulation.pipeline import default_pipeline

    pipeline = default_pipeline()
    expected = [
        "frame_start",
        "time_update",
        "environment",
        "entity_act",
        "lifecycle",
        "spawn",
        "collision",
        "soccer",
        "interaction",
        "reproduction",
        "frame_end",
    ]
    assert pipeline.step_names == expected


def test_pipeline_run_advances_frame() -> None:
    """Assert that executing the pipeline advances frame count."""
    from core.config.simulation_config import SimulationConfig
    from core.simulation.engine import SimulationEngine

    engine = SimulationEngine(config=SimulationConfig.headless_fast())
    engine.setup()

    initial_frame = engine.frame_count
    engine.update()
    assert engine.frame_count == initial_frame + 1


def test_pipeline_is_wired_after_setup() -> None:
    """Assert that the pipeline is properly set after setup()."""
    from core.config.simulation_config import SimulationConfig
    from core.simulation.engine import SimulationEngine
    from core.simulation.pipeline import EnginePipeline

    engine = SimulationEngine(config=SimulationConfig.headless_fast())

    # Before setup, pipeline should be None
    assert engine.pipeline is None

    engine.setup()

    # After setup, pipeline should be an EnginePipeline instance
    assert engine.pipeline is not None
    assert isinstance(engine.pipeline, EnginePipeline)


def test_custom_pipeline_can_be_created() -> None:
    """Assert that custom pipelines can be created with subset of steps."""
    from core.simulation.pipeline import EnginePipeline, PipelineStep

    def noop_step(engine, ctx) -> None:
        pass

    custom_pipeline = EnginePipeline(
        [
            PipelineStep("step_a", noop_step),
            PipelineStep("step_b", noop_step),
        ]
    )

    assert custom_pipeline.step_names == ["step_a", "step_b"]
    assert len(custom_pipeline.steps) == 2


def test_pipeline_step_execution_order() -> None:
    """Assert that pipeline steps are executed in order."""
    from core.simulation.pipeline import EnginePipeline, PipelineStep

    execution_order: list[str] = []

    def make_step(name: str):
        def step_fn(engine, ctx) -> None:
            execution_order.append(name)

        return step_fn

    pipeline = EnginePipeline(
        [
            PipelineStep("first", make_step("first")),
            PipelineStep("second", make_step("second")),
            PipelineStep("third", make_step("third")),
        ]
    )

    # Create a minimal mock engine (steps don't use it in this test)
    class MockEngine:
        pass

    pipeline.run(MockEngine())  # type: ignore

    assert execution_order == ["first", "second", "third"]
