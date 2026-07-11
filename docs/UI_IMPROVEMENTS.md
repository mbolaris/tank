# UI Improvements: Agent Execution Backlog

> Tactical implementation briefs for the experience roadmap. Before taking a task,
> read [EXPERIENCE_ROADMAP.md](EXPERIENCE_ROADMAP.md) and
> [UI_SPEC.md](UI_SPEC.md). Keep each task in its own Layer 2 PR.

## Status snapshot

Audited against the repository on 2026-07-11. This table replaces the old list, which
incorrectly described several shipped foundations as future work.

| ID | Capability | Status | Notes |
|---|---|---|---|
| U0 | Persistent metrics history and REST/WebSocket delivery | DONE | Ring buffer, persistence, deltas, and tests exist |
| U1 | Ecosystem and skill Trends view | DONE | Frame/generation axes, ecosystem health, trait drift, poker ELO, and soccer rate exist |
| U2 | One-command development startup | DONE | `python start.py` is implemented and documented |
| U3 | Remove inactive navigation fork | DONE | Delete unused `TankTabs` / `TankPlayTab` files and orphaned tests/styles |
| U4 | Fish inspector replacing click-to-transfer | DONE | Inspector drawer + on-demand `get_entity_details`; transfer is a secondary action |
| U5 | Persistent selection and follow camera | DONE | Selection reconciles across merged deltas/full resync; follow is opt-in and stops when an entity disappears |
| U6 | Structured story-event service | QUEUED | Backend/contract task; independent of U4 |
| U7 | Living History feed and timeline | QUEUED | Depends on U4 and U6 |
| U8 | Return recap and legends | QUEUED | Depends on U6 and U7; split into separate PRs |
| U9 | Observe / Design / Lab presentation shell | QUEUED | Depends on U4 and U7 |
| U10 | Contextual overlays and intervention toolbelt | QUEUED | Depends on U9 |
| U11 | Trust states and intervention provenance | QUEUED | Depends on U9 |
| U12 | Fixed-baseline soccer evaluation | QUEUED | Metrics follow-up; current baseline field is a placeholder |
| U13 | Champion progress view in Lab | DEFERRED | Useful research view, but weaker for the watch loop |
| U14 | First-run onboarding | DEFERRED | Build against the Observe shell, not the current dashboard |
| U15 | README visuals | DEFERRED | Capture after Observe and Living History are visually stable |

“DONE” means the repository contains the capability; it does not mean it can never be
improved. Do not reopen a done item without a specific observed defect or measurement.

## How an agent claims a task

1. Pick the first unblocked task only; do not bundle adjacent rows.
2. Confirm the cited files and assumptions still match the tree.
3. Record before/after screenshots for a visual change at desktop and mobile widths.
4. Add focused tests for interaction, contract, persistence, and/or accessibility.
5. Run the smoke gate, relevant frontend checks, and pre-PR gate required by
   [AGENTS.md](../AGENTS.md). Report exact commands and results.
6. Update this status table only in the PR that completes the task.

## U3 — Remove the inactive navigation fork

**Outcome:** one navigation architecture remains before the presentation shell is built.

**Scope:**

- Prove with a repository-wide import search that `TankTabs.tsx` and `TankPlayTab.tsx`
  are not in the active application graph.
- Delete those components, their CSS Modules, and tests used only by them.
- Preserve active tab components such as `TankTrendsTab`, `TankPokerTab`, and
  `TankSoccerTab`; they are used directly by `TankView.tsx`.

**Acceptance:** frontend lint, tests, and production build pass; no active route or panel
changes; repository search finds no stale imports. Do not redesign navigation in this PR.

## U4 — Fish inspector replaces click-to-transfer

**Outcome:** clicking a fish answers “what is this creature doing?” rather than asking to
move it to another server.

**Likely touch points:**

- `frontend/src/components/TankView.tsx`
- a new `EntityInspectorDrawer.tsx` and CSS Module
- the canvas/entity selection path
- `frontend/src/hooks/useWebSocket.ts` and its command-response helper
- `backend/runner/state_publisher.py` or a focused entity-detail command handler
- existing `TransferDialog.tsx`

**Minimum inspector content:** entity id/type, current intent or behavior, energy, age,
generation, parents or lineage link, notable traits/mutations, and available poker or
soccer participation. Request detailed behavior parameters on demand; do not add them to
every broadcast entity.

**Acceptance:**

- Clicking a fish selects and visibly highlights it and opens the inspector.
- Clicking does not open transfer. Transfer is an explicit secondary inspector action.
- Escape, close button, focus return, and touch interaction work.
- Missing or dead entities produce a clear state rather than stale data or a crash.
- The inspector remains usable at narrow viewport widths.
- Existing transfer behavior still works when explicitly invoked.

**PR boundary:** do not add follow camera, event history, or the mode shell here.

## U5 — Persistent selection and follow camera

**Outcome:** a viewer can track one organism through normal updates.

Key selection by stable entity id, reconcile it after sparse deltas and full-state
resync, and clear it with an explanation when the entity dies or disappears. Add an
opt-in follow toggle; do not force camera movement on every selection. Respect manual
camera input and reduced motion.

**Acceptance:** selection survives ordinary frames, the 90-frame full resync, and a
reconnect when the entity still exists; follow stops on deselect/death; keyboard and
touch controls are equivalent. Add reducer/hook tests before relying on canvas-only
manual testing.

## U6 — Structured story-event service

**Outcome:** the simulation produces reproducible facts that a feed, recap, or narrator
can render without inventing meaning.

Follow the service patterns in `backend/metrics_history.py` and
`backend/commentary_store.py`: a bounded per-world store, monotonic ids, persistence,
REST retrieval, initial state delivery, and sparse deltas. A versioned record should
contain at least:

