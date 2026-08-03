import { describe, expect, it } from 'vitest';
import { renderFromCanonical } from './renderFromCanonical';

describe('renderFromCanonical', () => {
    it('flips only the vertical axis for canonical coordinates', () => {
        expect(renderFromCanonical({ x: 12, y: 7 }, 'canonical')).toEqual({ x: 12, y: -7 });
    });

    it.each(['legacy_render', undefined, 'future_space'])('preserves compatibility coordinates for %s', (space) => {
        expect(renderFromCanonical({ x: 12, y: 7 }, space)).toEqual({ x: 12, y: 7 });
    });
});
