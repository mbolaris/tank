# Soccer Arena Design

> **Status:** design spec, not yet implemented. This document is the contract
> for the Soccer Arena work. Implementers should read this first, then
> [UI_SPEC.md](UI_SPEC.md) for the token system, then the staged PR plan in
> §12 below.
>
> **Scope:** the soccer arena, its match presentation, and its relationship to
> the aquarium. Explicitly *not* in scope: the aquarium renderer, tank
> navigation at large, RCSS network protocol, or new soccer physics.

---

## 1. Product Direction

**Soccer is not played inside the aquarium.**

Today the ball and goals live inside the tank itself (`tank_practice_enabled`
puts a ball at tank centre, and `core/movement_strategy.py` gives ball pursuit
priority 2, ahead of food seeking at priority 4). That remains valid as
*practice* — it is how fish acquire ball-engagement traits — but it is not the
competition.

The competition happens in a **dedicated soccer arena**: a separate view inside
the same simulation world and the same application, with its own pitch, its own
coordinate space, and its own presentation layer.

```
┌─────────────────────────────────────────────────────────────┐
│ AQUARIUM (World 1A)                                         │
│  fish live, eat, evolve, reproduce, inherit traits,         │
│  practice with the tank ball, and QUALIFY for the team      │
└───────────────────────────┬─────────────────────────────────┘
                            │  selection (core/minigames/soccer/selection.py)
                            │  "6 fish leave the tank to represent World 1A"
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ SOCCER ARENA                                                │
│  proper pitch · structured match · scoreboard · broadcast   │
│  opponent = another tank | frozen reference team | RCSS      │
└───────────────────────────┬─────────────────────────────────┘
                            │  results, rewards, records, breakthroughs
                            ▼
                     back to the aquarium
```

The three-layer rule of the project applies: the arena is where **Layer 1**
improvement becomes *legible*. A viewer should be able to see that this tank's
team is better than it was twenty generations ago.

### 1.1 Vocabulary

| Term | Meaning |
|---|---|
| **Arena** | The dedicated soccer view. Full-width, its own route/view mode. |
| **Pitch** | The playing surface inside the arena. |
| **Team** | A named side fielded by one tank (e.g. "World 1A Team"). |
| **Roster** | The fish selected to represent the tank in this match. |
| **Reference team** | A frozen ruler from `core/minigames/soccer/reference_teams.py` (L0–L3). |
| **Team Skill** | Standardised ladder-derived rating (`skill_index`), *not* league points. |
| **League** | Round-robin fixtures between tanks/bots; produces points and standings. |

---

## 2. Critique of the Current State

> **Note:** the screenshot referenced in the design brief did not arrive with
> the request. This critique is derived from the live implementation —
> `TankSoccerTab.tsx`, `SoccerLeagueLive.tsx`, `SoccerPitch.tsx`, and
> `renderers/soccer/SoccerTopDownRenderer.ts` — which is what produces that
> screenshot. If the screenshot shows something this section misses, treat the
> screenshot as authoritative and amend this section.

### 2.1 Structural problems

1. **The match is a panel, not a venue.** The arena is rendered inside a
   `Panel title="Soccer League"` in the analyze-mode panel grid
   (`TankView.tsx:495`). It competes for width with Board, Skills, and Poker
   panels. A live match is an *event*; it should be able to take the screen.
2. **Fixed 800×450 canvas with `height: auto`.** `SoccerPitch` defaults to
   `width=800, height=450` and then CSS-scales it (`width: 100%`,
   `maxWidth: 800px`). The backing store never matches the display size, so on
   a wide screen the pitch is upscaled and soft, and on a narrow one it is
   letterboxed inside a panel that is already narrow. There is no DPR handling
   despite `rc.dpr` being computed and passed.
3. **No render loop.** The renderer runs in a `useEffect` keyed on
   `gameState`. It draws exactly one frame per state push. Ball spin is derived
   from `Date.now()` inside that single draw, so it does not animate; motion is
   as choppy as the websocket cadence. Trails, halos, and easing are impossible
   in this structure.
4. **Everything is equally loud.** Standings, skill progress, fish leaders, and
   the results list are all stacked below the pitch at the same weight
   (`TankSoccerTab.tsx`). Nothing tells the viewer where to look.
5. **No view modes.** There is one presentation, and it serves neither the
   casual watcher nor the analyst.

### 2.2 Rendering problems

6. **The pitch is flat and dim.** `#2d5016` letterbox background with a
   `#2e9a30` field, 1.5px pure-white lines. It reads as a debug fixture, not a
   surface. The goals are `#222222` rectangles — dark boxes on dark green,
   which is the *least* readable choice for the single most important landmark.
7. **Field markings are proportion-guessed, not RCSS-derived.** Centre circle
   is `min(w,h)*0.15`, penalty box is `height*0.65 × width*0.16`, penalty spot
   at `width*0.11`. These are eyeballed fractions of the canvas. Real RCSS
   dimensions are absolute metres (penalty area 16.5 m deep, centre circle
   9.15 m radius); the current code will distort every marking the moment field
   proportions change — which is exactly what happens when we go to 11v11.
8. **Team identity is a 50%-alpha ring in yellow/red.** `rgba(255,255,0,0.5)` /
   `rgba(255,0,0,0.5)`. Yellow on green is low-contrast; the ring sits *behind*
   a genome-coloured fish, so a yellow-ish fish on the left team is
   indistinguishable at a glance. There is no side/attacking-direction cue at
   all.
9. **Jersey numbers are drawn at the fish's centre in white Arial** with a soft
   shadow, on top of the avatar. They collide with the fish's own body art and
   become unreadable at small radii (`max(10, r*0.6)` px on a 15px avatar).
10. **The ball can be smaller than a player's number.** `max(radius, 10)` in
    scene units, then scaled down by the fit transform. On a panel-width canvas
    the ball is a handful of pixels with no halo, no trail, and no contrast
    ring against white line markings.
