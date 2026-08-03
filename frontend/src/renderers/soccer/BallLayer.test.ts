import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BallLayer, MAX_BALL_TRAIL_POINTS } from './BallLayer';
import type { SoccerRenderEntity } from './scene';
import type { RenderContext } from '../../rendering/types';

const drawBall = vi.hoisted(() => vi.fn());
vi.mock('../../utils/drawSoccerBall', () => ({ drawSoccerBall: drawBall }));

function context(): CanvasRenderingContext2D {
    return {
        createRadialGradient: () => ({ addColorStop: vi.fn() }),
        beginPath: vi.fn(),
        arc: vi.fn(),
        fill: vi.fn(),
        stroke: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        setLineDash: vi.fn(),
    } as unknown as CanvasRenderingContext2D;
}

function ball(x: number, speed = 5): SoccerRenderEntity {
    return {
        id: 1,
        type: 'ball',
        x,
        y: 0,
        fieldX: x,
        fieldY: 0,
        radius: 20,
        vel_x: speed,
        vel_y: 0,
        fieldVelX: speed,
        fieldVelY: 0,
        speed,
    };
}

const rc = { dpr: 1 } as RenderContext;

describe('BallLayer', () => {
    beforeEach(() => drawBall.mockClear());

    it('keeps a bounded speed-gated trail', () => {
        const layer = new BallLayer();
        const ctx = context();
        for (let index = 0; index < 30; index += 1) layer.draw(ctx, ball(index), rc, 100);
        expect(layer.getTrailLength()).toBe(MAX_BALL_TRAIL_POINTS);
        expect(ctx.lineTo).toHaveBeenCalled();
    });

    it('clamps the ball to a readable minimum and true-scale maximum', () => {
        const layer = new BallLayer();
        const ctx = context();
        layer.draw(ctx, { ...ball(0), radius: 0.1 }, rc, 100);
        expect(drawBall).toHaveBeenLastCalledWith(ctx, 0, 0, 7, expect.any(Number));
        layer.draw(ctx, { ...ball(1), radius: 80 }, rc, 100);
        expect(drawBall).toHaveBeenLastCalledWith(ctx, 1, 0, 50, expect.any(Number));
    });
});
