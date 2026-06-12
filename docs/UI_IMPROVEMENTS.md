# UI Improvements: The Must-Implement List

> Prioritized list of UI improvements we should **100% implement** to make Tank World
> more appealing and easier to use. Each item is grounded in the current codebase
> (file paths included) so an agent or human can pick one up and start immediately.
>
> Visual/design rules live in [UI_SPEC.md](UI_SPEC.md) — everything here must conform
> to that spec. Smaller engineering items are tracked in
> [IMPROVEMENT_PROPOSALS.md](IMPROVEMENT_PROPOSALS.md); this document is the strategic
> UI roadmap and cross-references those proposals where they overlap.

---

## The Gap This List Closes

The web UI today is a good **live observatory**: real-time canvas, ecosystem stats,
poker and soccer leaderboards, energy-flow panels. What it almost completely lacks is
**memory**. Every panel shows the current frame; refresh the page and all history is
gone. For a project whose entire premise is *evolution* — change over time — the UI
cannot currently answer its most interesting question:

> **"Is the population actually getting better at anything?"**

Items 1–3 fix that. Items 4–8 lower the barrier to entry and deepen engagement.

---

## 1. Soccer & Poker Skill-Over-Time Tracking ★★★ (the headline feature)

**What**: Persistent time-series charts showing whether the fish population is
*improving* at soccer and poker across frames, generations, and sessions.

**Why this is #1**: It is the single most compelling story the UI can tell — visible
proof that evolution works. Today the only longitudinal signal is the 20-point,
in-memory sparkline in `frontend/src/components/PokerScoreDisplay.tsx`, which is lost
on page refresh. Soccer has no trend view at all (`SoccerLeagueLive.tsx` shows only
the current match and leaderboard).

**The measurement trap to avoid**: win rates *within* the population are zero-sum.
If every fish gets better at poker at the same rate, internal win rates stay flat at
~50%. Improvement is only measurable against a **fixed reference**:

- **Poker**: the auto-evaluation machinery already plays fish against scripted
  baseline opponents (see `EvolutionBenchmarkDisplay`, the auto-eval stats in
  `frontend/src/components/tank_tabs/TankPokerTab.tsx`, and
  `core/poker_stats_manager.py`). Record the population's mean/median ELO vs. these
  frozen baselines at a regular frame interval.
- **Soccer**: record per-match aggregate skill proxies from
  `core/systems/soccer_system.py` / `core/minigames/soccer/` — goals per 1k frames,
  goal-progress events per match, and (ideally) periodic exhibition matches against a
  frozen baseline team, mirroring the poker auto-eval pattern.

**Implementation sketch**:

1. **Backend metrics history service**: a ring buffer (e.g., one sample per 500
   frames, last N=2000 samples) collected in `backend/runner/stats_collector.py`,
   persisted alongside the existing auto-save (`backend/auto_save_service.py`) so
   history survives restarts.
2. **API**: a `GET /api/world/{world_id}/metrics/history` endpoint plus an initial
   `MetricsHistoryPayload` on WebSocket connect (extend
   `backend/state_payloads.py`); subsequent samples ride the existing delta stream.
3. **Frontend**: a new **Trends tab** alongside the existing tank tabs in
   `frontend/src/components/tank_tabs/`, with line charts for:
   - Poker: population ELO vs. baseline, showdown win rate, net energy from poker
   - Soccer: goals/1k frames, baseline-match results, kick/possession events
   - Overlaid generation markers so skill gains can be tied to genetic turnover
   `recharts` is already in `frontend/package.json` (currently unused) — use it
   rather than hand-rolling charts, styled per UI_SPEC tokens.
4. **Per-generation aggregation**: bucket samples by `max_generation` so the x-axis
   can toggle between *frames* and *generations* — "Gen 12 plays measurably better
   poker than Gen 3" is the headline claim this feature exists to support.

**Acceptance**: after a 30k-frame headless or live run, a user can open the Trends
tab and see, in one glance, whether poker ELO vs. baseline and soccer scoring rate
went up, down, or flat — and the data survives a page refresh.

**Ready-to-hand-off task brief**: a complete worker-agent sample for this item —
task prompt, data contracts, file-by-file change map, component skeleton, and
acceptance checklist — lives at
[examples/ui_trends_worker_task.md](examples/ui_trends_worker_task.md).

---

## 2. Ecosystem Time-Series Charts ★★★

**What**: Line charts for population, births/deaths per interval, generation count,
algorithm diversity (Shannon entropy), and mean energy over time.

**Why**: `StatsPanel.tsx` and `TankEcosystemTab.tsx` show instantaneous values only.
A population crash, a starvation spiral, or a diversity collapse is invisible unless
you happen to be watching. These are exactly the "Healthy Ecosystem Indicators"
already defined in CLAUDE.md — the UI should chart them, not just snapshot them.

**Implementation**: same metrics-history pipeline as item 1 (build the buffer once,
feed both features). All values already exist per-frame in `StatsPayload`
(`backend/state_payloads.py`); this is purely retention + charting.

---

## 3. Champion Progress Dashboard ★★

**What**: A view (UI panel or `/evolution` route) that renders the
`champions/*/*.json` registries — current score per benchmark plus the `history`
array of retired champions — as a "best known solution over time" chart.

