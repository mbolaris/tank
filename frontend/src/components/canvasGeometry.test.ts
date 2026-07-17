import { describe, expect, it } from 'vitest';
import {
    fitWorldToContainer,
    getRenderDpr,
    screenPointToWorld,
    WORLD_HEIGHT,
    WORLD_WIDTH,
} from './canvasGeometry';

describe('canvas geometry', () => {
    it.each([
        [1088, 612, 1088, 612],
        [544, 306, 544, 306],
        [1600, 900, 1600, 900],
        [1200, 1000, 1200, 675],
        [500, 1000, 500, 281.25],
    ])('fits %sx%s into %sx%s', (containerWidth, containerHeight, expectedWidth, expectedHeight) => {
        const result = fitWorldToContainer(containerWidth, containerHeight);
        expect(result.cssWidth).toBeCloseTo(expectedWidth);
        expect(result.cssHeight).toBeCloseTo(expectedHeight);
    });

    it('caps high-DPI rendering at 2x', () => {
        expect(getRenderDpr(WORLD_WIDTH, WORLD_HEIGHT, 3)).toBe(2);
    });

    it('reduces DPR when the pixel budget would be exceeded', () => {
        const dpr = getRenderDpr(7000, 4000, 2);
        expect(dpr).toBeLessThan(2);
        expect(7000 * 4000 * dpr * dpr).toBeLessThanOrEqual(12_000_000);
    });

    it.each([
        [1, 1, WORLD_WIDTH / 2, WORLD_HEIGHT / 2],
        [2, 2, WORLD_WIDTH / 2, WORLD_HEIGHT / 2],
        [0.5, 0.5, WORLD_WIDTH / 2, WORLD_HEIGHT / 2],
    ])('maps the pointer center to the world center at scale %s', (scale, _unused, expectedX, expectedY) => {
        const point = screenPointToWorld(
            100 + (WORLD_WIDTH * scale) / 2,
            50 + (WORLD_HEIGHT * scale) / 2,
            { left: 100, top: 50, width: WORLD_WIDTH * scale, height: WORLD_HEIGHT * scale },
            WORLD_WIDTH * 2,
            WORLD_HEIGHT * 2,
        );
        expect(point.worldX).toBeCloseTo(expectedX);
        expect(point.worldY).toBeCloseTo(expectedY);
    });
});
