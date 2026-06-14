"""Per-frame stats and entity-snapshot collection.

Extracted from SimulationRunner verbatim. The runner keeps thin
``_collect_stats()`` / ``_collect_entities()`` facades that delegate here
(StatePublisher calls them through the runner), so test monkeypatch points
are unchanged.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from backend.runner.state_builders import (
    build_base_stats,
    build_energy_stats,
    build_meta_stats,
    build_physical_stats,
    collect_poker_stats_payload,
)
from backend.state_payloads import EntitySnapshot, StatsPayload
from core.worlds.interfaces import StepResult

if TYPE_CHECKING:
    from backend.simulation_runner import SimulationRunner


def collect_entities(runner: SimulationRunner) -> list[EntitySnapshot]:
    """Collect entity snapshots for rendering/broadcast."""
    # Optimization: Use fast path if available (e.g. from C++ backend or optimized step result)
    get_step_result = getattr(runner.world, "get_last_step_result", None)
    if callable(get_step_result):
        step_result = get_step_result()
        if step_result is not None:
            return runner._entity_snapshot_builder.build(step_result, runner.world)

    # Prefer the builder's world-aware build() path so it can use the engine's
    # identity provider (canonical source for stable IDs).
    snapshots = runner._entity_snapshot_builder.build(
        StepResult(snapshot=runner.world.get_current_snapshot()),
        runner.world,
    )

    # OPTIMIZATION: Post-process snapshots to strip heavy fields not needed for WebSocket visualization
    # This bypasses potential hot-reload issues with the snapshot builder itself
    for s in snapshots:
        gd = s.genome_data
        if gd:
            if "trait_meta" in gd:
                del gd["trait_meta"]
            if "poker_strategy" in gd:
                del gd["poker_strategy"]
            if (
                "behavior" in gd
                and isinstance(gd["behavior"], dict)
                and "parameters" in gd["behavior"]
            ):
                del gd["behavior"]["parameters"]

    return snapshots


def collect_stats(
    runner: SimulationRunner, frame: int, include_distributions: bool = True
) -> StatsPayload:
    """Collect and organize simulation statistics."""
    # Use getattr/call to handle potential interface mismatches if world hasn't been updated
    get_stats = runner.world.get_stats
    compute_distributions = include_distributions
    if include_distributions and runner._distribution_interval_seconds > 0:
        now = time.perf_counter()
        if (now - runner._last_distribution_time) < runner._distribution_interval_seconds:
            compute_distributions = False
    else:
        now = time.perf_counter()
    try:
        stats = get_stats(include_distributions=compute_distributions)
    except TypeError:
        # Fallback for worlds that don't support include_distributions yet
        stats = get_stats()
        compute_distributions = True

    if compute_distributions:
        runner._cached_gene_distributions = stats.get("gene_distributions", {})
        runner._last_distribution_time = now
    elif runner._cached_gene_distributions:
        stats["gene_distributions"] = runner._cached_gene_distributions

    # Get Poker Score from evolution benchmark tracker
    poker_score: Any = None
    poker_score_history: list[float] = []
    if runner.evolution_benchmark_tracker is not None:
        latest = runner.evolution_benchmark_tracker.get_latest_snapshot()
        if latest is not None and latest.confidence_vs_strong is not None:
            poker_score = latest.confidence_vs_strong
        history = runner.evolution_benchmark_tracker.get_history()
        if history:
            valid_scores = [
                s.confidence_vs_strong for s in history if s.confidence_vs_strong is not None
            ]
            poker_score_history = valid_scores[-20:]

    # Get Poker Elo from evolution benchmark tracker
    poker_elo: Any = None
    poker_elo_history: list[float] = []
    if runner.evolution_benchmark_tracker is not None:
        latest = runner.evolution_benchmark_tracker.get_latest_snapshot()
        if latest is not None and latest.pop_mean_elo is not None:
            poker_elo = latest.pop_mean_elo
        history = runner.evolution_benchmark_tracker.get_history()
        if history:
            valid_elos = [s.pop_mean_elo for s in history if s.pop_mean_elo is not None]
            poker_elo_history = valid_elos[-20:]

    # Build stat components using helper functions
    base_stats = build_base_stats(stats, frame, runner.current_actual_fps, runner.fast_forward)
    energy_stats = build_energy_stats(
        stats,
        poker_score,
        poker_score_history,
        poker_elo,
        poker_elo_history,
    )
    physical_stats = build_physical_stats(stats)
    meta_stats = build_meta_stats(stats)
    poker_stats = collect_poker_stats_payload(stats)

    stats_payload = StatsPayload(
        **base_stats,
        **energy_stats,
        **physical_stats,
        poker_stats=poker_stats,
        meta_stats=meta_stats,
        diversity_score=stats.get("diversity_stats", {}).get("diversity_score", 0.0),
    )

    if hasattr(runner, "metrics_history") and runner.metrics_history is not None:
        # Collect soccer events if hooks are present
        soccer_events = []
        if hasattr(runner.world_hooks, "collect_soccer_events"):
            try:
                soccer_events = runner.world_hooks.collect_soccer_events(runner) or []
            except Exception:
                pass

        # Collect auto-eval if hooks are present
        auto_eval = None
        if hasattr(runner.world_hooks, "collect_auto_eval"):
            try:
                auto_eval = runner.world_hooks.collect_auto_eval(runner)
            except Exception:
                pass

        # Trait means are only meaningful (and only worth iterating fish for) on
        # frames that will actually be recorded as a sample.
        trait_means = None
        if runner.metrics_history.is_sample_due(frame):
            trait_means = _collect_trait_means(runner)

        runner.metrics_history.maybe_sample(
            frame=frame,
            stats=stats_payload,
            poker=poker_stats,
            soccer=soccer_events,
            auto_eval=auto_eval,
            trait_means=trait_means,
        )

    return stats_payload


def _collect_trait_means(runner: SimulationRunner) -> dict[str, float]:
    """Population mean of the tracked heritable traits across living fish.

    Read-only and defensive: any failure (e.g. a non-tank world without an
    ``entities_list``) yields an empty mapping rather than disturbing the step
    loop or stats collection.
    """
    try:
        from core.entities import Fish
        from core.services.stats.trait_trends import compute_trait_means

        entities = getattr(runner.world, "entities_list", None)
        if not entities:
            return {}
        living = [e for e in entities if isinstance(e, Fish) and not e.is_dead()]
        return compute_trait_means(living)
    except Exception:
        return {}
