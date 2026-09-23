/**
 * The shadow + glow "halo" drawn under every normal (non-live) food item.
 *
 * Drawn directly, each food cost two save/restore pairs, a freshly allocated
 * radial gradient with two colour stops, two paths and two fills - every
 * frame, for ~40 food items - which made food as expensive to draw as all the
 * fish together (IMPROVEMENT_PROPOSALS 13.9). Food comes in a handful of fixed
 * sizes, so the halo is rendered once per (size, canvas scale) into a sprite
 * and stamped with a single drawImage. Source-over compositing is associative,
 * so shadow-then-glow composited into a sprite and drawn over the scene equals
 * drawing them onto the scene in turn, up to resampling at fractional
 * positions.
 */

import { drawShadow } from './renderer_effects';

/** Draw the halo the original way: shadow ellipse, then a radial glow. */
export function drawFoodHaloDirect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    scaledWidth: number,
    scaledHeight: number
): void {
    drawShadow(ctx, x + width / 2, y + height, scaledWidth * 0.6, scaledHeight * 0.2);

    ctx.save();
    ctx.globalAlpha = 0.2;
    const gradient = ctx.createRadialGradient(
        x + width / 2,
        y + height / 2,
        0,
        x + width / 2,
        y + height / 2,
        scaledWidth * 0.6
    );
    gradient.addColorStop(0, '#ffeb3b');
    gradient.addColorStop(1, 'rgba(255, 235, 59, 0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x + width / 2, y + height / 2, scaledWidth * 0.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

interface HaloSprite {
    canvas: HTMLCanvasElement;
    /** Sprite origin and size in world units, relative to the food's (x, y). */
    left: number;
    top: number;
    width: number;
    height: number;
}

// Keys are (food size, canvas scale); a handful are live at once. The bound
// only guards against a pathological stream of distinct sizes or resizes.
const MAX_SPRITES = 64;
const sprites = new Map<string, HaloSprite>();

function buildSprite(
    width: number,
    height: number,
    scaledWidth: number,
    scaledHeight: number,
    scaleX: number,
    scaleY: number
): HaloSprite | null {
    const glowRadius = scaledWidth * 0.6;
    const shadowRx = (scaledWidth * 0.6) / 2;
    const shadowRy = (scaledHeight * 0.2) / 2;
    const pad = 1; // world units, for antialiased edges
    const left = width / 2 - Math.max(glowRadius, shadowRx) - pad;
    const right = width / 2 + Math.max(glowRadius, shadowRx) + pad;
    const top = Math.min(height / 2 - glowRadius, height - shadowRy) - pad;
    const bottom = Math.max(height / 2 + glowRadius, height + shadowRy) + pad;

    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.ceil((right - left) * scaleX));
    canvas.height = Math.max(1, Math.ceil((bottom - top) * scaleY));
    const sctx = canvas.getContext('2d');
    if (!sctx) return null;
    sctx.scale(scaleX, scaleY);
    drawFoodHaloDirect(sctx, -left, -top, width, height, scaledWidth, scaledHeight);
    return {
        canvas,
        left,
        top,
        width: canvas.width / scaleX,
        height: canvas.height / scaleY,
    };
}

/** Draw the halo from a cached sprite, falling back to direct drawing. */
export function drawFoodHalo(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    scaledWidth: number,
    scaledHeight: number
): void {
    if (typeof document === 'undefined' || typeof ctx.getTransform !== 'function') {
        drawFoodHaloDirect(ctx, x, y, width, height, scaledWidth, scaledHeight);
        return;
    }
    const transform = ctx.getTransform();
    const scaleX = Math.hypot(transform.a, transform.b);
    const scaleY = Math.hypot(transform.c, transform.d);
    const key = `${width}|${height}|${scaledWidth}|${scaledHeight}|${scaleX.toFixed(4)}|${scaleY.toFixed(4)}`;
    let sprite = sprites.get(key);
    if (sprite === undefined) {
        const built = buildSprite(width, height, scaledWidth, scaledHeight, scaleX, scaleY);
        if (!built) {
            drawFoodHaloDirect(ctx, x, y, width, height, scaledWidth, scaledHeight);
            return;
        }
        if (sprites.size >= MAX_SPRITES) sprites.clear();
        sprites.set(key, built);
        sprite = built;
    }
    ctx.drawImage(sprite.canvas, x + sprite.left, y + sprite.top, sprite.width, sprite.height);
}

/** For tests and renderer disposal. */
export function clearFoodHaloSprites(): void {
    sprites.clear();
}
