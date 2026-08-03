import type { RenderContext } from '../../rendering/types';
import { drawSoccerBall } from '../../utils/drawSoccerBall';
import type { SoccerRenderEntity } from './scene';

export const MAX_BALL_TRAIL_POINTS = 12;

interface TrailPoint {
    x: number;
    y: number;
}

export class BallLayer {
    private trail: TrailPoint[] = [];
    private lastFieldPoint: TrailPoint | null = null;
    private lastScreenPoint: TrailPoint | null = null;
    private rotation = 0;

    draw(ctx: CanvasRenderingContext2D, ball: SoccerRenderEntity, rc: RenderContext, pitchScale: number): void {
        const point = { x: ball.x, y: ball.y };
        const fieldDistance = this.lastFieldPoint
            ? Math.hypot(ball.fieldX - this.lastFieldPoint.x, ball.fieldY - this.lastFieldPoint.y)
            : 0;
        if (!this.lastFieldPoint || Math.hypot(ball.fieldX - this.lastFieldPoint.x, ball.fieldY - this.lastFieldPoint.y) > 20) {
            this.trail = [];
        }
        if (!this.lastScreenPoint || point.x !== this.lastScreenPoint.x || point.y !== this.lastScreenPoint.y) {
            this.trail.push(point);
            if (this.trail.length > MAX_BALL_TRAIL_POINTS) this.trail.shift();
        }
        this.lastFieldPoint = { x: ball.fieldX, y: ball.fieldY };
        this.lastScreenPoint = point;
        this.rotation += fieldDistance * 0.22;

        const minRadius = 7 * Math.max(rc.dpr, 1);
        const radius = Math.max(minRadius, Math.min(ball.radius, 0.5 * pitchScale));
        if (ball.speed > 4 && this.trail.length > 1) this.drawTrail(ctx, ball, rc.dpr);
        this.drawHalo(ctx, ball, radius, rc.dpr);
        drawSoccerBall(ctx, ball.x, ball.y, radius, this.rotation);
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.55)';
        ctx.lineWidth = 1.5 * Math.max(rc.dpr, 1);
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, radius + ctx.lineWidth / 2, 0, Math.PI * 2);
        ctx.stroke();
    }

    getTrailLength(): number {
        return this.trail.length;
    }

    private drawTrail(ctx: CanvasRenderingContext2D, ball: SoccerRenderEntity, dpr: number): void {
        const color = ball.team === 'left' ? '250, 204, 21' : ball.team === 'right' ? '248, 113, 113' : '226, 232, 240';
        for (let index = 1; index < this.trail.length; index += 1) {
            const from = this.trail[index - 1];
            const to = this.trail[index];
            const progress = index / this.trail.length;
            ctx.strokeStyle = `rgba(${color}, ${progress * 0.35})`;
            ctx.lineWidth = Math.max(1, progress * 4 * dpr);
            ctx.beginPath();
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
            ctx.stroke();
        }
    }

    private drawHalo(ctx: CanvasRenderingContext2D, ball: SoccerRenderEntity, radius: number, dpr: number): void {
        const halo = ctx.createRadialGradient(ball.x, ball.y, radius * 0.5, ball.x, ball.y, radius * 2.2);
        halo.addColorStop(0, `rgba(255, 255, 255, ${0.12 + Math.min(ball.speed / 30, 0.12)})`);
        halo.addColorStop(1, 'rgba(255, 255, 255, 0)');
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, radius * 2.2 + dpr, 0, Math.PI * 2);
        ctx.fill();
    }
}
