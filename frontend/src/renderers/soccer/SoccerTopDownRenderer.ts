/** Soccer renderer using canonical metres and a single uniform pitch transform. */

import type { RenderContext, RenderFrame, Renderer } from '../../rendering/types';
import type { EntityData } from '../../types/simulation';
import { drawSoccerBall } from '../../utils/drawSoccerBall';
import { drawAvatar, clearAvatarPathCache } from '../avatar_renderer';
import { renderFromCanonical } from './renderFromCanonical';
import { resolveSoccerGeometry, soccerMatchSnapshot, type ResolvedSoccerFieldGeometry } from './fieldGeometry';
import { StaticFieldLayer } from './StaticFieldLayer';
import { usePitchTransform, type PitchTransform } from './usePitchTransform';

interface SoccerRenderHint {
    team?: 'left' | 'right';
    jersey_number?: number;
    stamina?: number;
    facing_angle?: number;
    has_ball?: boolean;
    velocity_x?: number;
    velocity_y?: number;
}

interface SoccerEntity {
    id: number;
    type: EntityData['type'];
    x: number;
    y: number;
    radius: number;
    vel_x?: number;
    vel_y?: number;
    team?: 'left' | 'right';
    jersey_number?: number;
    stamina?: number;
    facing?: number;
    has_ball?: boolean;
    genome_data?: EntityData['genome_data'];
}

interface SoccerScene {
    entities: SoccerEntity[];
}

function buildSoccerScene(
    frame: RenderFrame,
    transform: PitchTransform,
): SoccerScene {
    const state = soccerMatchSnapshot(frame.snapshot);
    const coordSpace = state.coord_space;
    const entities: SoccerEntity[] = [];

    for (const entity of state.entities ?? []) {
        if (entity.type !== 'player' && entity.type !== 'ball') continue;

        const hint = entity.render_hint as SoccerRenderHint | undefined;
        const position = renderFromCanonical({ x: entity.x, y: entity.y }, coordSpace);
        const velocity = renderFromCanonical(
            { x: entity.vel_x ?? hint?.velocity_x ?? 0, y: entity.vel_y ?? hint?.velocity_y ?? 0 },
            coordSpace,
        );
        const [x, y] = transform.toScreen(position.x, position.y);
        const radius = (entity.radius ?? 0.3) * transform.scale;

        entities.push({
            id: entity.id,
            type: entity.type,
            x,
            y,
            radius: Math.max(radius, entity.type === 'ball' ? 8 : 12),
            vel_x: velocity.x,
            vel_y: velocity.y,
            team: entity.team ?? hint?.team,
            jersey_number: entity.jersey_number ?? hint?.jersey_number,
            stamina: entity.stamina ?? hint?.stamina,
            facing: entity.facing ?? hint?.facing_angle,
            has_ball: entity.has_ball ?? hint?.has_ball,
            genome_data: entity.genome_data,
        });
    }

    return { entities };
}

export class SoccerTopDownRenderer implements Renderer {
    id = 'soccer-topdown';
    private readonly staticFieldLayer = new StaticFieldLayer();

    dispose(): void {
        clearAvatarPathCache();
    }

    render(frame: RenderFrame, rc: RenderContext): void {
        const { ctx, canvas } = rc;
        const geometry = resolveSoccerGeometry(frame.snapshot);
        // This is a pure metres-to-pixels transform, not a React hook.
        // eslint-disable-next-line react-hooks/rules-of-hooks
        const transform = usePitchTransform(
            geometry,
            { width: canvas.width, height: canvas.height },
            20 * Math.max(rc.dpr, 1),
        );

        if (frame.options?.showSoccer ?? true) {
            this.staticFieldLayer.draw(ctx, geometry, transform);
        } else {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#071c22';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            this.drawFieldOutline(ctx, geometry, transform);
        }

        const scene = buildSoccerScene(frame, transform);
        const balls = scene.entities.filter((entity) => entity.type === 'ball');
        const players = scene.entities.filter((entity) => entity.type === 'player');
        const forceMicrobe = frame.options?.viewMode === 'topdown';

        // PR 1C will change z-order and animation. Keep the existing static draw
        // order for this foundation PR so the change remains behavior-neutral.
        if (frame.options?.showSoccer ?? true) {
            balls.forEach((ball) => this.drawBall(ctx, ball));
        }
        players.forEach((player) => this.drawPlayer(ctx, player, forceMicrobe));
    }

