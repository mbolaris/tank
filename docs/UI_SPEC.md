# Tank World UI Specification

> Canonical reference for the visual design system.
> All UI changes — whether by human or agent — should conform to this spec.
> To evolve the design, update this document first, then implement.

---

## 1. Design Principles

1. **Abyssal aquarium** — The UI evokes a deep-ocean observation station: dark
   backgrounds, luminous accents, translucent panels floating over a living
   simulation.
2. **Glass morphism** — Panels use semi-transparent backgrounds with backdrop
   blur, giving a layered depth-of-field effect.
3. **Dark-first** — The entire palette assumes a dark color scheme
   (`color-scheme: dark`). There is no light mode.
4. **Data density over decoration** — Prefer showing live data (stats, charts,
   leaderboards) over ornamental graphics. Every pixel should inform.
5. **Genetic expression** — Entity colors derive from genome data, making each
   organism visually distinct. The UI never assigns arbitrary colors to
   entities.
6. **Contrast for legibility** — Bright text/icons on dark surfaces. Canvas HUD
   elements use text shadows and dark backdrops so they remain readable
   regardless of what's behind them.
7. **Minimal motion** — Animations are functional (pulse to indicate liveness,
   float-up for events) rather than decorative. Transitions use ease curves,
   not bounce/spring.

---

## 2. Color System

### 2.1 Background Palette

| Token | Value | Usage |
|---|---|---|
| `--color-bg-deep` | `#020617` (Slate 950) | Page body, deepest layer |
| `--color-bg-surface` | `rgba(15, 23, 42, 0.6)` (Slate 900 / 60%) | Glass panels |
| `--color-bg-surface-hover` | `rgba(30, 41, 59, 0.7)` (Slate 800 / 70%) | Panel hover state |
| `--color-bg-card` / `--card-bg` | `#0f172a` | Opaque metric cards, dashboard panels |

Body background is a radial gradient:
```css
background: radial-gradient(circle at 50% 0%, #1e293b 0%, #020617 75%);
background-attachment: fixed;
```

### 2.2 Accent Colors

| Token | Value | Tailwind Equivalent | Usage |
|---|---|---|---|
| `--color-primary` | `#06b6d4` | Cyan 500 | Primary actions, active toggles, links |
| `--color-primary-glow` | `rgba(6, 182, 212, 0.5)` | — | Box-shadow glow for primary elements |
| `--color-secondary` | `#8b5cf6` | Violet 500 | Network view, poker theme |
| `--color-secondary-glow` | `rgba(139, 92, 246, 0.5)` | — | Box-shadow glow for secondary elements |

### 2.3 Semantic Colors

| Token | Value | Usage |
|---|---|---|
| `--color-success` | `#10b981` (Emerald 500) | Online status, positive changes, spawn actions |
| `--color-warning` | `#f59e0b` (Amber 500) | Offline status, caution states |
| `--color-danger` | `#ef4444` (Red 500) | Reset, destructive actions, errors |

### 2.4 Text Colors

| Token | Value | Usage |
|---|---|---|
| `--color-text-main` | `#f1f5f9` (Slate 100) | Primary text, values, headings |
| `--color-text-muted` | `#94a3b8` (Slate 400) | Secondary labels, descriptions |
| `--color-text-dim` | `#64748b` (Slate 500) | Tertiary text, section headers, metadata |

### 2.5 Theme Module Colors (theme.ts)

The `theme.ts` module defines a parallel set of constants used by inline-style
components. These should remain consistent with CSS variables:

| theme.ts key | Value | Equivalent CSS var |
|---|---|---|
| `colors.bgDark` / `bgDarker` | `#0f172a` | `--color-bg-card` |
| `colors.bgLight` | `#1e293b` | — (hover surface) |
| `colors.textPrimary` / `text` | `#e2e8f0` | `--color-text-main` |
| `colors.textSecondary` | `#94a3b8` | `--color-text-muted` |
| `colors.primary` | `#3b82f6` (Blue 500) | — |
| `colors.accent` | `#fbbf24` (Amber 400) | — |
| `colors.buttonPrimary` | `#3b82f6` | — |
| `colors.buttonSuccess` | `#10b981` | `--color-success` |
| `colors.buttonSecondary` | `#8b5cf6` | `--color-secondary` |
| `colors.buttonDanger` | `#ef4444` | `--color-danger` |

