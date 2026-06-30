"""Tests for attraction-based post-poker mate selection."""

from __future__ import annotations

import random
from typing import cast

from core.config.simulation_config import SimulationConfig
from core.entities import Fish, LifeStage
from core.genetics import BehavioralTraits, GeneticTrait, Genome, PhysicalTraits
from core.movement_strategy import AlgorithmicMovement
from core.reproduction.reproduction_service import ReproductionService


class _MiniEcosystem:
    def __init__(self) -> None:
        self._next_fish_id = 1
        self.reproductions: list[bool] = []
        self.mating_attempts: list[bool] = []
        self.births = 0
        self.max_population = 100

    def generate_new_fish_id(self) -> int:
        fish_id = self._next_fish_id
        self._next_fish_id += 1
        return fish_id

    def record_birth(self, *_args, **_kwargs) -> None:
        self.births += 1

    def record_reproduction(self, _algorithm_id: int, is_asexual: bool = False) -> None:
        self.reproductions.append(is_asexual)

    def record_mating_attempt(self, success: bool) -> None:
        self.mating_attempts.append(success)

    def can_reproduce(self, fish_count: int) -> bool:
        return fish_count < self.max_population


class _MiniEnvironment:
    def __init__(self) -> None:
        self.width = 300
        self.height = 200
        self.rng = random.Random(42)

    def get_bounds(self):
        return (0.0, 0.0), (float(self.width), float(self.height))

    def list_policy_component_ids(self, _kind: str) -> list[str]:
        return []


class _EntityManager:
    def __init__(self, fish: list[Fish]) -> None:
        self._fish = fish

    def get_fish(self) -> list[Fish]:
        return list(self._fish)


class _LifecycleSystem:
    def __init__(self) -> None:
        self.births = 0

    def record_birth(self) -> None:
        self.births += 1


class _MiniEngine:
    def __init__(self, fish: list[Fish], env: _MiniEnvironment, ecosystem: _MiniEcosystem) -> None:
        self.entity_manager = _EntityManager(fish)
        self.environment = env
        self.rng = env.rng
        self.ecosystem = ecosystem
        self.lifecycle_system = _LifecycleSystem()
        self.config = SimulationConfig.headless_fast()
        self.spawned: list[Fish] = []
        self.spawn_reasons: list[str] = []
        self.reproduction_service = None

    def request_spawn(self, entity: Fish, *, reason: str) -> bool:
        self.spawned.append(entity)
        self.spawn_reasons.append(reason)
        return True


def _genome(*, aggression: float, mate_preferences: dict[str, float] | None = None) -> Genome:
    physical = PhysicalTraits(
        size_modifier=GeneticTrait(1.0),
        color_hue=GeneticTrait(0.5),
        template_id=GeneticTrait(0),
        fin_size=GeneticTrait(1.0),
        tail_size=GeneticTrait(1.0),
        body_aspect=GeneticTrait(1.0),
        eye_size=GeneticTrait(1.0),
        pattern_intensity=GeneticTrait(0.5),
        pattern_type=GeneticTrait(0),
        lifespan_modifier=GeneticTrait(1.0),
    )
    behavioral = BehavioralTraits(
        aggression=GeneticTrait(aggression),
        social_tendency=GeneticTrait(0.5),
        pursuit_aggression=GeneticTrait(0.5),
        prediction_skill=GeneticTrait(0.5),
        hunting_stamina=GeneticTrait(0.5),
        asexual_reproduction_chance=GeneticTrait(0.5),
        poker_strategy=GeneticTrait(None),
        mate_preferences=GeneticTrait(mate_preferences or {}),
    )
    return Genome(physical=physical, behavioral=behavioral)


def _adult_fish(
    env: _MiniEnvironment,
    ecosystem: _MiniEcosystem,
    *,
    fish_id: int,
    x: float,
    y: float,
    aggression: float,
    mate_preferences: dict[str, float] | None = None,
) -> Fish:
    fish = Fish(
        environment=cast("World", env),
        movement_strategy=AlgorithmicMovement(),
        species="fish1.png",
        x=x,
        y=y,
        speed=1.0,
        genome=_genome(aggression=aggression, mate_preferences=mate_preferences),
        generation=2,
        ecosystem=cast("Any", ecosystem),
        initial_energy=150.0,
        parent_id=0,
    )
    fish.fish_id = fish_id
    fish.age = 2000  # Adult
    fish.force_life_stage(LifeStage.ADULT)
    fish.energy = fish.max_energy
    fish._reproduction_component.reproduction_cooldown = 0
    return fish


