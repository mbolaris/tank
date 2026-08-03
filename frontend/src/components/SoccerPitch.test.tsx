import { describe, expect, it } from 'vitest';
import { calculatePitchViewport } from './pitchViewport';

describe('calculatePitchViewport', () => {
    it('keeps the display aspect ratio from the active field profile', () => {
        const viewport = calculatePitchViewport(900, { length: 100, width: 60 }, 800, 1);
        expect(viewport).toEqual({ width: 800, height: 480, dpr: 1 });
    });

    it('matches the backing store to DPR without changing CSS dimensions', () => {
        const dprOne = calculatePitchViewport(600, { length: 105, width: 68 }, 800, 1);
        const dprTwo = calculatePitchViewport(600, { length: 105, width: 68 }, 800, 2);
        expect(dprTwo.width).toBe(dprOne.width);
        expect(dprTwo.height).toBe(dprOne.height);
        expect(dprTwo.dpr).toBe(2);
        expect(dprTwo.width * dprTwo.dpr).toBe(dprOne.width * 2);
        expect(dprTwo.height * dprTwo.dpr).toBe(dprOne.height * 2);
    });
});