### 2.6 Color Usage Rules

- **Never use raw hex in new code** — always reference a CSS variable or
  theme.ts constant.
- **Accent glow**: When an element uses an accent color as background, add a
  matching `box-shadow: 0 0 15px <glow-token>` for the luminous effect.
- **Status dot**: A small circle (`8px`) with the relevant semantic color and a
  matching `box-shadow: 0 0 8px` glow when active.
- **Positive/negative deltas**: Green `#4ade80` for positive, Red `#f87171`
  for negative, Gray `#94a3b8` for neutral.

---

## 3. Typography

### 3.1 Font Families

| Token | Stack | Usage |
|---|---|---|
| `--font-main` | `'Inter', system-ui, -apple-system, sans-serif` | All UI text |
| `--font-mono` | `'JetBrains Mono', 'Fira Code', monospace` | Numeric values, frame counts, IDs, code |

### 3.2 Size Scale

| Token | Size | Usage |
|---|---|---|
| `--font-size-xs` | `11px` | Badges, HUD labels, metadata |
| `--font-size-sm` | `13px` | Stat rows, button text, body text |
| `--font-size-md` | `14px` | Mono values, standard body |
| `--font-size-lg` | `18px` | Section headings, metric values |
| `--font-size-xl` | `20px` | Panel titles |

### 3.3 Weight Conventions

| Weight | Usage |
|---|---|
| 400 | Body text (default) |
| 500 | Mono values, button text |
| 600 | Labels, headings, badges, section titles |
| 700 | Logo text, large metric values |

### 3.4 Label Style

Uppercase labels (used in HUD, stat badges, section headers) follow this
pattern:
```css
font-size: 11px;
font-weight: 600;
letter-spacing: 0.05em;
text-transform: uppercase;
color: var(--color-text-dim);
```

---

## 4. Spacing & Layout

### 4.1 Spacing Scale

| Token | Value |
|---|---|
| `--spacing-xs` | `4px` |
| `--spacing-sm` | `8px` |
| `--spacing-md` | `16px` |
| `--spacing-lg` | `24px` |

### 4.2 Border Radius Scale

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | `6px` | Buttons (inside panels), stat rows, badges |
| `--radius-md` | `12px` | Dashboard cards, toggle bars |
| `--radius-lg` | `24px` | Glass panels, modal containers |
| `--radius-full` | `9999px` | Pill buttons, HUD items, status dots |

### 4.3 Page Layout

```
┌─ NavBar (sticky, z-index: 50) ──────────────────────────┐
│  height: auto (padding 12px 24px)                        │
│  background: rgba(2,6,23,0.8) + backdrop-filter blur     │
│  border-bottom: 1px solid rgba(255,255,255,0.05)         │
└──────────────────────────────────────────────────────────┘
│
│  <main> centered column
│    max-width: 1400px
│    padding: 24px clamp(16px, 5vw, 48px)
│
│    ┌─ Control Bar ──────────────────────────────────────┐
│    │  max-width: 1140px, flex row, gap: 16px            │
│    └────────────────────────────────────────────────────┘
│    ┌─ Stats HUD Bar ───────────────────────────────────┐
│    │  max-width: 1140px, glass-panel                    │
│    └────────────────────────────────────────────────────┘
│    ┌─ Canvas Wrapper ──────────────────────────────────┐
│    │  max-width: 1200px, canvas: 1088×612              │
│    └────────────────────────────────────────────────────┘
│    ┌─ Panel Toggle Bar ────────────────────────────────┐
│    │  max-width: 1140px                                 │
│    └────────────────────────────────────────────────────┘
│    ┌─ Panel Grid ──────────────────────────────────────┐
│    │  max-width: 1140px, single-column, gap: 20px       │
│    └────────────────────────────────────────────────────┘
│
│  <footer>
│    padding: 24px, font-size: 12px
│    border-top: 1px solid rgba(255,255,255,0.05)
```

