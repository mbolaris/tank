import type { EntityData } from '../types/simulation';

export function renderResourcePatch(ctx: CanvasRenderingContext2D, patch: EntityData) {
    const ratio = Math.max(0, Math.min(1, Number(patch.render_hint?.stock_ratio ?? 0)));
    const kind = String(patch.render_hint?.kind ?? patch.food_type ?? 'algae');
    
    // Curated glowing neon palettes
    const baseColor = kind === 'protein' ? '#e29eff' : '#6effb6';
    const glowColor = kind === 'protein' ? 'rgba(226, 158, 255, 0.25)' : 'rgba(110, 255, 182, 0.25)';
    const barGradientStart = kind === 'protein' ? '#f3d5ff' : '#a8ffd3';
    const barGradientEnd = kind === 'protein' ? '#c46eff' : '#3be88b';
    
    const x = patch.x;
    const y = patch.y;
    const w = patch.width;
    const h = patch.height;
    const radius = 14;

    // Time-based pulse for bioluminescent hover/glow effect
    const pulse = Math.sin(Date.now() / 350) * 0.5 + 0.5; // 0.0 to 1.0

    ctx.save();

    // 1. Draw Outer Glow (Bioluminescent shadow)
    ctx.shadowColor = baseColor;
    ctx.shadowBlur = 10 + pulse * 6;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    // 2. Glassmorphism Background Fill
    ctx.fillStyle = kind === 'protein' 
        ? 'rgba(35, 15, 55, 0.45)' 
        : 'rgba(10, 38, 30, 0.45)';
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fill();

    // Reset shadow for inner elements
    ctx.shadowBlur = 0;

    // 3. Glowing Border
    ctx.globalAlpha = 0.6 + pulse * 0.25;
    ctx.strokeStyle = baseColor;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.stroke();

    // 4. Subtle Inner Highlight Rim
    ctx.globalAlpha = 0.08;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(x + 1, y + 1, w - 2, h - 2, radius - 1);
    ctx.stroke();

    // 5. Header Badge Background
    ctx.globalAlpha = 0.85;
    ctx.fillStyle = 'rgba(12, 16, 28, 0.85)';
    ctx.beginPath();
    ctx.roundRect(x + 8, y + 8, w - 16, 18, 6);
    ctx.fill();

    // 6. Badge Text & Dot Indicator
    // Small bioluminescent dot
    ctx.fillStyle = baseColor;
    ctx.beginPath();
    ctx.arc(x + 16, y + 17, 3, 0, Math.PI * 2);
    ctx.fill();

    // Label Typography
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 9px monospace';
    ctx.textBaseline = 'middle';
    ctx.fillText(
        kind.toUpperCase() + ' PATCH', 
        x + 24, 
        y + 17
    );

    // 7. Modern Stock Progress Bar
    const barX = x + 10;
    const barY = y + h - 16;
    const barW = w - 20;
    const barH = 5;

    // Background track
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.roundRect(barX, barY, barW, barH, 2.5);
    ctx.fill();

    // Active progress bar with smooth color gradient
    if (ratio > 0) {
        ctx.globalAlpha = 0.9;
        const grad = ctx.createLinearGradient(barX, barY, barX + barW, barY);
        grad.addColorStop(0, barGradientStart);
        grad.addColorStop(1, barGradientEnd);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(barX, barY, barW * ratio, barH, 2.5);
        ctx.fill();
    }

    ctx.restore();
}
