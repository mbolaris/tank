"""Partition invariants for the pre-PR gate's test shards."""

from pathlib import Path

from tools.pre_pr_shards import (
    REMAINDER_SHARD,
    SHARD_PREFIXES,
    assign_shard,
    discover_test_files,
    resolve_shards,
    shard_names,
)

ROOT = Path(__file__).resolve().parents[1]


def test_shards_exactly_partition_discovered_test_files():
    """Every discovered test file lands in exactly one shard, none are dropped."""
    shards = resolve_shards()
    all_assigned = [test_file for files in shards.values() for test_file in files]
    assert sorted(all_assigned) == discover_test_files()
    assert len(all_assigned) == len(set(all_assigned))


def test_every_shard_is_nonempty():
    """An empty shard means dead prefixes; prune them instead of running no-ops."""
    for name, files in resolve_shards().items():
        assert files, f"shard '{name}' matched no test files"


def test_remainder_shard_is_last_and_prefix_free():
    """The remainder shard catches unmatched files, so it must not define prefixes
    and must run last (new test files fall into it automatically)."""
    assert REMAINDER_SHARD not in SHARD_PREFIXES
    assert shard_names()[-1] == REMAINDER_SHARD


def test_shard_prefixes_only_match_real_files():
    """Every prefix must match at least one discovered file; stale prefixes rot."""
    discovered = discover_test_files()
    for shard, prefixes in SHARD_PREFIXES.items():
        for prefix in prefixes:
            assert any(
                test_file.startswith(prefix) for test_file in discovered
            ), f"shard '{shard}' prefix '{prefix}' matches no test files"


def test_discovery_matches_pytest_python_files_convention():
    """Shard discovery must mirror pytest collection (python_files = test_*.py
    under tests/). If pyproject.toml widens that pattern, widen discovery too."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'python_files = ["test_*.py"]' in pyproject
    assert 'testpaths = ["tests"]' in pyproject

    for test_file in discover_test_files():
        assert test_file.startswith("tests/")
        assert Path(test_file).name.startswith("test_")


def test_assignment_is_first_match_wins_and_deterministic():
    shards = resolve_shards()
    for name, files in shards.items():
        assert files == sorted(files)
        for test_file in files:
            assert assign_shard(test_file) == name


def test_pre_pr_gate_orchestrates_shards():
    """The gate must run every shard by default and expose single-shard reruns."""
    source = (ROOT / "tools" / "pre_pr_gate.py").read_text(encoding="utf-8")
    assert "resolve_shards" in source
    assert "shard_names" in source
    assert "--shard" in source
    assert "--list-shards" in source
