import type { FishGenomeData } from '../../types/simulation';
import { drawAvatar } from '../avatar_renderer';
import type { SoccerRenderEntity } from './scene';

const TEAM_COLORS = { left: '#facc15', right: '#f87171' } as const;

export type SoccerAvatarKind = 'fish' | 'reference' | 'external' | 'bot';

export function avatarKindForEntity(player: SoccerRenderEntity): SoccerAvatarKind {
    const kind = player.participant?.avatar_kind;
    if (kind === 'reference' || kind === 'external' || kind === 'bot') return kind;
    return 'fish';
}

export class PlayersLayer {
    draw(ctx: CanvasRenderingContext2D, players: SoccerRenderEntity[], forceMicrobe = false): void {
        for (const player of players) this.drawPlayer(ctx, player, forceMicrobe);
    }

    private drawPlayer(ctx: CanvasRenderingContext2D, player: SoccerRenderEntity, forceMicrobe: boolean): void {
        const teamColor = player.team ? TEAM_COLORS[player.team] : '#cbd5e1';
        const radius = Math.max(player.radius, 15);
        ctx.save();
        try {
            ctx.translate(player.x, player.y);
            this.drawGroundRing(ctx, radius, teamColor, player.facing, player.has_ball);
            this.drawAvatarKind(ctx, player, radius, forceMicrobe);
            this.drawBadge(ctx, radius, teamColor, player.jersey_number);
        } finally {
            ctx.restore();
        }
    }

    private drawGroundRing(
        ctx: CanvasRenderingContext2D,
        radius: number,
        color: string,
        facing: number | undefined,
        hasBall: boolean | undefined,
    ): void {
        ctx.strokeStyle = color;
        ctx.lineWidth = hasBall ? 3 : 2;
        ctx.globalAlpha = hasBall ? 1 : 0.82;
        ctx.beginPath();
        const opening = facing ?? 0;
        ctx.arc(0, 0, radius + (hasBall ? 4 : 3), opening + 0.55, opening + Math.PI * 2 - 0.55);
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    private drawAvatarKind(
        ctx: CanvasRenderingContext2D,
        player: SoccerRenderEntity,
        radius: number,
        forceMicrobe: boolean,
    ): void {
        const kind = avatarKindForEntity(player);
        if (kind === 'fish') {
            this.drawFish(ctx, player, radius, forceMicrobe);
            return;
        }
        const color = kind === 'external' ? '#38bdf8' : kind === 'reference' ? '#94a3b8' : '#64748b';
        this.drawNeutralChevron(ctx, radius, color, player.facing);
    }

    private drawFish(ctx: CanvasRenderingContext2D, player: SoccerRenderEntity, radius: number, forceMicrobe: boolean): void {
        const genome = player.genome_data as FishGenomeData | undefined;
        if (genome) {
            drawAvatar(ctx, player.id, radius, player.vel_x, player.vel_y, genome, forceMicrobe, player.team);
            return;
        }
        ctx.fillStyle = player.team ? TEAM_COLORS[player.team] : '#e2e8f0';
        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        ctx.fill();
    }

    private drawNeutralChevron(ctx: CanvasRenderingContext2D, radius: number, color: string, facing: number | undefined): void {
        ctx.save();
        ctx.rotate(facing ?? 0);
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.9;
        ctx.beginPath();
        ctx.moveTo(radius * 0.95, 0);
        ctx.lineTo(-radius * 0.65, -radius * 0.72);
        ctx.lineTo(-radius * 0.28, 0);
        ctx.lineTo(-radius * 0.65, radius * 0.72);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    private drawBadge(ctx: CanvasRenderingContext2D, radius: number, color: string, jerseyNumber: number | undefined): void {
        if (jerseyNumber === undefined) return;
        const badgeWidth = Math.max(16, radius * 0.9);
        const badgeHeight = Math.max(11, radius * 0.52);
        const x = -radius * 1.15;
        const y = -radius * 1.2;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x, y, badgeWidth, badgeHeight, badgeHeight * 0.35);
        ctx.fill();
        ctx.fillStyle = '#0f172a';
        ctx.font = `bold ${Math.max(9, radius * 0.36)}px ui-monospace, monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(jerseyNumber), x + badgeWidth / 2, y + badgeHeight / 2 + 0.5);
    }
}
