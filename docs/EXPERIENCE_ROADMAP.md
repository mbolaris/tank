# Experience Roadmap: Make the Tank Fun to Watch

> **Goal:** turn Tank World from a developer dashboard around an aquarium into a
> living world where a newcomer notices change, follows a fish, understands why an
> event mattered, changes one environmental pressure, and later discovers the result.

This is the strategic experience roadmap. Use [UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md)
for agent-ready implementation briefs and [UI_SPEC.md](UI_SPEC.md) for visual and
interaction rules. This roadmap evaluates the July 2026 product review; it does not
repeat the review's engineering score as a project guarantee.

## North Star and product position

> A person unfamiliar with the project opens a tank, immediately notices something
> alive, clicks a fish, understands what it is doing and where it came from, changes one
> environmental pressure, and later returns to learn what resulted.

The player shapes an **ecosystem**, not an individual organism. Fish should become
memorable characters, but direct fish design must not replace selection pressure as the
core interaction. Research and play use one simulation engine with different
presentations; they must not become separate products.

The review's central diagnosis is correct: the simulation and telemetry are ahead of
the default viewing experience. The best next investment is meaning and watchability,
not another dense analytical panel.

## Verified current state

Audited against the repository on 2026-07-11:

| Finding | Status | Repository evidence |
|---|---|---|
| Clicking a fish immediately opens transfer | Confirmed | `handleEntityClick` in [`TankView.tsx`](../frontend/src/components/TankView.tsx) opens `TransferDialog` |
| The default tank view is a dense panel dashboard | Confirmed | Four panels are enabled by default; poker, trends, and genetics are additional toggles |
| Frame, FPS, population, generation, and plant-energy controls are always exposed | Confirmed | The HUD and control bar are rendered directly by `TankView.tsx` |
| A second navigation implementation remains | Confirmed | `TankTabs.tsx` and `TankPlayTab.tsx` exist but are not part of the active `TankView` composition |
| Metrics history must be built | **Already solved** | [`metrics_history.py`](../backend/metrics_history.py), the metrics API, persistence, WebSocket deltas, and `TankTrendsTab.tsx` are live |
| Generation-based trends must be built | **Already solved** | Trends defaults to a generation axis and can toggle to frames |
| Ecosystem time-series charts must be built | **Already solved** | Population, births/deaths, mortality, energy, diversity, trait drift, poker ELO, and soccer-rate views exist |
| One-command startup must be built | **Already solved** | [`start.py`](../start.py) is documented in the README and setup guide |
| A narrative surface must be invented | **Partly solved** | The Insights/commentary feed exists, but deterministic automatic story detection does not |

Do not rebuild the solved foundations. Extend them:

- Use the existing metrics-history service and Trends view. The main remaining metrics
  gap is a fixed-baseline soccer evaluation; `baseline_match_score_diff` is currently a
  placeholder. Internal match rates alone do not prove improvement.
- Feed structured story events into the existing Insights surface instead of creating a
  competing activity feed.
- Use the deterministic replay harness in [REPLAY.md](REPLAY.md) as the eventual source
  for “watch this moment.” An event marker is not a replay until the required state is
  actually retained.
- Keep transfer, but move it behind an explicit secondary action in the fish inspector.
- Reuse champion registry history for a future Lab-facing code-evolution view. Champion
  records are not organism legends and should not be presented as if they were.

## Evaluation of the review

### Adopt now

| Suggestion | Decision |
|---|---|
| Click a fish to inspect and follow it | Highest-value interaction fix; make this the first experience PR |
| Persistent selection and follow camera | Small follow-up that turns inspection into observation |
| Deterministic Living History | Highest-value subsystem; structured facts first, optional prose later |
| “Since your last visit” | Strong retention feature once story events persist |
| Notable named organisms and lineages | Builds emotional attachment without turning the product into a creature editor |
| Canvas-dominant Observe mode | Correct default after the inspector and story primitives prove useful |
| Contextual overlays and a compact toolbelt | Make the tank itself the interface; expose one relevant lens or tool at a time |
| Sandbox / Experiment / Exhibition trust states | Required before playful interventions and scientific comparisons coexist |

### Adapt

- **Do not make one large experience-shell PR.** Land the inspector, selection, story
  schema, detectors, and presentation shell as focused Layer 2 PRs. `TankView.tsx` and
  `TankTrendsTab.tsx` are already line-ratchet files, so extraction is part of safe
  delivery.
- **Hide technical density by mode, not globally.** Observe is welcoming and
  canvas-first; Lab preserves exact metrics, seeds, provenance, and debugging surfaces.
- **Use three initial modes, not five top-level products.** Observe, Design, and Lab are
  sufficient for the alpha. Stories live in Observe and comparison tools live in Design
  or Lab until user testing demonstrates a need for separate top-level areas.
- **Start with deterministic story records.** A narrator may rewrite structured records
  for tone, but it may not invent facts or become the system of record.
- **Treat ecosystem scores as a profile.** Use resilience, diversity, efficiency,
  adaptability, cooperation, generality, innovation, and task performance where data
  supports them. Never collapse the product into one universal score.

### Defer until after the invited alpha

