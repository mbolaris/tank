"""Petri dish world backend adapter.

This module wraps the existing Tank world backend to provide a distinct
Petri mode without duplicating simulation logic.
"""

from __future__ import annotations

from typing import Any

from core.worlds.interfaces import FAST_STEP_ACTION, MultiAgentWorldBackend, StepResult
from core.worlds.tank.backend import TankWorldBackendAdapter


class PetriWorldBackendAdapter(MultiAgentWorldBackend):
    """Adapter that reuses the Tank backend while reporting Petri metadata."""

    def __init__(
        self,
        seed: int | None = None,
        config: Any | None = None,
        **config_overrides: Any,
    ) -> None:
        self._tank_backend = TankWorldBackendAdapter(seed=seed, config=config, **config_overrides)
        self.supports_fast_step = True
        self._last_step_result: StepResult | None = None

    def _get_dish_dict(self) -> dict[str, Any]:
        """Get dish geometry from environment as a dict for render_hint."""
        env = getattr(self._tank_backend.engine, "environment", None)
        dish = getattr(env, "dish", None) if env else None

        if dish:
            return {
                "shape": "circle",
                "cx": dish.cx,
                "cy": dish.cy,
                "r": dish.r,
            }

        # Fallback to geometry constants (for early initialization)
        from core.worlds.petri.geometry import PETRI_CENTER_X, PETRI_CENTER_Y, PETRI_RADIUS

        return {
            "shape": "circle",
            "cx": PETRI_CENTER_X,
            "cy": PETRI_CENTER_Y,
            "r": PETRI_RADIUS,
        }

    def reset(self, seed: int | None = None, config: dict[str, Any] | None = None) -> StepResult:
        from core.worlds.petri.pack import PetriPack

        # Create a PetriPack from current config or provided overrides
        # Petri mode reuses TankWorldConfig format
        pack = PetriPack(self._tank_backend.config.to_simulation_config())

        result = self._tank_backend.reset(seed=seed, config=config, pack=pack)
        self._last_step_result = self._patch_step_result(result)
        return self._last_step_result

    def step(self, actions_by_agent: dict[str, Any] | None = None) -> StepResult:
        result = self._tank_backend.step(actions_by_agent=actions_by_agent)
        self._last_step_result = self._patch_step_result(result)
        return self._last_step_result

    def update(self) -> None:
        self.step({FAST_STEP_ACTION: True})

    def get_current_snapshot(self) -> dict[str, Any]:
        snapshot = self._tank_backend.get_current_snapshot()
        if snapshot:
            snapshot = dict(snapshot)
            snapshot["world_type"] = "petri"

            snapshot["render_hint"] = {
                "style": "topdown",
                "entity_style": "microbe",
                "dish": self._get_dish_dict(),
            }
        return snapshot

    def get_current_metrics(self) -> dict[str, Any]:
        return self._tank_backend.get_current_metrics()

    def get_debug_snapshot(self) -> dict[str, Any]:
        snapshot = self._tank_backend.get_debug_snapshot()
        if snapshot:
            snapshot = dict(snapshot)
            snapshot["world_type"] = "petri"

            snapshot["render_hint"] = {
                "style": "topdown",
                "entity_style": "microbe",
                "dish": self._get_dish_dict(),
            }
        return snapshot

    @property
    def world_type(self) -> str:
        """The world type identifier (protocol method)."""
        return "petri"

    @property
    def entities_list(self) -> list[Any]:
        return self._tank_backend.entities_list

    @property
    def frame_count(self) -> int:
        return self._tank_backend.frame_count

    @frame_count.setter
    def frame_count(self, value: int) -> None:
        self._tank_backend.frame_count = value

    @property
    def paused(self) -> bool:
        return self._tank_backend.paused

    @paused.setter
    def paused(self, value: bool) -> None:
        self._tank_backend.paused = value

    @property
    def world(self) -> Any:
        return self._tank_backend.world

    @property
    def engine(self) -> Any:
        return self._tank_backend.engine

    @property
    def ecosystem(self) -> Any:
        return self._tank_backend.ecosystem

    @property
    def config(self) -> Any:
        return self._tank_backend.config

    @property
    def rng(self) -> Any:
        return self._tank_backend.rng

    def get_stats(self, include_distributions: bool = True) -> dict[str, Any]:
        return self._tank_backend.get_stats(include_distributions=include_distributions)

    def get_last_step_result(self) -> StepResult | None:
        return self._last_step_result

    def _patch_step_result(self, result: StepResult) -> StepResult:
        snapshot = dict(result.snapshot)
        snapshot["world_type"] = "petri"

        render_hint = {
            "style": "topdown",
            "entity_style": "microbe",
            "dish": self._get_dish_dict(),
        }
        snapshot["render_hint"] = render_hint

        return StepResult(
            obs_by_agent=result.obs_by_agent,
            snapshot=snapshot,
            events=result.events,
            metrics=result.metrics,
            done=result.done,
            info=result.info,
            spawns=result.spawns,
            removals=result.removals,
            energy_deltas=result.energy_deltas,
            render_hint=render_hint,
        )

    # ========================================================================
    # Protocol methods for world-agnostic backend support
    # ========================================================================

    @property
    def is_paused(self) -> bool:
        """Whether the simulation is paused (protocol method)."""
        return self._tank_backend.is_paused

    def set_paused(self, value: bool) -> None:
        """Set the simulation paused state (protocol method)."""
        self._tank_backend.set_paused(value)

    def get_entities_for_snapshot(self) -> list[Any]:
        """Get entities for snapshot building (protocol method)."""
        return self._tank_backend.get_entities_for_snapshot()

    def capture_state_for_save(self) -> dict[str, Any]:
        """Capture complete world state for persistence (protocol method)."""
        return self._tank_backend.capture_state_for_save()

    def restore_state_from_save(self, state: dict[str, Any]) -> None:
        """Restore world state from a saved snapshot (protocol method)."""
        self._tank_backend.restore_state_from_save(state)