Content max-width is **1140px** for panels/controls, **1200px** for the canvas
wrapper, and **1400px** for the main container. All are horizontally centered
with `margin: 0 auto`.

### 4.4 Responsive Breakpoints

| Breakpoint | Behavior |
|---|---|
| `<= 768px` | Main padding reduces to 16px. HUD stacks vertically. |
| `<= 600px` | Panel toggle bar centers and wraps. Toggle label goes full-width. |
| `<= 1100px` | Panel grid collapses to single column (already default). |

---

## 5. Component Patterns

### 5.1 Glass Panel

The foundational surface component. Used for the control bar, stats bar, and
any floating container.

```css
background: var(--color-bg-surface);       /* rgba(15,23,42,0.6) */
backdrop-filter: var(--backdrop-blur);     /* blur(12px) */
border: var(--glass-border);               /* 1px solid rgba(148,163,184,0.1) */
border-top: var(--glass-shine);            /* 1px solid rgba(255,255,255,0.05) */
box-shadow: var(--glass-shadow);           /* 0 4px 30px rgba(0,0,0,0.1) */
border-radius: var(--radius-lg);           /* 24px */
```

### 5.2 Dashboard Card

Opaque card used inside panel grids (ecosystem stats, match results, metrics).

```css
background: var(--card-bg);                /* #0f172a */
border: 1px solid var(--card-border);      /* #334155 */
border-radius: var(--radius-md);           /* 12px */
padding: var(--spacing-md);               /* 16px */
```

### 5.3 Button

Pill-shaped, 7 variants. All share a base style:

```css
/* Base */
display: inline-flex;
align-items: center;
gap: 8px;
padding: 8px 16px;
border-radius: var(--radius-full);         /* pill */
font-weight: 600;
font-size: 13px;
font-family: var(--font-main);
border: 1px solid transparent;
cursor: pointer;
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
box-shadow: 0 2px 4px rgba(0,0,0,0.1);
```

**Hover**: `translateY(-1px)` + `brightness(1.1)`.
**Active**: `translateY(0)` + `brightness(0.95)`.
**Disabled**: `opacity: 0.5`, `grayscale(0.8)`, `cursor: not-allowed`.

| Variant | Background | Text | Border | Glow |
|---|---|---|---|---|
| `primary` | `rgba(6,182,212,0.15)` | `#22d3ee` | `rgba(6,182,212,0.3)` | cyan 15% |
| `secondary` | `rgba(148,163,184,0.1)` | `--color-text-muted` | `rgba(148,163,184,0.2)` | none |
| `success` | `rgba(16,185,129,0.15)` | `#34d399` | `rgba(16,185,129,0.3)` | emerald 15% |
| `danger` | `rgba(239,68,68,0.15)` | `#f87171` | `rgba(239,68,68,0.3)` | none |
| `special` | `rgba(245,158,11,0.15)` | `#fbbf24` | `rgba(245,158,11,0.3)` | none |
| `poker` | gradient violet→pink 20% | `#e879f9` | `rgba(139,92,246,0.4)` | violet 20% |
| `evaluate` | (same pattern as primary) | — | — | — |

### 5.4 Stat Row

Key-value display used inside panels:

```css
display: flex;
justify-content: space-between;
padding: 8px 12px;
font-size: 13px;
background: rgba(51,65,85,0.2);
border-radius: var(--radius-sm);           /* 6px */
border: 1px solid rgba(148,163,184,0.08);
```
- Label: `--color-text-muted`, 13px, regular weight.
- Value: `--color-text-main`, 13px, weight 600.

### 5.5 Collapsible Section

Used for grouping content within panels:

- Title: uppercase, 13px, weight 600, `--color-text-dim`, letter-spacing
  0.5px.