**Why**: Layer 1 evolution (AI agents improving algorithms via PRs) is the project's
core thesis, and it is completely invisible in the UI. The data already exists and is
versioned (`champions/tank/survival_5k.json`, `champions/tank/ecosystem_health_10k.json`,
`champions/soccer/training_3k.json`, `champions/soccer/training_5k.json`); each file
carries score, seed, timestamp, and full champion history. A simple static read +
chart makes the whole evolution loop legible to newcomers — and answers "is the
*codebase* improving at soccer?" the same way item 1 answers it for the live
population.

**Implementation**: a small backend endpoint that serves the champions directory as
JSON, plus a recharts step-chart per benchmark (score vs. timestamp, one point per
champion entry).

---

## 4. Entity Inspector ★★

**What**: Clicking a fish opens an inspector panel: genome traits (physical *and*
behavioral), behavior algorithm name + parameters, energy/age/generation, poker
record (games, win rate, best hand), and soccer involvement (kicks, goals).

**Why**: Today, clicking an entity only opens the transfer dialog
(`frontend/src/components/TransferDialog.tsx`). The simulation's stated design value
is *interpretable algorithms*, yet there is no way to ask "what is this fish and why
is it doing that?" — the single most natural question a viewer has. The backend
already strips behavior parameters from entity snapshots
(`backend/runner/state_publisher.py`); the inspector needs an on-demand
`get entity detail` command over the existing WebSocket command channel rather than
bloating the broadcast stream.

**Bonus**: surface **behavioral genes** (threat response, food approach, social mode,
poker engagement) side-by-side with the physical ones — `EcosystemStats.tsx` shows
population-level distributions, but no per-fish view exists.

---

## 5. One-Command Startup ★★★

**What**: `python start.py` launches backend + frontend together (dev mode), prints
one URL, and handles ctrl-C cleanly.

**Why**: The current two-terminal dance (`python main.py` + `cd frontend && npm run dev`)
is the first friction every new user hits. Easiest single win for "easy to use."
Already specced as proposal **4.1** in
[IMPROVEMENT_PROPOSALS.md](IMPROVEMENT_PROPOSALS.md) — listed here because it is a
hard prerequisite for the project being appealing to anyone new.

---

## 6. First-Run Onboarding Overlay ★★

**What**: A dismissible "what am I looking at?" overlay (or `?` keyboard shortcut)
that labels the canvas and panels: these are fish (colors = genome), this is food,
that's the soccer ball, fish bet energy at poker, energy above max funds offspring.

**Why**: Tank World's premise is unusual; a first-time visitor sees colorful dots and
has no idea that a full evolutionary economy is running. One overlay converts
confusion into the "wait, the fish play *poker*?" hook. Follow the existing modal
pattern (UI_SPEC §14, phylogenetic tree overlay) — no new design system needed.

---

## 7. Visual Assets in the README ★★★

**What**: An animated GIF of the live tank plus 2–3 screenshots (poker tab, soccer
match, ecosystem charts once item 2 lands) at the top of `README.md`.

**Why**: This is the project's storefront and currently text-only. For a project that
is literally a living aquarium, not showing it is the biggest missed marketing
opportunity. Already specced as proposal **5.1**; bundling it here because items 1–3
create the screenshots worth showing.

---

## 8. Event Timeline Scrubber ★

**What**: A horizontal timeline strip under the canvas marking notable events
(goals, big poker pots, births, deaths, extinctions, generation milestones), with
hover tooltips. Pairs naturally with the deterministic replay harness
(`backend/replay.py`, [REPLAY.md](REPLAY.md)) for an eventual "jump back and watch
that goal" interaction.

**Why**: Events currently scroll away in per-tab logs (`PokerEvents.tsx`,
`SoccerLeagueEvents.tsx`) and are easy to miss. A timeline gives the simulation a
narrative. Ranked last because items 1–2 deliver more insight per unit effort — but
it is the most "alive"-feeling feature on the list.

---

## Sequencing & Shared Infrastructure

| Order | Item | Depends on |
|-------|------|------------|
| 1 | Metrics history buffer + persistence (backend) | — |
| 2 | Trends tab: soccer/poker skill over time (item 1) | metrics buffer |
| 3 | Ecosystem time-series charts (item 2) | metrics buffer |
| 4 | One-command startup (item 5) | — (independent, do anytime) |
| 5 | Champion progress dashboard (item 3) | — (static data, independent) |
| 6 | Entity inspector (item 4) | WebSocket command channel (exists) |
| 7 | Onboarding overlay (item 6) | — |
| 8 | README visuals (item 7) | best after charts exist |
| 9 | Event timeline scrubber (item 8) | nice-to-have |

**Build the metrics-history buffer once; three features feed off it.** Charts should
use the `recharts` dependency already present in `frontend/package.json`, styled with
UI_SPEC tokens (no raw hex, glass-panel/dashboard-card containers, JetBrains Mono for
numbers).

## Ground Rules

- Every chart must remain correct under fast-forward and across reconnects
  (delta-stream resync happens every 90 frames — see
  `backend/runner/state_publisher.py`).
- Skill metrics must be measured against **fixed baselines**, never only intra-population
  win rates (zero-sum trap, see item 1).
- These are Layer 2 (tooling/UI) changes: keep them in separate PRs from any Layer 1
  algorithm changes, per [EVO_CONTRIBUTING.md](EVO_CONTRIBUTING.md).
- Determinism is non-negotiable: metrics collection must not perturb simulation
  state or RNG consumption.
