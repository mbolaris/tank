import { describe, expect, it } from 'vitest';
import { PASS_LINE_HOLD_FRAMES, PASS_MAX_LOOSE_FRAMES, PassLinesLayer } from './PassLinesLayer';
import type { SoccerRenderEntity } from './scene';

function player(participantId: string, side: 'left' | 'right', x: number): SoccerRenderEntity {
    return {
        id: 1,
        type: 'player',
        x,
        y: 0,
        fieldX: x,
        fieldY: 0,
        radius: 10,
        vel_x: 0,
        vel_y: 0,
        fieldVelX: 0,
        fieldVelY: 0,
        speed: 0,
        team: side,
        participant: {
            participant_id: participantId,
            side,
            team_id: side,
            uniform_number: 1,
            avatar_kind: 'fish',
        },
    };
}

const squad = [
    player('left_1', 'left', -20),
    player('left_2', 'left', 10),
    player('right_1', 'right', 25),
];

describe('PassLinesLayer', () => {
    it('links a release and a reception across the loose phase', () => {
        // The real shape of a pass: the ball leaves the striker's kickable
        // radius long before it enters the receiver's.
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, null, 1, 'match-1');
        layer.observe(squad, 'left_2', 4, 'match-1');

        const passes = layer.activePasses(4);
        expect(passes).toHaveLength(1);
        expect(passes[0]).toMatchObject({ fromX: -20, toX: 10, side: 'left' });
    });

    it('records a close-range handover with no loose phase', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, 'left_2', 1, 'match-1');
        expect(layer.activePasses(1)).toHaveLength(1);
    });

    it('does not draw a turnover as a pass', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, null, 1, 'match-1');
        layer.observe(squad, 'right_1', 3, 'match-1');
        expect(layer.activePasses(3)).toHaveLength(0);
    });

    it('does not join two owners across a long stoppage', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, null, 1, 'match-1');
        layer.observe(squad, 'left_2', PASS_MAX_LOOSE_FRAMES + 5, 'match-1');
        expect(layer.activePasses(PASS_MAX_LOOSE_FRAMES + 5)).toHaveLength(0);
    });

    it('expires a pass line after the hold window', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, 'left_2', 1, 'match-1');
        expect(layer.activePasses(1 + PASS_LINE_HOLD_FRAMES)).toHaveLength(1);
        expect(layer.activePasses(2 + PASS_LINE_HOLD_FRAMES)).toHaveLength(0);
    });

    it('draws nothing at all for a payload that predates ball_owner', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, undefined, 0, 'match-1');
        layer.observe(squad, undefined, 1, 'match-1');
        expect(layer.activePasses(1)).toHaveLength(0);
    });

    it('ignores a repeated frame so the rAF loop cannot double-count', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, 'left_2', 1, 'match-1');
        layer.observe(squad, 'left_1', 1, 'match-1');
        expect(layer.activePasses(1)).toHaveLength(1);
    });

    it('forgets the previous match', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, 'left_2', 1, 'match-1');
        layer.observe(squad, 'left_1', 0, 'match-2');
        expect(layer.activePasses(0)).toHaveLength(0);
    });

    it('ignores an owner that is not on the pitch', () => {
        const layer = new PassLinesLayer();
        layer.observe(squad, 'left_1', 0, 'match-1');
        layer.observe(squad, 'ghost_9', 1, 'match-1');
        expect(layer.activePasses(1)).toHaveLength(0);
    });
});
