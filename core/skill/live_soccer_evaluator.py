"""Incremental live soccer ladder evaluator for evolving tank worlds.

Periodically evaluates copies of the live tank's top fish genomes against the
frozen L0-L3 reference ladder using the SoccerMatch incremental pattern.
Evaluations do NOT consume engine RNG or spend fish energy.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from core.code_pool import GenomeCodePool, create_default_genome_code_pool
from core.genetics import Genome
from core.genetics.trait import GeneticTrait
from core.minigames.soccer.league_runtime import BotEntity
from core.minigames.soccer.match import SoccerMatch
from core.minigames.soccer.reference_teams import (
    REFERENCE_LADDER,
    ReferenceTeam,
    register_reference_policies,
)
from core.minigames.soccer.seeds import derive_soccer_seed
from core.skill.ladder import RungResult, SkillLadderSummary, ladder_position_index
from core.skill.snapshots import SkillSnapshot, SkillSnapshotStore

if TYPE_CHECKING:
    from core.simulation.engine import SimulationEngine

logger = logging.getLogger(__name__)


@dataclass
class MatchSpec:
    rung_id: str
    rung_name: str
    team: ReferenceTeam
    match_seed: int
    hero_on_left: bool


class IncrementalSoccerLadderEvaluator:
    """Evaluates top live fish against frozen soccer rulers incrementally.

    Performs bounded per-frame work (stepping one SoccerMatch) so continuous
    simulations never experience frame drops during a 45s ladder pass.
    """

    def __init__(
        self,
        store: SkillSnapshotStore | None = None,
        *,
        eval_interval_frames: int = 20_000,
        n_seeds: int = 3,
        frames_per_match: int = 5000,
        team_size: int = 3,
        cycles_per_frame: int = 1,
    ) -> None:
        self.store = store if store is not None else SkillSnapshotStore()
        self.eval_interval_frames = eval_interval_frames
        self.n_seeds = n_seeds
        self.frames_per_match = frames_per_match
        self.team_size = team_size
        self.cycles_per_frame = cycles_per_frame

        self.last_eval_start_frame: int = 0
        self.eval_counter: int = 0
        self.active: bool = False

        # Internal state during an active evaluation pass
        self._current_eval_frame: int = 0
        self._current_generation: int = 0
        self._subject_fish_ids: list[int] = []
        self._subject_lineage_ids: list[str] = []
        self._hero_genomes: list[Genome] = []

        self._pending_matches: list[MatchSpec] = []
        self._completed_matches: list[dict[str, Any]] = []
        self._active_match: SoccerMatch | None = None
        self._active_spec: MatchSpec | None = None
        self._code_pool: GenomeCodePool | None = None

        # Cached goal diff vs top unbeaten rung (populated after each pass)
        self._latest_baseline_score_diff: float | None = None

    @property
    def latest_baseline_score_diff(self) -> float | None:
        """Goal difference vs the top unbeaten rung from the latest evaluation."""
        return self._latest_baseline_score_diff

    def _ensure_code_pool(self) -> GenomeCodePool:
        if self._code_pool is None:
            self._code_pool = create_default_genome_code_pool()
            register_reference_policies(self._code_pool)
        return self._code_pool

    def _get_top_fish(self, engine: SimulationEngine) -> list[Any]:
        """Select top fish by existing soccer stats, energy, and generation."""
        fish_list = engine._entity_manager.get_fish()
        if not fish_list:
            return []

        soccer_events = getattr(engine, "soccer_events", None)
        fish_stats_map: dict[int, Any] = {}
        if soccer_events is not None and hasattr(soccer_events, "_fish_stats"):
            fish_stats_map = getattr(soccer_events._fish_stats, "_stats", {})

        def sort_key(f: Any) -> tuple[float, float, int, int]:
            fid = getattr(f, "fish_id", 0)
            stats = fish_stats_map.get(fid)
            score = stats.contribution_score if stats is not None else 0.0
            energy = getattr(f, "energy", 0.0)
            gen = getattr(f, "generation", 0)
            return (score, energy, gen, fid)

        sorted_fish = sorted(fish_list, key=sort_key, reverse=True)
        return sorted_fish[: self.team_size]

    def _build_hero_genomes(self, fish_team: list[Any]) -> list[Genome]:
        """Create genome copies of the selected fish team."""
        genomes: list[Genome] = []
        for fish in fish_team:
            g = getattr(fish, "genome", None)
            if g is not None:
                genomes.append(copy.deepcopy(g))

        # Pad team if fewer than team_size fish available
        while len(genomes) < self.team_size:
            if genomes:
                genomes.append(copy.deepcopy(genomes[0]))
            else:
                default_id = self._ensure_code_pool().get_default("soccer_policy")
                g = Genome.random(use_algorithm=False, rng=None)
                g.behavioral.soccer_policy_id = GeneticTrait(default_id)
                from core.code_pool import default_soccer_policy_params

                g.behavioral.soccer_policy_params = GeneticTrait(
                    default_soccer_policy_params(default_id)
                )
                genomes.append(g)

        return genomes[: self.team_size]

    def tick(self, engine: SimulationEngine) -> None:
        """Advance evaluation by one world frame."""
        server_cfg = getattr(getattr(engine, "config", None), "server", None)
        enabled = getattr(server_cfg, "soccer_ladder_eval_enabled", True)
        if not enabled:
            return

        interval = getattr(
            server_cfg, "soccer_ladder_eval_interval_frames", self.eval_interval_frames
        )
        frame = engine.frame_count

        # Check whether to start a new ladder pass
        if not self.active:
            if frame > 0 and (frame - self.last_eval_start_frame) >= interval:
                top_fish = self._get_top_fish(engine)
                if not top_fish:
                    return

                self._start_evaluation(engine, frame, top_fish)
            return

        # Step active match if one exists
        if self._active_match is not None and self._active_spec is not None:
            self._active_match.step(num_steps=self.cycles_per_frame)

            if self._active_match.game_over:
                self._record_match_result()
                self._active_match = None
                self._active_spec = None

        # If no active match, start next match or finalize evaluation pass
        if self._active_match is None:
            if self._pending_matches:
                self._start_next_match(engine)
            else:
                self._finalize_evaluation()

    def _start_evaluation(self, engine: SimulationEngine, frame: int, top_fish: list[Any]) -> None:
        self.active = True
        self._current_eval_frame = frame
        self.last_eval_start_frame = frame
        self.eval_counter += 1

        self._subject_fish_ids = [getattr(f, "fish_id", 0) for f in top_fish]
        self._subject_lineage_ids = [
            str(getattr(f, "parent_id", getattr(f, "fish_id", "0"))) for f in top_fish
        ]
        self._current_generation = max((getattr(f, "generation", 0) for f in top_fish), default=0)
        self._hero_genomes = self._build_hero_genomes(top_fish)

        seed_val = getattr(engine, "seed", 42)
        seed_base: int = 42 if seed_val is None else int(seed_val)

        self._pending_matches = []
        self._completed_matches = []

        for team in REFERENCE_LADDER:
            for s_idx in range(self.n_seeds):
                d_seed = derive_soccer_seed(seed_base, self.eval_counter, f"{team.rung_id}_{s_idx}")
                match_seed: int = int(d_seed) if d_seed is not None else seed_base

                for hero_on_left in (True, False):
                    self._pending_matches.append(
                        MatchSpec(
                            rung_id=team.rung_id,
                            rung_name=team.rung,
                            team=team,
                            match_seed=match_seed,
                            hero_on_left=hero_on_left,
                        )
                    )

        self._start_next_match(engine)

    def _start_next_match(self, engine: SimulationEngine) -> None:

        if not self._pending_matches:
            return
        spec = self._pending_matches.pop(0)
        self._active_spec = spec

        pool = self._ensure_code_pool()

        # Build reference genomes for ruler team
        ref_genomes: list[Genome] = []
        for slot in range(self.team_size):
            p_id = spec.team.policy_id_for_slot(slot)
            g = Genome.random(use_algorithm=False, rng=None)
            g.behavioral.soccer_policy_id = GeneticTrait(p_id)
            g.behavioral.soccer_policy_params = GeneticTrait(None)
            ref_genomes.append(g)

        # Assemble participant bot entities (energy-free, zero side effects)
        left_genomes = self._hero_genomes if spec.hero_on_left else ref_genomes
        right_genomes = ref_genomes if spec.hero_on_left else self._hero_genomes

        entities: list[BotEntity] = []
        for i, g in enumerate(left_genomes):
            bot = BotEntity(f"left_eval_bot_{i+1}", "left")
            bot.genome = g
            entities.append(bot)
        for i, g in enumerate(right_genomes):
            bot = BotEntity(f"right_eval_bot_{i+1}", "right")
            bot.genome = g
            entities.append(bot)

        match_id = f"eval_ladder_{self.eval_counter}_{spec.rung_id}_{len(self._completed_matches)}"
        self._active_match = SoccerMatch(
            match_id=match_id,
            entities=entities,
            duration_frames=self.frames_per_match,
            code_source=pool,
            view_mode="side",
            seed=spec.match_seed,
        )

    def _record_match_result(self) -> None:
        if self._active_match is None or self._active_spec is None:
            return

        spec = self._active_spec
        score_left = (
            self._active_match.score.get("left", 0) if hasattr(self._active_match, "score") else 0
        )
        score_right = (
            self._active_match.score.get("right", 0) if hasattr(self._active_match, "score") else 0
        )

        hero_goals = score_left if spec.hero_on_left else score_right
        ref_goals = score_right if spec.hero_on_left else score_left

        self._completed_matches.append(
            {
                "rung_id": spec.rung_id,
                "rung": spec.rung_name,
                "hero_goals": hero_goals,
                "ref_goals": ref_goals,
                "goal_diff": hero_goals - ref_goals,
            }
        )

    def _finalize_evaluation(self) -> None:
        self.active = False

        # Group results by rung
        rung_results: list[RungResult] = []
        per_rung_diffs: dict[str, list[float]] = {}
        per_rung_hero: dict[str, list[float]] = {}
        per_rung_ref: dict[str, list[float]] = {}

        for m in self._completed_matches:
            rid = m["rung_id"]
            per_rung_diffs.setdefault(rid, []).append(float(m["goal_diff"]))
            per_rung_hero.setdefault(rid, []).append(float(m["hero_goals"]))
            per_rung_ref.setdefault(rid, []).append(float(m["ref_goals"]))

        top_unbeaten_diff: float | None = None
        first_unbeaten_found = False

        for team in REFERENCE_LADDER:
            diffs = per_rung_diffs.get(team.rung_id, [0.0])
            mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
            hero_m = sum(per_rung_hero.get(team.rung_id, [0.0])) / len(diffs) if diffs else 0.0
            ref_m = sum(per_rung_ref.get(team.rung_id, [0.0])) / len(diffs) if diffs else 0.0
            beaten = mean_diff > 0.0

            rung_results.append(
                RungResult(
                    rung=team.rung,
                    rung_id=team.rung_id,
                    metric=mean_diff,
                    beaten=beaten,
                    detail={
                        "matches_played": len(diffs),
                        "hero_goals_mean": hero_m,
                        "reference_goals_mean": ref_m,
                    },
                )
            )

            if not beaten and not first_unbeaten_found:
                top_unbeaten_diff = mean_diff
                first_unbeaten_found = True

        # If all rungs are beaten, baseline diff is goal diff vs highest rung
        if not first_unbeaten_found and rung_results:
            top_unbeaten_diff = rung_results[-1].metric

        self._latest_baseline_score_diff = top_unbeaten_diff

        summary = SkillLadderSummary(
            domain="soccer",
            benchmark_id="soccer/ladder_live",
            metric_name="goal_diff_per_match",
            skill_index=ladder_position_index(tuple(rung_results)),
            rungs=tuple(rung_results),
            notes="Live in-tank evaluation against frozen L0-L3 reference ladder.",
        )

        prev_snap = self.store.get_latest_snapshot(domain="soccer")
        prev_score = prev_snap.summary.skill_index if prev_snap is not None else None
        pb = self.store.get_personal_best_for_team(self._subject_fish_ids)
        current_score = summary.skill_index
        if current_score > pb:
            pb = current_score

        tank_best = max(self.store.tank_best, current_score)

        snapshot = SkillSnapshot(
            domain="soccer",
            generation=self._current_generation,
            frame=self._current_eval_frame,
            subject_fish_ids=list(self._subject_fish_ids),
            subject_lineage_ids=list(self._subject_lineage_ids),
            summary=summary,
            previous_score=prev_score,
            personal_best=pb,
            tank_best=tank_best,
            sample_size=len(self._completed_matches),
        )

        self.store.add_snapshot(snapshot)
        logger.info(
            f"Live soccer ladder evaluation complete at frame {self._current_eval_frame}: "
            f"skill_index={summary.skill_index:.1f}, beaten={summary.rungs_beaten}/{summary.total_rungs}"
        )
