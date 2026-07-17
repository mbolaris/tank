import { describe, expect, it } from 'vitest';

import { getFollowViewport } from './followViewport';

describe('getFollowViewport', () => {
    it('centres an in-bounds entity at the follow zoom level', () => {
        const viewport = getFollowViewport(
            { x: 534, y: 300, width: 20, height: 12 },
            1088,
            612
        );

        expect(viewport.sourceWidth).toBeCloseTo(1088 / 1.75);
        expect(viewport.sourceHeight).toBeCloseTo(612 / 1.75);
        expect(viewport.sourceX + viewport.sourceWidth / 2).toBeCloseTo(544);
        expect(viewport.sourceY + viewport.sourceHeight / 2).toBeCloseTo(306);
    });

    it('clamps the viewport at the world edge instead of showing empty space', () => {
        const viewport = getFollowViewport(
            { x: 0, y: 0, width: 20, height: 12 },
            1088,
            612
        );

        expect(viewport.sourceX).toBe(0);
        expect(viewport.sourceY).toBe(0);
    });
});
