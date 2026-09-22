"""Fish genomes are serialized only when a payload actually sends them.

Serializing every fish's genome on every broadcast was over half of the cost of
building a WebSocket frame, and a delta frame - most frames - never sends it.
These pin both halves: delta frames build no genome dicts, and full frames send
exactly the stripped dict the eager version used to send.
"""

from __future__ import annotations

from backend.simulation_runner import SimulationRunner
from backend.state_payloads import DeltaStatePayload, EntitySnapshot, FullStatePayload
from core.genetics.genome import Genome
from core.worlds.interfaces import FAST_STEP_ACTION


def _runner(frames: int = 30) -> SimulationRunner:
    runner = SimulationRunner(seed=42, world_id="lazy-genome-test")
    runner.running = True
    for _ in range(frames):
        runner.world.step({FAST_STEP_ACTION: True})
    return runner


def _eager_broadcast_genome(genome: Genome) -> dict:
    """The stripped dict the builder used to compute eagerly for every fish."""
    gd = genome.to_dict()
    del gd["trait_meta"]
    gd.pop("poker_strategy", None)
    if isinstance(gd.get("behavior"), dict):
        gd["behavior"].pop("parameters", None)
    return gd


def test_factory_resolves_once_and_feeds_full_dict() -> None:
    calls = []

    def factory() -> dict:
        calls.append(1)
        return {"color_hue": 0.25}

    snap = EntitySnapshot(id=1, type="fish", x=0, y=0, width=1, height=1)
    snap.genome_data_factory = factory

    assert "genome_data" not in snap.to_delta_dict()
    assert calls == []
    assert snap.to_full_dict()["genome_data"] == {"color_hue": 0.25}
    assert snap.to_full_dict()["genome_data"] == {"color_hue": 0.25}
    assert calls == [1]


def test_delta_frames_build_no_genome_dicts(monkeypatch) -> None:
    runner = _runner()
    publisher = runner.state_publisher
    publisher.get_state(runner, force_full=True, allow_delta=False)

    calls = []
    original = Genome.to_dict

    def counting_to_dict(self: Genome) -> dict:
        calls.append(1)
        return original(self)

    monkeypatch.setattr(Genome, "to_dict", counting_to_dict)
    runner.world.step({FAST_STEP_ACTION: True})
    state = publisher.get_state(runner, force_full=False, allow_delta=True)

    assert isinstance(state, DeltaStatePayload)
    # Only fish born this frame (sent in full as "added") may cost a genome dict.
    assert len(calls) == len([e for e in state.added if e.get("type") == "fish"])


def test_full_frames_send_the_same_stripped_genome_as_before() -> None:
    runner = _runner()
    state = runner.state_publisher.get_state(runner, force_full=True, allow_delta=False)
    assert isinstance(state, FullStatePayload)

    fish_by_wire_id = {}
    provider = runner.world.engine._identity_provider
    for entity in runner.world.entities_list:
        entity_type, stable_id = provider.get_identity(entity)
        if entity_type == "fish":
            fish_by_wire_id[int(stable_id)] = entity

    sent = [e.to_full_dict() for e in state.entities if e.type == "fish"]
    assert sent, "expected fish in the full snapshot"
    for payload in sent:
        fish = fish_by_wire_id[payload["id"]]
        assert payload["genome_data"] == _eager_broadcast_genome(fish.genome)
