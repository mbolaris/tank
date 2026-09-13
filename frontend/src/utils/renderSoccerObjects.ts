import type { EntityData } from '../types/simulation';
import { drawSoccerBall } from './drawSoccerBall';
import {
    goalPalette,
    goalSide,
    goalZoneRevealAlpha,
    scoringRadius,
    type GoalPalette,
} from './goalZoneAppearance';

export function renderBall(ctx: CanvasRenderingContext2D, entity: EntityData) {
    const radius = entity.radius || (entity.width ? entity.width / 2 : 10);
    const rotation = entity.vel_x || entity.vel_y ? entity.x / radius : 0;
    drawSoccerBall(ctx, entity.x + radius, entity.y + radius, radius, rotation);
}

/**
 * A coral arch standing over the scoring point.
 *
 * This replaces a stroked arc captioned "GATE", which read as debug geometry
 * beside the styled reef, grotto and castle sprites. The arch is a world
 * object: two tapered coral columns rising from the sand, a span across the
 * top, and polyps along it, tinted by which end it defends. The scoring circle
 * is no longer drawn here at all - `drawGoalZoneReveal` shows it only in Build
 * Mode or as the ball closes in.
 *
 * Drawn centred on `entity.x, entity.y`, which is where the simulation measures
 * scoring from, so the arch marks the place a goal actually happens.
 */
export function renderGoalZone(ctx: CanvasRenderingContext2D, entity: EntityData) {
    const radius = entity.radius || 30;
    const palette = goalPalette(entity);
    // The arch opens towards the middle of the tank, so each end mirrors.
    const facing = goalSide(entity) === 'left' ? 1 : -1;

    ctx.save();
    ctx.translate(entity.x, entity.y);
    ctx.scale(facing, 1);
    drawCoralArch(ctx, radius, palette);
    ctx.restore();
}

function drawCoralArch(ctx: CanvasRenderingContext2D, radius: number, palette: GoalPalette) {
    const halfSpan = radius * 0.72;
    const top = -radius * 0.62;
    const base = radius * 0.92;
    const postWidth = Math.max(3, radius * 0.17);

    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    // Columns: wider at the sand, tapering as they rise.
    ctx.fillStyle = palette.coral;
    for (const side of [-1, 1]) {
        const x = side * halfSpan;
        ctx.beginPath();
        ctx.moveTo(x - postWidth * 0.9, base);
        ctx.quadraticCurveTo(x - postWidth * 0.5, radius * 0.1, x - postWidth * 0.42, top * 0.55);
        ctx.lineTo(x + postWidth * 0.42, top * 0.55);
        ctx.quadraticCurveTo(x + postWidth * 0.5, radius * 0.1, x + postWidth * 0.9, base);
        ctx.closePath();
        ctx.fill();
    }

    // The span, thick enough to read as structure rather than a stroke.
    ctx.strokeStyle = palette.coral;
    ctx.lineWidth = postWidth * 1.15;
    ctx.beginPath();
    ctx.moveTo(-halfSpan, top * 0.55);
    ctx.quadraticCurveTo(0, top - radius * 0.22, halfSpan, top * 0.55);
    ctx.stroke();

    // Lit edge along the inside of the span.
    ctx.strokeStyle = palette.accent;
    ctx.lineWidth = Math.max(1, postWidth * 0.3);
    ctx.globalAlpha = 0.75;
    ctx.beginPath();
    ctx.moveTo(-halfSpan * 0.92, top * 0.5);
    ctx.quadraticCurveTo(0, top - radius * 0.1, halfSpan * 0.92, top * 0.5);
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Polyps: fixed positions, so the arch does not shimmer frame to frame.
    ctx.fillStyle = palette.accent;
    ctx.shadowColor = palette.coral;
    ctx.shadowBlur = 8;
    const polypRadius = Math.max(1.6, radius * 0.075);
    const polyps: Array<[number, number]> = [
        [-halfSpan * 0.98, top * 0.22],
        [-halfSpan * 0.45, top - radius * 0.05],
        [halfSpan * 0.2, top - radius * 0.14],
        [halfSpan * 0.95, top * 0.3],
        [-halfSpan * 0.9, base - radius * 0.22],
        [halfSpan * 0.9, base - radius * 0.3],
    ];
    for (const [px, py] of polyps) {
        ctx.beginPath();
        ctx.arc(px, py, polypRadius, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.shadowBlur = 0;
}

/**
 * The scoring circle, shown only when it is worth showing.
 *
 * Kept separate from the arch because the ball's position and Build Mode are
 * known to the renderer that owns the frame, not to a single entity's sprite.
 */
export function drawGoalZoneReveal(
    ctx: CanvasRenderingContext2D,
    goal: EntityData,
    ball: EntityData | undefined,
    buildMode: boolean
) {
    const radius = scoringRadius(goal.radius || 30, ball?.width);
    const ballDistance = ball
        ? Math.hypot(ball.x - goal.x, ball.y - goal.y)
        : null;
    const alpha = goalZoneRevealAlpha({ buildMode, ballDistance, scoringRadius: radius });
    if (alpha <= 0) return;

    const palette = goalPalette(goal);
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(goal.x, goal.y);
    ctx.fillStyle = palette.zoneFill;
    ctx.strokeStyle = palette.zone;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
}
