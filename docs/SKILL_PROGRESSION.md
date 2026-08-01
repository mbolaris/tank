# Skill Progression: Make Evolution Visible as Entertainment

> **Goal:** a viewer watching a live tank for five minutes — without opening the Lab —
> can correctly answer: Which fish is currently best? Is the tank getting better?
> What milestone was recently reached? Which lineage produced the breakthrough?

Today's leaderboards show who *accumulated* the most results (lifetime wins, career
goals, current rank). Those numbers can move without genuine improvement, because
population-vs-population results are zero-sum. The question that makes evolution
watchable — *"are these fish actually better than their ancestors?"* — is only
answerable against **frozen references**, and the project already measures that way at
the benchmark layer. What is missing is applying the same doctrine to the **live,
evolving population** and surfacing it as a player-facing progression layer.

This document is the plan of record for that track. It expands the U12 brief in
[UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md) and slots into the delivery sequence of
[EXPERIENCE_ROADMAP.md](EXPERIENCE_ROADMAP.md).

## What already exists (do not rebuild)

Audited 2026-07-31. The frozen-ruler measurement layer is built and is established
doctrine — but its **subject is the unevolved default substrate**, not the evolved
fish in a running tank.

| Machinery | Location | Notes |
|---|---|---|
| Skill ladder schema (`RungResult`, `SkillLadderSummary`, 0–100 `skill_index`) | `core/skill/ladder.py` | Shared shape; summaries flow into the champions registry |
| Frozen soccer rulers L0–L3 (stationary, random walk, chase-and-shoot, formation) | `core/minigames/soccer/reference_teams.py` | Immutable by contract; add `*_v2` rungs, never edit |
| Soccer ladder benchmark (side-swapped, CI-backed, per-rung `beaten`) | `benchmarks/soccer/ladder_5k.py` | Hero is the **neutral default substrate**, deliberately not evolved fish |
| Poker ladder benchmark vs frozen baseline/standard/advanced/expert | `benchmarks/poker/ladder_20k.py` | Same doctrine, same schema |
| Sandboxed live soccer league (bounded per-frame work, energy-free bots, capped leaderboard) | `core/minigames/soccer/league_runtime.py`, driven from `core/worlds/shared/tank_like_phase_hooks.py` | The incremental-evaluation pattern to copy |
| Periodic in-sim poker evaluation of top fish vs benchmark suite | `core/poker/evaluation/periodic_benchmark.py` | Exists behind `config.poker.enable_periodic_benchmarks`; history is unbounded and never surfaced to the UI |
| Append-only ledger of benchmark skill runs (per commit, substrate-level) | `core/research/skill_ledger.py`, `tools/skill_report.py` | Layer-1 longitudinal history; distinct from the per-tank live snapshots this track adds — pick non-colliding names |
| Live leaderboards / minigame UI | `frontend/src/components/MinigameLeaders.tsx`, `SoccerLeagueLive.tsx`, `PokerLeaderboard.tsx` | Fun, but zero-sum "Season Leaders", not skill progress |
| Placeholder contract for fixed-baseline soccer skill | `baseline_match_score_diff` in `backend/state_payloads/metrics.py` (always `None`) | The wired-but-empty seam this track fills |

**The gap:** nothing evaluates *evolved genomes from a live tank* against the frozen
rungs, records the trajectory per generation, or narrates it. `SoccerMatchRunner.run_episode(genomes=...)`
already accepts arbitrary genomes and fish carry evolved `soccer_policy_params`, so the
missing piece is a subject swap plus a snapshot/presentation layer — not new
measurement machinery.

## Design rules

1. **Frozen references are the only proof of improvement.** Lifetime wins, career
   goals, rank, and streaks stay in the UI as **Season Leaders** — clearly labeled fun,
   never evidence.
2. **Evaluation must not touch the ecosystem.** Matches run in the sandboxed minigame
   engines with genome *copies*; no fish energy is spent, no engine RNG is consumed, no
   simulation state mutates. Reproduction is funded by overflow energy — an evaluation
   that costs energy would suppress the very evolution it measures.
