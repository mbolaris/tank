"""Deterministic tests for tank-object triggers and feeding capabilities."""

from types import SimpleNamespace

from core.entities import Fish
from core.movement_strategy import AlgorithmicMovement
from core.tank_interactions import (
    ContactTrigger,
    DwellTrigger,
    FeedingCapability,
    InteractionContext,
    ProximityTrigger,
    TankInteractionSystem,
)
from core.tank_objects import TankObject


def _fish(environment, fish_id: int, x: float, y: float) -> Fish:
    fish = Fish(
        environment,
        AlgorithmicMovement(),
        "school.png",
        x,
        y,
        1.0,
        fish_id=fish_id,
        skip_birth_recording=True,
    )
    fish.set_size(20, 20)
    return fish


def _engine(environment, entities):
    spawned = []

    def request_spawn(entity, *, reason="", metadata=None):
        spawned.append((entity, reason))
        return True

    return SimpleNamespace(
        environment=environment,
        entities_list=entities,
        request_spawn=request_spawn,
        spawned=spawned,
    )


def test_proximity_contact_and_dwell_triggers_use_ordinary_geometry(simulation_env):
    environment, _ = simulation_env
    obj = TankObject(environment, 100, 100, object_kind="decorative_rock", width=40, height=40)
    actor = _fish(environment, 7, 110, 110)
    context = InteractionContext(actor=actor, obj=obj)

    assert ProximityTrigger(radius=30).is_active(context)
    assert ContactTrigger().is_active(context)
    assert DwellTrigger(duration_frames=3, radius=30).is_active(context)


def test_feeding_capability_round_trip_keeps_trigger_and_capability_ids():
    capability = FeedingCapability(
        capability_id="feeding-primary",
        resource_type="protein",
        capacity=100,
        stock=80,
        recharge_rate=1,
        dispense_amount=12,
        cooldown_frames=4,
        trigger=DwellTrigger(duration_frames=5, radius=22),
    )

    restored = FeedingCapability.from_config(capability.to_config())

    assert restored.capability_id == "feeding-primary"
    assert restored.resource_type == "protein"
    assert isinstance(restored.trigger, DwellTrigger)
    assert restored.trigger.duration_frames == 5


def test_dwell_dispenses_once_then_respects_cooldown_and_spawn_phase(simulation_env):
    environment, _ = simulation_env
    obj = TankObject(
        environment,
        100,
        100,
        object_kind="protein_grotto",
        capability_config=(
            FeedingCapability(
                capability_id="feeding-primary",
                resource_type="protein",
                capacity=20,
                stock=12,
                recharge_rate=0,
                dispense_amount=12,
                cooldown_frames=3,
                trigger=DwellTrigger(duration_frames=2, radius=40),
            ).to_config(),
        ),
    )
    actor = _fish(environment, 42, 145, 125)
    engine = _engine(environment, [obj, actor])
    system = TankInteractionSystem(engine)

    assert system.update(1).details["activations"] == 0
    assert system.update(2).details["activations"] == 1
    assert obj.feeder_activity == {
        "feeding-primary": {
            "stock_percent": 0,
            "resource_type": "protein",
            "recent_activations": 1,
            "last_activation_frame": 2,
        }
    }
    assert system.update(3).details["activations"] == 0
    assert system.materialize_pending(2) == 1
    food, reason = engine.spawned[0]
    assert food.food_type == "protein"
    assert food.energy == 12
    assert reason == "tank_object_dispense"


def test_two_feeding_capabilities_on_one_object_track_activity_independently(simulation_env):
    environment, _ = simulation_env
    obj = TankObject(
        environment,
        100,
        100,
        object_kind="protein_grotto",
        width=40,
        height=40,
        capability_config=(
            FeedingCapability(
                capability_id="feeding-algae",
                resource_type="algae",
                capacity=20,
                stock=20,
                recharge_rate=0,
                dispense_amount=12,
                cooldown_frames=3,
                trigger=ProximityTrigger(radius=40),
            ).to_config(),
            FeedingCapability(
                capability_id="feeding-protein",
                resource_type="protein",
                capacity=40,
                stock=40,
                recharge_rate=0,
                dispense_amount=12,
                cooldown_frames=3,
                trigger=ProximityTrigger(radius=40),
            ).to_config(),
        ),
    )
    actor = _fish(environment, 42, 110, 110)
    engine = _engine(environment, [obj, actor])
    system = TankInteractionSystem(engine)

    assert system.update(1).details["activations"] == 2
    assert obj.feeder_activity == {
        "feeding-algae": {
            "stock_percent": 40,
            "resource_type": "algae",
            "recent_activations": 1,
            "last_activation_frame": 1,
        },
        "feeding-protein": {
            "stock_percent": 70,
            "resource_type": "protein",
            "recent_activations": 1,
            "last_activation_frame": 1,
        },
    }


def test_insufficient_stock_does_not_activate(simulation_env):
    environment, _ = simulation_env
    obj = TankObject(
        environment,
        100,
        100,
        object_kind="algae_reef",
        capability_config=(
            {
                "type": "feeding",
                "capability_id": "feeding-primary",
                "resource_type": "algae",
                "capacity": 5,
                "stock": 5,
                "recharge_rate": 0,
                "dispense_amount": 12,
                "cooldown_frames": 0,
                "trigger": {"type": "proximity", "radius": 50},
            },
        ),
    )
    actor = _fish(environment, 42, 110, 110)
    engine = _engine(environment, [obj, actor])

    assert TankInteractionSystem(engine).update(1).details["activations"] == 0
