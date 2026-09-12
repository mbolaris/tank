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

## Recently verified complete (2026-09-11)

Checked against the code rather than assumed. Two entries below had been sitting
in the open list while the work was already merged; an agent picking from this
list would have rebuilt them.

- [x] **Widen normal mode's aquarium.** The stage now fills the content column
  (canvas 916 -> 1080px at a 1600px viewport).
- [x] **Add a free pan/zoom camera.** `frontend/src/components/camera.ts`:
  scroll to zoom (1-4x, cursor-anchored), drag to pan, reset control. Follow
  and free look are one camera; `camera.test.ts` pins the equivalence.
- [x] **React to reef/grotto feeding visually** — *was already done when this
  entry said it was not*. `frontend/src/utils/renderer.ts::renderTankObject`
  reads `render_hint.feeder_activity`, and the active renderer
  (`TankSideRenderer` instantiates it) modulates the reef and grotto glow alpha
  by `stockRatio`, scales the shimmer/mote counts by it, and adds an
  `activationPulse` on a recent dispense. Stock, depletion and the dispense
  moment are all on screen.
- [x] **Remove the duplicate LIVE indicator.** The canvas HUD badge now renders
  only in Watch Mode, which is the one place the stats bar is hidden.

## High-value next steps

- [x] **Widen normal mode's aquarium.** Shipped: `TankStage.module.css` raised
  the caps (canvas 916px → 1080px measured, and the 200px-wide breakpoint gap
  that left the tablet canvas 8px wide is closed). The horizontal scrollbar is
  gone.
- [x] **Add a free pan/zoom canvas camera.** Shipped as
  `frontend/src/components/camera.ts` + `useCameraInteractions.ts` +
  `CameraControls.tsx`: wheel zoom about the cursor, drag to pan, clamped to
  the world, with the world re-rendered at zoom resolution up to
  `MAX_SUPERSAMPLE`. `followViewport.ts`'s behaviour is preserved exactly —
  `camera.test.ts` proves `cameraForTarget` + `getCameraViewport` reproduces
  `getFollowViewport` — and `e2e/tank-camera.spec.ts` drives real wheel/drag
  input against a live backend.
- [ ] **Turn goal zones into TankObjects, hidden by default.** The dashed
  circular `GOAL` markers read as debug geometry next to the styled
  reef/grotto/castle sprites. Render an actual object (arch/ring/hoop) and
  only show the raw collision zone in Build Mode or when the ball is near —
  same mechanics, a world object instead of a hitbox.

## P2 — later

- [ ] **Collapse the empty Board state.** Show a compact invitation to observe
  rather than a full-height panel of agent-oriented commands.
- [ ] **Explain energy balance discrepancies.** Add help text for the difference
  between measured energy change and the approximate inflow/outflow ledger.
- [ ] **Add user-selectable workspace presets.** For example: Observe (Trends),
  Operate (Ecosystem), Compare (Skills), and Collaborate (Board).
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

- [x] **Cinematic Director.** Shipped, now that both prerequisites had landed.
  `hooks/cinematicDirector.ts` holds the shot-selection rules as pure
  functions, `useCinematicDirector.ts` drives them, and
  `components/CinematicDirector.tsx` owns both the opt-in toggle and the
  caption. It cuts to the subject of a new story event, captions it with the
  event's own words, then hands the tank back after `SHOT_DURATION_MS`.
  Three decisions worth keeping:
  - **The backlog is not the story.** `useStoryEvents` backfills 200 events, so
    the cursor is taken when the director is switched on; otherwise enabling it
    would immediately cut to something from ten minutes ago.
  - **The viewer always wins.** The director follows by driving the ordinary
    selection, so any click, follow toggle, or inspector action ends the shot
    (`viewerTookOver`) with nothing wired per interaction.
  - **A moment without a subject is still a moment.** `population_danger` names
    no individual and is the most dramatic thing the tank does, so a shot may
    carry no entity: the caption runs and the camera stays put. `prefers-
    reduced-motion` uses the same path deliberately — captions, no camera
    movement.

  Remaining ideas from the original entry, not yet done: reacting to feeder
  activations and rare species (neither is a story-event detector yet), and
  ranking shots by interest rather than always taking the newest.
