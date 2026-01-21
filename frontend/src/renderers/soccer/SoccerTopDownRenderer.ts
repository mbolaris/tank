/**
 * Soccer mode top-down renderer.
 * Renders a soccer field with players and ball.
 */

import type { RenderContext, RenderFrame, RenderSnapshot, Renderer } from '../../rendering/types';
import { drawSoccerBall } from '../../utils/drawSoccerBall';
import type { EntityData, SoccerMatchState, SimulationUpdate } from '../../types/simulation';
import { drawAvatar } from '../avatar_renderer';


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
    genome_data?: EntityData['genome_data'];
}

/** Scene data for Soccer rendering */
interface SoccerScene {
    width: number;
    height: number;
    entities: SoccerEntity[];
}

/** Build Soccer scene from snapshot */
type SoccerField = SoccerMatchState['field'];

function isSimulationUpdate(snapshot: RenderSnapshot): snapshot is SimulationUpdate {
    return (snapshot as SimulationUpdate).snapshot !== undefined;
}

function buildSoccerScene(snapshot: RenderSnapshot): SoccerScene {
    const entities: SoccerEntity[] = [];

    const rawEntities = isSimulationUpdate(snapshot)
        ? snapshot.snapshot?.entities ?? snapshot.entities
        : snapshot.entities;

    // Read field dimensions from snapshot (meters) - with fallback
    // New backend provides field.length and field.width in meters, centered at origin
    const fieldData = isSimulationUpdate(snapshot)
        ? (snapshot.snapshot as { field?: SoccerField } | undefined)?.field ?? (snapshot as { field?: SoccerField }).field
        : snapshot.field;
    const fieldLength = fieldData?.length ?? 100.0; // meters (x-axis)
    const fieldWidth = fieldData?.width ?? 60.0;    // meters (y-axis)

    // Target canvas dimensions for the scene (16:9 aspect preserved)
    // These are the "virtual" scene units before final canvas scaling
    const SCENE_WIDTH = 1088;
    const SCENE_HEIGHT = 612;

    // Calculate scale from field meters to scene units
    const scaleX = SCENE_WIDTH / fieldLength;
    const scaleY = SCENE_HEIGHT / fieldWidth;
    const entityScale = (scaleX + scaleY) / 2.0;

    // Offset to center: field origin (0,0) maps to scene center
    const offsetX = SCENE_WIDTH / 2;
    const offsetY = SCENE_HEIGHT / 2;

    if (rawEntities && Array.isArray(rawEntities)) {
        rawEntities.forEach((e: EntityData) => {
            if (e.type === 'player' || e.type === 'ball') {
                const hint = e.render_hint as SoccerRenderHint | undefined;

                // Transform field-space (meters, centered) to scene-space (pixels, top-left origin)
                const sceneX = e.x * scaleX + offsetX;
                const sceneY = e.y * scaleY + offsetY;
                const sceneRadius = (e.radius ?? 0.3) * entityScale;

                entities.push({
                    id: e.id,
                    type: e.type,
                    x: sceneX,
                    y: sceneY,
                    radius: Math.max(sceneRadius, e.type === 'ball' ? 8 : 12), // Minimum visible size
                    vel_x: e.vel_x ?? hint?.velocity_x,
                    vel_y: e.vel_y ?? hint?.velocity_y,
                    team: e.team ?? hint?.team,
                    jersey_number: e.jersey_number ?? hint?.jersey_number,
                    stamina: e.stamina ?? hint?.stamina,
                    facing: e.facing ?? hint?.facing_angle,
                    has_ball: e.has_ball ?? hint?.has_ball,
                    genome_data: e.genome_data,
                });
            }
        });
    }

    return {
        width: SCENE_WIDTH,
        height: SCENE_HEIGHT,
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
        const showSoccer = options.showSoccer ?? true;

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
        try {
            ctx.translate(offsetX, offsetY);
            ctx.scale(scale, scale);

            // Draw field markings
            if (showSoccer) {
                this.drawField(ctx, scene.width, scene.height);
            } else {
                ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
                ctx.lineWidth = 1;
                ctx.strokeRect(0, 0, scene.width, scene.height);
            }

            // Draw entities
            const balls = scene.entities.filter(e => e.type === 'ball');
            const players = scene.entities.filter(e => e.type === 'player');

            // Draw ball first (underneath players)
            if (showSoccer) {
                balls.forEach(ball => {
                    this.drawBall(ctx, ball);
                });
            }

            // Determine avatar mode based on view_mode
            // "top" or "topdown" = petri/microbe mode, otherwise = fish mode
            const forceMicrobe = options.viewMode === 'topdown';

            // Draw players
            players.forEach(player => {
                this.drawPlayer(ctx, player, forceMicrobe);
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
        } catch (e) {
            console.error("Error in SoccerTopDownRenderer.render:", e);
        } finally {
            ctx.restore();
        }
    }

    private drawField(ctx: CanvasRenderingContext2D, width: number, height: number) {
        // RCSS-style field background (bright green)
        ctx.fillStyle = "#2e9a30";
        ctx.fillRect(0, 0, width, height);

        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;

        // Field boundary
        ctx.strokeRect(0, 0, width, height);

        // Center line
        ctx.beginPath();
        ctx.moveTo(width / 2, 0);
        ctx.lineTo(width / 2, height);
        ctx.stroke();

        // Center circle (RCSS standard: 9.15m = ~15% of half field)
        const centerRadius = Math.min(width, height) * 0.15;
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, centerRadius, 0, Math.PI * 2);
        ctx.stroke();

        // Center spot
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(width / 2, height / 2, 3, 0, Math.PI * 2);
        ctx.fill();

        // Goals - RCSS style (Black/Dark Grey box with depth)
        const goalWidth = height * 0.25;
        const goalDepth = 20;
        const goalY = (height - goalWidth) / 2;

        // Left goal
        ctx.fillStyle = "#222222";
        ctx.fillRect(-goalDepth, goalY, goalDepth, goalWidth);
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = 2;
        ctx.strokeRect(-goalDepth, goalY, goalDepth, goalWidth);

        // Right goal
        ctx.fillStyle = "#222222";
        ctx.fillRect(width, goalY, goalDepth, goalWidth);
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = 2;
        ctx.strokeRect(width, goalY, goalDepth, goalWidth);

        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.5;

        // Penalty boxes (16.5m = larger area)
        const penaltyWidth = height * 0.65;
        const penaltyDepth = width * 0.16;
        const penaltyY = (height - penaltyWidth) / 2;

        // Left penalty box
        ctx.strokeRect(0, penaltyY, penaltyDepth, penaltyWidth);

        // Right penalty box
        ctx.strokeRect(width - penaltyDepth, penaltyY, penaltyDepth, penaltyWidth);

        // Goal area boxes (smaller boxes near goals)
        const goalAreaWidth = height * 0.30;
        const goalAreaDepth = width * 0.055;
        const goalAreaY = (height - goalAreaWidth) / 2;

        // Left goal area
        ctx.strokeRect(0, goalAreaY, goalAreaDepth, goalAreaWidth);

        // Right goal area
        ctx.strokeRect(width - goalAreaDepth, goalAreaY, goalAreaDepth, goalAreaWidth);

        // Penalty spots
        ctx.fillStyle = "#ffffff";
        const penaltySpotDist = width * 0.11;
        ctx.beginPath();
        ctx.arc(penaltySpotDist, height / 2, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(width - penaltySpotDist, height / 2, 4, 0, Math.PI * 2);
        ctx.fill();

        // Penalty arcs
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        const arcRadius = centerRadius;

        // Left penalty arc
        ctx.beginPath();
        ctx.arc(penaltySpotDist, height / 2, arcRadius, -0.7, 0.7);
        ctx.stroke();

        // Right penalty arc
        ctx.beginPath();
        ctx.arc(width - penaltySpotDist, height / 2, arcRadius, Math.PI - 0.7, Math.PI + 0.7);
        ctx.stroke();

        // Corner arcs
        const cornerRadius = 8;
        ctx.beginPath();
        ctx.arc(0, 0, cornerRadius, 0, Math.PI / 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(width, 0, cornerRadius, Math.PI / 2, Math.PI);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(width, height, cornerRadius, Math.PI, Math.PI * 1.5);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(0, height, cornerRadius, Math.PI * 1.5, Math.PI * 2);
        ctx.stroke();
    }

    private drawBall(ctx: CanvasRenderingContext2D, ball: SoccerEntity) {
        // Use a larger visible radius (minimum 10 pixels)
        const visibleRadius = Math.max(ball.radius, 10);

        // Calculate rotation based on velocity or simple time-based spin
        let rotation = 0;
        if (ball.vel_x || ball.vel_y) {
            const speed = Math.sqrt((ball.vel_x || 0) ** 2 + (ball.vel_y || 0) ** 2);
            // Spin proportional to speed
            rotation = (Date.now() * 0.005 * speed) % (Math.PI * 2);
        }

        drawSoccerBall(ctx, ball.x, ball.y, visibleRadius, rotation);
    }



    private drawPlayer(ctx: CanvasRenderingContext2D, player: SoccerEntity, forceMicrobe: boolean = false) {
        ctx.save();
        try {
            ctx.translate(player.x, player.y);

            // Check if we have genome data for avatar rendering
            const genomeData = player.genome_data;

            // Use a sensible avatar size (the raw radius from physics might be too small)
            // Minimum player radius for visible avatars
            const avatarRadius = Math.max(player.radius, 15);

            if (genomeData) {
                // Draw team indicator ring (behind avatar)
                const ringColor = player.team === 'left' ? 'rgba(255, 255, 0, 0.5)' : 'rgba(255, 0, 0, 0.5)';
                ctx.strokeStyle = ringColor;
                ctx.lineWidth = 3;
                ctx.beginPath();
                ctx.arc(0, 0, avatarRadius + 5, 0, Math.PI * 2);
                ctx.stroke();

                // Use unified avatar renderer with proper size
                // Pass forceMicrobe for Petri dish mode
                drawAvatar(ctx, player.id, avatarRadius, player.vel_x, player.vel_y, genomeData, forceMicrobe);

            } else {
                // Fallback to simple circle rendering
                // Left = Yellow, Right = Red
                const teamColor = player.team === 'left' ? '#ffff00' : '#ff0000';
                const teamColorDark = player.team === 'left' ? '#b3b300' : '#b30000';

                // Shadow
                ctx.fillStyle = "rgba(0, 0, 0, 0.3)";
                ctx.beginPath();
                ctx.ellipse(0, avatarRadius * 0.3, avatarRadius * 0.9, avatarRadius * 0.4, 0, 0, Math.PI * 2);
                ctx.fill();

                // Player body
                const gradient = ctx.createRadialGradient(-avatarRadius * 0.3, -avatarRadius * 0.3, avatarRadius * 0.2, 0, 0, avatarRadius);
                gradient.addColorStop(0, teamColor);
                gradient.addColorStop(1, teamColorDark);
                ctx.fillStyle = gradient;
                ctx.beginPath();
                ctx.arc(0, 0, avatarRadius, 0, Math.PI * 2);
                ctx.fill();

                // Direction highlight (Black segment like RCSS)
                if (player.facing !== undefined) {
                    ctx.save();
                    ctx.rotate(player.facing);
                    ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
                    ctx.beginPath();
                    ctx.moveTo(0, 0);
                    ctx.arc(0, 0, avatarRadius, -0.5, 0.5);
                    ctx.lineTo(0, 0);
                    ctx.fill();
                    ctx.restore();
                }

                // Outline (Black for contrast)
                ctx.strokeStyle = "#000000";
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            // Jersey number
            if (player.jersey_number !== undefined) {
                ctx.fillStyle = "#ffffff";
                ctx.font = `bold ${Math.max(10, avatarRadius * 0.6)}px Arial`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.shadowColor = "rgba(0,0,0,0.5)";
                ctx.shadowBlur = 4;
                ctx.fillText(player.jersey_number.toString(), 0, 0);
                ctx.shadowBlur = 0;
            }

            // Ball possession indicator
            if (player.has_ball) {
                ctx.strokeStyle = "#fbbf24";
                ctx.lineWidth = 3;
                ctx.setLineDash([3, 3]);
                ctx.beginPath();
                ctx.arc(0, 0, avatarRadius + 8, 0, Math.PI * 2);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        } catch (e) {
            console.error("Error drawing player:", e);
        } finally {
            ctx.restore();
        }
    }



}
