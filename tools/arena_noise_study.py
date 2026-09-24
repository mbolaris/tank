#!/usr/bin/env python3
"""Champions Tank A0 noise study: is an arena share set by the house or by the seed?

Three steps, each writing JSON under ``research/arena/``:

    # 1. Capture: run ordinary evolving tanks and keep the leading taxon of each
    python tools/arena_noise_study.py capture --seeds 1-10 --frames 30000 \
        --out research/arena/roster_a0.json

    # 2. Melee: the captured houses compete in clonal arena matches
    python tools/arena_noise_study.py melee --roster research/arena/roster_a0.json \
        --seeds 1001-1020 --out research/arena/melee_cap60.json

    # 3. Analyze: apply the pre-registered decision rule (docs/CHAMPIONS_TANK.md)
    python tools/arena_noise_study.py analyze research/arena/melee_cap60.json

This is a prototype. The arena rules the design needs from the engine
(offspring are exact copies of a parent, no emergency spawns) are applied here
by patching, only inside arena matches; A2 replaces the patches with world
config flags. Houses are isolated with ``Fish.species``, which every mating
path already requires to match.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import random
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.tank.survival_5k import WORLD_CONFIG
from core.research.arena_noise import select_seed_pack, summarize_pair, summarize_shares, verdict

MATCH_FRAMES = 12_000
SETTLE_START = 9_000
CHALLENGER_INSERT_FRAME = 3_000
PACK_SIZE = 5
SERIES_EVERY = 250


def parse_seeds(raw: str) -> list[int]:
    """Parse ``"1-10"``, ``"1,2,5"`` or a mix of both."""
    seeds: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-", 1))
            seeds.extend(range(lo, hi + 1))
        elif part:
            seeds.append(int(part))
    if len(set(seeds)) != len(seeds):
        raise ValueError("--seeds must not contain duplicates")
    return seeds


def _fish(world: Any) -> list[Any]:
    return [e for e in world.entities_list if getattr(e, "snapshot_type", None) == "fish"]


def _new_world(seed: int, overrides: dict[str, Any]) -> Any:
    from core.worlds import WorldRegistry

    config = {**WORLD_CONFIG, **overrides}
    world = WorldRegistry.create_world("tank", seed=seed, config=config)
    world.reset(seed=seed, config=config)
    return world


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------


def capture_one(seed: int, frames: int) -> dict[str, Any]:
    """Run an ordinary evolving tank and return a seed pack of its leading taxon."""
    from core.worlds.interfaces import FAST_STEP_ACTION

    start = time.time()
    world = _new_world(seed, {})
    for _ in range(frames):
        world.step({FAST_STEP_ACTION: True})

    registry = world.ecosystem.taxonomy.registry
    by_taxon: dict[str, list[Any]] = {}
    for fish in _fish(world):
        if fish.taxon_id:
            by_taxon.setdefault(fish.taxon_id, []).append(fish)

    def rank(taxon_id: str) -> tuple[int, int, str]:
        established = registry.species[taxon_id].status == "established"
        return (int(established), len(by_taxon[taxon_id]), taxon_id)

    leader = max(by_taxon, key=rank)
    record = registry.species[leader]
    members = {f.fish_id: f for f in by_taxon[leader]}
    profiles = {
        i: record.member_profiles_cache.get(i)
        or world.ecosystem.taxonomy.fish_builder.build_profile(f)
        for i, f in members.items()
    }
    pack_ids = select_seed_pack(list(members), lambda a, b: profiles[a].distance(profiles[b]))
    genomes = [members[i].genome.to_dict() for i in pack_ids]
    while len(genomes) < PACK_SIZE:  # a taxon smaller than the pack repeats its members
        genomes.append(genomes[len(genomes) % len(pack_ids)])

    return {
        "source_seed": seed,
        "source_frames": frames,
        "taxon_id": leader,
        "status": record.status,
        "common_name": record.common_name,
        "scientific_name": record.scientific_name,
        "living_members": len(members),
        "taxa_alive": len(by_taxon),
        "fish_alive": len(_fish(world)),
        "generation_range": [
            min(f.generation for f in members.values()),
            max(f.generation for f in members.values()),
        ],
        "pack_fish_ids": pack_ids,
        "seed_pack": genomes,
        "runtime_seconds": round(time.time() - start, 1),
    }


# ---------------------------------------------------------------------------
# Arena match
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def arena_rules(counters: dict[str, int]) -> Iterator[None]:
    """Clonal births and no emergency spawns, for the duration of one match."""
    import core.genetics.code_policy_traits as code_policy_traits
    import core.reproduction.asexual_factory as asexual_factory
    from core.genetics import Genome
    from core.reproduction.reproduction_service import ReproductionService

    def copy_of(genome: Genome) -> Genome:
        return Genome.from_dict(genome.to_dict(), rng=random.Random(0))

    def weighted(
        cls: type[Genome],
        parent1: Genome,
        parent2: Genome,
        parent1_weight: float = 0.5,
        *args: Any,
        rng: random.Random | None = None,
        **kwargs: Any,
    ) -> Genome:
        counters["clonal_births"] += 1
        if parent1 is parent2 or parent1_weight >= 1.0 or rng is None:
            return copy_of(parent1)
        return copy_of(parent1 if rng.random() < parent1_weight else parent2)

    def recombined(
        cls: type[Genome],
        parent1: Genome,
        parent2: Genome,
        *args: Any,
        rng: random.Random | None = None,
        **kwargs: Any,
    ) -> Genome:
        counters["clonal_births"] += 1
        if rng is None:
            return copy_of(parent1)
        return copy_of(parent1 if rng.random() < 0.5 else parent2)

    def no_emergency(self: Any, frame: int, fish_count: int) -> int:
        counters["emergency_spawns_blocked"] += 1 if fish_count == 0 else 0
        return 0

    def no_policy_mutation(behavioral: Any, *args: Any, **kwargs: Any) -> Any:
        return behavioral

    saved = (
        Genome.__dict__["from_parents_weighted"],
        Genome.__dict__["from_parents"],
        ReproductionService._handle_emergency_spawning,
        code_policy_traits.mutate_code_policies,
        asexual_factory.mutate_code_policies,
    )
    Genome.from_parents_weighted = classmethod(weighted)  # type: ignore[method-assign,assignment]
    Genome.from_parents = classmethod(recombined)  # type: ignore[method-assign,assignment]
    ReproductionService._handle_emergency_spawning = no_emergency  # type: ignore[method-assign]
    code_policy_traits.mutate_code_policies = no_policy_mutation
    asexual_factory.mutate_code_policies = no_policy_mutation
    try:
        yield
    finally:
        (
            Genome.from_parents_weighted,  # type: ignore[method-assign]
            Genome.from_parents,  # type: ignore[method-assign]
            ReproductionService._handle_emergency_spawning,  # type: ignore[method-assign]
            code_policy_traits.mutate_code_policies,
            asexual_factory.mutate_code_policies,
        ) = saved


def _add_founders(
    world: Any, house: str, pack: list[dict[str, Any]], copies: int, placement: random.Random
) -> None:
    from core import movement_strategy
    from core.config.fish import FISH_BASE_SPEED
    from core.entities import Fish
    from core.genetics import Genome

    (min_x, min_y), (max_x, max_y) = world.environment.get_bounds()
    margin = 60
    for _ in range(copies):
        for genome_data in pack:
            fish = Fish(
                world.environment,
                movement_strategy.AlgorithmicMovement(),
                house,
                placement.uniform(min_x + margin, max_x - margin),
                placement.uniform(min_y + margin, max_y - margin),
                FISH_BASE_SPEED,
                genome=Genome.from_dict(genome_data, rng=random.Random(0)),
                generation=0,
                ecosystem=world.ecosystem,
            )
            fish.register_birth()
            world.add_entity(fish)


def run_match(
    packs: list[list[dict[str, Any]]],
    seed: int,
    *,
    copies: int = 1,
    max_population: int = 60,
    challenger: int | None = None,
    frames: int = MATCH_FRAMES,
    settle_start: int = SETTLE_START,
) -> dict[str, Any]:
    """One clonal arena match; returns per-house readouts.

    With ``challenger`` set, that house is held back until
    ``CHALLENGER_INSERT_FRAME`` and then dropped into the settled community.
    """
    from core.worlds.interfaces import FAST_STEP_ACTION

    counters = {"clonal_births": 0, "emergency_spawns_blocked": 0}
    houses = [f"house_{i:02d}" for i in range(len(packs))]
    start = time.time()
    with arena_rules(counters):
        world = _new_world(seed, {"num_schooling_fish": 0, "max_population": max_population})
        placement = random.Random(f"arena-placement-{seed}")
        for i, house in enumerate(houses):
            if i != challenger:
                _add_founders(world, house, packs[i], copies, placement)

        settle_sum = [0.0] * len(houses)
        settle_frames = 0
        extinct_at: list[int | None] = [None] * len(houses)
        series: list[list[int]] = []
        foreign_species: set[str] = set()
        index = {h: i for i, h in enumerate(houses)}
        for frame in range(1, frames + 1):
            if challenger is not None and frame == CHALLENGER_INSERT_FRAME + 1:
                _add_founders(world, houses[challenger], packs[challenger], copies, placement)
            world.step({FAST_STEP_ACTION: True})

            counts = [0] * len(houses)
            for fish in _fish(world):
                slot = index.get(fish.species)
                if slot is None:
                    foreign_species.add(str(fish.species))
                else:
                    counts[slot] += 1
            total = sum(counts)
            for i, c in enumerate(counts):
                present = challenger != i or frame > CHALLENGER_INSERT_FRAME
                if present and c == 0 and extinct_at[i] is None:
                    extinct_at[i] = frame
            if frame > settle_start and total:
                settle_frames += 1
                for i, c in enumerate(counts):
                    settle_sum[i] += c / total
            if frame % SERIES_EVERY == 0:
                series.append(counts)

    final = series[-1] if series else [0] * len(houses)
    return {
        "seed": seed,
        "copies": copies,
        "max_population": max_population,
        "challenger": challenger,
        "frames": frames,
        "settle_start": settle_start,
        "settled_share": [s / settle_frames if settle_frames else 0.0 for s in settle_sum],
        "alive": [c > 0 for c in final],
        "final_counts": final,
        "extinction_frame": extinct_at,
        "series_every": SERIES_EVERY,
        "series": series,
        "clonal_births": counters["clonal_births"],
        "emergency_spawns_blocked": counters["emergency_spawns_blocked"],
        "foreign_species": sorted(foreign_species),
        "runtime_seconds": round(time.time() - start, 1),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _match_job(job: tuple[list[list[dict[str, Any]]], int, dict[str, Any]]) -> dict[str, Any]:
    packs, seed, kwargs = job
    return run_match(packs, seed, **kwargs)


def _capture_job(job: tuple[int, int]) -> dict[str, Any]:
    return capture_one(*job)


def _write(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=1) + "\n")
    print(f"wrote {path}", file=sys.stderr)


def cmd_capture(args: argparse.Namespace) -> None:
    seeds = parse_seeds(args.seeds)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        houses = list(pool.map(_capture_job, [(s, args.frames) for s in seeds]))
    for h in houses:
        print(
            f"seed {h['source_seed']}: {h['taxon_id']} ({h['status']}, {h['common_name']}) "
            f"{h['living_members']}/{h['fish_alive']} fish, gens {h['generation_range']}, "
            f"{h['runtime_seconds']}s",
            file=sys.stderr,
        )
    _write(args.out, {"kind": "arena_roster_a0", "houses": houses})


def cmd_melee(args: argparse.Namespace) -> None:
    roster = json.loads(Path(args.roster).read_text())
    packs = [h["seed_pack"] for h in roster["houses"]]
    seeds = parse_seeds(args.seeds)
    kwargs: dict[str, Any] = {
        "copies": args.copies,
        "max_population": args.max_population,
        "challenger": args.challenger,
    }
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        matches = list(pool.map(_match_job, [(packs, s, kwargs) for s in seeds]))
    for m in matches:
        shares = " ".join(f"{s:.2f}" for s in m["settled_share"])
        print(f"seed {m['seed']}: [{shares}] {m['runtime_seconds']}s", file=sys.stderr)
    _write(
        args.out,
        {
            "kind": "arena_melee_a0",
            "roster": args.roster,
            "config": {**kwargs, "frames": MATCH_FRAMES, "settle_start": SETTLE_START},
            "matches": matches,
        },
    )


def _parse_pairs(raw: str) -> list[tuple[int, int]]:
    pairs = []
    for item in raw.split(","):
        a, b = item.split(":")
        pairs.append((int(a), int(b)))
    return pairs


def cmd_pairwise(args: argparse.Namespace) -> None:
    """Head-to-head matches: two houses per tank, same seeds for every pair."""
    roster = json.loads(Path(args.roster).read_text())
    packs = [h["seed_pack"] for h in roster["houses"]]
    pairs = _parse_pairs(args.pairs)
    seeds = parse_seeds(args.seeds)
    kwargs: dict[str, Any] = {"copies": args.copies, "max_population": args.max_population}
    jobs = [([packs[a], packs[b]], s, kwargs) for a, b in pairs for s in seeds]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(_match_job, jobs))
    matches = []
    for (a, b), result in zip([p for p in pairs for _ in seeds], results, strict=True):
        result["pair"] = [a, b]
        matches.append(result)
        print(
            f"{a} vs {b} seed {result['seed']}: "
            f"{result['settled_share'][0]:.2f} / {result['settled_share'][1]:.2f}",
            file=sys.stderr,
        )
    _write(
        args.out,
        {
            "kind": "arena_pairwise_a0",
            "roster": args.roster,
            "config": {**kwargs, "frames": MATCH_FRAMES, "settle_start": SETTLE_START},
            "matches": matches,
        },
    )


def cmd_analyze_pairwise(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.pairwise).read_text())
    by_pair: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for m in data["matches"]:
        by_pair.setdefault((m["pair"][0], m["pair"][1]), []).append(m)
    pairs = []
    for (a, b), matches in by_pair.items():
        summary = summarize_pair(
            [m["settled_share"][0] for m in matches], [m["settled_share"][1] for m in matches]
        )
        pairs.append({"pair": [a, b], "seeds": len(matches), **summary})
    decided = [p for p in pairs if p["wins"] + p["losses"]]
    report = {
        "pairs": pairs,
        "mean_majority_agreement": sum(p["majority_agreement"] for p in decided) / len(decided),
        "pooled_difference_sd": (sum(p["difference_sd"] ** 2 for p in pairs) / len(pairs)) ** 0.5,
        "pairs_significant_at_0.05": sum(p["sign_test_p"] < 0.05 for p in pairs),
    }
    print(json.dumps(report, indent=1))
    if args.out:
        _write(args.out, {"kind": "arena_pairwise_a0_analysis", **report})


def cmd_analyze(args: argparse.Namespace) -> None:
    melee = json.loads(Path(args.melee).read_text())
    matches = melee["matches"]
    houses = len(matches[0]["settled_share"])
    shares = [[m["settled_share"][h] for m in matches] for h in range(houses)]
    alive = [[m["alive"][h] for m in matches] for h in range(houses)]
    summary = summarize_shares(shares, alive)
    summary["verdict"] = verdict(summary)
    summary["checks"] = {
        "foreign_species": sorted({s for m in matches for s in m["foreign_species"]}),
        "total_clonal_births": sum(m["clonal_births"] for m in matches),
        "matches": len(matches),
    }
    print(json.dumps(summary, indent=1))
    if args.out:
        _write(args.out, {"kind": "arena_noise_a0_analysis", "melee": args.melee, **summary})


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    cap = sub.add_parser("capture", help="Run evolving tanks and capture each one's leading taxon")
    cap.add_argument("--seeds", default="1-10")
    cap.add_argument("--frames", type=int, default=30_000)
    cap.add_argument("--workers", type=int, default=4)
    cap.add_argument("--out", required=True)
    cap.set_defaults(func=cmd_capture)

    mel = sub.add_parser("melee", help="Run clonal arena matches for a captured roster")
    mel.add_argument("--roster", required=True)
    mel.add_argument("--seeds", default="1001-1020")
    mel.add_argument("--copies", type=int, default=1, help="Founding copies of each pack genome")
    mel.add_argument("--max-population", type=int, default=60)
    mel.add_argument("--challenger", type=int, help="Hold this house back until frame 3,000")
    mel.add_argument("--workers", type=int, default=4)
    mel.add_argument("--out", required=True)
    mel.set_defaults(func=cmd_melee)

    pw = sub.add_parser("pairwise", help="Head-to-head matches between pairs of houses")
    pw.add_argument("--roster", required=True)
    pw.add_argument("--pairs", required=True, help='e.g. "0:1,1:2"')
    pw.add_argument("--seeds", default="1001-1006")
    pw.add_argument("--copies", type=int, default=1)
    pw.add_argument("--max-population", type=int, default=60)
    pw.add_argument("--workers", type=int, default=4)
    pw.add_argument("--out", required=True)
    pw.set_defaults(func=cmd_pairwise)

    apw = sub.add_parser("analyze-pairwise", help="Summarize head-to-head consistency")
    apw.add_argument("pairwise")
    apw.add_argument("--out")
    apw.set_defaults(func=cmd_analyze_pairwise)

    ana = sub.add_parser("analyze", help="Apply the pre-registered A0 decision rule")
    ana.add_argument("melee")
    ana.add_argument("--out")
    ana.set_defaults(func=cmd_analyze)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
