"""Telemetry ingestion for the ecosystem.

Routes domain events (EventBus subscriptions and manual record_event calls),
energy delta batches, and food-consumption recording into the ecosystem's
trackers. Extracted from core/ecosystem.py; EcosystemManager keeps thin
delegating facades, and all calls go back through the manager so
monkeypatched manager methods are honored.
"""

from typing import TYPE_CHECKING, Any, Optional

from core.constants import SOURCE_POKER_FISH
from core.telemetry.events import BirthEvent, FoodEatenEvent, ReproductionEvent

if TYPE_CHECKING:
    from core.ecosystem import EcosystemManager
    from core.events import EventBus
    from core.genetics import Genome


class EcosystemTelemetryRouter:
    """Routes telemetry events and energy deltas into ecosystem trackers."""

    def __init__(self, manager: "EcosystemManager") -> None:
        self._manager = manager

    def subscribe(self, event_bus: "EventBus") -> None:
        """Subscribe handlers to domain events on the EventBus.

        This enables decoupled telemetry where entities emit events and
        EcosystemManager receives them without direct coupling.

        Note: Energy accounting now uses EnergyDeltaRecord via ingest_energy_deltas().
        EnergyGainEvent/EnergyBurnEvent handlers are no-ops to avoid double-counting.
        """
        # Non-energy events still active
        event_bus.subscribe(FoodEatenEvent, self.on_food_eaten)
        event_bus.subscribe(BirthEvent, self.on_birth)
        event_bus.subscribe(ReproductionEvent, self.on_reproduction)

    def on_food_eaten(self, event: "FoodEatenEvent") -> None:
        """Handle food consumption events."""
        if event.food_type == "nectar":
            self._manager.record_nectar_eaten(event.algorithm_id, event.energy_gained)
        elif event.food_type == "live_food":
            self._manager.record_live_food_eaten(
                event.algorithm_id,
                event.energy_gained,
                genome=event.genome,
                generation=event.generation,
            )
        elif event.food_type == "falling_food":
            self._manager.record_falling_food_eaten(event.algorithm_id, event.energy_gained)
        else:
            self._manager.record_food_eaten(event.algorithm_id, event.energy_gained)

    def on_birth(self, event: "BirthEvent") -> None:
        """Handle entity birth events."""
        self._manager.record_birth(
            event.fish_id,
            event.generation,
            parent_ids=list(event.parent_ids) if event.parent_ids else None,
            algorithm_id=event.algorithm_id,
            color=event.color_hex,
            algorithm_name=event.algorithm_name,
            tank_name=event.tank_name,
        )
        if event.is_soup_spawn:
            self._manager.record_energy_gain("soup_spawn", event.energy)

    def on_reproduction(self, event: "ReproductionEvent") -> None:
        """Handle reproduction events."""
        self._manager.record_reproduction(event.algorithm_id, is_asexual=event.is_asexual)

    def record_event(self, event: Any) -> None:
        """Record a telemetry event emitted by domain entities.

        This delegates to the specific event handlers to ensure consistent logic
        between manual recording and EventBus subscriptions.

        Note: Energy accounting now uses EnergyDeltaRecord via ingest_energy_deltas().
        EnergyGainEvent/EnergyBurnEvent are no-ops to avoid double-counting.
        """
        # Energy events are no-ops (accounting now via ingest_energy_deltas)
        if isinstance(event, FoodEatenEvent):
            self.on_food_eaten(event)
        elif isinstance(event, BirthEvent):
            self.on_birth(event)
        elif isinstance(event, ReproductionEvent):
            self.on_reproduction(event)

    def ingest_energy_deltas(self, deltas: list[Any]) -> None:
        """Process a batch of energy deltas from the engine recorder.

        This replaces the old event-based telemetry for energy.
        Args:
            deltas: List of EnergyDeltaRecord objects
        """
        for delta in deltas:
            if delta.delta > 0:
                # Energy Gain
                source = delta.source
                amount = delta.delta

                # Map source names if needed for consistency
                if source == "ate_food":
                    # Try to get detailed info from metadata if available
                    food_type = "food"
                    if delta.metadata and "food_type" in delta.metadata:
                        food_type = delta.metadata["food_type"]
                    self._manager.record_energy_gain(food_type, amount)
                elif source == "poker_win":
                    self._manager.record_energy_gain(SOURCE_POKER_FISH, amount)
                else:
                    self._manager.record_energy_gain(source, amount)

            elif delta.delta < 0:
                # Energy Burn
                source = delta.source
                amount = -delta.delta

                if source == "metabolism":
                    # Metabolism is now aggregated, but we can log it
                    self._manager.record_energy_burn("metabolism", amount)
                elif source == "poker_loss":
                    self._manager.record_energy_burn("poker", amount)
                else:
                    self._manager.record_energy_burn(source, amount)

    # =========================================================================
    # Food Recording
    # =========================================================================

    def record_nectar_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record nectar consumption."""
        if algorithm_id in self._manager.algorithm_stats:
            self._manager.algorithm_stats[algorithm_id].total_food_eaten += 1
        self._manager.enhanced_stats.record_energy_from_food(energy_gained)
        self._manager.record_energy_gain("nectar", energy_gained)

    def record_live_food_eaten(
        self,
        algorithm_id: int,
        energy_gained: float = 10.0,
        genome: Optional["Genome"] = None,
        generation: int | None = None,
    ) -> None:
        """Record live food consumption."""
        if algorithm_id in self._manager.algorithm_stats:
            self._manager.algorithm_stats[algorithm_id].total_food_eaten += 1
        self._manager.enhanced_stats.record_energy_from_food(energy_gained)
        if genome is not None:
            self._manager.enhanced_stats.record_live_food_capture(
                algorithm_id, energy_gained, genome, generation
            )
        self._manager.record_energy_gain("live_food", energy_gained)

    def record_falling_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record falling food consumption."""
        if algorithm_id in self._manager.algorithm_stats:
            self._manager.algorithm_stats[algorithm_id].total_food_eaten += 1
        self._manager.enhanced_stats.record_energy_from_food(energy_gained)
        self._manager.record_energy_gain("falling_food", energy_gained)

    def record_food_eaten(self, algorithm_id: int, energy_gained: float = 10.0) -> None:
        """Record generic food consumption."""
        if algorithm_id in self._manager.algorithm_stats:
            self._manager.algorithm_stats[algorithm_id].total_food_eaten += 1
        self._manager.enhanced_stats.record_energy_from_food(energy_gained)
        self._manager.record_energy_gain("food", energy_gained)