- Expand icon: `▼` (expanded) / `▶` (collapsed), 12px, left of title.
- Click target is the full title row. Cursor: pointer.
- Content appears/disappears without animation (conditional render).

### 5.6 Collapsible Panel

Used for top-level panel sections in the panel grid (Soccer, Poker, Ecosystem,
Genetics):

- Header: clickable bar, 14px weight 600, icon + label left, chevron `▼`
  right.
- Header background: `rgba(255,255,255,0.03)`, hover: `rgba(255,255,255,0.06)`.
- Border-bottom on header when open: `1px solid var(--card-border)`.
- Content padding: 16px.
- Container: dashboard card style (`--card-bg`, `--card-border`,
  `--radius-md`).

### 5.7 Panel Toggle Bar

Horizontal bar for showing/hiding panel sections:

```css
background: rgba(15, 23, 42, 0.6);
border-radius: 12px;
border: 1px solid rgba(51, 65, 85, 0.4);
padding: 8px 12px;
```

Toggle buttons:
- Default: `rgba(30,41,59,0.5)` bg, `#94a3b8` text, border
  `rgba(71,85,105,0.5)`, radius 8px.
- Active: `rgba(59,130,246,0.15)` bg, `#60a5fa` text, border
  `rgba(59,130,246,0.4)`.

### 5.8 Toast Notification

Fixed position bottom-right overlay:

```css
position: fixed;
bottom: 20px;
right: 20px;
padding: 16px 20px;
border-radius: 8px;
max-width: 400px;
font-weight: 500;
z-index: 1001;
box-shadow: 0 4px 12px rgba(0,0,0,0.3);
```

| Type | Background | Text | Border |
|---|---|---|---|
| success | `#166534` | `#bbf7d0` | `#22c55e` |
| error | `#7f1d1d` | `#fecaca` | `#ef4444` |

### 5.9 Badge

Compact status label:

```css
font-size: 10px;
font-weight: 600;
letter-spacing: 0.05em;
padding: 2px 8px;
border-radius: 4px;
text-transform: uppercase;
```

| Variant | Background | Text |
|---|---|---|
| purple | `rgba(139,92,246,0.2)` | `#a78bfa` |
| blue | `rgba(59,130,246,0.2)` | `#60a5fa` |

### 5.10 Metric Card

Used in the 5-column metrics grid:

```css
background: var(--card-bg);
border-radius: var(--spacing-sm);          /* 8px */
padding: 12px;
border: 1px solid var(--card-border);
text-align: center;
```
- Label: `--color-text-dim`, 11px, weight 600.
- Value: `--color-text-main`, 18px, weight 700.
- Subtext: `--color-text-dim`, 10px.

---

## 6. Navigation

### 6.1 NavBar

Sticky top bar with three zones:

| Zone | Content |
|---|---|
| Left | Logo icon (32px, gradient primary→secondary, 8px radius) + "Tank World" (18px, weight 700) |
| Center | View toggle (Tank / Network) + Tank navigator (prev/name/next) |
| Right | Status indicator or keyboard hint |

- Background: `rgba(2,6,23,0.8)` with `backdrop-filter: blur(12px)`.
- Height: auto, padding `12px 24px`.
- Border-bottom: `1px solid rgba(255,255,255,0.05)`.

### 6.2 View Toggle

Segmented control with two options (Tank, Network):

- Container: `rgba(2,6,23,0.4)`, pill shape, 4px padding, thin border.
- Active segment: filled with accent color (`--color-primary` for Tank,
  `--color-secondary` for Network), white text, glow shadow.
- Inactive segment: transparent, `--color-text-muted`.
- Each segment: 12px weight 600, with icon (14px) + label.

### 6.3 Tank Navigator

Appears only when multiple worlds exist:

- Container: same as view toggle (pill, dark bg, thin border).
- Prev/Next buttons: 28px circles, transparent, `--color-text-muted`.
  Hover: `rgba(255,255,255,0.1)` bg, `--color-text-main` color.
- Center: world name (12px weight 600) + index counter (10px,
  `--color-text-dim`).