    private drawFieldOutline(
        ctx: CanvasRenderingContext2D,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
    ): void {
        const [left, top] = transform.toScreen(-geometry.length / 2, -geometry.width / 2);
        const [right, bottom] = transform.toScreen(geometry.length / 2, geometry.width / 2);
        ctx.strokeStyle = 'rgba(241, 248, 244, 0.25)';
        ctx.lineWidth = Math.max(1, 1.5 * transform.scale / Math.max(transform.scale, 1));
        ctx.strokeRect(left, top, right - left, bottom - top);
    }

    private drawBall(ctx: CanvasRenderingContext2D, ball: SoccerEntity): void {
        const visibleRadius = Math.max(ball.radius, 10);
        let rotation = 0;
        if (ball.vel_x || ball.vel_y) {
            const speed = Math.sqrt((ball.vel_x || 0) ** 2 + (ball.vel_y || 0) ** 2);
            rotation = (Date.now() * 0.005 * speed) % (Math.PI * 2);
        }
        drawSoccerBall(ctx, ball.x, ball.y, visibleRadius, rotation);
    }

    private drawPlayer(ctx: CanvasRenderingContext2D, player: SoccerEntity, forceMicrobe = false): void {
        ctx.save();
        try {
            ctx.translate(player.x, player.y);
            const genomeData = player.genome_data;
            const avatarRadius = Math.max(player.radius, 15);

            if (genomeData) {
                const ringColor = player.team === 'left' ? 'rgba(255, 255, 0, 0.5)' : 'rgba(255, 0, 0, 0.5)';
                ctx.strokeStyle = ringColor;
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(0, 0, avatarRadius + 5, 0, Math.PI * 2);
                ctx.stroke();
                drawAvatar(ctx, player.id, avatarRadius, player.vel_x, player.vel_y, genomeData, forceMicrobe, player.team);
            } else {
                const teamColor = player.team === 'left' ? '#ffff00' : '#ff0000';
                const teamColorDark = player.team === 'left' ? '#b3b300' : '#b30000';
                ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
                ctx.beginPath();
                ctx.ellipse(0, avatarRadius * 0.3, avatarRadius * 0.9, avatarRadius * 0.4, 0, 0, Math.PI * 2);
                ctx.fill();
                const gradient = ctx.createRadialGradient(-avatarRadius * 0.3, -avatarRadius * 0.3, avatarRadius * 0.2, 0, 0, avatarRadius);
                gradient.addColorStop(0, teamColor);
                gradient.addColorStop(1, teamColorDark);
                ctx.fillStyle = gradient;
                ctx.beginPath();
                ctx.arc(0, 0, avatarRadius, 0, Math.PI * 2);
                ctx.fill();
                if (player.facing !== undefined) {
                    ctx.save();
                    ctx.rotate(player.facing);
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.beginPath();
                    ctx.moveTo(0, 0);
                    ctx.arc(0, 0, avatarRadius, -0.5, 0.5);
                    ctx.lineTo(0, 0);
                    ctx.fill();
                    ctx.restore();
                }
                ctx.strokeStyle = '#000000';
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            if (player.jersey_number !== undefined) {
                ctx.fillStyle = '#ffffff';
                ctx.font = `bold ${Math.max(10, avatarRadius * 0.6)}px Arial`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.shadowColor = 'rgba(0,0,0,0.5)';
                ctx.shadowBlur = 4;
                ctx.fillText(player.jersey_number.toString(), 0, 0);
                ctx.shadowBlur = 0;
            }

            if (player.has_ball) {
                ctx.strokeStyle = '#fbbf24';
                ctx.lineWidth = 3;
                ctx.setLineDash([3, 3]);
                ctx.beginPath();
                ctx.arc(0, 0, avatarRadius + 8, 0, Math.PI * 2);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        } catch (error) {
            console.error('Error drawing player:', error);
        } finally {
            ctx.restore();
        }
    }
}