11. **Two nested, redundant coordinate transforms.** `buildSoccerScene`
    projects metres → a hard-coded 1088×612 "scene", then `render()` fits that
    scene into the canvas with a second scale. The intermediate 1088×612 is
    arbitrary and forces a 16:9 assumption that the field data may not share.
12. **Possession is a dashed amber ring; selection is a dashed white ring.**
    Two dashed rings, similar radii, different meanings.
13. **No z-ordering by relevance.** Players are drawn in array order. The ball
    is drawn *underneath* all players (`drawBall` before the players loop), so
    the one object that must never be lost is the one most likely to be
    occluded.

### 2.3 Information problems

14. **The scoreboard is a strip, not a broadcast overlay.** It shows round,
    names, score, and a clock derived as `frame/10` — but no competition stage,
    no possession, no recent event, and its "live" indicator is an unlabelled
    green dot in an 80px spacer.
15. **Improvement is invisible during the match.** `SoccerSkillProgress` is a
    separate three-card block below the pitch; it polls
    `/api/skill/snapshots` every 10 s and is entirely disconnected from what is
    happening on the field. Nothing ever says "this is the first time we have
    beaten Chase-and-Shoot".
16. **The three kinds of number are not distinguished.** League points
    (`leaderboard`), live match score, and standardised ladder skill
    (`skill_index`) are presented as peers. Cumulative goals are shown as if
    they were evidence of improvement; they are not.
17. **Goals get no moment.** A goal appears only as "Last goal: LEFT by 284" in
    the post-match results card. The single most exciting event in the sport
    has no presentation at all.
18. **Nothing connects the team to its tank.** No tank emblem, no
    "Representing World 1A", no roster with generation/lineage, no way back.
19. **Match history is a raw event dump** — `12f ago`, `Energy Delta +3.4`,
    `Reason: insufficient_eligible_fish`. This is debugging output shown to
    spectators.

### 2.4 What is already good and must be kept

- Genome-derived avatars via `drawAvatar` — fish keep their identity on the
  pitch. This is the best thing about the current renderer.
- Field dimensions already arrive in metres from the backend
  (`SoccerMatchState.field.length/width/goal_width/goal_depth`), centred at the
  origin. The data contract is RCSS-shaped already.
- `render_hint` already carries `team`, `jersey_number`, `stamina`,
  `facing_angle`, `has_ball`, and velocity.
- The frozen reference ladder (L0–L3) is a genuinely sound absolute yardstick.
- Standings columns (P/W/D/L/GD/Pts) are correct football convention.

---

## 3. Information Hierarchy

Five tiers. Anything that cannot be placed in a tier does not go on screen.

| Tier | Content | Treatment |
|---|---|---|
| **0 — The field** | Pitch, ball, players, goals, attack direction | Largest element on screen. Always visible. Never occluded by more than ~12% of its area. |
| **1 — State of the match** | Team names, score, clock, stage, live/paused | Persistent broadcast overlay, top of the arena, ~64 px tall. Legible at a glance from across a room. |
| **2 — What just happened** | Goal, save, shot, possession change, halftime, breakthrough | Transient. Enters, holds 2–4 s, fades. Never more than one major card at a time. |
| **3 — Is it getting better?** | Team Skill, ladder rung, recent form, next milestone | A compact rail. Always present in Broadcast, expanded in Analysis. |
| **4 — Context** | Standings, lineups, match history, per-fish stats | Behind tabs. One at a time. Never competes with tier 0. |

**Governing rules**

- Tier 0 always wins a conflict. Overlays are translucent and edge-anchored.
- At most **one** tier-2 element animating at a time. Queue, don't stack.
- Tier 3 numbers are *rates and ranks*, never cumulative totals.
- Tier 4 is opt-in. The default view shows it collapsed or not at all.

---

## 4. Desktop Layout — Broadcast (default)

Target: ≥1280 px wide. The arena is a full view, not a panel.

```
┌────────────────────────────────────────────────────────────────────────────┐
│  ← Back to World 1A          SOCCER ARENA            [BROADCAST][TAC][ANA] │  48px
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   ┌──────────────────────────────────────────────────────────────────┐     │
│   │ ◤ WORLD 1A          2  –  0          REEF DELTA ◥                 │     │  scoreboard
│   │   Gen 41 · L2 ✓      12:04 · 2ND     Gen 33 · L1 ✓                │     │  64px
│   │   ▓▓▓▓▓▓▓▓▓░░░░░  possession 63%     LEAGUE · ROUND 4 · LIVE ●    │     │
│   └──────────────────────────────────────────────────────────────────┘     │
│                                                                            │
│  ┌─────────┐ ┌────────────────────────────────────────────┐ ┌───────────┐  │
│  │ LINEUP  │ │                                            │ │ SOCCER    │  │
│  │ ▸ #284  │ │        ← attacking          attacking →    │ │ PROGRESS  │  │
│  │   #91   │ │   ╔════════════════════════════════════╗   │ │           │  │
│  │   #12   │ │   ║  ┌──┐                        ┌──┐  ║   │ │ Skill  68 │  │
│  │         │ │   ║  │  │        ( ● )           │  │  ║   │ │        ↑9 │  │
│  │ ─────── │ │   ║  └──┘    ◉  ◉    ◉           └──┘  ║   │ │           │  │
│  │ ▸ #77   │ │   ║              ◉      ◉   ◉          ║   │ │ Beat:     │  │
│  │   #44   │ │   ╚════════════════════════════════════╝   │ │ Chase&    │  │
│  │   #08   │ │                                            │ │ Shoot     │  │
│  │         │ │                                            │ │ Next:     │  │
│  │ 200px   │ │              fluid, ≥ 720px                │ │ Formation │  │
│  │ collapsi│ │                                            │ │           │  │
│  │ ble     │ │                                            │ │ W W D W L │  │
│  └─────────┘ └────────────────────────────────────────────┘ └───────────┘  │
│                                                                  240px      │
├────────────────────────────────────────────────────────────────────────────┤
│  [ Live Match ] [ Lineups ] [ Team Progress ] [ Standings ] [ History ]     │  40px
│  ── collapsed by default; expands to a 240px drawer over the lower pitch ── │
└────────────────────────────────────────────────────────────────────────────┘
```

