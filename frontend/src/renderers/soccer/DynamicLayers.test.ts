import { describe, expect, it, vi } from 'vitest';
import { DEFAULT_SOCCER_GEOMETRY } from './fieldGeometry';
import { drawDynamicSoccerLayers } from './DynamicLayers';
import type { SoccerScene } from './scene';
import type { SoccerMatchState } from '../../types/simulation';
import type { PitchTransform } from './usePitchTransform';

describe('drawDynamicSoccerLayers', () => {
    it('keeps the ball above players in draw-call order', () => {
        const order: string[] = [];
        const layers = {
            players: { draw: vi.fn(() => order.push('players')) },
            ball: { draw: vi.fn(() => order.push('ball')) },
            labels: { draw: vi.fn(() => order.push('labels')) },
        };
        const scene = {
            entities: [
                { type: 'ball', id: 2 },
                { type: 'player', id: 1 },
            ],
        } as SoccerScene;
        const state = { entities: [] } as unknown as SoccerMatchState;
        const transform = { scale: 10 } as PitchTransform;

        drawDynamicSoccerLayers(
            {} as CanvasRenderingContext2D,
            { dpr: 1 } as never,
            scene,
            state,
            DEFAULT_SOCCER_GEOMETRY,
            transform,
            layers,
        );

        expect(order).toEqual(['players', 'ball', 'labels']);
    });
});
