/**
 * Live food (zooplankton): a pulsing translucent body, four swaying
 * appendages and a central highlight, under a soft shadow.
 *
 * Drawn directly, each item cost four save/restore pairs, a freshly allocated
 * three-stop radial gradient, two colour strings, four separately stroked
 * paths and three fills - every frame, for ~40% of the food in the default
 * config, which made plankton most of what `renderFood` still cost after the
 * normal-food halo became a sprite (IMPROVEMENT_PROPOSALS 13.9). The fast path
 * keeps the look and changes only how it is drawn:
 * - the body gradient is one sprite for every item: a radial gradient scaled
 *   by r is the unit gradient drawn at radius r, so a single high-resolution
 *   body is stamped at each item's size. (Live food sizes are continuous -
 *   they shrink as fish bite them - so per-size sprites would never be reused.)
 *   It is painted at full opacity and stamped at the pulse's alpha,
 * - the pulse is carried by globalAlpha, so the colours are constants,
 * - the four appendages share one path and one stroke,
 * - one save/restore pair for the whole item.
 */

import { drawShadow } from './renderer_effects';

const pulseAt = (elapsedTime: number) => Math.sin(elapsedTime * 0.005) * 0.3 + 0.7;

function paintBody(ctx: CanvasRenderingContext2D, cx: number, cy: number, radius: number): void {
    const bodyGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    bodyGlow.addColorStop(0, '#aaffaa');
    bodyGlow.addColorStop(0.6, '#6ad86a');
    bodyGlow.addColorStop(1, 'rgba(106, 216, 106, 0)');
    ctx.fillStyle = bodyGlow;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
}

/** Draw live food the original way; the reference the fast path is checked against. */
export function drawLiveFoodDirect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    scaledWidth: number,
    scaledHeight: number,
    elapsedTime: number
): void {
    drawShadow(ctx, x + width / 2, y + height, scaledWidth * 0.6, scaledHeight * 0.2);

    const pulse = pulseAt(elapsedTime);
    const cx = x + width / 2;
    const cy = y + height / 2;
    const planktonSeed = (x + y) * 0.01;

    ctx.save();
    ctx.globalAlpha = 0.4 * pulse;
    paintBody(ctx, cx, cy, scaledWidth * 0.8);
    ctx.restore();

    ctx.save();
    ctx.lineWidth = 0.8;
    ctx.strokeStyle = `rgba(140, 220, 140, ${0.35 * pulse})`;
    for (let i = 0; i < 4; i++) {
        const angle = (Math.PI * 2 * i) / 4 + pulse * 0.3;
        const sway = Math.sin(elapsedTime * 0.003 + planktonSeed + i) * 2;
        const length = scaledWidth * 0.5;
        const startX = cx + Math.cos(angle) * (scaledWidth * 0.3);
        const startY = cy + Math.sin(angle) * (scaledWidth * 0.3);
        const endX = cx + Math.cos(angle) * length + sway;
        const endY = cy + Math.sin(angle) * length + sway * 0.5;

        ctx.beginPath();
        ctx.moveTo(startX, startY);
        ctx.lineTo(endX, endY);
        ctx.stroke();
    }
    ctx.restore();

    ctx.save();
    ctx.fillStyle = `rgba(255, 255, 255, ${0.4 * pulse})`;
    ctx.beginPath();
    ctx.arc(cx, cy, scaledWidth * 0.15, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

// Big enough that stamping only ever scales down on screen (the largest live
// food is ~14 world units of body radius, ~42 px on a 3x display).
const BODY_SPRITE_RADIUS = 64;
let bodySprite: HTMLCanvasElement | null | undefined;

function getBodySprite(): HTMLCanvasElement | null {
    if (bodySprite === undefined) {
        bodySprite = null;
        if (typeof document !== 'undefined') {
            const canvas = document.createElement('canvas');
            canvas.width = canvas.height = BODY_SPRITE_RADIUS * 2;
            const sctx = canvas.getContext('2d');
            if (sctx) {
                paintBody(sctx, BODY_SPRITE_RADIUS, BODY_SPRITE_RADIUS, BODY_SPRITE_RADIUS);
                bodySprite = canvas;
            }
        }
    }
    return bodySprite;
}

/** Draw live food with the shared body sprite, falling back to direct drawing. */
export function drawLiveFood(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    scaledWidth: number,
    scaledHeight: number,
    elapsedTime: number
): void {
    const sprite = getBodySprite();
    if (sprite === null) {
        drawLiveFoodDirect(ctx, x, y, width, height, scaledWidth, scaledHeight, elapsedTime);
        return;
    }
    const pulse = pulseAt(elapsedTime);
    const cx = x + width / 2;
    const cy = y + height / 2;
    const bodyRadius = scaledWidth * 0.8;

    ctx.save();
    // Every alpha below was absolute in the direct drawing; scaling by the
    // context's own alpha is the same when renderFood runs at alpha 1.
    const baseAlpha = ctx.globalAlpha;

    // Shadow: drawShadow's ellipse, without its own save/restore.
    ctx.globalAlpha = baseAlpha * 0.15;
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.ellipse(cx, y + height, scaledWidth * 0.3, scaledHeight * 0.1, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalAlpha = baseAlpha * 0.4 * pulse;
    ctx.drawImage(sprite, cx - bodyRadius, cy - bodyRadius, bodyRadius * 2, bodyRadius * 2);

    // Four appendages, 90 degrees apart: rotate one unit vector instead of
    // four cos/sin pairs.
    const angle = pulse * 0.3;
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    const inner = scaledWidth * 0.3;
    const outer = scaledWidth * 0.5;
    const swayBase = elapsedTime * 0.003 + (x + y) * 0.01;
    ctx.globalAlpha = baseAlpha * 0.35 * pulse;
    ctx.lineWidth = 0.8;
    ctx.strokeStyle = 'rgb(140, 220, 140)';
    ctx.beginPath();
    for (let i = 0; i < 4; i++) {
        // (cos, sin) of angle + i * 90deg
        const dx = i === 0 ? c : i === 1 ? -s : i === 2 ? -c : s;
        const dy = i === 0 ? s : i === 1 ? c : i === 2 ? -s : -c;
        const sway = Math.sin(swayBase + i) * 2;
        ctx.moveTo(cx + dx * inner, cy + dy * inner);
        ctx.lineTo(cx + dx * outer + sway, cy + dy * outer + sway * 0.5);
    }
    ctx.stroke();

    ctx.globalAlpha = baseAlpha * 0.4 * pulse;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(cx, cy, scaledWidth * 0.15, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}
