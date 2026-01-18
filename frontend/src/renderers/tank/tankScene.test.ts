
import { describe, it, expect } from 'vitest';
import { buildTankScene } from './tankScene';

describe('buildTankScene', () => {
    it('should parse entities from snapshot', () => {
        const snapshot = {
            stats: { time: '100' },
            entities: [
                { id: 1, type: 'fish', x: 100, y: 100, width: 20, height: 10, vel_x: 10, vel_y: 0 },
                { id: 2, type: 'food', x: 200, y: 200, width: 5, height: 5 }
            ]
        };

        const scene = buildTankScene(snapshot);

        expect(scene.width).toBe(1088);
        expect(scene.time).toBe('100');
        expect(scene.entities).toHaveLength(2);

        const fish = scene.entities.find(e => e.id === 1);
        expect(fish).toBeDefined();
        expect(fish?.kind).toBe('fish');
        // buildTankScene converts from top-left to center: x + width/2, y + height/2
        expect(fish?.x).toBe(110); // 100 + 20/2
        expect(fish?.y).toBe(105); // 100 + 10/2
        expect(fish?.radius).toBe(10); // max(20, 10) / 2
        expect(fish?.headingRad).toBe(0); // atan2(0, 10)

        const food = scene.entities.find(e => e.id === 2);
        expect(food).toBeDefined();
        expect(food?.kind).toBe('food');
        expect(food?.x).toBe(202.5); // 200 + 5/2
        expect(food?.y).toBe(202.5); // 200 + 5/2
        expect(food?.radius).toBe(2.5); // max(5, 5) / 2
    });

    it('should handle empty snapshot', () => {
        const scene = buildTankScene({});
        expect(scene.entities).toHaveLength(0);
    });
});
