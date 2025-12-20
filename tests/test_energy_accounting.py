import math

from core.ecosystem import EcosystemManager
from core.entities import Fish
from core.entities.plant import Plant
from core.poker_interaction import PokerInteraction
from core.mixed_poker import MixedPokerInteraction, MixedPokerResult
from core.movement_strategy import AlgorithmicMovement
from core.genetics import PlantGenome
from core.simulation_engine import SimulationEngine
from core.skill_game_system import SkillGameSystem
from core.skills.base import SkillGameResult
from core.skills.config import SkillGameConfig


class _EnvStub:
    def __init__(self, width: int = 800, height: int = 600) -> None:
        self.width = width
        self.height = height
        self.agents = []

    def get_bounds(self):
        return (0.0, 0.0), (float(self.width), float(self.height))


class _RootSpotStub:
    def __init__(self, x: float = 100.0, y: float = 550.0, spot_id: int = 12) -> None:
        self.x = x
        self.y = y
        self.spot_id = spot_id
        self.manager = None

    def release(self) -> None:  # pragma: no cover - used by die()
        return None


def test_skill_game_records_energy_transfer(simulation_env):
    _unused_env, _agents_wrapper = simulation_env

    ecosystem = EcosystemManager()
    env = _EnvStub()

    fish1 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        ecosystem=ecosystem,
    )
    fish2 = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=120,
        y=100,
        speed=2.0,
        ecosystem=ecosystem,
    )

    fish1.energy = fish1.max_energy * 0.4
    fish2.energy = fish2.max_energy * 0.4

    cfg = SkillGameConfig(stake_multiplier=1.0)
    engine_stub = object()
    system = SkillGameSystem(engine_stub, config=cfg)

    result1 = SkillGameResult(
        player_id="fish1",
        opponent_id="fish2",
        won=True,
        score_change=10.0,
        was_optimal=True,
    )

    transferred = system._apply_energy_changes(fish1, fish2, result1, None)
    assert transferred > 0

    assert math.isclose(ecosystem.energy_sources.get("skill_game", 0.0), transferred, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(ecosystem.energy_burn.get("skill_game", 0.0), transferred, rel_tol=0, abs_tol=1e-9)


def test_single_player_skill_game_records_energy_delta(simulation_env):
    _unused_env, _agents_wrapper = simulation_env

    ecosystem = EcosystemManager()
    env = _EnvStub()

    fish = Fish(
        environment=env,
        movement_strategy=AlgorithmicMovement(),
        species="test",
        x=100,
        y=100,
        speed=2.0,
        ecosystem=ecosystem,
    )

    fish.energy = fish.max_energy * 0.2

    cfg = SkillGameConfig(stake_multiplier=1.0)
    engine_stub = object()
    system = SkillGameSystem(engine_stub, config=cfg)

    win = SkillGameResult(
        player_id="fish",
        opponent_id=None,
        won=True,
        score_change=7.0,
        was_optimal=True,
    )
    delta = system._apply_energy_changes(fish, None, win, None)
    assert delta > 0
    assert math.isclose(ecosystem.energy_sources.get("skill_game_env", 0.0), delta, rel_tol=0, abs_tol=1e-9)

    loss = SkillGameResult(
        player_id="fish",
        opponent_id=None,
        won=False,
        score_change=-5.0,
        was_optimal=False,
    )
    delta2 = system._apply_energy_changes(fish, None, loss, None)
    assert delta2 < 0
    assert math.isclose(ecosystem.energy_burn.get("skill_game_env", 0.0), -delta2, rel_tol=0, abs_tol=1e-9)








def test_plant_records_energy_gains_and_spends(simulation_env):
    _unused_env, _agents_wrapper = simulation_env

    ecosystem = EcosystemManager()
    env = _EnvStub()
    spot = _RootSpotStub(spot_id=12)
    genome = PlantGenome.create_random()

    plant = Plant(
        environment=env,
        genome=genome,
        root_spot=spot,
        initial_energy=1.0,
        ecosystem=ecosystem,
    )

    before_energy = plant.energy
    plant._collect_energy(time_modifier=1.0)
    assert plant.energy >= before_energy
    assert ecosystem.plant_energy_sources.get("photosynthesis", 0.0) > 0.0

    loss = plant.lose_energy(1.0, source="poker")
    assert loss >= 0.0
    if loss > 0:
        assert math.isclose(ecosystem.plant_energy_burn.get("poker", 0.0), loss, rel_tol=0, abs_tol=1e-9)

    gain = plant.gain_energy(1.0, source="poker")
    if gain > 0:
        assert math.isclose(
            ecosystem.plant_energy_sources.get("poker", 0.0),
            gain,
            rel_tol=0,
            abs_tol=1e-9,
        )


def test_energy_net_flow_reconciles_with_energy_delta_window():
    ecosystem = EcosystemManager()
    fish_count = 10
    total_energy = 100.0

    # Simulate 10 frames with deterministic, recorded energy gains/burns.
    for frame in range(1, 11):
        ecosystem.update(frame)

        gain = float(frame)  # 1..10
        burn = float(frame) * 0.25  # 0.25..2.5

        ecosystem.record_energy_gain("nectar", gain)
        ecosystem.record_energy_burn("metabolism", burn)

        total_energy += gain - burn
        ecosystem.record_energy_snapshot(total_energy, fish_count)

    window_frames = 5
    gains_recent = ecosystem.get_recent_energy_breakdown(window_frames=window_frames)
    burns_recent = ecosystem.get_recent_energy_burn(window_frames=window_frames)
    net_flow = sum(gains_recent.values()) - sum(burns_recent.values())

    energy_delta = ecosystem.get_energy_delta(window_frames=window_frames)["energy_delta"]
    assert math.isclose(net_flow, energy_delta, rel_tol=0, abs_tol=1e-9)


def test_mixed_poker_house_cut_only_hits_fish_when_fish_wins():
    engine = SimulationEngine(headless=True)
    engine.setup()
    assert engine.ecosystem is not None

    all_entities = engine.get_all_entities()
    fish = next(e for e in all_entities if isinstance(e, Fish))
    plant = next(e for e in all_entities if isinstance(e, Plant))

    fish.energy = 50.0
    plant.energy = 50.0

    poker = MixedPokerInteraction([fish, plant])

    # Simulate a fish win with a house cut:
    # fish: +8, plant: -10, house_cut: 2  => total delta = -2
    fish.energy = 58.0
    plant.energy = 40.0

    poker.result = MixedPokerResult(
        winner_id=poker._get_player_id(fish),
        winner_type="fish",
        winner_hand=None,
        loser_ids=[poker._get_player_id(plant)],
        loser_types=["plant"],
        loser_hands=[None],
        energy_transferred=8.0,
        total_pot=20.0,
        house_cut=2.0,
        is_tie=False,
        tied_player_ids=[],
        player_count=2,
        fish_count=1,
        plant_count=1,
    )

    engine._handle_mixed_poker_result(poker)

    assert math.isclose(engine.ecosystem.energy_sources.get("poker_plant", 0.0), 10.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(engine.ecosystem.energy_burn.get("poker_house_cut", 0.0), 2.0, rel_tol=0, abs_tol=1e-9)
    assert engine.ecosystem.plant_energy_burn.get("poker_house_cut", 0.0) == 0.0


def test_mixed_poker_house_cut_only_hits_plants_when_plant_wins():
    engine = SimulationEngine(headless=True)
    engine.setup()
    assert engine.ecosystem is not None

    all_entities = engine.get_all_entities()
    fish = next(e for e in all_entities if isinstance(e, Fish))
    plant = next(e for e in all_entities if isinstance(e, Plant))

    fish.energy = 50.0
    plant.energy = 50.0

    poker = MixedPokerInteraction([fish, plant])

    # Simulate a plant win with a house cut.
    # fish: -10, plant: +8, house_cut: 2 => total delta = -2
    fish.energy = 40.0
    plant.gain_energy(8.0, source="poker")

    poker.result = MixedPokerResult(
        winner_id=poker._get_player_id(plant),
        winner_type="plant",
        winner_hand=None,
        loser_ids=[poker._get_player_id(fish)],
        loser_types=["fish"],
        loser_hands=[None],
        energy_transferred=8.0,
        total_pot=20.0,
        house_cut=2.0,
        is_tie=False,
        tied_player_ids=[],
        player_count=2,
        fish_count=1,
        plant_count=1,
    )

    engine._handle_mixed_poker_result(poker)

    assert math.isclose(engine.ecosystem.energy_burn.get("poker_plant_loss", 0.0), 10.0, rel_tol=0, abs_tol=1e-9)
    assert engine.ecosystem.energy_burn.get("poker_house_cut", 0.0) == 0.0

    assert math.isclose(engine.ecosystem.plant_energy_sources.get("poker", 0.0), 10.0, rel_tol=0, abs_tol=1e-9)
    assert math.isclose(engine.ecosystem.plant_energy_burn.get("poker_house_cut", 0.0), 2.0, rel_tol=0, abs_tol=1e-9)
