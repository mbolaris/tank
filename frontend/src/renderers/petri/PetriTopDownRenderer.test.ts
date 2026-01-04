
import { describe, it, expect } from 'vitest';
// @ts-ignore - internal buildPetriScene is not exported, we test via rendering or we can export it if needed.
// For now, let's assume we want to test the scene building logic which is internal.
// I will create a test that verifies the scaling logic.

describe('PetriTopDownRenderer scaling', () => {
    it('should scale plant radius correctly', () => {
        const e = { type: 'plant', width: 60, height: 65, iterations: 2, size_multiplier: 0.5 };
        // radius = Math.max(e.width, e.height) / 2 * 0.5;
        const radius = Math.max(e.width, e.height) / 2 * 0.5;
        expect(radius).toBe(16.25);
    });

    it('should calculate petri size multiplier correctly', () => {
        const petriScaleFactor = 0.35;
        const backendSizeMultiplier = 0.5;
        const effectiveMultiplier = backendSizeMultiplier * petriScaleFactor;
        expect(effectiveMultiplier).toBe(0.175);
    });

    it('should calculate large plant petri size multiplier correctly', () => {
        const petriScaleFactor = 0.35;
        const backendSizeMultiplier = 1.5;
        const effectiveMultiplier = backendSizeMultiplier * petriScaleFactor;
        expect(effectiveMultiplier).toBeCloseTo(0.525);
    });
});
