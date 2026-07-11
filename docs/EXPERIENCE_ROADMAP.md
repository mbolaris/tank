# Experience Roadmap: Make the Tank Fun to Watch

> **Goal**: turn Tank World from a *developer monitoring dashboard placed around an
> aquarium* into a place where a newcomer opens a tank, sees something alive, clicks a
> fish, understands its story, changes one environmental pressure, and later discovers
> what happened. The evolving population — not the panels — is the product.

This document is the **strategic experience roadmap**. It sits between two existing docs:

- [UI_SPEC.md](UI_SPEC.md) — the *design system* (colors, typography, components). Every
  task here must conform to it. This doc never overrides a token.
- [UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md) — a *tactical must-implement list* (metrics
  history, trends, entity inspector, onboarding). Several items below extend those
  entries rather than replacing them; cross-references are called out inline.

It was written to evaluate an external product review (2026-07, engineering 91/100,
casual-player experience 60/100) whose central verdict was: **"The backend is ahead of
the product experience."** The claims in that review were checked against the tree
before anything below was written; the verification notes are in
[§1](#1-verified-current-state).

---

## The North Star

One sentence, testable, and the acceptance bar for "done" on Phases 0–2:

> A person unfamiliar with the project opens a tank, immediately notices something
> alive, clicks a fish, understands what it is and where it came from, changes one
> environmental pressure, and later returns to find out what resulted.

Everything in this roadmap is ranked by how directly it moves that sentence. If a
proposed feature does not, it is deferred (see [§6](#6-deferred-and-rejected)).

---

## 1. Verified current state

The review's factual claims were confirmed against the current branch:

| Review claim | Verified? | Evidence |
|---|---|---|
| Clicking an organism opens the **transfer dialog** | ✅ | `handleEntityClick` in [TankView.tsx](../frontend/src/components/TankView.tsx) sets the entity and immediately calls `setShowTransferDialog(true)` |
| **Seven** analytical panels, **four** on by default | ✅ | `useVisiblePanels(['skills','soccer','ecosystem','insights'])`; the grid also offers poker, trends, genetics |
| Frame, FPS, and research metrics always visible | ✅ | The stats HUD bar in `TankView.tsx` renders FRAME / SIM FPS / POPULATION / MAX GEN unconditionally |
| Plant-energy slider permanently exposed | ✅ | `plantEnergyControl` lives in the always-on control bar |
| A dead second navigation architecture exists | ✅ | `tank_tabs/TankTabs.tsx` and `tank_tabs/TankPlayTab.tsx` are imported by nothing — not by `TankView`, not even re-exported from `tank_tabs/index.ts` |
| "Network" dashboard is developer-facing | ✅ | The nav view toggle is Tank / Network; `pages/NetworkDashboard.tsx` surfaces host/port/server health |

### What already exists — do NOT rebuild it

The review treats several of its recommendations as greenfield. They are not. Reuse
these; the new work is smaller than the review implies.

- **Metrics history + Trends.** A persisted ring buffer already exists
  ([backend/metrics_history.py](../backend/metrics_history.py),
  [backend/routers/metrics.py](../backend/routers/metrics.py)) and feeds a live
  **Trends** panel (`tank_tabs/TankTrendsTab.tsx`, wired in `TankView.tsx`). The
  "population improving over generations" chart the user wants is *partly built* — it
  needs surfacing and a generation x-axis, not a new pipeline. (UI_IMPROVEMENTS items
  1–2.)
- **A narrative surface.** The **Insights** feed is real
  ([backend/commentary_store.py](../backend/commentary_store.py),
  `CommentaryFeed.tsx`, `tools/post_commentary.py`, the `/observe-sim` skill). It is a
  bounded ring buffer that "only *records annotations about* the simulation; it never
  reads or mutates simulation state." Today it is fed by agents posting manually. Living
  History ([§3](#3-phase-1--make-watching-rewarding)) should *feed this same surface
  automatically* from deterministic detectors — not invent a new feed.
- **Legend/Hall-of-Fame data.** The `champions/` registry already carries scored,
  seeded, timestamped champion history per benchmark.
- **Replay.** A deterministic record/replay harness exists ([REPLAY.md](REPLAY.md)) —
  the substrate for "jump back and watch that goal."
- **Transfer.** `TransferDialog.tsx` is not deleted by any task here; it *moves* to
  become a secondary action inside the inspector.

---

## 2. Evaluation of the review's suggestions

Grouped by verdict. Reasoning is grounded in this codebase's constraints
(determinism, Layer 1/2 separation, one-focused-change-per-PR, the god-class line
ratchet).

### Adopt (high value, aligned with the North Star)

| Suggestion | Why adopt | Where |
|---|---|---|
| **Click a fish → inspector, not transfer** | The single highest-value change; fixes the "biggest UX mistake." Also UI_IMPROVEMENTS item 4. | [0.2](#02--entity-inspector-replaces-click-to-transfer-m-) |
| **Follow-camera + persistent selection** | Makes the sim feel alive; cheap once the inspector exists. | [0.3](#03--selection-persistence--follow-camera-s-) |
| **Living History = deterministic structured event detectors** | Turns raw data into meaning; the review is right that this is the highest-value *subsystem*. Reuses the Insights feed. | [Phase 1](#3-phase-1--make-watching-rewarding) |
| **"Since your last visit" recap** | Directly serves retention and the "later discovers what resulted" clause of the North Star. | [1.3](#13--since-your-last-visit-recap-m-) |
| **Named legends / Hall of Fame** | Emotional hook without making fish the player's *design target*. | [1.4](#14--named-legends--hall-of-fame-m-) |
| **Canvas-dominant Observe mode; toolbelt; data-layer overlays** | Correct default for a living-world product. | [Phase 2](#4-phase-2--the-experience-shell) |
| **Ecosystem trust states (Sandbox / Experiment / Exhibition)** | Not just UX — this *protects research validity*. A hand-rescued tank must not be comparable to a controlled run. Strongly aligned with "determinism is non-negotiable." | [2.4](#24--ecosystem-trust-states-l-) |
| **Delete the dead TankTabs/TankPlayTab fork** | Two navigation architectures should not coexist. | [0.1](#01--delete-the-dead-navigation-fork-s-) |

### Adapt (right idea, wrong shape for this repo)

- **"One big experience-shell PR."** Rejected as a single PR; **decomposed into small,
  independently shippable PRs** (Phases 0–2). This repo values one focused change per PR,
  keeps Layer 2 (UI/tooling) changes separate from Layer 1 (algorithm) changes, and
  enforces a per-file line ratchet on grandfathered god-classes. A monolithic shell PR
  would fight all three.
- **"Hide frame/FPS/metrics by default."** Adopt *as a mode*, not as a redefinition of
  the design system. UI_SPEC principle #4 is "data density over decoration"; that stays
  true of **Lab** mode. Observe mode hides density; Lab mode keeps every current panel
  and number intact. This reconciles the review with UI_SPEC rather than overruling it.
- **"Narrator generates prose."** Adopt only *after* the deterministic detector exists,
  and route it through the existing Insights feed. The factual event must be
  reproducible even when the presentation is playful — start structured, add prose last.

### Defer (valuable, but blocked on the North Star landing first)

Public read-only links, fork-this-ecosystem, tank-vs-tank tournaments, organism trading,
friends, mobile notifications, global leaderboards. The review itself defers all of
these to its Phase 4, and the project's own [FEDERATION.md](FEDERATION.md) already owns
the wire-format prerequisites. Do not start them before a small invited alpha validates
Phases 0–2.

### Reject (conflicts with project values)

- **Separate "game" and "research" builds.** One engine, different presentation layers.
  The review agrees; stated here so no one forks the simulation.
- **A single universal ecosystem score.** The repo already knows single-number,
  single-seed scores are dangerous (see the `ecosystem_health` trajectory-sensitivity
  gotcha in [CLAUDE.md](../CLAUDE.md)). Any comparison UI must be **multi-axis**
  (resilience, diversity, adaptability, generality, …), never one leaderboard number.

---

## 3. Phase 0 — Foundations (do these first; each is a small, standalone PR)

These are prerequisites and quick wins. None depends on the mode-shell, so they can land
immediately and independently.

### 0.1 — Delete the dead navigation fork `S` ★

`tank_tabs/TankTabs.tsx` and `tank_tabs/TankPlayTab.tsx` are imported by nothing. Remove
them (and any now-orphaned styles/tests). Confirm with a repo-wide search that no route
or component references them. This clears the "two competing navigation architectures"
finding before new navigation work begins.

### 0.2 — Entity Inspector replaces click-to-transfer `M` ★★★

The headline UX fix. Clicking a fish must answer *"what is this thing and why is it doing
that?"* — not *"move it to another server?"*

- Add an `EntityInspectorDrawer` (new component, CSS Module per UI_SPEC §15). Change
  `handleEntityClick` in `TankView.tsx` to open the inspector, **not** the transfer
  dialog.
- Contents: current intent/behavior algorithm + parameters, energy, age, generation,
  parents/lineage link, notable mutations, poker record, soccer involvement, recent
  events. The backend already strips behavior params from the broadcast
  (`backend/runner/state_publisher.py`); fetch detail on demand over the existing
  WebSocket command channel (`sendCommandWithResponse`) rather than bloating the stream.
- **Transfer becomes a secondary button inside the inspector**, reusing
  `TransferDialog.tsx` unchanged.
- This supersedes UI_IMPROVEMENTS item 4 (Entity Inspector) — mark that item as folded
  into this task when it lands.

**Acceptance**: clicking an organism selects and highlights it and never immediately
initiates transfer; the inspector opens and closes via keyboard and touch; transfer is
reachable only as an explicit secondary action.

### 0.3 — Selection persistence + follow-camera `S` ★★

The selected organism must **stay selected as delta updates arrive** (today selection is
local state keyed by entity id — verify it survives the 90-frame resync). Add an optional
"follow" toggle that keeps the camera centered on the selected entity. This is what makes
the tank feel alive when watching one fish.

**Acceptance**: a selected fish remains selected across reconnects/resyncs; follow mode
tracks it until deselected.

### 0.4 — Rename "Network" → "Worlds"; move admin data into a subsection `S` ★

Rename the player-facing view (`App.tsx` view toggle, route, `NetworkDashboard.tsx`) to
**Worlds**. Host, port, memory, and server-health belong in an **Admin** subsection, not
the default view. Pure Layer 2 relabel + reorganization; no simulation impact.

---

## 4. Phase 1 — Make watching rewarding (the headline subsystem)

This is where the user's explicit goal — *"fun to watch how the fish are improving over
generations"* — is won. Build the deterministic detector first; add prose last.

### 1.1 — Structured story-event service (backend) `L` ★★★

A deterministic detector that scans per-frame stats and emits **structured** events. Do
**not** start with an LLM. Model it on the two existing ring-buffer services
(`metrics_history.py`, `commentary_store.py`): bounded buffer, monotonic ids, frame +
wall-clock stamps, REST poll + initial WS payload, persisted alongside the existing
auto-save so history survives restarts. It must be **read-only** over simulation state —
never perturb RNG or entity state (same contract `commentary_store` already documents).

Initial detectors (each with a clear numeric trigger so it is reproducible):

- species appeared / went extinct
- a lineage's population share crossed a threshold (e.g. 8% → 30%)
- a mutation spread through ≥50% of the tank
- a new longevity record
- a migrant produced successful descendants
- a cross-domain surprise (strong poker specialist becomes a strong soccer scorer)
- diversity (Shannon entropy) fell sharply
- population approached collapse, then recovered
- a generalist displaced a specialist
- an unusually large surviving family
- a previously dominant lineage disappeared

Each stored event retains: frame + sim time, the organisms/lineages involved, the metric
before and after, *why the detector fired* (the threshold it crossed), and ids for
inspect/replay/compare.

**Guardrail**: this is Layer 2 tooling. Keep it in its own PR, separate from any Layer 1
algorithm change, per [EVO_CONTRIBUTING.md](EVO_CONTRIBUTING.md).

### 1.2 — Living History timeline + feed `M` ★★★

Render 1.1's events two ways, reusing existing patterns:

- An **event feed** that reuses the Insights UI (`CommentaryFeed.tsx`) — Insights and
  Living History are the same surface, auto-detected events alongside agent commentary.
- A horizontal **timeline strip** under the canvas (UI_IMPROVEMENTS item 8), each marker
  linking to inspect and — via [REPLAY.md](REPLAY.md) — an eventual "watch that moment."

### 1.3 — "Since your last visit" recap `M` ★★★

On return, open with a short recap computed from the event buffer since the last-seen
event id (persist that id per client): *"While you were away, the Bluefin lineage grew
from 8% to 31%. Its members live shorter lives but reproduce earlier. Two descendants
reached the soccer finals."* Actions: watch the change, inspect the lineage, compare with
the previous dominant lineage, pin for observation. The review is right that this does
more for retention than another chart.

### 1.4 — Named legends / Hall of Fame `M` ★★

Automatically promote organisms into prominence *once they earn it* (long life, many
surviving descendants, unusual mutation, tournament win, successful migration,
cross-domain ability, lineage founder, survived a collapse). Give the promoted ones
display names/nicknames — not every fish, only the notable. A **Legends** archive can be
seeded from `champions/` plus lineage data. Organisms become characters without becoming
the player's *design target* — the player still shapes the ecosystem, not the fish.

### 1.5 — Generation-over-generation skill view `M` ★★

The user's literal ask. The Trends pipeline already exists (`TankTrendsTab`,
`metrics_history.py`); the gap is legibility: bucket samples by `max_generation` so the
x-axis toggles frames↔generations, and measure skill against **fixed baselines**, never
intra-population win rates (the zero-sum trap documented in UI_IMPROVEMENTS item 1). The
headline claim to make visible: *"Gen 12 plays measurably better poker than Gen 3."*
Surface this chart in Observe mode, not only in the Lab panel grid.

---

## 5. Phase 2 — The experience shell

Now — and only now, after watchability is proven — rearchitect navigation. This is the
largest, riskiest change, which is exactly why it comes *after* the Phase 1 wins rather
than blocking them (a deliberate resequencing of the review, whose Phase order put the
shell first; see the note below).

### 2.1 — Observe / Design / Lab modes; Observe default `L` ★★★

Three presentation layers over the **same** engine and data:

- **Observe** (default): canvas dominant, minimal health header (tank name, population
  condition, sim time, pause/speed, one current noteworthy event), the inspector, the
  current stories, time controls, the intervention toolbelt. No destructive or deeply
  technical controls.
- **Design**: the ecosystem editor ([Phase 3](#7-phase-3--make-ecosystem-design-rewarding)).
- **Lab**: **everything that exists today, unchanged** — the full panel grid, exact
  metrics, seeds, skill ledgers, benchmark provenance. This is the compatibility contract
  that lets Observe safely hide density elsewhere.

Replace the flat panel pile with these modes. Fold the (now-deleted) TankTabs fork's
intent into this single navigation model.

**Acceptance**: Observe exposes no destructive/technical control; Lab retains every
current research number; a new visitor can pause, inspect, and feed the tank without docs.

### 2.2 — Bottom intervention toolbelt `M` ★★

A compact palette (WorldBox "god powers" pattern) grouped by intent: Resources / Climate
/ Challenges / Pressure / Life / Time. Selecting a tool reveals only its relevant
settings — retire the permanently-exposed plant-energy slider into the Resources group.

### 2.3 — Contextual data-layer overlays `M` ★★

Instead of always-on dashboards, let the user overlay one lens on the canvas at a time:
energy flow, food pressure, species territories, family relationships, mutation spread,
reproductive success, death locations, selection pressure. (SimCity's lesson: complex
agent systems become legible through selectable layers, not permanent stat walls.)

### 2.4 — Ecosystem trust states `L` ★★★

Three world states, tracked and displayed, because scientific and playful use *will*
conflict otherwise:

- **Sandbox**: anything goes (feed, mutate, release predators, change weather live). Fun,
  exploratory, makes **no** claim to experimental validity.
- **Experiment**: protocol locked — config versioned, seed recorded, interventions
  prohibited or formally logged; results can earn a verified badge and be reproduced by
  others.
- **Exhibition**: shareable, read-only; visitors fork into their own Sandbox rather than
  altering the original.

This is the mechanism that keeps a hand-rescued tank from competing against a controlled
run — it operationalizes the project's "determinism is non-negotiable" value at the
product layer. Reuse config-hashing/versioning that the champion-provenance tooling
already relies on.

> **Why Phase 1 precedes Phase 2 here (differs from the review).** The review sequenced
> the experience-shell first. This roadmap leads with the entity inspector (Phase 0) and
> Living History (Phase 1) because they deliver the North Star's "notices something
> alive → understands its story → discovers what resulted" in small, low-risk PRs, while
> the mode-shell is the biggest rearchitecture and should not gate those wins. Phase 0.2
> alone removes the worst UX mistake.

---

## 6. Deferred and rejected

See the [evaluation table](#2-evaluation-of-the-reviews-suggestions) for reasoning.
**Deferred to post-alpha:** public links, fork, tournaments, trading, friends, mobile
notifications, global leaderboards (own prerequisites live in
[FEDERATION.md](FEDERATION.md)). **Rejected:** a separate game/research build; a single
universal ecosystem score.

---

## 7. Phase 3 — Make ecosystem design rewarding (post-alpha)

Frame the editor around **hypotheses**, not raw config fields: a hypothesis text field,
an ecosystem "recipe" (challenge mix, scarcity, seasonality, migration, mutation), and a
**clone-as-comparison** flow (change one variable, run both tanks, compare on the
multi-axis scorecard). This is simultaneously good gameplay and good experimental
practice. Blocked on Phase 2's trust states and Design mode.

---

## 8. Guardrails (apply to every task above)

1. **Determinism is non-negotiable.** No new subsystem may read RNG or mutate simulation
   state as a side effect. Detectors and history buffers observe only, like
   `commentary_store` and `metrics_history` already do.
2. **Layer 2 stays separate from Layer 1.** All of this is UI/tooling — keep it out of
   PRs that touch `core/algorithms/` or champion files
   ([EVO_CONTRIBUTING.md](EVO_CONTRIBUTING.md)).
3. **Conform to [UI_SPEC.md](UI_SPEC.md).** No raw hex, tokenized spacing/radius, glass /
   dashboard-card surfaces, `recharts` for charts, CSS Modules for new components.
4. **Charts survive fast-forward and reconnects** (90-frame delta resync) and measure
   skill against **fixed baselines**, never intra-population win rates.
5. **Small PRs.** One task = one PR. Respect the per-file line ratchet on grandfathered
   god-classes (a +1-line change to a pinned file fails the pre-PR gate).
6. **No universal score.** Any comparison surface is multi-axis.

---

## 9. Definition of done for the alpha

After Phases 0–2 and the first Living History pass, Tank World should be ready for a
small invited alpha: give 10–20 people a few prepared ecosystems and watch what they
click, what they misunderstand, and whether they return unprompted. The bar is the North
Star sentence at the top of this document.

---

*Created 2026-07-11. Evaluates the 2026-07 external product review. Companion to
[UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md) (tactical list) and [UI_SPEC.md](UI_SPEC.md)
(design system); strategic milestones live in [ROADMAP.md](ROADMAP.md).*
