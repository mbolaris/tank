import type { EntityData } from '../types/simulation';
import { drawSoccerBall } from './drawSoccerBall';

export function renderBall(ctx: CanvasRenderingContext2D, entity: EntityData) {
    const radius = entity.radius || (entity.width ? entity.width / 2 : 10);
    const rotation = entity.vel_x || entity.vel_y ? entity.x / radius : 0;
    drawSoccerBall(ctx, entity.x + radius, entity.y + radius, radius, rotation);
}

export function renderGoalZone(ctx: CanvasRenderingContext2D, entity: EntityData) {
    const radius = entity.radius || 30;
    const coral = entity.team === 'left' ? '#75c7a7' : '#76b8df';
    const accent = entity.team === 'left' ? '#d1f7b4' : '#c8ebff';
    ctx.save();
    ctx.translate(entity.x, entity.y);
    ctx.strokeStyle = coral;
    ctx.lineWidth = Math.max(4, radius * 0.16);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.arc(0, radius * 0.18, radius * 0.68, Math.PI * 1.12, Math.PI * 1.88);
    ctx.stroke();
    ctx.fillStyle = accent;
    ctx.shadowColor = coral;
    ctx.shadowBlur = 10;
    for (let i = 0; i < 3; i++) {
        const angle = Math.PI * (1.18 + i * 0.32);
        ctx.beginPath();
        ctx.arc(Math.cos(angle) * radius * 0.66, radius * 0.18 + Math.sin(angle) * radius * 0.66, Math.max(2, radius * 0.09), 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.shadowBlur = 0;
    ctx.fillStyle = 'rgba(228, 245, 241, 0.9)';
    ctx.font = '700 9px "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('GATE', 0, radius * 0.28);
    ctx.restore();
}