3. **Bounded state, always.** Snapshot history is capped and/or rolled up from day one
   (see the `MAX_LEADERBOARD_SIZE` precedent and the unbounded-state incident fixed in
   PR #865).
4. **Never edit an existing rung.** Add a taller `*_v2` rung instead
   (`core/minigames/soccer/reference_teams.py` module docstring is binding).
5. **Layer separation.** All of this is Layer 2 support/UI work: no behavior-algorithm,
   benchmark-scoring, or champion changes ride along. Beware that adding constants to
   any module listed in `SIM_CONFIG_MODULES` (`core/solutions/config_hash.py`) changes
   the `config_hash` of **every** champion at once. Put new evaluation flags in server
   config (explicitly excluded from the hash) or another non-hashed seam.
6. **Reuse the shared schema.** Snapshots embed `SkillLadderSummary.to_dict()` rather
   than inventing a parallel record shape.

## Delivery sequence

One row is one PR. S1 is the enabling PR; S2 delivers the first visible win.

| Order | ID | Deliverable | Status | Depends on |
|---:|---|---|---|---|
| 1 | S1 | Live soccer ladder evaluation + bounded skill snapshot store + API | NEXT | — |
| 2 | S2 | Skill Progress UI panel; relabel existing boards "Season Leaders" | QUEUED | S1 |
| 3 | S3 | Per-fish poker skill vs frozen opponents (build on `periodic_benchmark.py`) | QUEUED | S1 |
| 4 | S4 | Breakthrough events (tank record, rung beaten, parent surpassed) into Insights | QUEUED | S1, E3 |

### S1 — Live soccer ladder evaluation and skill snapshot store

Periodically evaluate the tank's current best team (top fish by existing soccer stats,
genome copies) against the frozen L0–L3 ladder, side-swapped with derived seeds, using
the `SoccerLeagueRuntime` incremental pattern so per-frame work stays bounded. Record a
snapshot per completed ladder pass:

```text
domain, generation, frame, subject fish ids + lineage,
SkillLadderSummary (rungs beaten, per-rung goal diff),
previous score, personal best, tank best, sample size
```

Store snapshots in a capped store, persist with the world, expose via a backend API,
and populate the `baseline_match_score_diff` metrics field so Trends can chart it.
This completes U12's acceptance criteria (baseline id/version + cadence recorded; no
population/energy/RNG side effects; deterministic seeded tests).

### S2 — Skill Progress display

A compact panel above the existing soccer leaderboard:

```text
SOCCER PROGRESS
Tank level: L2 Chase-and-Shoot beaten
Best team skill: 50 (2/4 rungs)   vs Formation: -0.4 goals/match (was -1.3)
Since generation 8: +0.9
```

Current leaderboards remain directly beneath, retitled **Season Leaders**.

### S3 — Poker per-fish skill

Extend `PeriodicBenchmarkEvaluator` (cap its history, surface it) to produce the same
snapshot shape: per-fish `bb/100` vs the frozen opponent suite, paired deals, personal
best and tank record. Reuses `core/poker/strategy/implementations/` as the rungs.

### S4 — Breakthrough events

Only the highest-value events, emitted from snapshot transitions and fed into the
structured story-event schema (E3) and Insights feed:

- `tank_skill_record` — a snapshot exceeds the tank's best-ever score
- `soccer_ladder_rung_beaten` / `poker_rung_beaten` — first time a rung's `beaten`
  flips true for this tank
- `parent_surpassed` — a fish's skill exceeds its parent's best snapshot

Depends on E3 landing first (or serves as the forcing function to land it); do not
build a parallel event store.

## Explicitly deferred

- **Standardized individual soccer attribution** (fixed teammates/opponents/role,
  per-fish contribution scoring). A research project, not a UI feature; team-level
  ladder progress plus Season Leaders covers the alpha.
- **"Why is this fish improving" interpretable metrics** (fold discipline, assist
  rates, turnover rates). Good v2 material once snapshots exist to hang them on.
- Multi-game "star" events, lineage breakthrough streaks, sparkline polish.

## Success criterion

The product-research question for the first campaign is not "can fish scientifically
improve?" — the benchmarks already answer that for the substrate. It is:

> **Can a viewer recognize skill evolution without opening the Lab?**

Five minutes of watching should let a newcomer name the current best fish, say whether
the tank is improving, and cite the most recent milestone. Instrument the alpha
accordingly (see [EXPERIENCE_ROADMAP.md](EXPERIENCE_ROADMAP.md) alpha definition).

---

*Created 2026-07-31 from a repository audit of the skill/ladder machinery.*
