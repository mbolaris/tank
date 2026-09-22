/**
 * Which end of the tank a goal belongs to, and how much of its scoring zone to
 * show. Pure functions, kept out of the renderers so the side view and the
 * top-down view cannot drift into disagreeing about which end is which.
 *
 * The vocabulary needs care. `core/entities/goal_zone.py` builds tank goals
 * with `team="A"` / `team="B"` (see `core/worlds/tank/pack.py`), while
 * `EntityData.team` was declared `'left' | 'right'` - a vocabulary the backend
 * never sends. Every renderer comparison against `'left'` was therefore dead,
 * and both ends drew in the same palette. `render_hint.goal_id` is the one
 * field that states the side outright, so it is trusted first.
 */
export type GoalSide = 'left' | 'right';

export interface GoalPalette {
    /** Structural colour of the arch itself. */
    coral: string;
    /** Lit edge, and the colour of the polyps. */
    accent: string;
    /** Scoring-zone outline, shown only on reveal. */
    zone: string;
    /** Scoring-zone fill, shown only on reveal. */
    zoneFill: string;
}

export const GOAL_PALETTES: Record<GoalSide, GoalPalette> = {
    left: {
        coral: '#4fae86',
        accent: '#d7f7b6',
        zone: 'rgba(143, 231, 178, 0.9)',
        zoneFill: 'rgba(88, 196, 140, 0.10)',
    },
    right: {
        coral: '#5d93c9',
        accent: '#cfe9ff',
        zone: 'rgba(150, 199, 244, 0.9)',
        zoneFill: 'rgba(92, 148, 216, 0.10)',
    },
};

/**
 * Structural, because the two views hand in different shapes: the side view
 * passes a wire `EntityData` (which carries `render_hint`), while the top-down
 * view passes a `TankEntity` projected by `buildTankScene` (which does not).
 * Both carry `team`, so both resolve.
 */
export interface GoalLike {
    team?: string;
    render_hint?: Record<string, unknown>;
}

/**
 * Resolve which end a goal defends, tolerating every vocabulary in the tree.
 *
 * `goal_id` ("goal_left" / "goal_right") is authoritative because it names the
 * side directly. `team` is the A/B pairing the engine actually sends, and
 * 'left'/'right' are accepted so a future backend that switches vocabulary
 * does not silently fall back.
 */
export function goalSide(goal: GoalLike): GoalSide {
    const goalId = goal.render_hint?.goal_id;
    if (typeof goalId === 'string') {
        if (goalId.includes('right')) return 'right';
        if (goalId.includes('left')) return 'left';
    }
    const team = goal.team ?? (typeof goal.render_hint?.team === 'string' ? goal.render_hint.team : undefined);
    if (team === 'B' || team === 'right') return 'right';
    return 'left';
}

export function goalPalette(goal: GoalLike): GoalPalette {
    return GOAL_PALETTES[goalSide(goal)];
}

/**
 * Radius of the circle that actually scores, matching `GoalZone.check_goal`:
 * `distance <= self.radius + ball_radius`, measured between `pos` values.
 *
 * Note what this exposes. `Entity.pos` is the rect's top-left corner
 * (`core/entities/base.py` keeps `self.rect.topleft = self.pos`), even though
 * `GoalZone`'s own docstring calls it a centre. So the scoring circle is
 * centred on the goal's top-left corner, not on the middle of its 80x80 box.
 * Drawing the real circle makes that visible instead of implying a tidier
 * geometry than the simulation has. Moving it would change scoring and
 * invalidate every champion, so this only reports it.
 */
export function scoringRadius(goalRadius: number, ballWidth: number | undefined): number {
    return goalRadius + (ballWidth ?? 0) / 2;
}

export interface RevealInput {
    /** Build Mode reveals interaction geometry outright. */
    buildMode: boolean;
    /** Distance from the goal's scoring centre to the ball's, or null with no ball. */
    ballDistance: number | null;
    /** The scoring radius the reveal is drawn at. */
    scoringRadius: number;
}

/** How far out the approach fade begins, as a multiple of the scoring radius. */
export const REVEAL_RANGE_FACTOR = 3;

/**
 * Opacity for the scoring-zone overlay: 0 keeps the aquarium clean, 1 is the
 * full reveal. Build Mode pins it open; otherwise it fades in as the ball
 * approaches, so the zone appears exactly when it is about to matter.
 */
export function goalZoneRevealAlpha({ buildMode, ballDistance, scoringRadius }: RevealInput): number {
    if (buildMode) return 1;
    if (ballDistance === null || !Number.isFinite(ballDistance)) return 0;
    if (scoringRadius <= 0) return 0;
    const range = scoringRadius * REVEAL_RANGE_FACTOR;
    if (ballDistance >= range) return 0;
    // Inside the scoring radius the ball is about to score: hold at full.
    if (ballDistance <= scoringRadius) return 1;
    return (range - ballDistance) / (range - scoringRadius);
}
