import { describe, it, expect } from 'vitest';
import {
    GOAL_PALETTES,
    REVEAL_RANGE_FACTOR,
    goalPalette,
    goalSide,
    goalZoneRevealAlpha,
    scoringRadius,
} from './goalZoneAppearance';

describe('goalSide', () => {
    it('resolves the A/B pairing the engine actually sends', () => {
        // The regression this module exists for: core/worlds/tank/pack.py builds
        // goals with team "A" and "B", so a renderer comparing against 'left'
        // matched neither and both ends drew in one palette.
        expect(goalSide({ team: 'A' })).toBe('left');
        expect(goalSide({ team: 'B' })).toBe('right');
        expect(goalPalette({ team: 'A' })).not.toEqual(goalPalette({ team: 'B' }));
    });

    it('gives the two tank goals visibly different palettes', () => {
        const left = goalPalette({ team: 'A' });
        const right = goalPalette({ team: 'B' });
        expect(left.coral).not.toBe(right.coral);
        expect(left.accent).not.toBe(right.accent);
        expect(left.zone).not.toBe(right.zone);
    });

    it('prefers goal_id, which names the side outright', () => {
        expect(goalSide({ render_hint: { goal_id: 'goal_right' } })).toBe('right');
        expect(goalSide({ render_hint: { goal_id: 'goal_left' } })).toBe('left');
    });

    it('lets goal_id win over a team that disagrees', () => {
        // goal_id states the side; team states a pairing. If a future backend
        // swaps which team defends which end, the side must follow goal_id.
        expect(goalSide({ team: 'A', render_hint: { goal_id: 'goal_right' } })).toBe('right');
        expect(goalSide({ team: 'B', render_hint: { goal_id: 'goal_left' } })).toBe('left');
    });

    it('still accepts a left/right vocabulary', () => {
        expect(goalSide({ team: 'left' })).toBe('left');
        expect(goalSide({ team: 'right' })).toBe('right');
    });

    it('reads team out of render_hint when the top-level field is absent', () => {
        expect(goalSide({ render_hint: { team: 'B' } })).toBe('right');
    });

    it('falls back to left rather than throwing on an unknown shape', () => {
        expect(goalSide({})).toBe('left');
        expect(goalSide({ team: 'purple' })).toBe('left');
        expect(goalSide({ render_hint: { goal_id: 42 } })).toBe('left');
    });

    it('only ever answers with a palette it has', () => {
        for (const side of ['A', 'B', 'left', 'right', undefined] as const) {
            expect(Object.values(GOAL_PALETTES)).toContain(goalPalette({ team: side }));
        }
    });
});

describe('scoringRadius', () => {
    it('matches what GoalZone.check_goal compares against', () => {
        // check_goal: distance <= self.radius + ball_radius, with ball_radius
        // taken as ball.width / 2.
        expect(scoringRadius(40, 16)).toBe(48);
    });

    it('degrades to the goal radius when no ball is in the scene', () => {
        expect(scoringRadius(40, undefined)).toBe(40);
    });
});

describe('goalZoneRevealAlpha', () => {
    const radius = 40;

    it('stays fully hidden in the ordinary view with no ball', () => {
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: null, scoringRadius: radius })).toBe(0);
    });

    it('is pinned open in Build Mode even with no ball', () => {
        expect(goalZoneRevealAlpha({ buildMode: true, ballDistance: null, scoringRadius: radius })).toBe(1);
    });

    it('hides a zone the ball is nowhere near', () => {
        const farOff = radius * REVEAL_RANGE_FACTOR + 1;
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: farOff, scoringRadius: radius })).toBe(0);
    });

    it('holds at full inside the radius that actually scores', () => {
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: radius, scoringRadius: radius })).toBe(1);
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: 0, scoringRadius: radius })).toBe(1);
    });

    it('fades in monotonically as the ball closes', () => {
        const range = radius * REVEAL_RANGE_FACTOR;
        const samples = [range, range * 0.9, range * 0.75, range * 0.6, radius * 1.2, radius]
            .map((distance) => goalZoneRevealAlpha({ buildMode: false, ballDistance: distance, scoringRadius: radius }));
        for (let i = 1; i < samples.length; i++) {
            expect(samples[i]).toBeGreaterThanOrEqual(samples[i - 1]);
        }
        expect(samples[0]).toBe(0);
        expect(samples[samples.length - 1]).toBe(1);
    });

    it('never leaves the 0..1 range', () => {
        for (const distance of [-5, 0, 10, 80, 119, 120, 500, Number.MAX_VALUE]) {
            const alpha = goalZoneRevealAlpha({ buildMode: false, ballDistance: distance, scoringRadius: radius });
            expect(alpha).toBeGreaterThanOrEqual(0);
            expect(alpha).toBeLessThanOrEqual(1);
        }
    });

    it('hides rather than dividing by zero on a degenerate radius', () => {
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: 0, scoringRadius: 0 })).toBe(0);
    });

    it('hides on a non-finite distance rather than drawing at NaN opacity', () => {
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: NaN, scoringRadius: radius })).toBe(0);
        expect(goalZoneRevealAlpha({ buildMode: false, ballDistance: Infinity, scoringRadius: radius })).toBe(0);
    });
});