Rules:

- **Pitch is the flex child.** It consumes all width left after the two rails
  and all height left after scoreboard and tab bar, then letterboxes to the
  field's true aspect ratio inside that box.
- Left rail (Lineup) and right rail (Progress) are collapsible to 0. At
  <1440 px the left rail auto-collapses to a 40 px strip of team-coloured
  number chips.
- The bottom drawer overlays the pitch's lower ~30% at 92% opacity when open.
  Opening it never resizes the pitch canvas (avoids a re-fit mid-match).
- Goal/breakthrough cards render in a centred overlay layer above everything
  except the scoreboard.

### 4.1 Tactical layout

Same shell. Differences:

- Pitch is forced to fit fully at all times, centred, with a fixed 2.5% margin.
- Right rail switches from Progress to **Formation & Spacing**: team shape
  polygon area, average x-position per player, possession-chain count.
- Player trails on (last ~90 frames), pass lines persist ~3 s, heat tint
  optional.
- Scoreboard compresses to 44 px (score + clock only).

### 4.2 Analysis layout

- Pitch shrinks to ~55% width, left-anchored.
- Right column becomes a full metrics stack: ladder history sparkline,
  per-fish contribution table, evaluation history, policy/param readout.
- No transient event cards; events go to a scrolling timeline instead.

---

## 5. Compact Layout (<900 px)

Single column, vertical priority order:

```
┌──────────────────────────┐
│ ← W1A   ARENA   [B][T][A]│  40px
├──────────────────────────┤
│ W1A  2 – 0  RFD          │  scoreboard, 52px
│ 12:04 · 2ND · LIVE ●     │  two lines only
├──────────────────────────┤
│                          │
│   ╔══════════════════╗   │  pitch, rotated?  NO —
│   ║                  ║   │  keep landscape, full width,
│   ║   ◉  ( ● )  ◉    ║   │  aspect-fit. Never rotate the
│   ║                  ║   │  pitch: attack direction must
│   ╚══════════════════╝   │  stay left/right to match the
│    ←W1A        RFD→      │  data model.
├──────────────────────────┤
│ Skill 68 ↑9 · W W D W L  │  progress strip, 36px, one line
├──────────────────────────┤
│ [Match][Line][Prog][Tbl] │  segmented control
│  ...content...           │  scrolls under
└──────────────────────────┘
```

- Rails become tabs. Progress collapses to a single strip.
- Goal cards become a full-width banner under the scoreboard rather than a
  centred card, so they never cover the pitch.
- Below 600 px the lineup shows numbers only, no names.
- Touch: tap a player to select (drawer opens with their card), tap pitch
  background to deselect. No hover-dependent information anywhere.

---

## 6. Detailed Designs

### 6.1 Scoreboard

Broadcast overlay, not a config panel. Three zones: home block, centre block,
away block.

```
┌───────────────────────────────────────────────────────────────────┐
│ ▌ WORLD 1A TEAM              2 – 0              REEF DELTA ▐      │
│ ▌ ⬢ tank emblem  Gen 41       12:04              Gen 33  ⬢       │
│ ▌ ████████████░░░░░░  63%     2ND HALF          37%  ░░░░████    │
│                    LEAGUE · ROUND 4 · ● LIVE                      │
└───────────────────────────────────────────────────────────────────┘
```

| Element | Spec |
|---|---|
| Team name | `--font-size-lg` 600 weight, `--color-text-main`. Team colour used as a 4 px leading bar, **not** as the text colour (keeps names legible on dark). |
| Score | `--font-mono`, 34 px, 800 weight, `--color-text-main`. Scoring side's digit flashes to its team colour for 600 ms then returns. |
| Clock | `--font-mono` 15 px. Displays `mm:ss` derived from match frames **plus** a `frame` tooltip. Never invent seconds: label it `SIM 12:04` when the mapping is nominal. |
| Stage | `LEAGUE · ROUND 4`, `LADDER · vs L2`, `FRIENDLY`, `RCSS` — one uppercase 11 px line, `--color-text-dim`. |
| Status | Dot + word: `● LIVE` (success), `❙❙ PAUSED` (warning), `HALF TIME` (dim), `FULL TIME` (dim), `⚠ DISCONNECTED` (danger). Never a bare dot. |
| Possession | Two-sided bar, team colours, 4 px tall, rolling 30 s window. Optional; hidden if the backend does not supply it. |
| Emblem | 20 px tank emblem (see §6.7) — the only aquarium visual allowed in the arena. |

Behaviour: the scoreboard never moves, never resizes between states, and never
disappears. State changes swap content inside fixed slots.

### 6.2 Field

Replace the two-transform pipeline with **one** transform derived from real
field metres.

```
metres (centred at origin, +x = right, +y = down)
  ──[ fitTransform(field, viewport, margin) ]──▶  css pixels
```

```ts
interface PitchTransform {
  scale: number;        // px per metre, uniform (never anisotropic)
  originX: number;      // px offset of field x=0
  originY: number;      // px offset of field y=0
  toScreen(x: number, y: number): [number, number];
  toField(px: number, py: number): [number, number];
}
```

Everything — markings, players, ball, trails, labels — is expressed in metres
and passed through `toScreen`. This is the single change that makes 11v11 and
RCSS field dimensions free.

**Markings, in metres (RCSS-standard, scaled proportionally for small fields):**

| Marking | Metres |
|---|---|
| Touchline / goal line | field length × width from `field.length` / `field.width` |
| Halfway line | x = 0 |
| Centre circle | r = 9.15 |
| Centre spot | r = 0.15 |
| Penalty area | 16.5 deep × 40.32 wide |
| Goal area | 5.5 deep × 18.32 wide |
| Penalty spot | 11.0 from goal line |
| Penalty arc | r = 9.15 about the penalty spot, clipped outside the area |
| Corner arc | r = 1.0 |
| Goal | `field.goal_width` × `field.goal_depth` from the payload |

