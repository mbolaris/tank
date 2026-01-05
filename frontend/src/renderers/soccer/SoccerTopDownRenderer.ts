/**
 * Soccer mode top-down renderer.
 * Renders a soccer field with players and ball.
 */

import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import type { EntityData } from '../../types/simulation';

/** Soccer-specific render hint structure */
interface SoccerRenderHint {
    style?: string;
    sprite?: 'player' | 'ball' | string;
    team?: 'left' | 'right';
    jersey_number?: number;
    stamina?: number;
    facing_angle?: number;
    has_ball?: boolean;
    velocity_x?: number;
    velocity_y?: number;
}

/** Lightweight entity representation for Soccer rendering */
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
}

/** Scene data for Soccer rendering */
interface SoccerScene {
    width: number;
    height: number;
    entities: SoccerEntity[];
}

/** Build Soccer scene from snapshot */
function buildSoccerScene(snapshot: any): SoccerScene {
    const entities: SoccerEntity[] = [];

    const rawEntities = snapshot.snapshot?.entities ?? snapshot.entities;

    // Field dimensions (assuming standard soccer field proportions)
    const worldWidth = 1088;
    const worldHeight = 612;

    if (rawEntities && Array.isArray(rawEntities)) {
        rawEntities.forEach((e: EntityData) => {
            if (e.type === 'player' || e.type === 'ball') {
                const hint = e.render_hint as SoccerRenderHint | undefined;

                entities.push({
                    id: e.id,
                    type: e.type,
                    x: e.x + e.width / 2,
                    y: e.y + e.height / 2,
                    radius: e.radius ?? Math.max(e.width, e.height) / 2,
                    vel_x: e.vel_x ?? hint?.velocity_x,
                    vel_y: e.vel_y ?? hint?.velocity_y,
                    team: e.team ?? hint?.team,
                    jersey_number: e.jersey_number ?? hint?.jersey_number,
                    stamina: e.stamina ?? hint?.stamina,
                    facing: e.facing ?? hint?.facing_angle,
                    has_ball: e.has_ball ?? hint?.has_ball,
                });
            }
        });
    }

    return {
        width: worldWidth,
        height: worldHeight,
        entities,
    };
}

export class SoccerTopDownRenderer implements Renderer {
    id = "soccer-topdown";

    dispose() {
        // No heavy resources to dispose
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        const scene = buildSoccerScene(frame.snapshot);
        const options = frame.options ?? {};

        // Grass green background
        ctx.fillStyle = "#2d5016";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Calculate scale to fit world
        const padding = 20;
        const availWidth = canvas.width - padding * 2;
        const availHeight = canvas.height - padding * 2;

        const scaleX = availWidth / scene.width;
        const scaleY = availHeight / scene.height;
        const scale = Math.min(scaleX, scaleY);

        const offsetX = (canvas.width - scene.width * scale) / 2;
        const offsetY = (canvas.height - scene.height * scale) / 2;

        ctx.save();
        ctx.translate(offsetX, offsetY);
        ctx.scale(scale, scale);

        // Draw field markings
        this.drawField(ctx, scene.width, scene.height);

        // Draw entities
        const balls = scene.entities.filter(e => e.type === 'ball');
        const players = scene.entities.filter(e => e.type === 'player');

        // Draw ball first (underneath players)
        balls.forEach(ball => {
            this.drawBall(ctx, ball);
        });

        // Draw players
        players.forEach(player => {
            this.drawPlayer(ctx, player);
        });

        // Draw stamina bars
        players.forEach(player => {
            if (player.stamina !== undefined) {
                const barWidth = Math.max(player.radius * 2.5, 30);
                this.drawStaminaBar(
                    ctx,
                    player.x - barWidth / 2,
                    player.y - player.radius - 12,
                    barWidth,
                    player.stamina
                );
            }
        });

        // Draw selection ring (top-most)
        if (options.selectedEntityId !== undefined && options.selectedEntityId !== null) {
            const selected = scene.entities.find(e => e.id === options.selectedEntityId);
            if (selected) {
                ctx.save();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.arc(selected.x, selected.y, selected.radius + 4, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }
        }

        ctx.restore();
    }

    private drawField(ctx: CanvasRenderingContext2D, width: number, height: number) {
        // Field background (darker green)
        ctx.fillStyle = "#3a661e";
        ctx.fillRect(0, 0, width, height);

        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;

        // Field boundary
        ctx.strokeRect(0, 0, width, height);

        // Center line
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.stroke();

        // Center circle
        const centerRadius = Math.min(width, height) * 0.15;
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, centerRadius, 0, Math.PI * 2);
        ctx.stroke();

        // Center spot
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, 3, 0, Math.PI * 2);
        ctx.fill();

        // Goals
        const goalWidth = height * 0.35;
        const goalDepth = 20;
        const goalY = (height - goalWidth) / 2;

        // Left goal
        ctx.strokeStyle = "#cccccc";
        ctx.lineWidth = 3;
        ctx.strokeRect(-goalDepth, goalY, goalDepth, goalWidth);
        ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
        ctx.fillRect(-goalDepth, goalY, goalDepth, goalWidth);

        // Right goal
        ctx.strokeRect(width, goalY, goalDepth, goalWidth);
        ctx.fillRect(width, goalY, goalDepth, goalWidth);

        // Penalty boxes
        const penaltyWidth = height * 0.6;
        const penaltyDepth = width * 0.15;
        const penaltyY = (height - penaltyWidth) / 2;

        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;

        // Left penalty box
        ctx.strokeRect(0, penaltyY, penaltyDepth, penaltyWidth);

