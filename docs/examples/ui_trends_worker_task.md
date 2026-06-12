# Worker Task Sample: Soccer & Poker Skill-Over-Time (Trends Tab)

> **This file is a hand-off sample.** Give it to a worker agent verbatim. It
> implements item 1 (and the shared infrastructure for item 2) of
> [../UI_IMPROVEMENTS.md](../UI_IMPROVEMENTS.md). It contains the task prompt,
> the exact data contracts to implement, the file-by-file change map, a frontend
> skeleton, and the acceptance checklist.

---

## Task Prompt (copy-paste to the worker agent)

> Implement the "Trends" feature described in `docs/UI_IMPROVEMENTS.md` item 1,
> following the contracts and file map in `docs/examples/ui_trends_worker_task.md`
> exactly. Build the backend metrics-history buffer, expose it over the existing
> WebSocket/REST surface, and add a Trends tab to the frontend showing whether
> the population is improving at poker and soccer over time. Do not change any
> simulation behavior, RNG consumption, or benchmark scoring — this is a Layer 2
> (tooling/UI) change and must be a separate PR from any algorithm work. Run
> `python tools/smoke_gate.py` before coding and `python tools/fast_gate.py`
> plus `cd frontend && npm run lint && npm run build` before pushing.

---

## 1. What "improving" means (read this first)

Win rates *inside* the population are zero-sum: if every fish gets better at the
same rate, internal win rates stay flat at ~50%. Improvement is only measurable
against **fixed references**:

- **Poker**: the auto-evaluation system already plays fish against scripted
  baseline opponents and reports ELO (`AutoEvaluateStatsPayload` in
  `backend/state_payloads.py`, surfaced today as a 20-point ephemeral sparkline
  in `frontend/src/components/PokerScoreDisplay.tsx`). Sample that ELO over time.
- **Soccer**: there is no baseline opponent yet, so use absolute production
  rates as the v1 proxy: goals per 1k frames and completed matches, computed
  from the soccer events already collected by
  `backend/runner/hooks/soccer_mixin.py`. Leave a `baseline_match_score_diff`
  field in the schema as `null` for the future frozen-baseline exhibition match.

Overlay `max_generation` on every sample so the charts can answer the headline
question: *"does Gen 12 play better than Gen 3?"*

## 2. Data contract

### 2.1 MetricsSample (one row, collected every `sample_interval_frames`)

```json
{
  "frame": 12000,
  "max_generation": 7,
  "population": 34,
  "births_total": 61,
  "deaths_total": 47,
  "fish_energy": 2841.6,
  "poker": {
    "auto_eval_elo": 1287.4,
    "total_games": 96,
    "showdown_win_rate": 0.54,
    "net_energy_total": 412.5
  },
  "soccer": {
    "goals_total": 11,
    "goals_per_1k_frames": 0.92,
    "matches_completed": 4,
    "matches_skipped": 2,
    "baseline_match_score_diff": null
  }
}
```

Field sources (all already exist — no new simulation instrumentation):

| Field | Source |
|---|---|
| `frame`, `population`, `births_total`, `deaths_total`, `max_generation`, `fish_energy` | `StatsPayload` fields built in `backend/runner/stats_collector.py` |
| `poker.auto_eval_elo` | auto-eval ELO history (`AutoEvaluateStatsPayload.performance_history`, `backend/state_payloads.py:595`) |
| `poker.total_games`, `poker.showdown_win_rate`, `poker.net_energy_total` | `PokerStatsPayload` (`backend/state_payloads.py:181`) |
| `soccer.*` | cumulative counters over `SoccerEventPayload` events (`score_left + score_right`, `skipped`, `skip_reason`) collected by `backend/runner/hooks/soccer_mixin.py` |

### 2.2 MetricsHistoryPayload (the buffer)

```json
{
  "schema_version": 1,
  "world_id": "tank-1",
  "sample_interval_frames": 500,
  "max_samples": 2000,
  "samples": [ "...MetricsSample, oldest first..." ]
}
```

- Ring buffer: one sample per 500 frames, capacity 2000 (≈1M frames of history).
- Persistence: serialize the buffer with the existing auto-save
  (`backend/auto_save_service.py`) so history survives restarts; tolerate a
  missing/old-schema buffer on load (start empty, never crash).

### 2.3 Transport

- **REST**: `GET /api/world/{world_id}/metrics/history` → `MetricsHistoryPayload`
  (add a router under `backend/routers/`, register in `backend/app_factory.py`).
- **WebSocket**: include the full `MetricsHistoryPayload` once in the initial
  full state (`FullStatePayload`, `backend/state_payloads.py:609`); afterwards,
  append-only — attach a new sample to the delta frame on the frame it is taken
  (extend the delta payload the same way `soccer_league_live` is attached).
  Bump `STATE_SCHEMA_VERSION`.