For sub-regulation fields (the current small-sided pitch), scale all marking
constants by `field.length / 105` so the pitch stays proportionate rather than
having a penalty area that swallows the field.

**Surface treatment:**

- Base: `#1b6b3a` → `#15532e` vertical gradient (darker than today's `#2e9a30`;
  it must sit *under* bright overlays without fighting them).
- Mow stripes: 8 alternating vertical bands at ±3% lightness. Cheap, gives
  scale reference and depth without fake 3D.
- Subtle vignette: radial darkening to 12% at the corners.
- Lines: `rgba(255,255,255,0.82)`, 0.12 m wide (so line weight scales with the
  pitch), with a 1 px `rgba(0,0,0,0.25)` under-stroke for contrast on stripes.
- Surround: `--color-bg-deep` void with a soft inner shadow at the touchline —
  the "stadium edge". No crowd, no stands, no sky.
- Goals: bright, not dark. Frame in `rgba(255,255,255,0.9)` 0.2 m, net as a
  fine cross-hatch at `rgba(255,255,255,0.18)`, and the goal mouth tinted with
  the *defending* team's colour at 12% alpha. This is what makes "which goal is
  whose" readable in under a second.
- Attack direction: a low-contrast chevron band just inside each touchline
  behind each half, pointing the way that half's occupants attack, plus a
  persistent `← WORLD 1A` / `REEF DELTA →` label outside the touchlines.

**Rendering:** the static layer (grass, stripes, markings, goals, vignette)
draws once to an offscreen canvas and is re-drawn only on resize. The dynamic
layer (players, ball, trails, effects) draws every animation frame. This is
required for the 60 fps loop; today's single-draw-per-push cannot support
trails.

### 6.3 Fish / Player Treatment

**The fish must stay a fish.** Keep `drawAvatar` and genome colouring exactly
as it is. Add team identity *around* the fish, never over it.

Recommended treatment — **team ring beneath + jersey badge offset**:

```
        ╭────╮
        │ 12 │ ← badge: team-coloured pill, 9px mono,
        ╰────╯   anchored up-left of the body, only
      ⌢⌢⌢⌢⌢⌢     drawn above a minimum on-screen radius
     ( ●    ⟩⟩   ← the fish, unmodified genome art
      ⌣⌣⌣⌣⌣⌣
    ╰──────────╯ ← contact ring: 2px team colour arc,
                   drawn UNDER the fish, opened at the
                   fish's heading so it reads as a
                   direction cue as well as a team cue
```

Why this over the alternatives:

| Option | Verdict |
|---|---|
| **Ring beneath + offset badge** | ✅ **Recommended.** Team colour never touches genome colour, so both stay readable. The ring doubles as a ground-contact shadow (depth) and a heading cue (the opening). The badge sits in dead space, so numbers never collide with body art. |
| Coloured outline on the body | Rejected — a 2 px stroke on a 15 px avatar visually recolours the fish and destroys the genome signal at small sizes. |
| Team-coloured fins | Rejected as *primary* — too small to read at match zoom, and fins are already a genome-expressed feature. Keep as a secondary flourish in Analysis mode only. |
| Jersey side-stripe on the body | Rejected — requires body-space UV mapping in canvas and mangles the avatar silhouette. |
| Number centred on the body | Rejected — this is today's bug. |

Additional per-player cues, in strict priority order (at most two active at
once on any given player):

| Cue | Visual | When |
|---|---|---|
| Possession | Solid team-coloured ring, 3 px, 1.15× radius, with a slow 1.2 s pulse | `has_ball` |
| Selected | White 2 px dashed ring at 1.35× radius + persistent name label | User selection |
| Scorer emphasis | Golden bloom + 1.25× scale ease-out over 900 ms | 2 s after goal |
| Stamina | Thin arc on the ring's lower half, drains clockwise | Tactical/Analysis only |
| Role | Single glyph in the badge corner (`D`/`M`/`F`/`GK`) | Tactical/Analysis only |

**Z-order (back to front):** ground rings → trails → non-involved players →
teammates of ball carrier → ball carrier → ball → effects → labels. The ball is
never behind a player.

**Labels fade.** A player's name/ID label appears for 2.5 s after they touch
the ball, then fades. Selected players keep a permanent label. Nothing else
does. Never label all 12 (or 22) players at once.

### 6.4 Ball

The ball is the single most important pixel on screen and is currently the
weakest.

| Layer | Spec |
|---|---|
| Minimum size | Never smaller than 7 css px radius regardless of zoom, and never larger than 0.5 m of true scale. Clamp, don't scale linearly. |
| Contrast ring | 1.5 px `rgba(0,0,0,0.55)` outer stroke. Guarantees separation from white line markings — the case where the ball currently disappears. |
| Halo | Radial `rgba(255,255,255,0.22)` → transparent, radius 2.2×, always on but subtle. Intensity rises with speed. |
| Trail | Last 12 positions, tapering width and alpha, only rendered above ~4 m/s. Team-tinted to whoever last touched it. |
| Spin | Driven by accumulated distance travelled, not `Date.now()` — so it stops when the ball stops. |
| Loose-ball flash | When possession is nobody's for >1.5 s, the halo gets a slow breathe. Draws the eye to a contested ball. |
| Shot line | On a kick with power above a threshold, a 250 ms fading line from kick origin along the velocity vector. |

### 6.5 Goal Presentation

The one moment that gets full treatment.

**Timeline (total ~3.6 s, non-blocking — the sim keeps running):**

| t | Effect |
|---|---|
| 0 ms | Goal detected. Scoring team's goal mouth flashes to full team colour; a shockwave ring expands from the ball. |
| 0–200 ms | Pitch desaturates to 60% *except* a radial window around the scorer. Scoreboard digit animates 0→1. |
| 250 ms | Card enters from below with a 220 ms ease-out. Ball trail from the shot origin redraws once, bright. |
| 250–3000 ms | Card holds. Scorer's fish gets the golden bloom (§6.3). |
| 3000–3600 ms | Card fades and drops 8 px. Desaturation releases. Play presentation resumes. |

