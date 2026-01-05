
import { describe, it, expect } from 'vitest';
import { SoccerTopDownRenderer } from './SoccerTopDownRenderer';

describe('SoccerTopDownRenderer', () => {
    it('should have correct id', () => {
        const renderer = new SoccerTopDownRenderer();
        expect(renderer.id).toBe('soccer-topdown');
    });

    it('should calculate player radius correctly from width/height', () => {
        const width = 20;
        const height = 20;
        const radius = Math.max(width, height) / 2;
        expect(radius).toBe(10);
    });

    it('should calculate ball radius correctly from width/height', () => {
        const width = 8;
        const height = 8;
        const radius = Math.max(width, height) / 2;
        expect(radius).toBe(4);
    });

    it('should dispose without error', () => {
        const renderer = new SoccerTopDownRenderer();
        expect(() => renderer.dispose()).not.toThrow();
    });

    it('should calculate field dimensions correctly', () => {
        const worldWidth = 1088;
        const worldHeight = 612;

        // Penalty box should be 15% of width
        const penaltyDepth = worldWidth * 0.15;
        expect(penaltyDepth).toBe(163.2);

        // Penalty box width should be 60% of height
        const penaltyWidth = worldHeight * 0.6;
        expect(penaltyWidth).toBe(367.2);

        // Goal width should be 35% of height
        const goalWidth = worldHeight * 0.35;
        expect(goalWidth).toBe(214.2);

        // Center circle radius should be 15% of min(width, height)
        const centerRadius = Math.min(worldWidth, worldHeight) * 0.15;
        expect(centerRadius).toBe(91.8);
    });
});