## 3. File-by-file change map

| File | Change |
|---|---|
| `backend/metrics_history.py` (new) | `MetricsHistory` ring buffer: `maybe_sample(frame, stats, poker, soccer, auto_eval)`, `to_payload()`, `load()/dump()` for auto-save |
| `backend/state_payloads.py` | Add `MetricsSamplePayload` + `MetricsHistoryPayload` dataclasses (follow the existing `_to_dict` pattern); add optional field to full/delta payloads; bump `STATE_SCHEMA_VERSION` |
| `backend/runner/stats_collector.py` | Call `metrics_history.maybe_sample(...)` from the existing per-frame stats build (read-only inputs; must not touch engine state) |
| `backend/auto_save_service.py` | Persist/restore the buffer alongside existing snapshot data |
| `backend/routers/metrics.py` (new) | `GET /api/world/{world_id}/metrics/history` |
| `frontend/src/types/simulation.ts` | `MetricsSample`, `MetricsHistory` interfaces mirroring §2 |
| `frontend/src/hooks/useWebSocket.ts` | Store history from initial state; append samples from deltas; cap at `max_samples` |
| `frontend/src/components/tank_tabs/TankTrendsTab.tsx` (new) | The Trends tab (skeleton in §4) |
| `frontend/src/components/TankView.tsx` | Register the tab + panel toggle next to `TankSoccerTab`/`TankPokerTab` (`frontend/src/components/TankView.tsx:377`) |
| `tests/` | Unit tests: ring-buffer capacity/interval, payload round-trip, determinism guard (running with collection on/off yields identical sim state hashes) |

## 4. Frontend skeleton

`recharts` (v2.15.4) is already in `frontend/package.json` — use it. Style per
[UI_SPEC.md](../UI_SPEC.md): dashboard-card containers, CSS variable colors
(poker = `--color-secondary` violet, soccer = `--color-success` emerald,
population = `--color-primary` cyan), JetBrains Mono for numbers, no raw hex.

```tsx
// frontend/src/components/tank_tabs/TankTrendsTab.tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
import type { MetricsHistory } from '../../types/simulation';

interface TankTrendsTabProps {
    history: MetricsHistory | null;
}

type XAxisMode = 'frames' | 'generations';

export function TankTrendsTab({ history }: TankTrendsTabProps) {
    // 1. Empty state: "Collecting samples… first point at frame 500."
    // 2. X-axis toggle: frames | generations (bucket samples by max_generation,
    //    plot the per-generation mean when in generation mode).
    // 3. Charts (one dashboard-card each, ~180px tall, ResponsiveContainer):
    //    a. Poker ELO vs baseline   — samples[].poker.auto_eval_elo
    //       + ReferenceLine at the first sample's ELO ("starting skill")
    //    b. Soccer goals / 1k frames — samples[].soccer.goals_per_1k_frames
    //    c. Population & generation — population line + max_generation step line
    // 4. Generation markers: vertical ReferenceLines where max_generation increments.
    // 5. Trend badge per chart: Δ between mean of first and last quartile of
    //    samples, rendered ▲ green / ▼ red / ◆ gray (see UI_SPEC §2.6 deltas).
}
```

## 5. Acceptance checklist

- [ ] `python main.py --headless --max-frames 30000 --export-stats results.json --seed 42`
      runs unchanged: byte-identical `results.json` vs. master at the same seed
      (determinism guard — collection must not perturb the sim).
- [ ] After a live 30k-frame run, the Trends tab shows poker ELO, soccer
      goals/1k frames, and population charts with ≥ 50 samples.
- [ ] Page refresh and backend restart both preserve history (auto-save).
- [ ] X-axis toggles between frames and generations; generation markers render.
- [ ] Empty/fresh world shows the empty state, not a crash or blank panel.
- [ ] Reconnect mid-run does not duplicate or reorder samples (delta resync
      happens every 90 frames — see `backend/runner/state_publisher.py`).
- [ ] `python tools/fast_gate.py` passes; `cd frontend && npm run lint && npm run build` pass.
- [ ] No UI_SPEC violations: tokens only, dashboard-card pattern, panel toggle
      added with `aria-pressed`.
- [ ] PR contains only Layer 2 changes (no `core/algorithms/`, `core/config/`,
      `benchmarks/`, or `champions/` edits).

## 6. Out of scope (do not do in this PR)

- Frozen-baseline soccer exhibition matches (schema slot reserved:
  `baseline_match_score_diff`).
- Champion progress dashboard (UI_IMPROVEMENTS item 3).
- Entity inspector (item 4).
- Any change to poker/soccer gameplay, rewards, or energy accounting.
