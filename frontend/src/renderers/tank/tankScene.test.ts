
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

    it('should pass through generation and behavioral genome_data fields unchanged', () => {
        // docs/EVOLVABILITY.md sec 3.5 phenotype legibility: TankTopDownRenderer's
        // trait cues (aggression/prediction_skill/hunting_stamina/food_approach) read
        // these straight from genome_data, so the scene builder must not drop or
        // reshape them on the way from the raw snapshot to the TankEntity.
        const genome_data = {
            speed: 1, size: 1, color_hue: 0.5, template_id: 0, fin_size: 1, tail_size: 1,
            body_aspect: 1, eye_size: 1, pattern_intensity: 0.5, pattern_type: 0,
            aggression: 0.8, pursuit_aggression: 0.4, hunting_stamina: 0.6, prediction_skill: 0.3,
            behavior: { food_approach: 2 },
        };
        const snapshot = {
            entities: [
                { id: 1, type: 'fish', x: 0, y: 0, width: 20, height: 20, generation: 7, genome_data },
            ],
        };

        const scene = buildTankScene(snapshot);
        const fish = scene.entities.find(e => e.id === 1);

        expect(fish?.generation).toBe(7);
        expect(fish?.genome_data).toEqual(genome_data);
    });

    it('should default generation to undefined when the snapshot omits it', () => {
        const scene = buildTankScene({
            entities: [{ id: 1, type: 'fish', x: 0, y: 0, width: 20, height: 20 }],
        });
        expect(scene.entities.find(e => e.id === 1)?.generation).toBeUndefined();
    });
});
