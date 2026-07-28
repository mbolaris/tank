"""Fails fast when a champion's recorded config_hash goes stale.

Motivation
----------
``config_hash`` covers *every* module in
``core.solutions.config_hash.SIM_CONFIG_MODULES`` for *every* benchmark, so a
change to one domain's config invalidates every other domain's champions too.
That is exactly what happened here: editing ``core/config/fish.py``
(``EXISTENCE_ENERGY_COST`` 0.035 -> 0.025, ``LIFE_STAGE_MATURE_MAX`` 5400 ->
1800) invalidated the ``poker/ladder_20k`` and ``soccer/training_*`` champions,
whose scores reproduce bit-for-bit and cannot depend on fish energy costs.

Only the nightly ``verify-champions`` job noticed, and it had already been red
since 2026-06-22, so the staleness sat unnoticed for weeks. This test recomputes
each champion's hash from the current tree, which is pure hashing - no
simulation - so it can run in the ordinary PR gates and fail the moment a config
edit invalidates a champion record.

Note what this does and does not prove. A matching hash means the champion was
recorded under today's configuration; it does *not* mean the score still
reproduces, because code changes move scores without touching config (see
d94ae59d). Score reproduction remains the job of
``tools/verify_all_champions.py``.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

from core.solutions.config_hash import compute_config_hash

ROOT = Path(__file__).resolve().parents[1]
CHAMPIONS = ROOT / "champions"


def _champion_files() -> list[Path]:
    return sorted(CHAMPIONS.glob("**/*.json"))


def _load_active(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("champion", data)


@pytest.mark.parametrize("path", _champion_files(), ids=lambda p: p.stem)
def test_champion_config_hash_matches_current_tree(path: Path) -> None:
    """Every champion must be recorded under today's effective configuration."""
    data = json.loads(path.read_text(encoding="utf-8"))
    benchmark_id = data["benchmark_id"]
    active = _load_active(path)

    recorded = active.get("config_hash")
    assert recorded, f"{path.name}: active champion has no config_hash"

    module = importlib.import_module("benchmarks." + benchmark_id.replace("/", "."))
    expected = compute_config_hash(benchmark_id, active["seed"], getattr(module, "CONFIG", None))

    assert recorded == expected, (
        f"{benchmark_id} champion config_hash is stale.\n"
        f"  recorded: {recorded}\n"
        f"  current:  {expected}\n"
        "A core/config change has invalidated this champion record. Re-verify the "
        "benchmark still reproduces the recorded score, then refresh the hash - or "
        "re-baseline the champion if the score genuinely moved.\n"
        f"  python tools/run_bench.py benchmarks/{benchmark_id}.py "
        f"--seed {active['seed']}"
    )


def test_every_champion_is_covered() -> None:
    """Guard against the parametrisation silently collecting nothing."""
    assert (
        len(_champion_files()) >= 6
    ), "Expected at least 6 champion files; the glob may have broken."
