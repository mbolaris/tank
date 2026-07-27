/**
 * Canvas primitives shared by the top-down renderers and the avatar renderer.
 *
 * Every function here existed in two or three near-identical private copies
 * across `renderers/tank/`, `renderers/petri/` and `renderers/avatar_renderer.ts`
 * before it was lifted; the point of one implementation is that improving a
 * primitive improves all three views at once.
 *
 * These are pure path/state helpers: they never read entity types, so they stay
 * usable from any renderer.
 */

import type { FishGenomeData } from '../../types/simulation';

export function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

/**
 * mulberry32. Seeded per entity so an organism keeps the same wobble, cilia and
 * speckle layout across frames without any per-entity state being stored.
 *
 * Draw order is part of the contract: callers consume the sequence in a fixed
 * order, so inserting a `rand()` call in the middle of a drawing routine
 * re-rolls every feature after it.
 */
export function seededRand(seed: number): () => number {
    let t = seed >>> 0;
    return () => {
        t += 0x6D2B79F5;
        let x = t;
        x = Math.imul(x ^ (x >>> 15), x | 1);
        x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
        return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
}

/** Stable hue for an entity with no genome (or no `color_hue`). */
export function idHueDegrees(entityId: number): number {
    return ((entityId * 2654435761) >>> 0) % 360;
}

/**
 * Hue in degrees from the genome's normalised `color_hue`, falling back to a
 * stable hash of the id. `color_hue` is the mate-choice signal, so it drives
 * body colour everywhere an organism is drawn.
 */
export function genomeHueDegrees(
    genome: FishGenomeData | null | undefined,
    entityId: number
): number {
    const hue = genome?.color_hue;
    if (typeof hue === 'number' && Number.isFinite(hue)) {
        return ((hue % 1) + 1) % 1 * 360;
    }
    return idHueDegrees(entityId);
}

/**
 * Heading to draw an organism at: its velocity when it is actually moving,
 * otherwise a stable pseudo-random resting angle so idle organisms don't all
 * point the same way.
 */
export function movementAngle(
    velX: number | undefined,
    velY: number | undefined,
    rand: () => number
): number {
    const vx = velX ?? 0;
    const vy = velY ?? 0;
    const magSq = vx * vx + vy * vy;
    if (magSq > 0.04) return Math.atan2(vy, vx);
    return (rand() * Math.PI * 2) - Math.PI;
}

/** `ctx.roundRect` with a square-corner fallback for older canvas backends. */
export function roundRectPath(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    radius: number
) {
    const ctxWithRoundRect = ctx as CanvasRenderingContext2D & {
        roundRect?: (x: number, y: number, w: number, h: number, r: number) => void;
    };
    if (ctxWithRoundRect.roundRect) {
        ctxWithRoundRect.roundRect(x, y, width, height, radius);
    } else {
        ctx.rect(x, y, width, height);
    }
}

/**
 * Closed organic outline of radius `r`, jittered by `wobble` (0-1) and smoothed
 * with quadratic segments. Consumes 18 values from `rand`.
 */
export function wobblyBlobPath(
    ctx: CanvasRenderingContext2D,
    r: number,
    rand: () => number,
    wobble: number
) {
    const steps = 18;
    const points: Array<{ x: number; y: number }> = [];

    for (let i = 0; i < steps; i++) {
        const a = (i / steps) * Math.PI * 2;
        const jitter = (rand() - 0.5) * 2 * wobble;
        const rr = r * (1 + jitter);
        points.push({ x: Math.cos(a) * rr, y: Math.sin(a) * rr });
    }

    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
        const p0 = points[i];
        const p1 = points[(i + 1) % points.length];
        const midX = (p0.x + p1.x) / 2;
        const midY = (p0.y + p1.y) / 2;
        if (i === 0) ctx.moveTo(midX, midY);
        else ctx.quadraticCurveTo(p0.x, p0.y, midX, midY);
    }
    ctx.closePath();
}

/** Rounded rectangle body whose elongation follows the genome's `body_aspect`. */
export function capsulePath(ctx: CanvasRenderingContext2D, r: number, aspect: number) {
    const rx = r * clamp(aspect, 0.7, 1.6);
    const ry = r * clamp(1 / aspect, 0.7, 1.6);
    const cap = Math.min(rx, ry);

    ctx.beginPath();
    ctx.moveTo(-rx + cap, -ry);
    ctx.lineTo(rx - cap, -ry);
    ctx.quadraticCurveTo(rx, -ry, rx, -ry + cap);
    ctx.lineTo(rx, ry - cap);
    ctx.quadraticCurveTo(rx, ry, rx - cap, ry);
    ctx.lineTo(-rx + cap, ry);
    ctx.quadraticCurveTo(-rx, ry, -rx, ry - cap);
    ctx.lineTo(-rx, -ry + cap);
    ctx.quadraticCurveTo(-rx, -ry, -rx + cap, -ry);
    ctx.closePath();
}

/** Deterministic debug colour for an entity kind with no assigned palette. */
export function hashColor(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
    return "#" + "00000".substring(0, 6 - c.length) + c;
}
