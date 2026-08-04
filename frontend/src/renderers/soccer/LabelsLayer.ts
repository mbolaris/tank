import type { SoccerMatchState } from '../../types/simulation';
import type { ResolvedSoccerFieldGeometry } from './fieldGeometry';
import { resolveSideAssignment } from './sideAssignment';
import type { PitchTransform } from './usePitchTransform';

export class LabelsLayer {
    draw(
        ctx: CanvasRenderingContext2D,
        state: SoccerMatchState,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
    ): void {
        ctx.save();
        ctx.fillStyle = 'rgba(226, 232, 240, 0.42)';
        ctx.strokeStyle = 'rgba(226, 232, 240, 0.2)';
        ctx.lineWidth = 1;
        // Sides are the pitch's; names belong to the teams and follow the swap.
        const sides = resolveSideAssignment(state);
        this.drawAttackBand(ctx, geometry, transform, -1, sides.leftAttackDirection);
        this.drawAttackBand(ctx, geometry, transform, 1, sides.rightAttackDirection);
        this.drawTeamLabel(ctx, sides.leftLabel, geometry, transform, -1, sides.leftAttackDirection);
        this.drawTeamLabel(ctx, sides.rightLabel, geometry, transform, 1, sides.rightAttackDirection);
        ctx.restore();
    }

    private drawAttackBand(ctx: CanvasRenderingContext2D, geometry: ResolvedSoccerFieldGeometry, transform: PitchTransform, side: -1 | 1, direction: -1 | 1): void {
        const xStart = side < 0 ? -geometry.length / 2 + 2 : 2;
        const [screenX, screenY] = transform.toScreen(xStart, -geometry.width / 2 + 2);
        ctx.save();
        ctx.translate(screenX, screenY);
        ctx.scale(transform.scale, transform.scale);
        ctx.globalAlpha = 0.4;
        for (let index = 0; index < 3; index += 1) {
            const x = index * 4 * direction;
            ctx.beginPath();
            ctx.moveTo(x, -1.2);
            ctx.lineTo(x + direction * 2, 0);
            ctx.lineTo(x, 1.2);
            ctx.stroke();
        }
        ctx.restore();
    }

    private drawTeamLabel(
        ctx: CanvasRenderingContext2D,
        label: string,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
        side: -1 | 1,
        direction: -1 | 1,
    ): void {
        const [x, y] = transform.toScreen(side * geometry.length / 2, -(geometry.width / 2 + 3));
        ctx.fillStyle = 'rgba(226, 232, 240, 0.48)';
        ctx.font = `${Math.max(9, Math.min(13, transform.scale * 0.22))}px ui-monospace, monospace`;
        ctx.textAlign = side < 0 ? 'left' : 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${direction > 0 ? '→' : '←'} ${label}`, x, y);
    }
}