Public galleries, global tournaments, trading, friends, mobile notifications, and
public read-only links are valuable only after the core watch loop works. Federation
prerequisites remain owned by [FEDERATION.md](FEDERATION.md).

### Reject

- Separate game and research simulations.
- Direct fish design as the main progression loop.
- A universal ecosystem leaderboard score.
- LLM-only event narration without reproducible structured evidence.

## Delivery sequence

Status values are `NEXT`, `QUEUED`, and `DEFERRED`. One row is one PR unless the row
explicitly says otherwise. Detailed acceptance criteria are in
[UI_IMPROVEMENTS.md](UI_IMPROVEMENTS.md).

| Order | ID | Deliverable | Status | Depends on |
|---:|---|---|---|---|
| 1 | E0 | Remove the inactive `TankTabs` / `TankPlayTab` navigation fork | DONE | — |
| 2 | E1 | Fish inspector; transfer becomes secondary | NEXT | — |
| 3 | E2 | Selection persistence, highlight, and follow camera | QUEUED | E1 |
| 4 | E3 | Structured story-event schema, store, API, and first three detectors | QUEUED | — |
| 5 | E4 | Living History feed and event timeline markers | QUEUED | E1, E3 |
| 6 | E5 | “Since your last visit” recap | QUEUED | E3, E4 |
| 7 | E6 | Notable-organism and lineage legends | QUEUED | E1, E3 |
| 8 | E7 | Observe / Design / Lab shell; Observe becomes default | QUEUED | E1, E4 |
| 9 | E8 | Contextual overlays and intervention toolbelt | QUEUED | E7 |
| 10 | E9 | Trust states and intervention provenance | QUEUED | E7 |
| 11 | E10 | Hypothesis-led clone-and-compare design flow | DEFERRED | E9 |

E0 and E1 may be developed independently but should remain separate PRs. E3 should begin
with only three detectors—population danger/recovery, generation milestone, and lineage
share threshold—so the event contract can stabilize before detector breadth grows.

## Phase outcomes

### Phase 0: curiosity has somewhere to go

Complete E0–E2. Clicking a fish selects and highlights it; the inspector explains its
intent, energy, age, generation, lineage, mutations, and game participation. Keyboard
and touch users can open and close it. Selection survives normal state updates and
reconnects. Transfer is available only through an explicit inspector action.

### Phase 1: the world remembers

Complete E3–E6. A story record contains a stable id, type, frame, simulation time,
severity, involved entity/lineage ids, before/after metrics, detector threshold, and
replay availability. Detectors observe state without consuming RNG or mutating the
simulation. Events persist with the world, appear in Insights and on a compact timeline,
and can link back to the inspector. Recaps are computed from records since the client's
last-seen event id.

Legends are promoted by explicit criteria such as longevity record, surviving
descendants, tournament result, migration success, cross-domain ability, lineage
founding, or collapse survival. Do not name every fish and do not confuse benchmark
champions with in-world legends.

### Phase 2: the tank becomes the interface

Complete E7–E9. Observe is canvas-dominant and contains a compact world header, current
story, inspector, time controls, and contextual toolbelt. Design owns ecosystem recipes
and interventions. Lab retains the current exact research data and provenance. Host,
port, memory, and server health move under Admin within a player-facing Worlds area.

Trust states make intervention provenance visible:

- **Sandbox:** live interventions are allowed; no experimental-validity claim.
- **Experiment:** configuration and seed are versioned; interventions are blocked or
  formally logged; reproducibility can be verified.
- **Exhibition:** read-only presentation; visitors fork rather than mutate it.

### Phase 3: ecosystem design becomes an experiment

After the invited alpha, implement E10. The editor starts with a hypothesis and an
ecosystem recipe, offers clone-as-comparison, encourages changing one variable, and
compares outcomes with a multi-axis profile. It must not imply causal confidence that
the run design does not support.

## Guardrails for every experience PR

1. **No simulation side effects.** Telemetry, selection, event detection, and narration
   must not consume RNG or mutate simulation state.
2. **Layer 2 stays separate from Layer 1.** Do not mix UI/telemetry work with behavior
   algorithms, benchmark scoring, or champion changes.
3. **One focused PR.** Respect the god-class line ratchet; extract components instead of
   expanding pinned files.
4. **Preserve research capability.** Observe may hide density; Lab must keep exact data.
5. **Measure improvement against fixed references.** Population-vs-population win rates
   are zero-sum and cannot establish skill gain.
6. **Be honest about replay.** Disable “watch” when no replay segment exists.
7. **Meet [UI_SPEC.md](UI_SPEC.md).** Use tokens, CSS Modules, accessible focus behavior,
   keyboard/touch parity, and reduced-motion support.
8. **Test reconnect and fast-forward behavior.** Selection, history, and events must
   tolerate sparse delta publishing and full-state resync.

## Alpha definition of done

After E0–E9, invite 10–20 people to prepared ecosystems. The alpha succeeds when a new
visitor can pause, inspect, follow, and feed the tank without documentation; can explain
one meaningful change they observed; and returns to a recap that accurately describes
what happened. Measure task completion, inspector use, intervention comprehension, and
unprompted return—not only page views or time on screen.

---

*Updated 2026-07-11 from a repository audit and the July 2026 external product review.*