class MockPokerResult:
    def __init__(self, winner_id: int, fish_count: int = 3):
        self.is_tie = False
        self.fish_count = fish_count
        self.plant_count = 0
        self.winner_type = "fish"
        self.winner_id = winner_id


class MockPoker:
    def __init__(self, fish_players: list[Fish], winner_id: int):
        self.result = MockPokerResult(winner_id, len(fish_players))
        self.fish_players = fish_players

    def _get_player_id(self, player: Fish) -> int:
        return player.fish_id


def test_post_poker_mating_prefers_highest_attraction() -> None:
    env = _MiniEnvironment()
    ecosystem = _MiniEcosystem()

    winner = _adult_fish(
        env,
        ecosystem,
        fish_id=1,
        x=80,
        y=80,
        aggression=0.5,
        mate_preferences={"prefer_high_aggression": 1.0},
    )
    # Opponent 1: High aggression = High attraction
    opponent1 = _adult_fish(env, ecosystem, fish_id=2, x=90, y=80, aggression=1.0)
    # Opponent 2: Low aggression = Low attraction
    opponent2 = _adult_fish(env, ecosystem, fish_id=3, x=95, y=80, aggression=0.0)

    engine = _MiniEngine([winner, opponent1, opponent2], env, ecosystem)
    service = ReproductionService(cast("SimpleNamespace", engine))

    poker = MockPoker([winner, opponent1, opponent2], winner_id=1)
    baby = service.handle_post_poker_reproduction(cast("Any", poker))

    assert baby is not None
    # Opponent 1 (high attraction) should be selected and pay energy
    assert opponent1.energy < 150.0
    assert opponent2.energy == 150.0


def test_post_poker_mating_breaks_attraction_tie_by_closer_distance() -> None:
    env = _MiniEnvironment()
    ecosystem = _MiniEcosystem()

    winner = _adult_fish(env, ecosystem, fish_id=1, x=80, y=80, aggression=0.5)
    # Both opponents have identical traits (identical attraction), but opponent1 is closer
    opponent1 = _adult_fish(env, ecosystem, fish_id=2, x=90, y=80, aggression=0.5)
    opponent2 = _adult_fish(env, ecosystem, fish_id=3, x=105, y=80, aggression=0.5)

    engine = _MiniEngine([winner, opponent1, opponent2], env, ecosystem)
    service = ReproductionService(cast("SimpleNamespace", engine))

    poker = MockPoker([winner, opponent1, opponent2], winner_id=1)
    baby = service.handle_post_poker_reproduction(cast("Any", poker))

    assert baby is not None
    # Opponent 1 (closer) should be selected and pay energy
    assert opponent1.energy < 150.0
    assert opponent2.energy == 150.0


def test_post_poker_mating_breaks_tie_by_fish_id() -> None:
    env = _MiniEnvironment()
    ecosystem = _MiniEcosystem()

    winner = _adult_fish(env, ecosystem, fish_id=1, x=80, y=80, aggression=0.5)
    # Both opponents have identical traits and identical distances (on left/right of winner),
    # but opponent1 has a lower fish_id (2 vs 3).
    opponent1 = _adult_fish(env, ecosystem, fish_id=2, x=70, y=80, aggression=0.5)
    opponent2 = _adult_fish(env, ecosystem, fish_id=3, x=90, y=80, aggression=0.5)

    engine = _MiniEngine([winner, opponent1, opponent2], env, ecosystem)
    service = ReproductionService(cast("SimpleNamespace", engine))

    poker = MockPoker([winner, opponent1, opponent2], winner_id=1)
    baby = service.handle_post_poker_reproduction(cast("Any", poker))

    assert baby is not None
    # Opponent 1 (lower fish_id) should be selected
    assert opponent1.energy < 150.0
    assert opponent2.energy == 150.0
