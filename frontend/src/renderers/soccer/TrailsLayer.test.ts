import { describe, expect, it, vi } from 'vitest';
import { TRAIL_CAPACITY, TrailsLayer, trailKey } from './TrailsLayer';
import type { SoccerRenderEntity } from './scene';
import type { PitchTransform } from './usePitchTransform';

function player(participantId: string, x: number, side: 'left' | 'right' = 'left'): SoccerRenderEntity {
    return {
        id: Number(participantId.split('_')[1] ?? 1),
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

const transform = { toScreen: (x: number, y: number) => [x, y], scale: 1 } as unknown as PitchTransform;

function context(): CanvasRenderingContext2D {
    return {
        save: vi.fn(),
        restore: vi.fn(),
        beginPath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        stroke: vi.fn(),
    } as unknown as CanvasRenderingContext2D;
}

describe('TrailsLayer', () => {
    it('bounds the buffer at the trail capacity however long the match runs', () => {
        const layer = new TrailsLayer();
        for (let frame = 0; frame < TRAIL_CAPACITY * 4; frame += 1) {
            layer.record([player('left_1', frame)], frame, 'match-1');
        }
        expect(layer.samplesFor(trailKey(player('left_1', 0)))).toHaveLength(TRAIL_CAPACITY);
    });

    it('samples a match frame once however many times the rAF loop redraws it', () => {
        const layer = new TrailsLayer();
        for (let tick = 0; tick < 10; tick += 1) layer.record([player('left_1', tick)], 7, 'match-1');
        expect(layer.samplesFor(trailKey(player('left_1', 0)))).toHaveLength(1);
    });

    it('drops a player who leaves the pitch instead of leaking an entry per match', () => {
        const layer = new TrailsLayer();
        layer.record([player('left_1', 0), player('left_2', 1)], 0, 'match-1');
        expect(layer.size).toBe(2);
        layer.record([player('left_1', 2)], 1, 'match-1');
        expect(layer.size).toBe(1);
        expect(layer.samplesFor(trailKey(player('left_2', 0)))).toHaveLength(0);
    });

    it('starts clean on a new match rather than splicing two matches into one path', () => {
        const layer = new TrailsLayer();
        layer.record([player('left_1', 0)], 0, 'match-1');
        layer.record([player('left_1', 5)], 1, 'match-1');
        layer.record([player('left_1', 9)], 0, 'match-2');
        expect(layer.samplesFor(trailKey(player('left_1', 0)))).toHaveLength(1);
    });

    it('starts a new trail at half time rather than drawing a line across the pitch', () => {
        // `_handle_half_time` mirrors every position (x -> -x) while the frame
        // keeps counting and the match id holds, so neither the match nor the
        // rewind guard fires. Joining the two halves would draw a straight
        // ~60m line from each player's old position to their mirrored one.
        const layer = new TrailsLayer();
        layer.record([player('left_1', -45)], 598, 'match-1', false);
        layer.record([player('left_1', -44)], 599, 'match-1', false);
        expect(layer.samplesFor(trailKey(player('left_1', 0)))).toHaveLength(2);

        layer.record([player('left_1', 44)], 600, 'match-1', true);
        const samples = layer.samplesFor(trailKey(player('left_1', 0)));
        expect(samples).toHaveLength(1);
        expect(samples[0].x).toBe(44);
    });

    it('keeps accumulating while the swap state holds', () => {
        const layer = new TrailsLayer();
        layer.record([player('left_1', 10)], 601, 'match-1', true);
        layer.record([player('left_1', 11)], 602, 'match-1', true);
        expect(layer.samplesFor(trailKey(player('left_1', 0)))).toHaveLength(2);
    });

    it('discards history the sim has rewound past', () => {
        const layer = new TrailsLayer();
        layer.record([player('left_1', 0)], 10, 'match-1');
        layer.record([player('left_1', 1)], 11, 'match-1');
        layer.record([player('left_1', 2)], 3, 'match-1');
        expect(layer.samplesFor(trailKey(player('left_1', 0)))).toHaveLength(1);
    });

    it('keys on participant_id, and namespaces legacy entity ids so they cannot collide', () => {
        const withParticipant = player('left_1', 0);
        const legacy: SoccerRenderEntity = { ...withParticipant, participant: undefined };
        expect(trailKey(withParticipant)).toBe('participant:left_1');
        expect(trailKey(legacy)).toBe('entity:1');
    });

    it('draws nothing until there are two points to join', () => {
        const layer = new TrailsLayer();
        const ctx = context();
        layer.record([player('left_1', 0)], 0, 'match-1');
        layer.draw(ctx, [player('left_1', 0)], transform);
        expect(ctx.stroke).not.toHaveBeenCalled();

        layer.record([player('left_1', 4)], 1, 'match-1');
        layer.draw(ctx, [player('left_1', 4)], transform);
        expect(ctx.stroke).toHaveBeenCalled();
    });

    it('clears on demand', () => {
        const layer = new TrailsLayer();
        layer.record([player('left_1', 0)], 0, 'match-1');
        layer.clear();
        expect(layer.size).toBe(0);
    });
});
