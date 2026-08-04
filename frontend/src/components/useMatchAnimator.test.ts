import { describe, expect, it } from 'vitest';
import type { SoccerMatchState } from '../types/simulation';
import {
    DEFAULT_INTERPOLATION_DELAY_MS,
    MatchAnimator,
    interpolateMatchState,
    lerpAngle,
} from './useMatchAnimator';

function match(frame: number, x: number, options: Partial<SoccerMatchState> = {}): SoccerMatchState {
    return {
        match_id: 'm1',
        game_over: false,
        winner_team: null,
        message: '',
        frame,
        score: { left: 0, right: 0 },
        entities: [{ id: 1, type: 'ball', x, y: 0, width: 1, height: 1, radius: 0.11 }],
        ...options,
    };
}

function playerMatch(frame: number, x: number, facing: number): SoccerMatchState {
    return {
        ...match(frame, 0),
        frame,
        entities: [
            {
                id: 1,
                type: 'player',
                x,
                y: 0,
                width: 0.6,
                height: 0.6,
                radius: 0.3,
                facing,
                participant_id: 'left_1',
            } as SoccerMatchState['entities'][number],
        ],
    };
}

const DELAY = DEFAULT_INTERPOLATION_DELAY_MS;

describe('interpolateMatchState', () => {
    it('interpolates physical position only', () => {
        expect(interpolateMatchState(match(0, 0), match(10, 10), 0.5).entities[0].x).toBe(5);
        expect(interpolateMatchState(match(0, 0), match(10, 10), 0.25).entities[0].x).toBe(2.5);
    });

    it('takes identity, score and events from the newest snapshot', () => {
        const previous = match(0, 0, { score: { left: 0, right: 0 }, events: [] });
        const newest = match(10, 10, {
            score: { left: 1, right: 0 },
            events: [{ frame: 8, seq: 0, kind: 'goal', event_id: 'm1-goal-8-0' }],
            play_mode: 'kick_off_right',
            participants: [{ participant_id: 'left_1', side: 'left', team_id: 'L', uniform_number: 1, avatar_kind: 'fish' }],
        });
        const mid = interpolateMatchState(previous, newest, 0.5);
        expect(mid.score).toEqual({ left: 1, right: 0 });
        expect(mid.events).toHaveLength(1);
        expect(mid.play_mode).toBe('kick_off_right');
        expect(mid.participants).toHaveLength(1);
    });

    it('leaves entities without a counterpart at their true position', () => {
        const before = match(0, 0);
        const after = { ...match(10, 10), entities: [{ ...match(10, 10).entities[0], id: 2, x: 20 }] };
        expect(interpolateMatchState(before, after, 0.5).entities[0].x).toBe(20);
    });

    it('keeps entity count stable across additions and removals', () => {
        const before = { ...match(0, 0), entities: [match(0, 0).entities[0]] };
        const after = {
            ...match(10, 10),
            entities: [match(10, 10).entities[0], { ...match(10, 10).entities[0], id: 7, x: 30 }],
        };
        expect(interpolateMatchState(before, after, 0.5).entities).toHaveLength(2);
        expect(interpolateMatchState(after, before, 0.5).entities).toHaveLength(1);
    });
});

describe('lerpAngle', () => {
    it('takes the short arc across +pi', () => {
        // 170deg -> -170deg is +20deg the short way, not -340deg.
        const result = lerpAngle((170 * Math.PI) / 180, (-170 * Math.PI) / 180, 0.5);
        expect((result * 180) / Math.PI).toBeCloseTo(180, 6);
    });

    it('takes the short arc across -pi', () => {
        const result = lerpAngle((-170 * Math.PI) / 180, (170 * Math.PI) / 180, 0.5);
        expect((result * 180) / Math.PI).toBeCloseTo(-180, 6);
    });

    it('interpolates normally away from the wrap', () => {
        expect(lerpAngle(0, Math.PI / 2, 0.5)).toBeCloseTo(Math.PI / 4, 6);
    });
});

describe('MatchAnimator', () => {
    it('produces intermediate positions on a forward-moving clock', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);

        // renderTime = now - 100, so 210/240/280 render at 110/140/180.
        const at210 = animator.sample(210)!.entities[0].x;
        const at240 = animator.sample(240)!.entities[0].x;
        const at280 = animator.sample(280)!.entities[0].x;

        expect(at210).toBeCloseTo(1, 6);
        expect(at240).toBeCloseTo(4, 6);
        expect(at280).toBeCloseTo(8, 6);
        // Genuinely intermediate, not pinned to either endpoint.
        for (const value of [at210, at240, at280]) {
            expect(value).toBeGreaterThan(0);
            expect(value).toBeLessThan(10);
        }
    });

    it('never moves backward as the sample clock advances', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);

        let last = -Infinity;
        for (let now = 150; now <= 400; now += 5) {
            const x = animator.sample(now)!.entities[0].x;
            expect(x).toBeGreaterThanOrEqual(last);
            last = x;
        }
    });

    it('holds the newest snapshot instead of extrapolating past it', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);

        expect(animator.sample(300)!.entities[0].x).toBe(10);
        expect(animator.sample(5_000)!.entities[0].x).toBe(10);
    });

    it('holds the previous snapshot before the interval opens', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);
        expect(animator.sample(150)!.entities[0].x).toBe(0);
    });

    it('resets interpolation when the match changes', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);
        animator.push({ ...match(0, 99), match_id: 'm2' }, 300);

        // No stale bridge from the old match: the new one renders as-is.
        expect(animator.sample(310)!.entities[0].x).toBe(99);
        expect(animator.sample(400)!.match_id).toBe('m2');
    });

    it('resets when the frame moves backward', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(10, 10), 100);
        animator.push(match(20, 20), 200);
        animator.push(match(5, 5), 300);
        expect(animator.sample(350)!.entities[0].x).toBe(5);
    });

    it('ignores a redelivered frame', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);
        animator.push(match(10, 10), 250);
        expect(animator.sample(240)!.entities[0].x).toBeCloseTo(4, 6);
    });

    it('returns null until the first snapshot arrives, and after a reset', () => {
        const animator = new MatchAnimator(DELAY);
        expect(animator.sample(1_000)).toBeNull();
        animator.push(match(0, 0), 100);
        expect(animator.sample(200)).not.toBeNull();
        animator.reset();
        expect(animator.sample(300)).toBeNull();
    });

    it('interpolates facing along the short arc between snapshots', () => {
        const animator = new MatchAnimator(DELAY);
        animator.push(playerMatch(0, 0, (170 * Math.PI) / 180), 100);
        animator.push(playerMatch(10, 10, (-170 * Math.PI) / 180), 200);
        const facing = animator.sample(250)!.entities[0].facing!;
        expect(Math.abs((facing * 180) / Math.PI)).toBeGreaterThan(170);
    });
});
