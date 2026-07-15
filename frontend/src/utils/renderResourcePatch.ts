import type { EntityData } from '../types/simulation';

export function renderResourcePatch(ctx: CanvasRenderingContext2D, patch: EntityData) {
    const ratio = Math.max(0, Math.min(1, Number(patch.render_hint?.stock_ratio ?? 0)));
    const kind = String(patch.render_hint?.kind ?? patch.food_type ?? 'algae');
    const color = kind === 'protein' ? '#d890ff' : '#55d6a1';

    ctx.save();
    ctx.globalAlpha = 0.18 + ratio * 0.22;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(patch.x, patch.y, patch.width, patch.height, 18);
    ctx.fill();
    ctx.globalAlpha = 0.8;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.globalAlpha = 0.75;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(
        patch.x + 5,
        patch.y + patch.height - 10,
        Math.max(0, (patch.width - 10) * ratio),
        5,
        2,
    );
    ctx.fill();
    ctx.globalAlpha = 0.55;
    ctx.font = '11px sans-serif';
    ctx.fillText(kind === 'protein' ? 'PROTEIN PATCH' : 'ALGAE PATCH', patch.x + 9, patch.y + 17);
    ctx.restore();
}
