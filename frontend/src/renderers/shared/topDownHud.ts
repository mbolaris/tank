/**
 * The HUD layer the top-down views draw above their entities: energy bars,
 * death cause badges, birth bursts, poker outcome arrows and the selection
 * ring. Previously duplicated verbatim between the tank and petri renderers.
 *
 * These are all screen-space overlays drawn in world coordinates — the caller
 * has already applied the world-to-canvas transform, so positions arrive as
 * world x/y.
 *
 * Distinct from `utils/renderer_effects.ts`, which is the *side* view's
 * chunkier take on the same ideas (6px bars, floating hearts); the two are
 * deliberately different visual languages, not an accidental duplicate.
 */

import { roundRectPath } from './canvasPrimitives';

/** Poker outcome as it arrives on the wire. */
export interface PokerEffectState {
    status: string;
    amount: number;
    target_id?: number;
    target_type?: string;
}

/** Slim, gradient-filled energy bar with a colour ramp from red to green. */
export function drawEnergyBar(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    energy: number
) {
    const barHeight = 4;
    const barWidth = width;
    const padding = 1;

    // Background with border
    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    const radius = 2;
    ctx.beginPath();
    roundRectPath(ctx, x, y, barWidth, barHeight, radius);
    ctx.fill();
    ctx.stroke();

    let colorStart: string, colorEnd: string, glowColor: string;
    if (energy < 30) {
        colorStart = '#ff6b6b';
        colorEnd = '#ef4444';
        glowColor = 'rgba(239, 68, 68, 0.5)';
    } else if (energy < 60) {
        colorStart = '#ffd93d';
        colorEnd = '#fbbf24';
        glowColor = 'rgba(251, 191, 36, 0.5)';
    } else {
        colorStart = '#6bffb8';
        colorEnd = '#4ade80';
        glowColor = 'rgba(74, 222, 128, 0.5)';
    }

    const barFillWidth = Math.max(0, (barWidth - padding * 2) * (energy / 100));

    if (barFillWidth > 0) {
        // Glow effect
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 4;

        // Gradient fill
        const gradient = ctx.createLinearGradient(x, y, x + barFillWidth, y);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        ctx.fillStyle = gradient;

        ctx.beginPath();
        roundRectPath(ctx, x + padding, y + padding, barFillWidth, barHeight - padding * 2, radius - 1);
        ctx.fill();

        // Highlight on top
        ctx.shadowBlur = 0;
        ctx.globalAlpha = 0.4;
        const highlightGradient = ctx.createLinearGradient(x, y, x, y + barHeight / 2);
        highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
        highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = highlightGradient;
        ctx.fillRect(x + padding, y + padding, barFillWidth, barHeight / 3);
    }

    ctx.restore();
}

/** Badge naming why an organism died, so mortality is readable while it happens. */
export function drawDeathIndicator(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    cause: string
) {
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Background circle
    ctx.fillStyle = 'rgba(0, 0, 0, 0.65)';
    ctx.beginPath();
    ctx.arc(x, y, 12, 0, Math.PI * 2);
    ctx.fill();

    switch (cause) {
        case 'starvation': {
            ctx.strokeStyle = '#60a5fa';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(x, y, 6, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x - 4, y + 4);
            ctx.lineTo(x + 4, y - 4);
            ctx.stroke();
            break;
        }
        case 'old_age': {
            ctx.fillStyle = '#a0a0a0';
            ctx.beginPath();
            ctx.moveTo(x - 5, y - 6);
            ctx.lineTo(x + 5, y - 6);
            ctx.lineTo(x, y);
            ctx.closePath();
            ctx.fill();
            ctx.beginPath();
            ctx.moveTo(x - 5, y + 6);
            ctx.lineTo(x + 5, y + 6);
            ctx.lineTo(x, y);
            ctx.closePath();
            ctx.fill();
            break;
        }
        case 'predation': {
            ctx.strokeStyle = '#ff4444';
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(x - 5, y - 5);
            ctx.lineTo(x - 1, y + 5);
            ctx.moveTo(x, y - 5);
            ctx.lineTo(x, y + 5);
            ctx.moveTo(x + 5, y - 5);
            ctx.lineTo(x + 1, y + 5);
            ctx.stroke();
            break;
        }
        case 'migration': {
            ctx.fillStyle = '#4da6ff';
            ctx.beginPath();
            ctx.moveTo(x + 6, y);
            ctx.lineTo(x - 2, y - 5);
            ctx.lineTo(x - 2, y - 2);
            ctx.lineTo(x - 6, y - 2);
            ctx.lineTo(x - 6, y + 2);
            ctx.lineTo(x - 2, y + 2);
            ctx.lineTo(x - 2, y + 5);
            ctx.closePath();
            ctx.fill();
            break;
        }
        default: {
            ctx.fillStyle = '#888888';
            ctx.font = 'bold 14px Arial';
            ctx.fillText('?', x, y);
        }
    }

    ctx.restore();
}