**Card:**

```
╔════════════════════════════════════════╗
║  ⚡ G O A L                             ║   ← 11px letter-spaced label
║                                        ║
║  WORLD 1A TEAM                         ║   ← 22px, team colour leading bar
║  ┌──┐                                  ║
║  │🐟│  FISH #284  ·  Gen 41            ║   ← the actual avatar, 40px,
║  └──┘  Assist: Fish #91                ║     rendered live from genome
║                                        ║
║  WORLD 1A LEADS  2 – 0        12:04    ║   ← 13px dim
╚════════════════════════════════════════╝
```

The scorer's real avatar in the card is what ties the moment back to the
aquarium. It is a fish, and you can see which fish.

**Event tiers** — this is how we avoid visual noise:

| Tier | Events | Treatment |
|---|---|---|
| **Major** | Goal, breakthrough (§6.6), final result | Full card, ~3.6 s, pitch treatment, at most one at a time |
| **Notable** | Save, shot on target, kickoff, halftime, possession swing >3 passes | 220 px toast, top-right of pitch, 1.8 s, stacked max 2 |
| **Ambient** | Pass, tackle, throw-in, routine possession change | No card. Rendered *on the pitch* only (pass line, ring change). Logged to the timeline. |

Rate limit: no more than one Notable toast per 1.2 s; excess collapses to the
timeline. Major events preempt and clear Notable toasts.

**Kickoff:** 1.4 s — centre circle pulses, both team names slide in from their
sides and settle into the scoreboard, `KICK OFF` label, then clear.
**Halftime:** pitch dims 25%, `HALF TIME` card with the half's shot/possession
summary, teams' attack-direction labels swap sides with a 400 ms cross-fade
(this is important — the swap must be *shown*, not silently applied).
**Full time:** result card with final score, scorers list, points/rating delta,
and — if applicable — the breakthrough banner.

### 6.6 Team Progress

The panel that answers "is this tank getting better?". Lives in the right rail
in Broadcast, expands in Analysis.

```
┌──────────────────────────────┐
│ SOCCER PROGRESS              │
│ ──────────────────────────── │
│ TEAM SKILL                   │
│   68  ↑9                     │  ← skill_index, delta vs oldest snapshot
│   ▁▂▂▃▅▅▆▆█  since gen 12    │  ← sparkline over snapshots
│ ──────────────────────────── │
│ REFERENCE LADDER             │
│   L0 Stationary      ✓       │
│   L1 Random Walk     ✓       │
│   L2 Chase & Shoot   ✓       │  ← highest beaten, emphasised
│   L3 Formation      +0.4 ◐   │  ← current target w/ live margin
│ ──────────────────────────── │
│ LEAGUE                       │
│   2nd of 5 · 11 pts          │
│   Last 5:  W W D W L         │  ← coloured chips
│ ──────────────────────────── │
│ TOP PERFORMERS               │
│   #284  Gen 41   7g 3a  ★    │
│   #91   Gen 39   2g 6a       │
│ ──────────────────────────── │
│ NEXT MILESTONE               │
│   Beat Formation (L3)        │
│   need +0.6 goals/match      │
└──────────────────────────────┘
```

**The three number families must be visually distinct and labelled:**

| Family | Source | Label style | Meaning |
|---|---|---|---|
| **Skill** | `/api/skill/snapshots`, ladder vs frozen refs | Cyan accent, `SKILL` tag | Absolute, longitudinally comparable. **This is the improvement metric.** |
| **League** | `soccer_league_live.leaderboard` | Amber accent, `LEAGUE` tag | Relative to current opponents. Says nothing absolute. |
| **Match** | `active_match.score` and live stats | White/team colours | This match only. |

Never let cumulative goals imply improvement. If we show total goals anywhere,
it is labelled `career` and sits in tier 4.

**Breakthroughs.** These are the payoff moments. Each fires once, is persisted,
and gets a Major-tier card during or after the match:

| Breakthrough | Trigger |
|---|---|
| `LADDER RUNG CLEARED` | First match where a previously-unbeaten reference rung is beaten |
| `TEAM SKILL RECORD` | `skill_index` exceeds all prior snapshots for this tank |
| `CHILD SURPASSES PARENT` | A fish's contribution score exceeds its parent's best |
| `NEW LEADING SCORER` | Career goals leader changes |
| `ASSIST RECORD` | New single-match or career assist high |
| `LEAGUE PROMOTION` | Tank moves up a position at round end |
| `FIRST BLOOD vs EXTERNAL` | First win against an RCSS client |

Breakthrough card styling: same geometry as the goal card, but cyan/violet
accent (Tank World identity colours) rather than team colour, with a
`BREAKTHROUGH` eyebrow. It must feel like a *project* milestone, not a sports
one — because it is.

### 6.7 Standings

Supports the match; never dominates it. Lives in the bottom drawer.

```
┌────────────────────────────────────────────────────────────────┐
│ LEAGUE STANDINGS                          Round 4 of 10        │
├──┬──────────────────────┬──┬──┬──┬──┬────┬────┬────────────────┤
│  │ TEAM                 │ P│ W│ D│ L│ GD │ PTS│ SKILL          │
├──┼──────────────────────┼──┼──┼──┼──┼────┼────┼────────────────┤
│1 │ ⬢ Reef Delta         │ 4│ 3│ 1│ 0│ +7 │ 10 │ 71  ↑4         │
│2 │ ⬢ World 1A Team  ◀   │ 4│ 3│ 0│ 1│ +5 │  9 │ 68  ↑9         │
│3 │ ▣ Chase & Shoot (L2) │ 4│ 1│ 2│ 1│  0 │  5 │ —   frozen     │
│4 │ ⬢ Coral Basin        │ 4│ 1│ 0│ 3│ -4 │  3 │ 44  ↓2         │
│5 │ ▣ Random Walk (L1)   │ 4│ 0│ 1│ 3│ -8 │  1 │ —   frozen     │
└──┴──────────────────────┴──┴──┴──┴──┴────┴────┴────────────────┘
   ⬢ tank team    ▣ frozen reference    ◀ your tank
```

