import { describe, expect, it } from 'vitest';
import { usePitchTransform } from './usePitchTransform';

describe('usePitchTransform', () => {
    it.each([
        { length: 105, width: 68 },
        { length: 100, width: 60 },
        { length: 91.44, width: 54.86 },
    ])('round-trips field coordinates for $length x $width metres', (geometry) => {
        const transform = usePitchTransform(geometry, { width: 1200, height: 760 }, 24);
        const fieldPoint = [geometry.length * 0.31, -geometry.width * 0.22] as const;
        const screenPoint = transform.toScreen(...fieldPoint);
        expect(transform.toField(...screenPoint)[0]).toBeCloseTo(fieldPoint[0]);
        expect(transform.toField(...screenPoint)[1]).toBeCloseTo(fieldPoint[1]);
    });

    it('uses one uniform scale and centers the field', () => {
        const transform = usePitchTransform({ length: 105, width: 68 }, { width: 1200, height: 760 }, 24);
        expect(transform.toScreen(0, 0)).toEqual([600, 380]);
        expect(transform.scale).toBeCloseTo((760 - 48) / 68);
        expect(transform.toScreen(105 / 2, 0)[0] - transform.toScreen(-105 / 2, 0)[0]).toBeCloseTo(105 * transform.scale);
    });
});
