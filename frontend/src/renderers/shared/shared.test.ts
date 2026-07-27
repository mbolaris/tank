/**
 * Unit tests for the shared renderer primitives.
 *
 * The interesting assertions here are the structural invariants the shared
 * modules document but that nothing previously enforced: that an organism's
 * appearance is a pure function of its genome, and that the optional layers
 * (trait cues, substrate crystals) are strictly additive — they were written to
 * be appended so that turning them on cannot disturb the drawing underneath,
 * and that is the property that keeps the seeded RNG sequence stable.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';

import { createCanvasTrace } from '../testing/canvasTrace';
import {
    clamp,
    genomeHueDegrees,
    hashColor,
    idHueDegrees,
    movementAngle,
    seededRand,
} from './canvasPrimitives';
import { drawMicrobeAvatar, type MicrobeAvatarSpec } from './microbeAvatar';
import { drawMicrobeSubstrate } from './microbeScenery';
import { drawFoodSprite, foodImageName, TANK_FOOD_SPRITE } from './foodAvatar';
import { ImageLoader } from '../../utils/ImageLoader';
import type { FishGenomeData } from '../../types/simulation';

const genome: FishGenomeData = {
    speed: 1,
    size: 1,
    color_hue: 0.25,
    template_id: 1,
    fin_size: 1.1,
    tail_size: 0.9,
    body_aspect: 1.2,
    eye_size: 1,
    pattern_intensity: 0.5,
    pattern_type: 0,
    aggression: 0.6,
    hunting_stamina: 0.8,
    prediction_skill: 0.4,
    behavior: { food_approach: 1 },
};

function traceAvatar(spec: Partial<MicrobeAvatarSpec> = {}): string[] {
    const trace = createCanvasTrace();
    drawMicrobeAvatar(trace.ctx, {
        entityId: 42,
        radius: 14,
        velX: 1,
        velY: 0.5,
        genome,
        ...spec,
    });
    return trace.ops;
}

describe('seededRand', () => {
    it('replays the same sequence for the same seed', () => {
        const a = seededRand(1234);
        const b = seededRand(1234);
        const first = Array.from({ length: 8 }, a);
        const second = Array.from({ length: 8 }, b);
        expect(first).toEqual(second);
    });

    it('produces different sequences for different seeds', () => {
        const a = seededRand(1);
        const b = seededRand(2);
        expect(a()).not.toEqual(b());
    });

    it('stays within [0, 1)', () => {
        const rand = seededRand(0xdeadbeef);
        for (let i = 0; i < 500; i++) {
            const v = rand();
            expect(v).toBeGreaterThanOrEqual(0);
            expect(v).toBeLessThan(1);
        }
    });
});

describe('genomeHueDegrees', () => {
    it('maps a normalised hue onto degrees', () => {
        expect(genomeHueDegrees({ ...genome, color_hue: 0.5 }, 1)).toBe(180);
    });

    it('wraps hues outside [0, 1)', () => {
        expect(genomeHueDegrees({ ...genome, color_hue: 1.25 }, 1)).toBeCloseTo(90);
        expect(genomeHueDegrees({ ...genome, color_hue: -0.25 }, 1)).toBeCloseTo(270);
    });

    it('falls back to a stable id hash when the genome has no hue', () => {
        expect(genomeHueDegrees(undefined, 7)).toBe(idHueDegrees(7));
        expect(idHueDegrees(7)).toBe(idHueDegrees(7));
    });
});

describe('movementAngle', () => {
    it('follows velocity once the organism is actually moving', () => {
        const rand = seededRand(1);
        expect(movementAngle(1, 0, rand)).toBe(0);
        expect(movementAngle(0, 2, rand)).toBeCloseTo(Math.PI / 2);
    });

    it('falls back to a resting angle below the movement threshold', () => {
        // Same seed, same drift: a drifting organism must not jitter frame to frame.
        expect(movementAngle(0, 0, seededRand(9))).toBe(movementAngle(0, 0, seededRand(9)));
        expect(movementAngle(0, 0, seededRand(9))).toBeGreaterThanOrEqual(-Math.PI);
    });
});

describe('clamp and hashColor', () => {
    it('clamps to the given bounds', () => {
        expect(clamp(5, 0, 1)).toBe(1);
        expect(clamp(-5, 0, 1)).toBe(0);
        expect(clamp(0.5, 0, 1)).toBe(0.5);
    });

    it('produces a six-digit hex colour', () => {
        expect(hashColor('decorative_rock')).toMatch(/^#[0-9A-F]{6}$/);
        expect(hashColor('crab')).toBe(hashColor('crab'));
    });
});

describe('drawMicrobeAvatar', () => {
    it('draws the same organism twice for an unchanged genome', () => {
        expect(traceAvatar()).toEqual(traceAvatar());
    });

    it('redraws differently when a visual gene changes', () => {
        const recoloured = traceAvatar({ genome: { ...genome, color_hue: 0.9 } });
        expect(recoloured).not.toEqual(traceAvatar());
    });

    it('treats an unknown generation as generation zero', () => {
        // Portrait rendering omits generation; it must not shift the body colour.
        expect(traceAvatar({ generation: 0 })).toEqual(traceAvatar({ generation: undefined }));
    });

    it('shades older lineages more vividly', () => {
        expect(traceAvatar({ generation: 30 })).not.toEqual(traceAvatar({ generation: 0 }));
    });

    it('appends trait cues without disturbing the organism underneath', () => {
        const withoutCues = traceAvatar({ traitCues: false });
        const withCues = traceAvatar({ traitCues: true });

        // Both end with the matching restore(); everything before it must agree.
        const body = withoutCues.slice(0, -1);
        expect(withCues.slice(0, body.length)).toEqual(body);
        expect(withCues.length).toBeGreaterThan(withoutCues.length);
    });
});

describe('drawMicrobeSubstrate', () => {
    it('appends crystals without disturbing the substrate underneath', () => {
        const trace = (crystals: boolean) => {
            const t = createCanvasTrace();
            drawMicrobeSubstrate(t.ctx, { entityId: 15, radius: 40, crystals });
            return t.ops;
        };

        const plain = trace(false);
        expect(trace(true).slice(0, plain.length)).toEqual(plain);
        expect(trace(true).length).toBeGreaterThan(plain.length);
    });
});

describe('food sprites', () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('cycles animation frames on a fixed interval', () => {
        expect(foodImageName('protein', 0)).toBe('food_protein1.png');
        expect(foodImageName('protein', 500)).toBe('food_protein2.png');
        expect(foodImageName('protein', 1000)).toBe('food_protein1.png');
    });

    it('falls back to algae for an unknown food type', () => {
        expect(foodImageName('mystery_pellet', 0)).toBe('food_algae1.png');
        expect(foodImageName(undefined, 0)).toBe('food_algae1.png');
    });

    it('reports failure when the sprite has not been decoded yet', () => {
        vi.spyOn(ImageLoader, 'getCachedImage').mockReturnValue(null);
        const t = createCanvasTrace();

        const drawn = drawFoodSprite(t.ctx, {
            radius: 6,
            foodType: 'algae',
            isLive: false,
            nowMs: 0,
            style: TANK_FOOD_SPRITE,
        });

        // The caller needs this to fall back to a primitive rather than
        // silently dropping the entity from the frame.
        expect(drawn).toBe(false);
        expect(t.ops).toEqual([]);
    });
});