- Keyboard: Left/Right arrow keys navigate.

---

## 7. Canvas & Rendering

### 7.1 Canvas Dimensions

- World size: **1088 x 612** pixels (16:9 aspect ratio).
- Canvas scales responsively within `.canvas-wrapper` (max-width 1200px).
- Border-radius on canvas element: 16px.
- Wrapper has a subtle glass border effect:
  ```css
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
  box-shadow: 0 0 0 1px rgba(255,255,255,0.05), 0 20px 50px -12px rgba(0,0,0,0.5);
  ```

### 7.2 Canvas Backgrounds

| Mode | Background |
|---|---|
| Tank side view | Rendered by TankRenderer (gradient ocean) |
| Tank top-down | `#1a1a2e` with `#2a2a3e` grid at 100px intervals |
| Petri dish | Rendered by PetriTopDownRenderer |
| Soccer | `#2d5016` base, `#2e9a30` field surface, white `#ffffff` markings |

### 7.3 Entity Visual Language

**Fish / Microbes:**
- Color derived from genome `color_hue` (0-360 HSL).
- Fallback: deterministic hash `((id * 2654435761) >>> 0) % 360`.
- Membrane: HSL(hue, 70%, 62%, 0.95) with gradient.
- Nucleus: HSL(hue+190, ...) as contrasting accent.
- Pattern overlay: HSL(hue+60, 70%, ...) at 0.25-0.60 opacity.

**Plants:**
- Fractal L-system rendering driven by `PlantGenomeData`.
- Fallback: `#27ae60` (green) circle.
- Subtle shadow ellipse at base.

**Crabs (Predators):**
- Hue 340 (magenta-red), hexagonal head, animated corona.
- Glowing red eyes: `rgba(255, 40, 80, 0.65-0.9)`.

**Food:**
- Sprite-based with animation frames (500ms interval).
- Types: algae, protein, energy, rare, nectar, live food.
- Glow: live food hue 130 (green), other food hue 55 (amber).

**Soccer Ball:**
- White `#ffffff` body with `#333333` center pentagon pattern.
- Shadow: `rgba(0,0,0,0.5)`, blur 10.
- Rotation driven by velocity.

**Goal Zones:**
- Team A (left): `rgba(255,100,100,0.3)` fill, `#ff4444` dashed border.
- Team B (right): `rgba(100,100,255,0.3)` fill, `#4444ff` dashed border.

### 7.4 HUD Overlays (Canvas)

Rendered when `showEffects` is true. Layer order (bottom to top):

1. Entity base rendering (fish, plants, crabs, castles, food, ball, goals)
2. Birth effects (8-particle radial burst, 60-frame duration)
3. Energy bars above fish (3-tier color: red < 30%, yellow 30-60%, green > 60%)
4. Death indicators (icon circle above entity, color-coded by cause)
5. Poker transfer arrows (green `#4ade80` lines with arrowheads)
6. Selection ring (white dashed circle, `[4,4]` pattern, radius + 4px)

### 7.5 Energy Bar Specification

```
width:  2 * entity.radius (clamped)
height: 4px
y:      entity.y - entity.radius - 8
```

| Threshold | Gradient | Glow |
|---|---|---|
| < 30% | `#ff6b6b → #ef4444` | `rgba(239,68,68,0.5)` |
| 30-60% | `#ffd93d → #fbbf24` | `rgba(251,191,36,0.5)` |
| > 60% | `#6bffb8 → #4ade80` | `rgba(74,222,128,0.5)` |

Background: `rgba(0,0,0,0.6)`. White highlight overlay at alpha 0.4.

### 7.6 Canvas Effect Text (Soccer)

Floating text popups above entities for game events:

| Event | Color | Font Size |
|---|---|---|
| Kick | `#00ff00` | 16px |
| Goal | `#ffdd00` | 24px |
| Progress | `#88ff88` | 16px |

Style: weight 900, black shadow (blur 4), thin black stroke (1.5px). Floats
upward over 60 frames, fades in last 15 frames.

