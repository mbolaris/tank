import json
import random

from core.genetics import Genome


def test_debug_snapshot_is_json_serializable() -> None:
    rng = random.Random(123)
    genome = Genome.random(use_algorithm=False, rng=rng)

    snapshot = genome.debug_snapshot()
    assert isinstance(snapshot, dict)
    assert "trait_meta" in snapshot
    assert "derived" in snapshot

    json.dumps(snapshot)

