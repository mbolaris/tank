/**
 * Food sprites for the top-down views. The image table was duplicated three
 * times (tank top-down, petri, `utils/renderer.ts` for the side view) and has
 * to stay in step with `core/constants.py`, which is exactly the kind of table
 * that should exist once.
 */

import { ImageLoader } from '../../utils/ImageLoader';
import { clamp } from './canvasPrimitives';

/** Frame pairs per food type; must match the food types the backend emits. */
export const FOOD_TYPE_IMAGES: Record<string, string[]> = {
    algae: ['food_algae1.png', 'food_algae2.png'],
    protein: ['food_protein1.png', 'food_protein2.png'],
    energy: ['food_energy1.png', 'food_energy2.png'],
    rare: ['food_rare1.png', 'food_rare2.png'],
    nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
    live: ['food_live1.png', 'food_live2.png'],
};

export const DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

const IMAGE_CHANGE_RATE = 500; // milliseconds per animation frame

export function animationFrame(nowMs: number, frameCount: number): number {
    if (frameCount <= 1) return 0;
    return Math.floor(nowMs / IMAGE_CHANGE_RATE) % frameCount;
}

/** Current animation frame's sprite filename for a food type. */
export function foodImageName(foodType: string | undefined, nowMs: number): string | null {
    const frames = (foodType && FOOD_TYPE_IMAGES[foodType])
        ? FOOD_TYPE_IMAGES[foodType]
        : DEFAULT_FOOD_IMAGES;
    return frames[animationFrame(nowMs, frames.length)] ?? null;
}

/**
 * Per-view sizing. The tank and petri views drifted to slightly different
 * numbers before this was shared; the constants keep each view looking the way
 * it does today rather than silently picking a winner.
 */
export interface FoodSpriteStyle {
    /** Floor applied to the entity radius before scaling. */
    minRadius: number;
    /** Upper clamp on the drawn sprite size, in world units. */
    maxSize: number;
    /** Glow radius as a multiple of the sprite size. */
    glowScale: number;
}

export const TANK_FOOD_SPRITE: FoodSpriteStyle = { minRadius: 0, maxSize: 28, glowScale: 0.95 };
export const PETRI_FOOD_SPRITE: FoodSpriteStyle = { minRadius: 4, maxSize: 26, glowScale: 0.9 };

export interface FoodSpriteSpec {
    radius: number;
    /** `undefined` falls back to the algae frames. Nectar passes `'nectar'`. */
    foodType?: string;
    /** Live food pulses and glows green; everything else is static and warm. */
    isLive: boolean;
    nowMs: number;
    style: FoodSpriteStyle;
}

/**
 * Draws the food sprite centred on the current origin.
 *
 * Returns `false` when the sprite has not been decoded yet, so the caller can
 * fall back to a primitive rather than dropping the entity from the frame.
 */
export function drawFoodSprite(ctx: CanvasRenderingContext2D, spec: FoodSpriteSpec): boolean {
    const imageName = foodImageName(spec.foodType, spec.nowMs);
    const image = imageName ? ImageLoader.getCachedImage(imageName) : null;
    if (!image) return false;

    const { style, isLive } = spec;
    const r = Math.max(spec.radius, style.minRadius);
    const baseScale = isLive ? 0.35 : 0.7;
    const pulse = isLive ? (Math.sin(spec.nowMs * 0.005) * 0.12 + 1) : 1;
    const size = clamp(r * 2 * baseScale * pulse, 6, style.maxSize);

    // Subtle glow so small food still reads against the background
    ctx.save();
    ctx.globalAlpha = isLive ? 0.22 : 0.16;
    const glowHue = isLive ? 130 : 55;
    const glowR = size * style.glowScale;
    const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, glowR);
    grad.addColorStop(0, `hsla(${glowHue}, 90%, 60%, 0.9)`);
    grad.addColorStop(1, `hsla(${glowHue}, 90%, 60%, 0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(0, 0, glowR, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    ctx.save();
    ctx.globalAlpha = 0.95;
    ctx.drawImage(image, -size / 2, -size / 2, size, size);
    ctx.restore();

    return true;
}
