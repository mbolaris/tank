/**
 * Entity status/effect overlays: poker outcome visuals, birth/death effects,
 * energy bars, shadows and glows. Extracted from utils/renderer.ts
 * (god-class ratchet harvest); behavior is unchanged.
 */

import type { EntityData } from '../types/simulation';

export function drawShadow(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number
) {
    ctx.save();
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = '#000000';
    ctx.beginPath();
    ctx.ellipse(x, y, width / 2, height / 2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

export function drawGlow(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    size: number,
    energy: number,
    maxEnergy: number = 100
) {
    const threshold = maxEnergy * 0.7;
    const range = maxEnergy - threshold;
    const intensity = Math.max(0, Math.min(1, (energy - threshold) / range));

    ctx.save();
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
    gradient.addColorStop(0, `rgba(100, 220, 255, ${0.15 * intensity})`);
    gradient.addColorStop(0.5, `rgba(80, 200, 240, ${0.08 * intensity})`);
    gradient.addColorStop(1, 'rgba(60, 180, 220, 0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, size, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

export function drawEnhancedEnergyBar(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    energy: number
) {
    const barHeight = 6;
    const barWidth = width;
    const padding = 1;

    // Background with border
    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    const radius = 2;
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, barHeight, radius);
    ctx.fill();
    ctx.stroke();

    // Energy bar with gradient
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

    const barFillWidth = (barWidth - padding * 2) * (energy / 100);

    if (barFillWidth > 0) {
        // Glow effect
        ctx.shadowColor = glowColor;
        ctx.shadowBlur = 8;

        // Gradient fill
        const gradient = ctx.createLinearGradient(x, y, x + barFillWidth, y);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        ctx.fillStyle = gradient;

        ctx.beginPath();
        ctx.roundRect(x + padding, y + padding, barFillWidth, barHeight - padding * 2, radius - 1);
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

/**
 * Poker outcome overlay. For a loss with a known winner, draws the animated
 * energy-flow arrow from loser to winner; for ties, a "TIE" bubble.
 * `pokerEffectStartTime` is the caller-owned map tracking when each entity's
 * one-time animation began (pruned by the Renderer alongside its other
 * per-entity caches).
 */
export function drawPokerStatus(
    ctx: CanvasRenderingContext2D,
    pokerEffectStartTime: Map<number, number>,
    entityId: number,
    x: number,
    y: number,
    state: { status: string; amount: number; target_id?: number; target_type?: string },
    allEntities?: EntityData[],
    entityX?: number,
    entityY?: number
) {
    // If we have a target ID and it's a loss, draw an arrow FROM Loser (entity) TO Winner (target)
    // This visualizes energy flowing from the loser to the winner
    if (state.target_id !== undefined && state.target_type !== undefined && allEntities && entityX !== undefined && entityY !== undefined) {

        // Only draw for 'lost' status (Loser draws the arrow pointing to Winner)
        // This ensures we handle multiple losers correctly (one arrow per loser)
        // and avoids double-drawing (since we ignore 'won' status)
        if (state.status === 'lost') {
            const target = allEntities.find(e => e.id === state.target_id && e.type === state.target_type);

            if (target) {
                // Calculate target center (Winner position)
                const targetX = target.x + target.width / 2;
                const targetY = target.y + target.height / 2;

                // Track when this poker effect started for one-time animation
                const now = Date.now();
                if (!pokerEffectStartTime.has(entityId)) {
                    pokerEffectStartTime.set(entityId, now);
                }
                const startTime = pokerEffectStartTime.get(entityId)!;
                const elapsed = now - startTime;
                const animationDuration = 1000; // 1 second animation

                // Calculate progress (0 to 1, clamped)
                const progress = Math.min(elapsed / animationDuration, 1);

                // If animation is complete, clear the tracking and don't render
                if (progress >= 1) {
                    // Animation complete - do NOT delete here.
                    // We wait for the backend to clear the state, handled by pruneEntityFacingCache
                    return;
                }


                // Check distance - if too far, stop rendering to prevent "stretching" artifact
                // Use 120px (1.5x max poker distance) as cutoff
                const dx = targetX - entityX;
                const dy = targetY - entityY;
                const distSq = dx * dx + dy * dy;
                if (distSq > 120 * 120) {
                    return;
                }

                // Arrow direction: Loser (entity) -> Winner (target)
                // Energy flows from the loser to the winner
                const startX = entityX!;  // Loser position (arrow origin)
                const startY = entityY!;
                const endX = targetX;     // Winner position (arrow destination)
                const endY = targetY;

                // Draw green energy arrow
                ctx.save();

                // Draw the main line (solid)
                ctx.beginPath();
                ctx.moveTo(startX, startY);
                ctx.lineTo(endX, endY);

                // Glow effect
                ctx.shadowColor = '#4ade80';
                ctx.shadowBlur = 10;
                ctx.strokeStyle = '#4ade80';
                ctx.lineWidth = 3;
                ctx.stroke();



                // Draw arrow head at Winner (end of arrow, where energy flows to)
                const angle = Math.atan2(endY - startY, endX - startX);
                const headLen = 15;

                ctx.setLineDash([]);
                ctx.fillStyle = '#4ade80';
                ctx.beginPath();
                ctx.moveTo(endX, endY);
                ctx.lineTo(
                    endX - headLen * Math.cos(angle - Math.PI / 6),
                    endY - headLen * Math.sin(angle - Math.PI / 6)
                );
                ctx.lineTo(
                    endX - headLen * Math.cos(angle + Math.PI / 6),
                    endY - headLen * Math.sin(angle + Math.PI / 6)
                );
                ctx.closePath();
                ctx.fill();

                // Red dot on loser (start of arrow, where energy is lost from)
                ctx.shadowBlur = 0;
                ctx.fillStyle = '#ff0000';
                ctx.beginPath();
                ctx.arc(startX, startY, 5, 0, Math.PI * 2);
                ctx.fill();

                // Draw energy amount moving along the line (one-time animation)
                const particleX = startX + (endX - startX) * progress;
                const particleY = startY + (endY - startY) * progress;

                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 14px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                // Show amount (e.g. "120")
                ctx.fillText(`${state.amount.toFixed(0)}`, particleX, particleY - 10);

                ctx.restore();

                // Return early as we've handled the visual
                return;
            }
        }
    }

    // For 'won' and 'lost', we have returned above if target exists.
    // If we represent a tie, show the bubble.
    if (state.status !== 'tie') {
        return;
    }

    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 20px Arial';

    // Draw background bubble for TIE
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.beginPath();
    const text = 'TIE';
    const bubbleWidth = 60;

    ctx.roundRect(x - bubbleWidth / 2, y - 15, bubbleWidth, 30, 15);
    ctx.fill();

    // Tie text
    ctx.fillStyle = '#fbbf24'; // Amber
    ctx.font = 'bold 18px Arial';
    ctx.fillText(text, x, y);

    ctx.restore();
}

export function drawBirthEffect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    timerRemaining: number
) {
    const maxDuration = 60; // Max frames (2 seconds at 30fps)
    const progress = 1 - (timerRemaining / maxDuration); // 0 to 1

    ctx.save();

    // === HEARTS === //
    // Float 3-5 hearts upward with fade out
    const heartCount = 4;
    for (let i = 0; i < heartCount; i++) {
        const heartProgress = Math.min(1, (progress * 1.5) - (i * 0.1)); // Stagger appearance
        if (heartProgress <= 0) continue;

        const heartX = x + (Math.sin((i + progress) * 2) * 15); // Wobble side to side
        const heartY = y - (heartProgress * 40) - (i * 8); // Float upward
        const heartSize = 8 + (i * 2);
        const alpha = (1 - heartProgress) * 0.9; // Fade out as they rise

        ctx.globalAlpha = alpha;
        ctx.fillStyle = '#ff69b4'; // Hot pink

        // Draw heart shape
        ctx.beginPath();
        const topCurveHeight = heartSize * 0.3;
        ctx.moveTo(heartX, heartY + topCurveHeight);
        // Left curve
        ctx.bezierCurveTo(
            heartX, heartY,
            heartX - heartSize / 2, heartY,
            heartX - heartSize / 2, heartY + topCurveHeight
        );
        ctx.bezierCurveTo(
            heartX - heartSize / 2, heartY + (heartSize + topCurveHeight) / 2,
            heartX, heartY + (heartSize + topCurveHeight) / 1.5,
            heartX, heartY + heartSize
        );
        // Right curve
        ctx.bezierCurveTo(
            heartX, heartY + (heartSize + topCurveHeight) / 1.5,
            heartX + heartSize / 2, heartY + (heartSize + topCurveHeight) / 2,
            heartX + heartSize / 2, heartY + topCurveHeight
        );
        ctx.bezierCurveTo(
            heartX + heartSize / 2, heartY,
            heartX, heartY,
            heartX, heartY + topCurveHeight
        );
        ctx.fill();
    }

    // === PARTICLE BURST === //
    // Explosion of colorful particles at the start
    if (progress < 0.6) { // Show particles only for first 60% of animation
        const particleCount = 12;
        const burstProgress = Math.min(1, progress / 0.6); // 0 to 1 over first 60%

        for (let i = 0; i < particleCount; i++) {
            const angle = (Math.PI * 2 * i) / particleCount;
            const distance = burstProgress * 35; // Expand outward
            const particleX = x + Math.cos(angle) * distance;
            const particleY = y + Math.sin(angle) * distance;
            const size = 4 * (1 - burstProgress); // Shrink as they expand
            const alpha = (1 - burstProgress) * 0.8; // Fade out

            // Use different colors for each particle
            const colors = ['#ff69b4', '#ffd700', '#87ceeb', '#98fb98', '#ff6b6b'];
            const particleColor = colors[i % colors.length];

            ctx.globalAlpha = alpha;
            ctx.fillStyle = particleColor;
            ctx.shadowColor = particleColor;
            ctx.shadowBlur = 5;
            ctx.beginPath();
            ctx.arc(particleX, particleY, size, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.shadowBlur = 0;
    }

    ctx.restore();
}

export function drawDeathEffect(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    cause: string
) {
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = 'bold 16px Arial';

    // Draw a semi-transparent background circle
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.beginPath();
    ctx.arc(x, y, 12, 0, Math.PI * 2);
    ctx.fill();

    // Draw icon based on death cause
    switch (cause) {
        case 'starvation':
            // Empty stomach icon (circle with line through)
            ctx.strokeStyle = '#ff6b6b';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(x, y, 6, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x - 4, y + 4);
            ctx.lineTo(x + 4, y - 4);
            ctx.stroke();
            break;

        case 'old_age':
            // Hourglass-like icon
            ctx.fillStyle = '#a0a0a0';
            ctx.beginPath();
            // Top triangle
            ctx.moveTo(x - 5, y - 6);
            ctx.lineTo(x + 5, y - 6);
            ctx.lineTo(x, y);
            ctx.closePath();
            ctx.fill();
            // Bottom triangle
            ctx.beginPath();
            ctx.moveTo(x - 5, y + 6);
            ctx.lineTo(x + 5, y + 6);
            ctx.lineTo(x, y);
            ctx.closePath();
            ctx.fill();
            break;

        case 'predation':
            // Claw marks icon
            ctx.strokeStyle = '#ff4444';
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            // Three diagonal claw marks
            ctx.beginPath();
            ctx.moveTo(x - 5, y - 5);
            ctx.lineTo(x - 1, y + 5);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y - 5);
            ctx.lineTo(x, y + 5);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x + 5, y - 5);
            ctx.lineTo(x + 1, y + 5);
            ctx.stroke();
            break;

        case 'migration':
            // Arrow icon (leaving)
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

        default:
            // Question mark for unknown
            ctx.fillStyle = '#888888';
            ctx.fillText('?', x, y);
            break;
    }

    ctx.restore();
}
