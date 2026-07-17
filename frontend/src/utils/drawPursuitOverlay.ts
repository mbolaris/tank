/**
 * Shared utility for drawing a selected fish's Target Pursuit Module vectors:
 * the direct target vector (dashed) vs. the module's predicted aim (solid).
 */

import type { PursuitOverlayData } from '../rendering/types';

export function drawPursuitOverlay(
    ctx: CanvasRenderingContext2D,
    originX: number,
    originY: number,
    overlay: PursuitOverlayData
) {
    if (overlay.targetVector) {
        drawVectorArrow(ctx, originX, originY, overlay.targetVector[0], overlay.targetVector[1], 1, '#9aa0a6', [4, 4]);
    }
    if (overlay.aimVector) {
        // aimVector's magnitude is the module's "pursuit commitment" (typically
        // ~0-3), not a world distance - scale it up to a visible arrow length.
        const AIM_DISPLAY_SCALE = 50;
        drawVectorArrow(ctx, originX, originY, overlay.aimVector[0], overlay.aimVector[1], AIM_DISPLAY_SCALE, '#ffb300');
    }
}

/** One straight arrow from (fromX, fromY) toward (fromX + dx * scale, fromY + dy * scale). */
function drawVectorArrow(
    ctx: CanvasRenderingContext2D,
    fromX: number,
    fromY: number,
    dx: number,
    dy: number,
    scale: number,
    color: string,
    dash: number[] = []
) {
    if (Math.hypot(dx, dy) < 1e-6) return;
    const toX = fromX + dx * scale;
    const toY = fromY + dy * scale;
    const angle = Math.atan2(dy, dx);
    const headLength = 8;

    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2;
    ctx.setLineDash(dash);
    ctx.beginPath();
    ctx.moveTo(fromX, fromY);
    ctx.lineTo(toX, toY);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(toX - headLength * Math.cos(angle - Math.PI / 6), toY - headLength * Math.sin(angle - Math.PI / 6));
    ctx.lineTo(toX - headLength * Math.cos(angle + Math.PI / 6), toY - headLength * Math.sin(angle + Math.PI / 6));
    ctx.closePath();
    ctx.fill();
    ctx.restore();
}