- Your tank's row is highlighted with a 3 px cyan leading bar and never
  scrolled out (sticky if the table overflows).
- Reference teams are visually marked as frozen — their skill column reads
  `frozen`, because a ruler that moves is not a ruler.
- Skill delta column is optional and hidden below 900 px.
- Teams currently playing get a live pulse on their row.

### 6.8 Lineups

```
┌─────────────────────────────────┐
│ WORLD 1A TEAM   Representing ⬢  │
│ ─────────────────────────────── │
│ ┌──┐ 12  FISH #284       ★      │  ← avatar rendered from real genome
│ │🐟│     Gen 41 · ↑#91          │  ← generation · parent
│ └──┘     7g 3a · skill 74       │
│ ┌──┐  7  FISH #91               │
│ │🐟│     Gen 39 · ↑#40          │
│ └──┘     2g 6a · skill 66       │
│ ┌──┐  3  FISH #12               │
│ │🐟│     Gen 40 · founder       │
│ └──┘     0g 1a · skill 51       │
│ ─────────────────────────────── │
│ Avg generation 40.0             │
│ [ Return squad to tank ]        │
└─────────────────────────────────┘
```

- Hovering/selecting a row highlights that fish on the pitch (and vice versa) —
  this is the single most useful interaction in the whole arena.
- Reference-team lineups show the frozen policy name per slot instead of an
  avatar, with a `FROZEN` tag.
- `Return squad to tank` is present after full time and navigates back to the
  aquarium with those fish selected.

---

## 7. Interaction & Transitions

| Interaction | Behaviour |
|---|---|
| Enter arena | From the tank: 350 ms transition — the tank view dims and pushes back, the arena rises. The tank stays *running* behind it. |
| Leave arena | `← Back to World 1A`, reverse transition, same 350 ms. Arena state is preserved; re-entering resumes, not restarts. |
| Switch view mode | 180 ms cross-fade of the rails only. Pitch never re-fits or jumps. Mode is persisted per user. |
| Select player | Click on pitch, or click a lineup row. Adds dashed ring + persistent label, opens the player card in the right rail. Escape or background click deselects. |
| Camera | Broadcast may gently ease the viewport toward the ball (max 15% of field span of pan, 1.0–1.15× zoom, critically damped, never snapping). Tactical and Analysis are fixed full-field. A `LOCK` toggle pins Broadcast to full-field for users who dislike motion. |
| Open drawer | 200 ms slide up over the pitch. Pitch canvas size unchanged. |
| Scrub history | In Analysis, the timeline is clickable; clicking an event seeks the replay if one is loaded (see [REPLAY.md](REPLAY.md)). Live matches cannot seek — the control is disabled with a tooltip, not hidden. |
| Reduced motion | `prefers-reduced-motion` disables camera easing, trails, ball spin, and card slide (cards cross-fade instead). All information remains available. |
| Keyboard | `B`/`T`/`A` switch modes, `Space` toggles pause, `L` toggles camera lock, `Esc` deselects then exits, arrow keys move selection through the lineup. |

---

## 8. States

Every state keeps the scoreboard in place. Only its content and the pitch layer
change.

| State | Pitch | Scoreboard | Rails / other |
|---|---|---|---|
| **Empty** (league off / no fixtures) | Static pitch, no players, 55% dim | `SOCCER LEAGUE · IDLE`, no score | Progress rail shows historical skill; CTA: `Enable Soccer League`. Explains what the arena is in one sentence. |
| **Loading** (match starting) | Pitch drawn, players fade in at formation positions | `WARMING UP`, clock `--:--` | Lineups populate progressively. Skeleton shimmer on rails, never a spinner over the pitch. |
| **Live** | Full render loop | `● LIVE` | All normal. |
| **Paused** (sim paused) | Last frame held, 18% dim, `❙❙` watermark centre | `❙❙ PAUSED` in warning colour | Rails stay interactive. Trails freeze, do not clear. |
| **Halftime** | 25% dim, attack labels cross-fading | `HALF TIME` | Half summary card; drawer auto-opens to Team Progress. |
| **Finished** | Players hold final positions, 30% dim | `FULL TIME` + final score | Result card; `Return squad to tank` and `Next fixture in N frames`. |
| **Disconnected** | Last frame, 40% dim, greyscale | `⚠ DISCONNECTED` danger, clock stops | Amber banner: `Reconnecting… last update 14s ago`. Nothing is cleared — stale data stays visible and is *labelled* stale. |
| **Skipped** (insufficient eligible fish) | Static pitch | `MATCH SKIPPED` | Plain-language reason: "World 1A could not field 3 eligible fish (needs 3, had 1)". Never the raw `skip_reason` enum. |
| **Error** | Static pitch | `ARENA ERROR` | ErrorBoundary card with retry. The arena must never take the app down. |

---

## 9. Component Implementation Map

New tree under `frontend/src/components/soccer/`. Existing components are
either absorbed or kept and re-parented — noted per row.

