import { describe, expect, it } from 'vitest';
import type { SoccerMatchState } from '../types/simulation';
import { MatchAnimator, interpolateMatchState } from './useMatchAnimator';

function match(frame: number, x: number): SoccerMatchState {
    return {
        match_id: 'm1',
        game_over: false,
        winner_team: null,
        message: '',
        frame,
        score: { left: 0, right: 0 },
        entities: [{ id: 1, type: 'ball', x, y: 0, width: 1, height: 1, radius: 0.11 }],
    };
}

describe('MatchAnimator', () => {
    it('interpolates monotonically between pushed snapshots', () => {
        expect(interpolateMatchState(match(0, 0), match(10, 10), 0.5).entities[0].x).toBe(5);
        expect(interpolateMatchState(match(0, 0), match(10, 10), 0.25).entities[0].x).toBe(2.5);
    });

    it('clamps sampling at the newest frame', () => {
        const animator = new MatchAnimator();
        animator.push(match(0, 0), 100);
        animator.push(match(10, 10), 200);
        expect(animator.sample(150)?.entities[0].x).toBe(5);
        expect(animator.sample(500)?.entities[0].x).toBe(10);
        expect(animator.sample(50)?.entities[0].x).toBe(0);
    });

    it('bounds identity interpolation to matching entities', () => {
        const before = match(0, 0);
        const after = { ...match(10, 10), entities: [{ ...match(10, 10).entities[0], id: 2, x: 20 }] };
        expect(interpolateMatchState(before, after, 0.5).entities[0].x).toBe(20);
    });
});