        // Right penalty box
        ctx.strokeRect(width - penaltyDepth, penaltyY, penaltyDepth, penaltyWidth);

        // Penalty spots
        ctx.fillStyle = "#ffffff";
        const penaltySpotDist = width * 0.10;
        ctx.beginPath();
        ctx.arc(penaltySpotDist, height / 2, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(width - penaltySpotDist, height / 2, 3, 0, Math.PI * 2);
        ctx.fill();
    }

    private drawBall(ctx: CanvasRenderingContext2D, ball: SoccerEntity) {
        ctx.save();

        // Shadow
        ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
        ctx.beginPath();
        ctx.ellipse(ball.x, ball.y + 2, ball.radius * 0.8, ball.radius * 0.4, 0, 0, Math.PI * 2);
        ctx.fill();

        // Ball body
        const gradient = ctx.createRadialGradient(
            ball.x - ball.radius * 0.3,
            ball.y - ball.radius * 0.3,
            ball.radius * 0.2,
            ball.x,
            ball.y,
            ball.radius
        );
        gradient.addColorStop(0, "#ffffff");
        gradient.addColorStop(0.7, "#e0e0e0");
        gradient.addColorStop(1, "#b0b0b0");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
        ctx.fill();

        // Ball outline
        ctx.strokeStyle = "#888888";
        ctx.lineWidth = 1;
        ctx.stroke();

        // Simple pentagon pattern
        ctx.strokeStyle = "#333333";
        ctx.lineWidth = 1.5;
        const sides = 5;
        ctx.beginPath();
        for (let i = 0; i <= sides; i++) {
            const angle = (i / sides) * Math.PI * 2 - Math.PI / 2;
            const x = ball.x + Math.cos(angle) * ball.radius * 0.5;
            const y = ball.y + Math.sin(angle) * ball.radius * 0.5;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        ctx.restore();
    }

    private drawPlayer(ctx: CanvasRenderingContext2D, player: SoccerEntity) {
        ctx.save();
        ctx.translate(player.x, player.y);

        // Determine team color
        const teamColor = player.team === 'left' ? '#3b82f6' : '#ef4444'; // Blue vs Red
        const teamColorDark = player.team === 'left' ? '#1e40af' : '#991b1b';

        // Shadow
        ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
        ctx.beginPath();
        ctx.ellipse(0, player.radius * 0.3, player.radius * 0.9, player.radius * 0.4, 0, 0, Math.PI * 2);
        ctx.fill();

        // Player body (circle with team color)
        const gradient = ctx.createRadialGradient(
            -player.radius * 0.3,
            -player.radius * 0.3,
            player.radius * 0.2,
            0,
            0,
            player.radius
        );
        gradient.addColorStop(0, teamColor);
        gradient.addColorStop(1, teamColorDark);
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(0, 0, player.radius, 0, Math.PI * 2);
        ctx.fill();

        // Player outline
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();

        // Facing indicator (small wedge pointing in direction)
        if (player.facing !== undefined) {
            ctx.save();
            ctx.rotate(player.facing);
            ctx.fillStyle = "#ffffff";
            ctx.beginPath();
            ctx.moveTo(player.radius * 0.7, 0);
            ctx.lineTo(player.radius * 0.3, -player.radius * 0.3);
            ctx.lineTo(player.radius * 0.3, player.radius * 0.3);
            ctx.closePath();
            ctx.fill();
            ctx.restore();
        }

        // Jersey number
        if (player.jersey_number !== undefined) {
            ctx.fillStyle = "#ffffff";
            ctx.font = `bold ${Math.max(10, player.radius * 0.8)}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(String(player.jersey_number), 0, 0);
        }

        // Ball possession indicator
        if (player.has_ball) {
            ctx.strokeStyle = "#fbbf24";
            ctx.lineWidth = 3;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.arc(0, 0, player.radius + 5, 0, Math.PI * 2);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        ctx.restore();
    }

    private drawStaminaBar(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, stamina: number) {
        const barHeight = 4;
        const padding = 1;

        // Background
        ctx.save();
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        const radius = 2;
        ctx.beginPath();
        if ((ctx as any).roundRect) {
            (ctx as any).roundRect(x, y, width, barHeight, radius);
        } else {
            ctx.rect(x, y, width, barHeight);
        }
        ctx.fill();
        ctx.stroke();

        // Stamina bar (0-100)
        const normalizedStamina = Math.max(0, Math.min(100, stamina));
        let colorStart: string, colorEnd: string;

        if (normalizedStamina < 30) {
            colorStart = '#ff6b6b';
            colorEnd = '#ef4444';
        } else if (normalizedStamina < 60) {
            colorStart = '#ffd93d';
            colorEnd = '#fbbf24';
        } else {
            colorStart = '#6bffb8';
            colorEnd = '#4ade80';
        }

        const barFillWidth = Math.max(0, (width - padding * 2) * (normalizedStamina / 100));

        if (barFillWidth > 0) {
            const gradient = ctx.createLinearGradient(x, y, x + barFillWidth, y);
            gradient.addColorStop(0, colorStart);
            gradient.addColorStop(1, colorEnd);
            ctx.fillStyle = gradient;

            ctx.beginPath();
            if ((ctx as any).roundRect) {
                (ctx as any).roundRect(x + padding, y + padding, barFillWidth, barHeight - padding * 2, radius - 1);
            } else {
                ctx.rect(x + padding, y + padding, barFillWidth, barHeight - padding * 2);
            }
            ctx.fill();
        }

        ctx.restore();
    }
}