```
frontend/src/
  views/
    SoccerArenaView.tsx            NEW  route/view shell, owns view mode + selection
  components/soccer/
    ArenaHeader.tsx                NEW  back nav, title, view-mode segmented control
    Scoreboard/
      Scoreboard.tsx               NEW  §6.1
      TeamBlock.tsx                NEW  name, emblem, gen, possession bar
      MatchClock.tsx               NEW  frames → mm:ss + stage + status
    Pitch/
      PitchCanvas.tsx              NEW  sizing, DPR, rAF loop, layer orchestration
      usePitchTransform.ts         NEW  metres ↔ px, §6.2
      useMatchAnimator.ts          NEW  interpolates between websocket pushes
      layers/
        StaticFieldLayer.ts        NEW  offscreen: grass, stripes, markings, goals
        PlayersLayer.ts            NEW  wraps drawAvatar + team treatment §6.3
        BallLayer.ts               NEW  §6.4  (absorbs utils/drawSoccerBall.ts)
        EffectsLayer.ts            NEW  trails, pass lines, blooms, shockwaves
        LabelsLayer.ts             NEW  fading labels, badges, attack direction
    Events/
      EventPresenter.tsx           NEW  queue + rate limiting, §6.5 tiers
      GoalCard.tsx                 NEW
      BreakthroughCard.tsx         NEW
      EventToast.tsx               NEW  notable tier
      MatchTimeline.tsx            NEW  analysis mode scroll list
    Progress/
      TeamProgressPanel.tsx        NEW  §6.6 — absorbs SoccerSkillProgress.tsx
      ReferenceLadder.tsx          NEW
      FormChips.tsx                NEW
      TopPerformers.tsx            NEW  reuses MinigameLeaders data
    Standings/
      StandingsTable.tsx           NEW  replaces LeaderboardTable in SoccerLeagueLive
    Lineups/
      LineupPanel.tsx              NEW
      PlayerRow.tsx                NEW
      PlayerCard.tsx               NEW  selected-player detail
    History/
      MatchHistoryList.tsx         NEW  humanises SoccerLeagueEventsFiltered
  renderers/soccer/
    SoccerTopDownRenderer.ts       KEEP for the in-tank practice ball only;
                                   the arena uses the layer stack above
  hooks/
    useSoccerArenaState.ts         NEW  selects arena slice from the sim stream
    useSkillSnapshots.ts           NEW  extracted from SoccerSkillProgress
    useBreakthroughs.ts            NEW  diffing + once-only firing
  types/
    soccer.ts                      NEW  arena-specific types, §10
```

**Absorbed / retired:**

- `SoccerLeagueLive.tsx` → split into `Scoreboard` + `StandingsTable`; file retired.
- `SoccerPitch.tsx` → replaced by `PitchCanvas.tsx`; file retired.
- `SoccerSkillProgress.tsx` → the `SkillProgress` generic stays (poker uses it);
  the soccer wrapper moves into `TeamProgressPanel`.
- `TankSoccerTab.tsx` → becomes a thin **preview card** in the analyze panel
  grid: score, clock, mini pitch, and a `Open Arena →` button. The panel stops
  trying to be the whole experience.

**State ownership:** `SoccerArenaView` owns `viewMode`, `selectedPlayerId`,
`drawerTab`, and `cameraLocked`. Match data flows down from the existing
simulation websocket stream; the arena adds no new socket.

---

## 10. Data Contracts

Most of what the arena needs already exists. Additions are marked **NEW** and
must all be **optional** so the arena degrades gracefully against an older
backend.

```ts
interface SoccerMatchState {
  // existing
  match_id: string;
  frame: number;
  score: { left: number; right: number };
  game_over: boolean;
  winner_team: 'left' | 'right' | 'draw' | null;
  entities: EntityData[];
  field?: { length: number; width: number; goal_width: number; goal_depth: number };
  teams?: { left: number[]; right: number[] };
  home_id?: string; away_id?: string; home_name?: string; away_name?: string;
  league_round?: number;
  last_goal?: SoccerGoalEvent | null;

  // NEW — presentation
  play_mode?: 'before_kick_off' | 'kick_off' | 'play_on' | 'after_goal'
           | 'half_time' | 'time_over' | 'free_kick' | 'goal_kick' | 'corner_kick';
  half?: 1 | 2;
  period_frames?: number;          // frames per half, for clock + progress
  possession?: { left: number; right: number };   // rolling window, 0..1
  ball_owner_id?: number | null;   // last/current touch
  home_tank_id?: string; away_tank_id?: string;   // link back to aquarium
  home_color?: string;  away_color?: string;      // team colours, backend-assigned
  events?: SoccerMatchEvent[];     // append-only, presentation reads the tail
}

// NEW
interface SoccerMatchEvent {
  frame: number;
  seq: number;                     // monotonic; the presenter dedupes on this
  kind: 'kickoff' | 'goal' | 'shot' | 'save' | 'assist' | 'possession_change'
      | 'half_time' | 'full_time' | 'breakthrough';
  team?: 'left' | 'right';
  actor_id?: number;               // scorer / shooter / keeper
  assist_id?: number;
  detail?: Record<string, string | number>;
}

// NEW — per-player, rides on EntityData.render_hint (already exists as a bag)
interface SoccerRenderHint {
  team?: 'left' | 'right';
  jersey_number?: number;
  stamina?: number;                // 0..1
  facing_angle?: number;
  has_ball?: boolean;
  velocity_x?: number; velocity_y?: number;
  role?: 'GK' | 'D' | 'M' | 'F';   // NEW
  fish_id?: number;                // NEW — tank identity, distinct from entity id
  generation?: number;             // NEW
  parent_id?: number | null;       // NEW
}
```

**RCSS forward-compatibility rules** (§8 of the brief) — the design commits to
these so the later protocol work is a data-source swap, not a rewrite:

1. All positions are **metres, field-centred, +x right, +y down**. Already true.
2. Team sides are **left/right**, never home/away, in the render path. Home/away
   is a *label* resolved at the scoreboard, so a half swap is a label change
   plus an attack-direction flip, nothing more.
3. Uniform numbers are **1–11** and are the render key for a player slot.
   `jersey_number` must be stable for a whole match.
4. Player count is **data-driven**. No component may hard-code 3 or 6. Layout
   (lineup rail, badges, label thresholds) must be tested at 3, 6, and 11.
5. `play_mode` uses RCSS mode names verbatim. Unknown modes render as `play_on`
   rather than breaking.
6. Body orientation (`facing_angle`) and neck/view angle are separate concepts;
   the hint reserves `facing_angle` for body. If we later add view angle, it is
   a new field, not a redefinition.
7. Field dimensions always come from the payload. A default of 105×68 (RCSS
   full size) replaces today's 100×60 fallback.
8. Stamina is normalised 0..1 on the wire, not RCSS's raw 8000-scale.

---

## 11. MVP vs Later

**MVP** — the 30-second success criteria are met:

- Dedicated full-size arena view, reachable from the tank and back.
- One-transform pitch with real RCSS-proportioned markings, gradient + stripes,
  bright goals, attack-direction labels.