---

## 8. Iconography

### 8.1 Icon System

All icons are SVG components in `frontend/src/components/ui/Icons.tsx`.

- Default size: **16px**.
- Color: `currentColor` (inherits from parent text color).
- Stroke-based icons: `strokeWidth="2"`, `strokeLinecap="round"`,
  `strokeLinejoin="round"`.
- Fill-based icons (Play, Pause, FastForward): `fill="currentColor"`.
- ViewBox: `0 0 24 24` (standard).

### 8.2 Available Icons

| Icon | Style | Usage |
|---|---|---|
| `FoodIcon` | stroke | Add food button |
| `FishIcon` | stroke + fill eye | Spawn fish, tank view toggle |
| `PlayIcon` | fill | Resume simulation |
| `PauseIcon` | fill | Pause simulation |
| `FastForwardIcon` | fill | Fast-forward toggle |
| `ResetIcon` | stroke | Reset simulation |
| `PlantIcon` | stroke | Plant energy control label |
| `ChartIcon` | stroke | Statistics sections |
| `WaveIcon` | stroke | Logo, water theme |
| `GlobeIcon` | stroke | Network view toggle |
| `EyeIcon` | stroke + fill | Show HUD |
| `EyeOffIcon` | stroke | Hide HUD |
| `ChevronLeftIcon` | stroke | Previous navigation |
| `ChevronRightIcon` | stroke | Next navigation |
| `SlotsIcon` | stroke + fill | Slots/game reference |
| `CardsIcon` | stroke | Poker/cards reference |

### 8.3 Icon Guidelines

- Use existing icons before creating new ones.
- New icons must follow the same pattern: `IconProps` interface
  (`size`, `className`, `style`), `currentColor`, 24x24 viewBox.
- Prefer stroke style for consistency. Use fill only for playback controls
  where solid shapes aid recognition.

---

## 9. Interaction Patterns

### 9.1 Hover States

- **Buttons**: `translateY(-1px)` lift + `brightness(1.1)`.
- **Toggle buttons**: background darkens, text brightens.
- **Nav buttons**: background `rgba(255,255,255,0.1)`, color to
  `--color-text-main`.
- **Collapsible headers**: color shift from `--color-text-dim` to
  `--color-text-muted`.

### 9.2 Click Interactions

- **Canvas entities**: Click to open transfer dialog. Selected entity gets
  white dashed ring overlay.
- **Panel toggles**: Toggle visibility of corresponding panel section.
  `aria-pressed` attribute tracks state.
- **Collapsible panels**: Toggle content visibility. No animation on
  expand/collapse (conditional render).

### 9.3 Keyboard Navigation

- **Left/Right arrows**: Navigate between tanks (when not in an input field).
- Focus management: Standard browser tab order.

### 9.4 Toast Notifications

- Appear at bottom-right on entity transfer completion.
- Auto-dismiss after 5 seconds.
- Color-coded: green for success, red for error.

---

## 10. Transitions & Animations

### 10.1 Timing Tokens

| Token | Value | Usage |
|---|---|---|
| `--transition-fast` | `0.15s ease` | Toggle states, hover |
| `--transition-normal` | `0.2s ease` | Buttons, panels |
| `--transition-smooth` | `0.3s cubic-bezier(0.4, 0, 0.2, 1)` | Layout shifts, canvas wrapper |

### 10.2 Keyframe Animations

| Name | Duration | Usage |
|---|---|---|
| `pulse` | 2s infinite | Status dot opacity (0.6 → 1 → 0.6) |
| `subtle-pulse` | — | Scale 1 → 1.02, opacity 1 → 0.9 |
| `glow-pulse` | — | Box-shadow 8px → 16px |
| `pulse-glow` | 2s infinite | Opacity 0.5 → 1, scale 1 → 1.05 |

### 10.3 Canvas Animations

- **Birth particles**: 60-frame burst, 8 radial particles (pink, gold, sky
  blue, green), alpha fade.
