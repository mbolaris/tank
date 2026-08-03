
import { describe, it, expect } from 'vitest';
import { SoccerTopDownRenderer } from './SoccerTopDownRenderer';

describe('SoccerTopDownRenderer', () => {
    it('should have correct id', () => {
        const renderer = new SoccerTopDownRenderer();
        expect(renderer.id).toBe('soccer-topdown');
    });

    it('should dispose without error', () => {
        const renderer = new SoccerTopDownRenderer();
        expect(() => renderer.dispose()).not.toThrow();
    });
});