- rAF render loop with interpolation between pushes.
- Fish rendered with genome avatars + team ring beneath + offset number badge.
- Ball with minimum size, contrast ring, halo, and trail.
- Broadcast scoreboard with names, score, clock, stage, status.
- Goal card (Major tier) with scorer avatar and assist.
- Team Progress rail: skill index, delta, highest rung beaten, next target,
  last-5 form.
- Standings and lineups in the drawer.
- Empty / loading / paused / finished / disconnected states.

**Later:**

- Tactical and Analysis view modes.
- Possession bar, pass networks, spacing/shape metrics, heat tint.
- Full breakthrough catalogue with persistence and aquarium notifications.
- Camera easing and camera lock.
- Replay scrubbing integration.
- 11v11 layout hardening and RCSS-client-driven matches.
- Match history humanisation beyond a basic list.

---

## 12. Staged Implementation Plan

Each PR is independently shippable, gated by
`python tools/pre_pr_gate.py`, and must not regress the existing panel.

### PR 1 — Arena shell and rendering foundation

*Goal: a real venue with a readable pitch.*

- `SoccerArenaView` + route/view-mode entry; `TankSoccerTab` reduced to a
  preview card with `Open Arena →`.
- `PitchCanvas` with correct sizing, DPR handling, resize observer, and a rAF
  loop.
- `usePitchTransform` — single metres→px transform; delete the 1088×612
  intermediate.
- `StaticFieldLayer` (offscreen; grass gradient, stripes, vignette,
  metre-accurate markings, bright goals) + `PlayersLayer` + `BallLayer` +
  `LabelsLayer` (attack direction only).
- Team treatment: ring beneath, offset badge. Ball: min size, contrast ring,
  halo.
- `Scoreboard` with team blocks, score, clock, stage, status.
- Empty / loading / paused / disconnected states.
- Tests: transform round-trip (`toField(toScreen(p)) ≈ p`) at 3 field sizes;
  marking geometry at 105×68 and at the small-sided size; scoreboard renders
  every status; canvas layer smoke test via the existing renderer test harness.

### PR 2 — Broadcast event presentation

*Goal: you can see what just happened.*

- `EventPresenter` with the three-tier queue and rate limiting.
- `GoalCard` (with live-rendered scorer avatar), `EventToast`, kickoff,
  halftime (including the visible attack-direction swap), full-time card.
- `EffectsLayer`: ball trail, shot line, scorer bloom, goal shockwave,
  possession ring.
- Backend: emit `SoccerMatchEvent` list with `seq`; add `play_mode`, `half`,
  `ball_owner_id`. All optional.
- Tests: presenter tier/queue/rate-limit logic; dedupe on `seq`; reduced-motion
  path; goal card content from a fixture event.

### PR 3 — Team progress and improvement

*Goal: you can see the tank getting better.*

- `TeamProgressPanel`, `ReferenceLadder`, `FormChips`, `TopPerformers`.
- `useSkillSnapshots` extracted; `useBreakthroughs` with once-only firing and
  persistence.
- `BreakthroughCard` wired into the Major tier.
- Standings gains the skill column and the frozen/tank distinction.
- Backend: persist breakthrough records; expose recent form and league position.
- Tests: skill vs league vs match number families never mixed; breakthrough
  fires once across reloads; ladder rendering with 0, partial, and all rungs
  beaten.

### PR 4 — Tactical mode

*Goal: you can see how they play, not just that they play.*

- Tactical layout, fixed full-field, compressed scoreboard.
- Player trails, pass lines, role glyphs, stamina arcs.
- Formation/spacing metrics rail; lineup ↔ pitch highlighting both ways.
- `LineupPanel` / `PlayerCard` with generation and lineage.
- Tests: mode switch preserves pitch size; trail buffer bounded; lineup
  selection sync.

### PR 5 — 11v11 and RCSS readiness

*Goal: nothing here has to be rebuilt for the real thing.*

- Player-count-driven layout hardening; render and layout tests at 11v11.
- Default field 105×68; `play_mode` handling for all RCSS modes with graceful
  unknown fallback.
- Left/right vs home/away separation enforced by a lint-level test.
- Analysis mode with metrics stack and match timeline.
- Fixture-driven RCSS-shaped match state (from `fake_server.py`) rendered end
  to end in a test.

**Sequencing note:** PRs 1–3 deliver the success criteria. PR 4 and PR 5 are
enhancement and future-proofing and may be reordered against other priorities.

---

## 13. Success Criteria

A viewer who has never seen Tank World, watching for 30 seconds, can state:

- [ ] Two teams from tanks are playing soccer.
- [ ] Which team is on which side, and which goal each attacks.
- [ ] The current score and how far into the match it is.
- [ ] Where the ball is, at every moment, without hunting for it.
- [ ] Who scored the last goal, and that they are a specific fish.
- [ ] Whether this tank's team is improving.

And a viewer who knows the project can additionally state:

- [ ] The players are the same evolving fish that live in the aquarium.
- [ ] Improvement is measured against frozen rulers, not against itself.
- [ ] This is an artificial-life experiment presented as a sport — not a sports
      game with fish skins.

---

## Related Documents

- [UI_SPEC.md](UI_SPEC.md) — colour tokens, typography, panel and glass rules
- [SKILL_PROGRESSION.md](SKILL_PROGRESSION.md) — the frozen-ladder evaluation
  that Team Progress renders
- [SOCCER_INTEGRATION_GUIDE.md](SOCCER_INTEGRATION_GUIDE.md) — soccer physics
  and observation integration (historical design guide)
- [soccer_training.md](soccer_training.md) — soccer training pipeline
- [EXPERIENCE_ROADMAP.md](EXPERIENCE_ROADMAP.md) — the wider "fun to watch"
  strategy this fits into
- [REPLAY.md](REPLAY.md) — deterministic replay, used by Analysis scrubbing
- [WORLDS.md](WORLDS.md) — world types and backends
- RoboCup Soccer Simulator: <https://github.com/rcsoccersim>
