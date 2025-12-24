from __future__ import annotations

"""Dedicated builder for exporting simulation statistics.

This module centralizes the JSON export logic that was previously embedded in
``SimulationEngine``. Keeping this logic in its own class reduces the
responsibility surface of the engine and makes it easier to evolve the export
format without touching the simulation loop.
"""

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List

from core.algorithms.registry import get_algorithm_name
from core.config.display import FRAME_RATE
from core.registry import get_algorithm_metadata

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.simulation import SimulationEngine

logger = logging.getLogger(__name__)


class SimulationStatsExporter:
    """Build and persist comprehensive simulation statistics."""

    def __init__(self, engine: "SimulationEngine") -> None:
        self.engine = engine

    def export_stats_json(self, filename: str) -> None:
        """Export comprehensive simulation statistics to JSON file for LLM analysis."""

        ecosystem = self.engine.ecosystem
        if ecosystem is None:
            logger.warning("Cannot export stats: ecosystem not initialized")
            return

        algorithm_metadata = get_algorithm_metadata()

        export_data = {
            "simulation_metadata": self._build_simulation_metadata(ecosystem),
            "population_summary": self._build_population_summary(ecosystem),
            "reproduction_summary": ecosystem.get_reproduction_summary(),
            "death_causes": dict(ecosystem.death_causes),
            "algorithm_registry": algorithm_metadata,
            "algorithm_performance": self._build_algorithm_performance(
                ecosystem, algorithm_metadata
            ),
            "poker_statistics": self._build_poker_statistics(ecosystem),
            "skill_game_statistics": self._build_skill_game_statistics(ecosystem),
            "generation_trends": self._build_generation_trends(ecosystem),
            "recommendations": {
                "top_performers": self._identify_top_performers(ecosystem),
                "worst_performers": self._identify_worst_performers(ecosystem),
                "extinct_algorithms": self._identify_extinct_algorithms(ecosystem),
            },
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info("Comprehensive stats exported to: %s", filename)
        logger.info("Export includes %s algorithms", len(export_data["algorithm_performance"]))
        logger.info("Use this data for LLM-based behavior analysis and improvement!")

    def _build_simulation_metadata(self, ecosystem: "EcosystemManager") -> Dict[str, Any]:
        """Build simulation metadata for stats export."""

        return {
            "total_frames": self.engine.frame_count,
            "total_sim_time_seconds": self.engine.frame_count / FRAME_RATE,
            "elapsed_real_time_seconds": time.time() - self.engine.start_time,
            "simulation_speed_multiplier": (
                self.engine.frame_count / (FRAME_RATE * (time.time() - self.engine.start_time))
                if time.time() > self.engine.start_time
                else 0
            ),
            "max_population": ecosystem.max_population,
        }

    def _build_population_summary(self, ecosystem: "EcosystemManager") -> Dict[str, Any]:
        """Build population summary for stats export."""

        return {
            "total_births": ecosystem.total_births,
            "total_deaths": ecosystem.total_deaths,
            "current_generation": ecosystem.current_generation,
            "final_population": len(self.engine.get_fish_list()),
        }

    def _build_algorithm_performance(
        self, ecosystem: "EcosystemManager", algorithm_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build per-algorithm performance statistics."""

        performance = {}
        for algo_id, stats in ecosystem.algorithm_stats.items():
            algo_name = get_algorithm_name(algo_id)
            if algo_name == "Unknown":
                algo_name = f"algorithm_{algo_id}"

            metadata = algorithm_metadata.get(algo_name, {})
            performance[algo_name] = {
                "algorithm_id": algo_id,
                "source_file": metadata.get("source_file", "unknown"),
                "category": metadata.get("category", "unknown"),
                "total_births": stats.total_births,
                "total_deaths": stats.total_deaths,
                "current_population": stats.current_population,
                "avg_lifespan_frames": stats.get_avg_lifespan(),
                "survival_rate": stats.get_survival_rate(),
                "reproduction_rate": stats.get_reproduction_rate(),
                "total_reproductions": stats.total_reproductions,
                "total_food_eaten": stats.total_food_eaten,
                "death_breakdown": {
                    "starvation": stats.deaths_starvation,
                    "old_age": stats.deaths_old_age,
                    "predation": stats.deaths_predation,
                },
                "energy_efficiency": (
                    stats.total_food_eaten / stats.total_births if stats.total_births > 0 else 0.0
                ),
                "reproductive_success": (
                    stats.total_reproductions / stats.total_deaths if stats.total_deaths > 0 else 0.0
                ),
            }
        return performance

    def _build_poker_statistics(self, ecosystem: "EcosystemManager") -> Dict[str, Any]:
        """Build poker statistics per algorithm."""

        poker_stats_export = {}
        for algo_id, poker_stats in ecosystem.poker_stats.items():
            algo_name = get_algorithm_name(algo_id)
            if algo_name == "Unknown":
                algo_name = f"algorithm_{algo_id}"

            if poker_stats.total_games > 0:
                poker_stats_export[algo_name] = {
                    "algorithm_id": algo_id,
                    "total_games": poker_stats.total_games,
                    "win_rate": poker_stats.get_win_rate(),
                    "fold_rate": poker_stats.get_fold_rate(),
                    "net_energy": poker_stats.get_net_energy(),
                    "roi": poker_stats.get_roi(),
                    "vpip": poker_stats.get_vpip(),
                    "aggression_factor": poker_stats.get_aggression_factor(),
                    "showdown_win_rate": poker_stats.get_showdown_win_rate(),
                    "bluff_success_rate": poker_stats.get_bluff_success_rate(),
                    "positional_advantage": poker_stats.get_positional_advantage(),
                }
        return poker_stats_export

    def _build_generation_trends(self, ecosystem: "EcosystemManager") -> List[Dict[str, Any]]:
        """Build generation trend data."""

        trends = []
        for gen_num, gen_stats in sorted(ecosystem.generation_stats.items()):
            trends.append(
                {
                    "generation": gen_num,
                    "population": gen_stats.population,
                    "births": gen_stats.births,
                    "deaths": gen_stats.deaths,
                    "avg_age": gen_stats.avg_age,
                    "avg_speed": gen_stats.avg_speed,
                    "avg_size": gen_stats.avg_size,
                    "avg_energy": gen_stats.avg_energy,
                }
            )
        return trends

    def _identify_top_performers(self, ecosystem: "EcosystemManager") -> List[Dict[str, Any]]:
        """Identify top performing algorithms for LLM to learn from."""

        algorithms_with_data = [
            (algo_id, stats)
            for algo_id, stats in ecosystem.algorithm_stats.items()
            if stats.total_births >= 5  # Minimum sample size
        ]
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate(), reverse=True)

        top_performers = []
        for algo_id, stats in algorithms_with_data[:5]:  # Top 5
            algo_name = get_algorithm_name(algo_id)
            top_performers.append(
                {
                    "algorithm_name": algo_name,
                    "algorithm_id": algo_id,
                    "reproduction_rate": stats.get_reproduction_rate(),
                    "avg_lifespan": stats.get_avg_lifespan(),
                    "survival_rate": stats.get_survival_rate(),
                    "reason": f"High reproduction rate ({stats.get_reproduction_rate():.2%}) and survival",
                }
            )
        return top_performers

    def _identify_worst_performers(self, ecosystem: "EcosystemManager") -> List[Dict[str, Any]]:
        """Identify worst performing algorithms for LLM to learn what to avoid."""

        algorithms_with_data = [
            (algo_id, stats)
            for algo_id, stats in ecosystem.algorithm_stats.items()
            if stats.total_births >= 5  # Minimum sample size
        ]
        algorithms_with_data.sort(key=lambda x: x[1].get_reproduction_rate())

        worst_performers = []
        for algo_id, stats in algorithms_with_data[:5]:  # Bottom 5
            algo_name = get_algorithm_name(algo_id)
            death_causes = {
                "starvation": stats.deaths_starvation,
                "old_age": stats.deaths_old_age,
                "predation": stats.deaths_predation,
            }
            main_death_cause = (
                max(death_causes, key=death_causes.get) if any(death_causes.values()) else "unknown"
            )

            worst_performers.append(
                {
                    "algorithm_name": algo_name,
                    "algorithm_id": algo_id,
                    "reproduction_rate": stats.get_reproduction_rate(),
                    "avg_lifespan": stats.get_avg_lifespan(),
                    "main_death_cause": main_death_cause,
                    "reason": (
                        f"Low reproduction rate ({stats.get_reproduction_rate():.2%}), "
                        f"main death: {main_death_cause}"
                    ),
                }
            )
        return worst_performers

    def _identify_extinct_algorithms(self, ecosystem: "EcosystemManager") -> List[Dict[str, Any]]:
        """Identify algorithms that went extinct."""

        extinct = []
        for algo_id, stats in ecosystem.algorithm_stats.items():
            if stats.total_births > 0 and stats.current_population == 0:
                algo_name = get_algorithm_name(algo_id)
                extinct.append(
                    {
                        "algorithm_name": algo_name,
                        "algorithm_id": algo_id,
                        "total_births": stats.total_births,
                        "avg_lifespan": stats.get_avg_lifespan(),
                    }
                )
        return extinct

    def _build_skill_game_statistics(
        self, ecosystem: "EcosystemManager"
    ) -> Dict[str, Any]:
        """Build skill game statistics for observation.

        These metrics help us observe how well evolution is progressing
        on the active skill game. They do NOT drive selection - that
        happens through energy flow.

        Args:
            ecosystem: The ecosystem manager

        Returns:
            Skill game statistics dictionary
        """
        # Check if skill game system exists
        if not hasattr(self.engine, "skill_game_system"):
            return {"status": "skill_game_system_not_initialized"}

        skill_system = self.engine.skill_game_system
        if skill_system is None:
            return {"status": "skill_game_system_disabled"}

        # Get aggregate stats
        aggregate = skill_system.get_aggregate_stats()

        # Collect per-fish skill game stats
        fish_stats = []
        for fish in self.engine.get_fish_list():
            if hasattr(fish, "_skill_game_component"):
                component = fish._skill_game_component
                fish_data = {
                    "fish_id": fish.fish_id,
                    "generation": fish.generation,
                    "algorithm": fish.genome.algorithm.__class__.__name__,
                    "skill_games": component.get_all_stats_dict(),
                }
                fish_stats.append(fish_data)

        # Calculate population-level skill metrics
        population_metrics = self._calculate_population_skill_metrics(fish_stats)

        return {
            "active_game": aggregate.get("active_game", "Unknown"),
            "total_games_played": aggregate.get("total_games_played", 0),
            "total_energy_transferred": aggregate.get("total_energy_transferred", 0.0),
            "config": aggregate.get("config", {}),
            "population_metrics": population_metrics,
            "top_skill_performers": self._identify_top_skill_performers(fish_stats),
            "recent_events": skill_system.get_recent_events(20),
        }

    def _calculate_population_skill_metrics(
        self, fish_stats: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate population-level skill game metrics.

        Args:
            fish_stats: List of per-fish stats

        Returns:
            Aggregate metrics
        """
        if not fish_stats:
            return {}

        # Aggregate across all fish and game types
        total_optimality_sum = 0.0
        total_games = 0
        total_wins = 0
        games_by_type: Dict[str, int] = {}
        optimality_by_type: Dict[str, List[float]] = {}

        for fish_data in fish_stats:
            for game_type, stats in fish_data.get("skill_games", {}).items():
                games = stats.get("total_games", 0)
                if games == 0:
                    continue

                total_games += games
                total_wins += stats.get("wins", 0)
                total_optimality_sum += stats.get("optimality_rate", 0) * games

                if game_type not in games_by_type:
                    games_by_type[game_type] = 0
                    optimality_by_type[game_type] = []
                games_by_type[game_type] += games
                optimality_by_type[game_type].append(stats.get("optimality_rate", 0))

        return {
            "total_fish_with_stats": len(fish_stats),
            "total_games_across_fish": total_games,
            "population_win_rate": total_wins / total_games if total_games > 0 else 0.0,
            "population_avg_optimality": (
                total_optimality_sum / total_games if total_games > 0 else 0.0
            ),
            "games_by_type": games_by_type,
            "avg_optimality_by_type": {
                game_type: sum(rates) / len(rates) if rates else 0.0
                for game_type, rates in optimality_by_type.items()
            },
        }

    def _identify_top_skill_performers(
        self, fish_stats: List[Dict[str, Any]], top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Identify fish with highest skill game optimality.

        Args:
            fish_stats: List of per-fish stats
            top_n: Number of top performers to return

        Returns:
            List of top performer summaries
        """
        # Score fish by average optimality across games
        scored_fish = []
        for fish_data in fish_stats:
            total_optimality = 0.0
            game_count = 0
            for game_type, stats in fish_data.get("skill_games", {}).items():
                if stats.get("total_games", 0) >= 5:  # Minimum sample
                    total_optimality += stats.get("optimality_rate", 0)
                    game_count += 1

            if game_count > 0:
                avg_optimality = total_optimality / game_count
                scored_fish.append({
                    "fish_id": fish_data.get("fish_id"),
                    "generation": fish_data.get("generation"),
                    "algorithm": fish_data.get("algorithm"),
                    "avg_optimality": avg_optimality,
                    "games_played": sum(
                        s.get("total_games", 0)
                        for s in fish_data.get("skill_games", {}).values()
                    ),
                })

        # Sort by optimality
        scored_fish.sort(key=lambda x: x["avg_optimality"], reverse=True)
        return scored_fish[:top_n]
