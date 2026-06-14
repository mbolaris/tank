"""Metrics history buffer for tracking poker and soccer skill over time."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Bumped to 2 when per-trait means ("traits") were added to each sample so the
# running UI/API can show directional selection over time, not just churn.
SCHEMA_VERSION = 2


def get_val(obj: Any, attr: str, default: Any = 0) -> Any:
    """Safely get value from dictionary or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


class MetricsHistory:
    """Ring buffer for simulation metrics history."""

    def __init__(
        self,
        world_id: str | None = None,
        sample_interval_frames: int = 500,
        max_samples: int = 2000,
    ) -> None:
        self.schema_version = SCHEMA_VERSION
        self.world_id = world_id or "unknown"
        self.sample_interval_frames = sample_interval_frames
        self.max_samples = max_samples
        self.samples: list[dict[str, Any]] = []

        # Cumulative soccer counters
        self.soccer_goals_total = 0
        self.soccer_matches_completed = 0
        self.soccer_matches_skipped = 0
        self.processed_soccer_match_ids: set[str] = set()

    def is_sample_due(self, frame: int) -> bool:
        """Whether ``frame`` lands on a sampling boundary.

        Exposed so callers can compute expensive per-sample data (e.g. trait
        means over the live population) only on frames that will be recorded,
        rather than on every stats collection.
        """
        return frame > 0 and frame % self.sample_interval_frames == 0

    def maybe_sample(
        self,
        frame: int,
        stats: Any,
        poker: Any,
        soccer: Any,
        auto_eval: Any,
        trait_means: dict[str, float] | None = None,
    ) -> None:
        """Sample metrics if the frame interval is reached.

        ``trait_means`` is an optional mapping of heritable trait key -> current
        population mean (see ``core.services.stats.trait_trends``). It is stored
        under ``"traits"`` so the history exposes directional selection over
        time. When omitted (or empty) the field is recorded as ``{}``.
        """
        # 1. Update cumulative soccer counters from the events list passed
        if soccer:
            for event in soccer:
                match_id = get_val(event, "match_id", None)
                if not match_id or match_id in self.processed_soccer_match_ids:
                    continue

                self.processed_soccer_match_ids.add(match_id)

                score_left = get_val(event, "score_left", 0)
                score_right = get_val(event, "score_right", 0)
                skipped = get_val(event, "skipped", False)

                self.soccer_goals_total += score_left + score_right
                if skipped:
                    self.soccer_matches_skipped += 1
                else:
                    self.soccer_matches_completed += 1

        # 2. Check if we should record a sample for this frame
        if frame > 0 and frame % self.sample_interval_frames == 0:
            # Avoid duplicate samples for the same frame
            if not self.samples or self.samples[-1]["frame"] < frame:
                # Extract poker ELO
                auto_eval_elo = 1200.0
                if stats is not None:
                    poker_elo = get_val(stats, "poker_elo", None)
                    if poker_elo is not None:
                        auto_eval_elo = poker_elo

                # Extract poker stats
                poker_total_games = 0
                poker_showdown_win_rate = 0.0
                poker_net_energy = 0.0
                if poker is not None:
                    poker_total_games = get_val(poker, "total_games", 0)
                    poker_net_energy = get_val(poker, "net_energy", 0.0)

                    raw_win_rate = get_val(poker, "showdown_win_rate", "0.0%")
                    if isinstance(raw_win_rate, str):
                        try:
                            poker_showdown_win_rate = float(raw_win_rate.rstrip("%")) / 100.0
                        except ValueError:
                            poker_showdown_win_rate = 0.0
                    elif isinstance(raw_win_rate, (int, float)):
                        poker_showdown_win_rate = float(raw_win_rate)

                goals_per_1k_frames = (
                    (self.soccer_goals_total / frame) * 1000.0 if frame > 0 else 0.0
                )

                sample = {
                    "frame": frame,
                    "max_generation": get_val(stats, "max_generation", 0),
                    "population": get_val(stats, "population", 0),
                    "births_total": get_val(stats, "births", 0),
                    "deaths_total": get_val(stats, "deaths", 0),
                    "fish_energy": round(get_val(stats, "fish_energy", 0.0), 2),
                    "poker": {
                        "auto_eval_elo": round(auto_eval_elo, 2),
                        "total_games": poker_total_games,
                        "showdown_win_rate": round(poker_showdown_win_rate, 4),
                        "net_energy_total": round(poker_net_energy, 2),
                    },
                    "soccer": {
                        "goals_total": self.soccer_goals_total,
                        "goals_per_1k_frames": round(goals_per_1k_frames, 4),
                        "matches_completed": self.soccer_matches_completed,
                        "matches_skipped": self.soccer_matches_skipped,
                        "baseline_match_score_diff": None,
                    },
                    "diversity_score": round(get_val(stats, "diversity_score", 0.0), 4),
                    "traits": dict(trait_means) if trait_means else {},
                }

                self.samples.append(sample)

                # Keep buffer within capacity
                if len(self.samples) > self.max_samples:
                    self.samples.pop(0)

    def to_payload(self) -> dict[str, Any]:
        """Convert metrics history to a serializable dictionary."""
        return {
            "schema_version": self.schema_version,
            "world_id": self.world_id,
            "sample_interval_frames": self.sample_interval_frames,
            "max_samples": self.max_samples,
            "samples": self.samples,
            # State fields needed to resume cumulative counting
            "_soccer_goals_total": self.soccer_goals_total,
            "_soccer_matches_completed": self.soccer_matches_completed,
            "_soccer_matches_skipped": self.soccer_matches_skipped,
            "_processed_soccer_match_ids": list(self.processed_soccer_match_ids),
        }

    def load(self, payload: dict[str, Any] | None) -> None:
        """Load history from a payload, tolerating old/invalid formats."""
        if not payload or not isinstance(payload, dict):
            logger.info("MetricsHistory: missing or invalid payload, starting empty.")
            return

        try:
            self.schema_version = payload.get("schema_version", SCHEMA_VERSION)
            self.world_id = payload.get("world_id", self.world_id)
            self.sample_interval_frames = payload.get(
                "sample_interval_frames", self.sample_interval_frames
            )
            self.max_samples = payload.get("max_samples", self.max_samples)
            self.samples = payload.get("samples", [])

            # Reload accumulators
            self.soccer_goals_total = payload.get("_soccer_goals_total", 0)
            self.soccer_matches_completed = payload.get("_soccer_matches_completed", 0)
            self.soccer_matches_skipped = payload.get("_soccer_matches_skipped", 0)
            self.processed_soccer_match_ids = set(payload.get("_processed_soccer_match_ids", []))
            logger.info(
                f"MetricsHistory: loaded {len(self.samples)} samples for world {self.world_id}"
            )
        except Exception as e:
            logger.warning(f"MetricsHistory: failed to load payload due to {e}. Starting empty.")