- **Death indicators**: Static icon, no animation.
- **Soccer event text**: 60-frame float-up with fade in last 15 frames.
- **Food sprites**: 500ms frame toggle between two animation frames.
- **Live food pulse**: `sin(time * 0.005) * 0.12 + 1` scale oscillation.

---

## 11. Scrollbar

Custom WebKit scrollbar:

```css
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: rgba(15,23,42,0.5); }
::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.2); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(148,163,184,0.4); }
```

---

## 12. Z-Index Layers

| Layer | z-index | Element |
|---|---|---|
| Base content | 0 | Panels, canvas, grid |
| NavBar | 50 | Sticky navigation |
| Tree overlay | 100 | Phylogenetic tree modal |
| Toast notifications | 1001 | Transfer success/error |

---

## 13. Shadows

| Token / Usage | Value |
|---|---|
| `--glass-shadow` | `0 4px 30px rgba(0,0,0,0.1)` |
| `shadows.card` (theme.ts) | `0 35px 55px rgba(2,6,23,0.65)` |
| `shadows.button` (theme.ts) | `0 10px 25px rgba(15,23,42,0.45)` |
| Canvas wrapper | `0 0 0 1px rgba(255,255,255,0.05), 0 20px 50px -12px rgba(0,0,0,0.5)` |
| Tree overlay content | `0 25px 50px -12px rgba(0,0,0,0.5)` |
| Button base | `0 2px 4px rgba(0,0,0,0.1)` |

---

## 14. Modal / Overlay Pattern

The phylogenetic tree overlay establishes the modal convention:

```css
position: fixed;
inset: 0;
background-color: rgba(2, 6, 23, 0.85);
z-index: 100;
backdrop-filter: blur(8px);
padding: 40px;
```

Content container:
```css
max-width: 1600px;
height: 100%;
background: var(--color-bg-deep);
border-radius: var(--radius-lg);
border: var(--glass-border);
padding: 24px;
box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
```

---

## 15. File Organization

| Path | Purpose |
|---|---|
| `frontend/src/index.css` | CSS variables, global styles, animations, scrollbar, utility classes |
| `frontend/src/App.css` | Layout, glass-panel utility, canvas wrapper, HUD, footer, overlays |
| `frontend/src/styles/theme.ts` | JS constants for inline styles (colors, shadows, commonStyles) |
| `frontend/src/components/ui/` | Reusable primitives (Button, Panel, StatRow, CollapsibleSection, Icons) |
| `frontend/src/components/*.module.css` | Component-scoped styles (CSS Modules) |
| `frontend/src/renderers/` | Canvas rendering engines (TankSide, TankTopDown, Petri, Soccer) |

### 15.1 Styling Conventions

- **New components**: Use CSS Modules (`.module.css`) for component-scoped
  styles.
- **Shared layout patterns**: Use `.glass-panel` and other utility classes from
  `App.css`.
- **Inline styles**: Acceptable for one-off layout (flex, gap, padding) but
  colors and typography must reference tokens.
- **CSS variables over theme.ts**: Prefer CSS variables in new code. The
  `theme.ts` module exists for legacy inline-style components.

---

## 16. Conformance Checklist

When adding or modifying UI, verify:

- [ ] Colors reference CSS variables or theme.ts constants (no raw hex)
- [ ] Text uses `--font-main` or `--font-mono` (no other font families)
- [ ] Font sizes use the defined scale (xs/sm/md/lg/xl)
- [ ] Spacing uses the 4/8/16/24 scale
- [ ] Border radius uses the defined tokens (sm/md/lg/full)
- [ ] Panels use the glass-panel or dashboard-card pattern
- [ ] Buttons use the `<Button>` component with an appropriate variant
- [ ] Icons use existing icons from `Icons.tsx` or follow the icon guidelines
- [ ] Hover/active states follow the established patterns
- [ ] New CSS uses CSS Modules (not global classes)
- [ ] Transitions use the defined timing tokens
- [ ] Canvas overlays respect the layer ordering
- [ ] z-index values stay within the defined layer system
