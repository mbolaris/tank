"""Shard definitions for the pre-PR gate.

The broad non-slow suite (~2000 tests) is split into named, thematically
coherent shards so contributors and agents can isolate failures without
re-running everything:

  worlds        - soccer, poker, RCSS, petri, and other world-specific rules
  evolution     - genetics, genomes, traits, mutation, selection, code pools
  backend_tools - backend API, websockets, persistence, tools, docs, benchmarks
  core          - the remainder: engine, determinism, energy, entities,
                  protocols, and architecture contracts

Membership is decided by matching each collected test file's repo-relative
path against ordered prefix lists (first match wins); files that match no
prefix fall into the ``core`` remainder shard. Because ``core`` is defined
as the remainder, the shards always partition the collected files exactly:
every test file lands in exactly one shard, and new test files are picked
up automatically. ``tests/test_pre_pr_shards.py`` enforces the partition
invariants.

File discovery mirrors pytest collection: ``pyproject.toml`` sets
``python_files = ["test_*.py"]`` under ``testpaths = ["tests"]``, so shards
glob ``tests/**/test_*.py``. Marker filtering (``not slow and not
integration and not manual``) stays the gate's job, exactly as before.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = REPO_ROOT / "tests"

# The remainder shard: any collected test file not claimed by a prefix below.
REMAINDER_SHARD = "core"

# Ordered shard -> path-prefix definitions (repo-relative, posix separators).
# Earlier shards win when prefixes overlap.
SHARD_PREFIXES: dict[str, tuple[str, ...]] = {
    "worlds": (
        "tests/test_soccer",
        "tests/test_poker",
        "tests/test_rcss",
        "tests/test_texas",
        "tests/test_ball",
        "tests/test_composable",
        "tests/test_human_poker",
        "tests/test_ecosystem_poker",
        "tests/test_mixed_poker",
        "tests/test_post_poker",
        "tests/test_tank_soccer",
        "tests/test_crab",
        "tests/test_petri",
        "tests/test_zigzag",
    ),
    "evolution": (
        "tests/test_gen",
        "tests/test_evolution",
        "tests/test_trait",
        "tests/test_mutation",
        "tests/test_reproduction",
        "tests/test_hgt",
        "tests/test_proximity",
        "tests/test_selection",
        "tests/test_migration",
        "tests/test_diversity",
        "tests/test_algorithm",
        "tests/test_code_pool",
        "tests/test_visual_genetics",
        "tests/test_behavioral",
        "tests/test_per_kind",
        "tests/test_policy",
        "tests/test_fish_policy",
        "tests/test_life_evolution",
        "tests/test_agent_memory",
        "tests/test_solution_tracking",
        "tests/test_population_tracker",
    ),
    "backend_tools": (
        "tests/test_backend",
        "tests/test_websocket",
        "tests/test_commentary",
        "tests/test_auto_save",
        "tests/test_persistence",
        "tests/test_shutdown",
        "tests/test_startup",
        "tests/test_world_manager",
        "tests/test_world_broadcast",
        "tests/test_demo_tool",
        "tests/test_run_bench",
        "tests/test_gate_common",
        "tests/test_pre_pr",
        "tests/test_validation",
        "tests/test_tally",
        "tests/test_docs",
        "tests/test_security",
        "tests/test_champion",
        "tests/test_benchmark",
        "tests/test_serializers",
        "tests/test_telemetry",
        "tests/test_metrics",
        "tests/test_entity_snapshot",
        "tests/test_entity_transfer",
        "tests/test_tank_snapshot",
        "tests/test_fingerprint",
        "tests/test_replay",
        "tests/test_mode_switch",
        "tests/test_guardrails",
        "tests/test_multi_engine",
        "tests/test_long_run",
        "tests/test_connector",
    ),
}


def shard_names() -> list[str]:
    """All shard names in run order (remainder shard last)."""
    return [*SHARD_PREFIXES, REMAINDER_SHARD]


def discover_test_files() -> list[str]:
    """Repo-relative posix paths of every file pytest would collect from tests/."""
    return sorted(path.relative_to(REPO_ROOT).as_posix() for path in TESTS_DIR.rglob("test_*.py"))


def assign_shard(test_file: str) -> str:
    """Return the shard owning a repo-relative test file path (first match wins)."""
    for shard, prefixes in SHARD_PREFIXES.items():
        if any(test_file.startswith(prefix) for prefix in prefixes):
            return shard
    return REMAINDER_SHARD


def resolve_shards() -> dict[str, list[str]]:
    """Map every shard name to its sorted list of test files (exact partition)."""
    shards: dict[str, list[str]] = {name: [] for name in shard_names()}
    for test_file in discover_test_files():
        shards[assign_shard(test_file)].append(test_file)
    return shards
