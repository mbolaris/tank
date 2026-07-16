# UI improvement backlog

This backlog was created from an interactive review of the live Tank and
Network views at 1280 x 720 and 390 x 844. Priorities reflect impact on a
researcher trying to observe, understand, and safely operate a live world.

## Completed P0s

- [x] **Focused analysis workspace.** The tank now opens to Trends and allows
  one analysis view at a time. Closing the active view leaves the tank
  unobstructed. The selection persists in `localStorage` under a versioned key.
  This replaces the prior default stack of Board, Skills, Soccer, and Ecosystem
  panels, which made the page roughly 4,885 px tall on desktop.
- [x] **Mobile layout repair.** The navigation, Network header, server metadata,
  and tank cards now wrap within a 320–600 px viewport. Network cards no longer
  require a 350 px minimum column and can use the available width.
- [x] **Accessible control names and focus.** The Plant Energy slider has an
  associated label; the soccer display, Network pause/fast-forward/delete, and
  transfer-history close controls have meaningful names; key buttons show a
  visible keyboard focus ring. New Tank form labels are programmatically
  associated with their inputs.

## Completed P1s

- [x] **Place a compact evolution-health readout beside the aquarium.** Show
  selection, diversity, turnover, starvation, and population stability with a
  direct link to Trends, so the main research question is visible without
  scrolling.
- [x] **Clarify metric time windows and absent data.** Every metric should say
  whether it is recent, since-start, or last-N-frames. Display "No deaths
  observed" rather than a misleading `0 / 0` starvation rate.
- [x] **Use loading states for Network snapshots.** Retain the prior snapshot or
  show a skeleton while fresh world status loads; do not briefly report zero
  fish, energy, generation, and FPS for a running world.
- [x] **Make Network actions clearer and safer.** Keep the new accessible names,
  then consolidate pause/speed/delete into labeled or overflow actions and
  confirm destructive actions with the tank identity.
- [x] **Repair soccer provenance and result states.** A world should not show
  standings with played matches alongside "No matches recorded yet", and leader
  rows should identify their source tank.

## High-value next steps

Identified while shipping Watch Mode (see `git log` on `TankView.tsx` /
`EvolutionHealthReadout.tsx` / `EntityInspectorDrawer.tsx`): a lot of the
"make it fun to watch" wishlist turned out to already have backend or
frontend infrastructure sitting unused behind a dashboard tab. These three
are the highest-leverage remaining gaps, ordered by how much already exists
to build on.

- [ ] **Surface the Board as ambient events over the tank, not a buried tab.**
  `CommentaryFeed.tsx` / `backend/commentary_store.py` already carry
  agent-posted observations (species emerging, population crashes, new
  records) with topics and reactions, polled every 4s — but they're only
  visible behind the "Board" entry in the Analysis tab bar, and invisible
  entirely in the new Watch Mode. Float new posts as small dismissible
  toasts over the canvas using the same fetch/poll the feed already does;
  clicking one can jump into the full Board. No new backend work required.
- [ ] **Add a free pan/zoom canvas camera.** The existing follow camera
  (`followViewport.ts`) only re-centers on a selected entity. There is no
  way to freely explore the tank — mouse-wheel zoom and click-drag pan,
  independent of any selection, would make Watch Mode substantially more
  engaging on its own.
- [ ] **Give Algae Reef / Protein Grotto an actual feeding capability, then
  react to it visually.** `core/tank_objects.py`'s own catalog descriptions
  call them "ready for a feeding capability" — today they are purely
  decorative placements with no stock, depletion, or usage tracking at all.
  This is a bigger, two-sided item (a real backend feeding mechanic before
  any lush/depleted/glow visual can mean anything), but it is the
  prerequisite for the single most-requested "glance at the tank and
  understand the ecosystem" improvement.

## P2 — later

- [ ] **Collapse the empty Board state.** Show a compact invitation to observe
  rather than a full-height panel of agent-oriented commands.
- [ ] **Explain energy balance discrepancies.** Add help text for the difference
  between measured energy change and the approximate inflow/outflow ledger.
- [ ] **Add user-selectable workspace presets.** For example: Observe (Trends),
  Operate (Ecosystem), Compare (Skills), and Collaborate (Board).