```text
id, schema_version, event_type, frame, simulation_time,
severity, entity_ids, lineage_ids, metrics_before, metrics_after,
detector_name, detector_threshold, replay_ref (optional)
```

The first PR implements exactly three detectors:

1. population entered danger / recovered from danger;
2. a generation milestone was reached;
3. a lineage crossed a configured population-share threshold.

Thresholds must be explicit, deterministic, debounced, and tested with synthetic sample
sequences. The service reads simulation output only and must not consume RNG. Do not add
an LLM, UI timeline, or a dozen detector types in this PR.

**Acceptance:** identical samples produce identical ordered events; restart persistence
does not duplicate events; buffer limits work; old schema payloads fail safely or
migrate explicitly; no event is emitted repeatedly while a metric remains on one side
of a threshold.

## U7 — Living History feed and timeline

**Outcome:** important events remain visible instead of scrolling away.

Render U6 records in the existing Insights/commentary surface with a visible distinction
between deterministic world events and agent commentary. Add a compact, keyboard-
navigable timeline under the canvas. Selecting a marker opens event detail and, when an
entity still exists, links to U4.

Only show “watch” when `replay_ref` resolves to retained replay data. Otherwise show the
event frame without pretending replay is available.

**Acceptance:** ordering and deduplication survive reconnects; markers aggregate at high
density; severity is conveyed by text/icon as well as color; timeline remains usable on
touch and narrow screens; an event can open its related entity or explain why it cannot.

## U8 — Return recap and legends

This row intentionally produces **two PRs**.

### U8a: Since your last visit

Persist the client's last-seen event id per world. On return, summarize only structured
events after that id. Begin with deterministic templates; optional generated prose can
come later and must cite the source event ids.

**Acceptance:** first visit, cleared storage, expired buffer entries, multiple worlds,
and no-new-event cases all have explicit behavior. The recap never claims causality that
the event records do not establish.

### U8b: In-world legends

Promote only notable organisms or lineages using explicit criteria: longevity record,
surviving descendants, tournament result, migration success, cross-domain performance,
lineage founding, or collapse survival. Store why each legend qualified.

**Acceptance:** names are stable across reloads, promotion is deterministic, duplicates
are prevented, and benchmark champions are not mixed with in-world legends.

## U9 — Observe / Design / Lab shell

**Outcome:** the default experience is a living tank, while research capability remains
intact.

- **Observe (default):** canvas, compact world header, current story, inspector, time
  controls, and safe interventions.
- **Design:** ecosystem configuration and experiment setup.
- **Lab:** the existing detailed panels, exact metrics, seed/config/provenance, and
  debugging information.

Rename the player-facing Network area to Worlds and place host, port, memory, and server
health under Admin. Extract new components rather than growing `TankView.tsx` or
`NetworkDashboard.tsx`, both of which are line-ratchet risks.

**Acceptance:** a new visitor can pause, inspect, and feed without documentation;
Observe contains no destructive or unexplained technical controls; every existing
research panel remains reachable in Lab; mode and selected entity persist sensibly;
keyboard, touch, and responsive layouts pass.

## U10 — Contextual overlays and intervention toolbelt

Add one overlay/lens at a time: start with energy/food pressure, family relationships,
and death locations only if the required data already exists. A compact toolbelt groups
Resources, Climate, Challenges, Pressure, Life, and Time; selecting a tool reveals only
its settings. Move the permanent plant-energy slider into Resources.

**Acceptance:** overlays have legends and can be disabled; tool activation is explicit;
controls do not obscure the canvas at narrow widths; intervention actions are ready to
emit provenance for U11. Do not fabricate unavailable spatial history.

## U11 — Trust states and intervention provenance

Implement Sandbox, Experiment, and Exhibition as enforced state, not decorative badges.
Experiment records config version, seed, and permitted/logged interventions. Exhibition
is read-only. Sandbox allows play but cannot claim verified experimental results.

**Acceptance:** server-side authorization enforces restrictions; every intervention has
actor, frame/time, old/new value, and reason/type; verification status is invalidated or
updated deterministically; tests cover attempts to bypass UI restrictions.

## U12 — Fixed-baseline soccer evaluation

The existing Trends view charts goals per 1k frames, but that rate can change with match
frequency and opponent composition. Complete the existing
`baseline_match_score_diff` contract with periodic exhibition matches against a frozen,
versioned team or another equivalently stable reference.

**Acceptance:** the baseline id/version and evaluation cadence are recorded; evaluation
does not alter the evolving population, energy economy, or RNG stream; Trends clearly
separates baseline skill from live internal match activity; deterministic tests and a
seeded reproduction command are included.

## Deferred supporting work

- **Champion progress in Lab:** expose champion registry score history with benchmark,
  seed, timestamp, and provenance. Do not label it population evolution.
- **First-run onboarding:** wait for U9, then teach the stable Observe interactions. A
  tour of the current dashboard would become immediate rework.
- **README visuals:** after U7 and U9, capture a short tank clip plus Observe, inspector,
  and Living History screenshots. Include alt text and a repeatable capture recipe.

## Shared ground rules

- Use fixed baselines for skill claims; intra-population results are zero-sum.
- Preserve correctness under fast-forward, sparse deltas, reconnect, and world switches.
- Never consume simulation RNG for telemetry or presentation.
- Use CSS variables and CSS Modules; meet [UI_SPEC.md](UI_SPEC.md), keyboard/touch,
  contrast, reduced-motion, and responsive requirements.
- Keep UI/telemetry work separate from algorithms, benchmark scoring, and champion data.
- Prefer focused components and hooks over adding lines to ratcheted god classes.

---

*Updated 2026-07-11 from a repository audit and the July 2026 external product review.*
