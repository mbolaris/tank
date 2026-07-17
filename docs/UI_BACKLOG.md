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
- [x] **Make Watch Mode's tank fill the viewport, not just hide chrome.**
  `Canvas.tsx` now takes an opt-in `responsive` mode (measures its container,
  sizes the backing store to container-size x devicePixelRatio) instead of a
  fixed 1088x612 buffer, and Watch Mode drops `.sceneWorkspace`'s 1140px cap
  for a real viewport-height budget. Previously Watch Mode just added empty
  space around the same small canvas.
- [x] **Surface the Board as ambient events over the tank.** Shipped as
  `LivingWorldToasts.tsx` — new posts float over the canvas as small
  dismissible toasts, reusing `CommentaryFeed`'s existing fetch/poll via a
  shared `useCommentary` hook. No new backend work needed.
- [x] **Give Algae Reef / Protein Grotto an actual feeding capability.**
  Correcting an earlier entry in this backlog: this was already done before
  this backlog existed (commit `0f93a707`), not a gap. `core/entity_factory.py`
  attaches a real `FeedingCapability` (stock, depletion, cooldown, regrowth) to
  every reef/grotto in the default layout, and
  `backend/runner/commands/build.py` attaches the same config to any
  reef/grotto placed via Build Mode. `core/tank_interactions.py`'s
  `TankInteractionSystem` evaluates proximity/dwell triggers each frame and
  spawns real `Food` entities. Retired the older, separate
  `ResourcePatch`/`local_resource_patches_enabled` experiment (2 hardcoded
  patches, off by default, no dependents) since it was redundant with the
  working mechanic above — see `docs/SUBSYSTEM_CLASSIFICATION.md`'s retirement
  policy for optional/experimental subsystems.
- [x] **Give Watch / Build / Analyze real mode-switching UI.** `ModeSwitch.tsx`
  is a single floating segmented control (🎬 Watch / 🔨 Build / 📊 Analyze) in
  the canvas HUD, replacing the separate Watch Mode toggle and "+Build" pill.
  `useUiMode` derives one active mode and makes the three mutually exclusive:
  selecting one now backs out of whichever of the other two was active
  (previously Build and Analyze could be open at the same time). Analyze still
  has no dedicated boolean — it's "on" whenever a panel is visible — so
  selecting it restores the last-open panel rather than forcing a fixed one.

## High-value next steps

- [ ] **Widen normal mode's aquarium.** Outside Watch Mode, `.sceneWorkspace` /
  `.canvas-wrapper` still cap at 1140px/1200px on a `.main` column that goes
  up to 1400px — hundreds of pixels sit unused beside the tank on a normal
  desktop viewport. Now that the canvas is responsive (see above), raising
  these caps is a pure CSS change with no coordinate-math risk; the narrower
  research panels don't need to widen with it.
- [ ] **Add a free pan/zoom canvas camera.** The existing follow camera
  (`followViewport.ts`) only re-centers on a selected entity; there's still no
  way to freely explore the tank independent of any selection. More valuable
  now that the canvas actually has room to pan around in.
- [ ] **Turn goal zones into TankObjects, hidden by default.** The dashed
  circular `GOAL` markers read as debug geometry next to the styled
  reef/grotto/castle sprites. Render an actual object (arch/ring/hoop) and
  only show the raw collision zone in Build Mode or when the ball is near —
  same mechanics, a world object instead of a hitbox.
- [ ] **React to reef/grotto feeding visually.** The feeding capability itself
  is real (see Completed, above) but invisible — the canvas doesn't yet show
  stock level, depletion, or a dispense moment. A lush/depleted/glow treatment
  driven by `render_hint.capabilities`/the capability's stock ratio would make
  the ecosystem's food economy legible at a glance.

## P2 — later

- [ ] **Collapse the empty Board state.** Show a compact invitation to observe
  rather than a full-height panel of agent-oriented commands.
- [ ] **Explain energy balance discrepancies.** Add help text for the difference
  between measured energy change and the approximate inflow/outflow ledger.
- [ ] **Add user-selectable workspace presets.** For example: Observe (Trends),
  Operate (Ecosystem), Compare (Skills), and Collaborate (Board).
- [ ] **Remove the duplicate LIVE indicator.** One shows in the stats bar,
  another in the canvas HUD; keep one.
- [ ] **Regroup the default object layout into habitat zones.** The algae reef
  currently reads as floating mid-water rather than attached to terrain.
  Anchor reef/grotto to left/right habitat zones (matching
  `core/tank_objects.py`'s `DEFAULT_TANK_LAYOUT`) and keep the center corridor
  clear for soccer and general swim traffic.
- [ ] **Reorganize the control bar by purpose.** ~9 controls (Add Food, Spawn
  Fish, Pause, Fast, Reset, Hide HUD, Soccer toggle, World select, Plant
  Energy) currently sit at equal visual weight. Group by Simulation / World
  actions / Modes / Advanced, and de-emphasize Reset specifically since it's
  destructive and shouldn't read the same as Pause.

## Someday / stretch goal

- [ ] **Cinematic Director.** Once the camera and Living World Events have
  landed, an opt-in auto-camera that follows notable individuals or moments
  (a newborn from a high-performing lineage, a rare species, a feeder
  activation, a population crisis) with a one-line caption. This is the
  "leave it running and it tells you a story" payoff of the items above, not
  a starting point — sequence it last.
