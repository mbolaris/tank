# Subsystem Classification

Tank World has accumulated many subsystems, and reviews keep re-asking the
same question: *is this scope creep or is it the point?* This document is the
standing answer. Every subsystem belongs to one of three tiers, and the tier
determines its maintenance priority, review scrutiny, and deletion policy.

## The tiers

### 1. Core experimental domains

The substrate the research runs on. These are the environments where Layer 0
evolution happens and the capabilities Layers 1-2 are trying to improve.
**Deleting or degrading these destroys the science, no matter how much
smaller it makes the repository.**

| Subsystem | Where | Why it is core |
|---|---|---|
| Tank ecosystem | `core/entities`, `core/energy`, `core/reproduction`, `core/genetics`, `core/ecosystem*` | The primary selection environment: survival, foraging, reproduction. |
| Composable behavior substrate | `core/algorithms/`, `core/behavior/`, `core/pursuit/` | The evolvable genome-to-behavior mapping, including the reusable modules (behavior graphs, target memory) under active transfer study. |
| Soccer domain | `core/minigames/soccer`, `core/modes` (SoccerRuleSet), `benchmarks/soccer/` | The second selection goal. Multi-goal evolution and cross-domain transfer (food-to-ball) are explicit project theses (docs/VISION.md, docs/EVOLVABILITY.md S3); the transfer studies are meaningless without a ball domain. |
| Poker domain | `core/poker/`, `core/mixed_poker` | The third selection goal: an adversarial skill game with evolvable strategies, exercising a different capability axis (opponent modeling) than foraging or ball play. |
| Petri world | `core/worlds/petri` | The minimal second world backend that keeps the multi-world abstraction honest. |

Soccer and poker are **not** scope creep. They are the experimental domains
that make "evolving reusable behavior across multiple domains" a testable
claim rather than a slogan. Proposals to remove them "to simplify the
repository" should be rejected on those grounds; proposals to *improve their
usefulness as selection environments* are welcome.

### 2. Support infrastructure

Everything that lets the experiments run, be observed, and be trusted.
Judged on reliability and maintenance cost; refactor freely, delete only
when replaced.

| Subsystem | Where |
|---|---|
| Simulation engine and plumbing | `core/simulation/`, `core/spatial/`, `core/cache_manager.py`, `core/environment.py`, `core/worlds/` (registry/interfaces) |
| Backend server | `backend/` (FastAPI, WebSocket, runner, stats) |
| Frontend UI | `frontend/` (React observation/control surface) |
| Benchmarks, champions, gates | `benchmarks/`, `champions/`, `tools/*_gate.py`, `tools/run_bench.py`, `tools/validate_improvement.py`, CI workflows |
| Genetics serialization and validation | `core/genetics/genome_codec.py`, `core/genetics/validation.py` |
| Telemetry, stats, replay | `core/telemetry/`, `core/ecosystem_stats.py`, `core/replay/`, `backend/runner/stats_collector.py` |
| Research instrumentation | `core/research/`, `research/` reports, the Board (`tools/post_commentary.py`, `backend/commentary_store.py`) |
| Agent tooling and docs | `scripts/`, `docs/`, `CLAUDE.md`, `AGENTS.md` |

### 3. Optional demonstrations

Engagement, visualization, and exploratory features. Valuable, but the
science survives without them. These may be trimmed when their maintenance
cost exceeds their value - with a deprecation note, never silently.

| Subsystem | Where | Notes |
|---|---|---|
| Human-facing poker play | human seat/game UI paths in `core/mixed_poker` + frontend poker views | The poker *domain* is core (tier 1); the human-playable presentation of it is a demo. |
| Federation / multi-tank migration | `backend/migration_handler.py`, `backend/connection_*`, docs/FEDERATION.md | Exploratory distributed-world work; not load-bearing for any benchmark. |
| Auxiliary dashboards | parts of `frontend/src/components` beyond the core observation UI | Keep the ones agents actually read; treat the rest as demos. |
| Tournament/challenge framing | docs/AI_TOURNAMENT_*.md, related scripts | Outreach material. |

## Policy implications

- **Review scrutiny**: tier 1 changes need benchmark evidence and multi-seed
  validation (see CLAUDE.md); tier 2 changes need tests and gates; tier 3
  changes need to not break tiers 1-2.
- **Deletion**: tier 1 is never deleted for repository-size reasons. Tier 2
  is deleted only when replaced. Tier 3 may be retired when the maintenance
  cost exceeds the value, with a deprecation note in the PR and this file
  updated.
- **New subsystems**: a PR adding one should state its intended tier in the
  PR body; "tier 1" claims require an argument for what new selection
  pressure or capability axis it adds.

When a subsystem's role changes (a demo becomes load-bearing, an experiment
concludes), update its row here in the same PR.