/** Short particle burst marking a birth. `timerRemaining` counts down from 60. */
export function drawBirthEffect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    timerRemaining: number
) {
    const maxDuration = 60;
    const progress = 1 - (timerRemaining / maxDuration);

    ctx.save();

    if (progress < 0.6) {
        const particleCount = 8;
        const burstProgress = Math.min(1, progress / 0.6);

        for (let i = 0; i < particleCount; i++) {
            const angle = (Math.PI * 2 * i) / particleCount;
            const distance = burstProgress * 25;
            const particleX = x + Math.cos(angle) * distance;
            const particleY = y + Math.sin(angle) * distance;
            const size = 3 * (1 - burstProgress);
            const alpha = (1 - burstProgress) * 0.8;

            const colors = ['#ff69b4', '#ffd700', '#87ceeb', '#98fb98'];
            ctx.globalAlpha = alpha;
            ctx.fillStyle = colors[i % colors.length];
            ctx.beginPath();
            ctx.arc(particleX, particleY, size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    ctx.restore();
}

/** The minimum an entity must expose to take part in the poker overlay. */
export interface PokerEffectEntity {
    id: number;
    x: number;
    y: number;
    radius: number;
    poker_effect_state?: PokerEffectState;
}

/**
 * Energy-flow arrow from the loser to the winner of a hand, or a "TIE" bubble.
 *
 * Only the loser draws, which is what keeps multi-loser pots to one arrow each
 * rather than double-drawing every pairing. Arrows longer than 120px are
 * dropped: that is past the maximum poker range, so a longer line means the
 * winner has already swum away and the arrow would read as a stray streak.
 */
export function drawPokerEffect(
    ctx: CanvasRenderingContext2D,
    entity: PokerEffectEntity,
    allEntities: readonly PokerEffectEntity[]
) {
    const state = entity.poker_effect_state;
    if (!state) return;

    if (state.status === 'lost' && state.target_id !== undefined) {
        const target = allEntities.find(e => e.id === state.target_id);
        if (!target) return;

        const dx = target.x - entity.x;
        const dy = target.y - entity.y;
        const distSq = dx * dx + dy * dy;
        if (distSq > 120 * 120) return;

        ctx.save();

        // Draw the main line (solid)
        ctx.beginPath();
        ctx.moveTo(entity.x, entity.y);
        ctx.lineTo(target.x, target.y);

        // Glow effect
        ctx.shadowColor = '#4ade80';
        ctx.shadowBlur = 10;
        ctx.strokeStyle = '#4ade80';
        ctx.lineWidth = 3;
        ctx.stroke();

        // Draw arrow head at Winner (end of arrow)
        const angle = Math.atan2(target.y - entity.y, target.x - entity.x);
        const headLen = 15;

        ctx.setLineDash([]);
        ctx.fillStyle = '#4ade80';
        ctx.beginPath();
        ctx.moveTo(target.x, target.y);
        ctx.lineTo(
            target.x - headLen * Math.cos(angle - Math.PI / 6),
            target.y - headLen * Math.sin(angle - Math.PI / 6)
        );
        ctx.lineTo(
            target.x - headLen * Math.cos(angle + Math.PI / 6),
            target.y - headLen * Math.sin(angle + Math.PI / 6)
        );
        ctx.closePath();
        ctx.fill();

        // Red dot on loser
        ctx.shadowBlur = 0;
        ctx.fillStyle = '#ff0000';
        ctx.beginPath();
        ctx.arc(entity.x, entity.y, 5, 0, Math.PI * 2);
        ctx.fill();

        // Energy amount label
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const midX = (entity.x + target.x) / 2;
        const midY = (entity.y + target.y) / 2;
        ctx.fillText(`${state.amount.toFixed(0)}`, midX, midY - 8);

        ctx.restore();
    } else if (state.status === 'tie') {
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.beginPath();
        roundRectPath(ctx, entity.x - 25, entity.y - entity.radius - 25, 50, 20, 10);
        ctx.fill();
        ctx.fillStyle = '#fbbf24';
        ctx.font = 'bold 12px Arial';
        ctx.fillText('TIE', entity.x, entity.y - entity.radius - 15);
        ctx.restore();
    }
}

/** Dashed ring around the entity the inspector is currently pinned to. */
export function drawSelectionRing(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    radius: number
) {
    ctx.save();
    ctx.strokeStyle = "#fff";
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.arc(x, y, radius + 4, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
}
