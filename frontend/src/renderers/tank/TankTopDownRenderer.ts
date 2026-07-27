
import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import type { SimulationUpdate } from '../../types/simulation';
import { buildTankScene, type TankEntity } from './tankScene';
import { drawPursuitOverlay } from '../../utils/drawPursuitOverlay';
import { drawTargetMemoryOverlay } from '../../utils/drawTargetMemoryOverlay';
import { hashColor } from '../shared/canvasPrimitives';
import { drawFoodSprite, TANK_FOOD_SPRITE } from '../shared/foodAvatar';
import { drawMicrobeAvatar } from '../shared/microbeAvatar';
import {
    drawMicrobePredator,
    drawMicrobeSubstrate,
    TANK_PREDATOR_STYLE,
} from '../shared/microbeScenery';
import {
    drawBirthEffect,
    drawDeathIndicator,
    drawEnergyBar,
    drawPokerEffect,
    drawSelectionRing,
} from '../shared/topDownHud';
import { renderPlant, type PlantGenomeData } from '../../utils/plant';

/** Kinds whose heading is already conveyed by the sprite's own orientation. */
const HEADING_IMPLIED_BY_SPRITE = new Set(['fish', 'food', 'plant_nectar']);

export class TankTopDownRenderer implements Renderer {
    id = "tank-topdown";
    private lastNowMs: number = 0;
    private elapsedTime: number = 0;

    dispose() {
        // No heavy resources to dispose
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        this.lastNowMs = rc.nowMs;
        const state = frame.snapshot as SimulationUpdate;
        this.elapsedTime = state.snapshot?.elapsed_time ?? state.elapsed_time ?? rc.nowMs;
        const scene = buildTankScene(frame.snapshot);
        const options = frame.options ?? {};
        const showEffects = options.showEffects ?? true;

        // Clear and fill background
        ctx.fillStyle = "#1a1a2e"; // Dark blue-ish gray
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Calculate scale to fit world
        // Add some padding
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

        // Draw World Bounds
        ctx.strokeStyle = "#444";
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, scene.width, scene.height);

        // Draw grid
        ctx.strokeStyle = "#2a2a3e";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 0; x <= scene.width; x += 100) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, scene.height);
        }
        for (let y = 0; y <= scene.height; y += 100) {
            ctx.moveTo(0, y);
            ctx.lineTo(scene.width, y);
        }
        ctx.stroke();

        // Draw Entities
        // Pass 1: base entities (lowest layer)
        scene.entities.forEach(entity => {
            this.drawEntity(ctx, entity);
        });

        if (showEffects) {
            // Pass 2: birth effects (above entities)
            scene.entities.forEach(entity => {
                if (entity.birth_effect_timer && entity.birth_effect_timer > 0) {
                    drawBirthEffect(ctx, entity.x, entity.y, entity.birth_effect_timer);
                }
            });

            // Pass 3: energy bars (HUD)
            scene.entities.forEach(entity => {
                if (entity.energy !== undefined && entity.kind === 'fish') {
                    const barWidth = Math.max(entity.radius * 2, 20);
                    drawEnergyBar(
                        ctx,
                        entity.x - barWidth / 2,
                        entity.y - entity.radius - 8,
                        barWidth,
                        entity.energy
                    );
                }
            });

            // Pass 4: death indicators (HUD)
            scene.entities.forEach(entity => {
                const cause = entity.death_effect_state?.cause;
                if (cause) {
                    drawDeathIndicator(ctx, entity.x, entity.y - entity.radius - 16, cause);
                }
            });

            // Pass 5: poker arrows/bubbles (HUD)
            scene.entities.forEach(entity => {
                if (entity.poker_effect_state) {
                    drawPokerEffect(ctx, entity, scene.entities);
                }
            });
        }

        // Pass 6: selection ring + pursuit-module overlay (HUD, top-most)
        if (options.selectedEntityId !== undefined && options.selectedEntityId !== null) {
            const selected = scene.entities.find(e => e.id === options.selectedEntityId);
            if (selected) {
                drawSelectionRing(ctx, selected.x, selected.y, selected.radius);
                if (options.pursuitOverlay) drawPursuitOverlay(ctx, selected.x, selected.y, options.pursuitOverlay);
                if (options.targetMemoryOverlay) drawTargetMemoryOverlay(ctx, selected.x, selected.y, options.targetMemoryOverlay);
            }
        }

        ctx.restore();
    }

    /**
     * Base layer for one entity. Fish and crabs get gene-driven microbe avatars,
     * food reuses the side view's PNG sprites, plants are drawn as L-systems;
     * everything else falls back to a coloured disc.
     */
    private drawEntity(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        // Plants position from their base rather than their centre, so they draw
        // in world coordinates instead of a translated local frame.
        if (entity.kind === 'plant') {
            this.drawFractalPlant(ctx, entity);
            return;
        }

        ctx.save();
        ctx.translate(entity.x, entity.y);

        switch (entity.kind) {
            case 'fish':
                drawMicrobeAvatar(ctx, {
                    entityId: entity.id,
                    radius: entity.radius,
                    velX: entity.vel_x,
                    velY: entity.vel_y,
                    genome: entity.genome_data,
                    generation: entity.generation,
                    traitCues: true,
                });
                // Energy gain indicator from soccer play
                this.drawSoccerEffect(ctx, entity);
                break;
            case 'crab':
                drawMicrobePredator(ctx, {
                    entityId: entity.id,
                    radius: entity.radius,
                    velX: entity.vel_x,
                    velY: entity.vel_y,
                    timeMs: this.elapsedTime,
                    style: TANK_PREDATOR_STYLE,
                });
                break;
            case 'castle':
                drawMicrobeSubstrate(ctx, {
                    entityId: entity.id,
                    radius: entity.radius,
                    crystals: true,
                });
                break;
            case 'food':
            case 'plant_nectar':
                if (!this.drawFoodAvatar(ctx, entity)) {
                    this.drawCircleFallback(ctx, entity);
                }
                break;
            case 'ball':
                this.drawBall(ctx, entity);
                break;
            case 'goal_zone':
                this.drawGoalZone(ctx, entity);
                break;
            default:
                this.drawCircleFallback(ctx, entity);
        }

        // Heading whisker for sprites that are drawn unrotated. This used to be
        // emitted after the restore below, which pinned every whisker to the
        // world origin instead of its entity.
        if (entity.headingRad !== undefined && !HEADING_IMPLIED_BY_SPRITE.has(entity.kind)) {
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(Math.cos(entity.headingRad) * entity.radius, Math.sin(entity.headingRad) * entity.radius);
            ctx.stroke();
        }

        ctx.restore();
    }

    private drawFoodAvatar(ctx: CanvasRenderingContext2D, entity: TankEntity): boolean {
        return drawFoodSprite(ctx, {
            radius: entity.radius,
            foodType: entity.kind === 'plant_nectar' ? 'nectar' : entity.food_type,
            isLive: entity.kind === 'food' && entity.food_type === 'live',
            nowMs: this.lastNowMs,
            style: TANK_FOOD_SPRITE,
        });
    }

    private drawFractalPlant(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        const genome = entity.plant_genome as PlantGenomeData | undefined;
        if (!genome) {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawCircleFallback(ctx, entity);
            ctx.restore();
            return;
        }

        const sizeMultiplier = entity.size_multiplier ?? 1.0;
        const iterations = entity.iterations ?? 3;
        const nectarReady = entity.nectar_ready ?? false;

        // The snapshot positions plants by top-left; tankScene converted to center.
        // The plant renderer expects the root/base coordinate.
        const baseX = entity.x;
        const baseY = entity.y + entity.height / 2;

        // Shadow for plant (kept subtle in top-down)
        ctx.save();
        ctx.globalAlpha = 0.22;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.beginPath();
        ctx.ellipse(baseX, baseY + 6, entity.width * 0.35, entity.height * 0.10, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        renderPlant(
            ctx,
            entity.id,
            genome,
            baseX,
            baseY,
            sizeMultiplier,
            iterations,
            this.elapsedTime,
            nectarReady
        );
    }

    private drawCircleFallback(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        let color: string;
        switch (entity.kind) {
            case 'plant':
            case 'plant_nectar':
                color = "#27ae60";
                break;
            case 'crab':
                color = "#e74c3c";
                break;
            case 'castle':
                color = "#95a5a6";
                break;
            case 'food':
                color = "#2ecc71";
                break;
            default:
                color = hashColor(entity.kind);
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(0, 0, entity.radius, 0, Math.PI * 2);
        ctx.fill();
    }

    private drawBall(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        const radius = entity.radius || 10;

        // Ball shadow
        ctx.shadowColor = "rgba(0,0,0,0.5)";
        ctx.shadowBlur = 10;

        // Ball body
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        ctx.fill();

        // Pattern (soccer ball-ish)
        ctx.fillStyle = "#333333";
        ctx.beginPath();
        ctx.arc(0, 0, radius * 0.4, 0, Math.PI * 2);
        ctx.fill();

        // Hexagon/Pentagon hints
        for (let i = 0; i < 5; i++) {
            const angle = (Math.PI * 2 * i) / 5;
            const px = Math.cos(angle) * (radius * 0.65);
            const py = Math.sin(angle) * (radius * 0.65);
            ctx.beginPath();
            ctx.arc(px, py, radius * 0.25, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    private drawGoalZone(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        // Safe cast since we know backend sends team
        const team = entity.team;

        const radius = entity.radius || 30;
        const color = team === 'A' ? 'rgba(255, 100, 100, 0.3)' : 'rgba(100, 100, 255, 0.3)';
        const borderColor = team === 'A' ? '#ff4444' : '#4444ff';

        // Goal area
        ctx.fillStyle = color;
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);

        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        // Label
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 16px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("GOAL", 0, 0);
    }

    private drawSoccerEffect(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        const soccerState = entity.soccer_effect_state;
        if (!soccerState) return;

        const { type, amount, timer } = soccerState;

        // Calculate fade based on timer (60 frames max)
        // Keep opaque longer (until last 15 frames)
        const opacity = Math.min(1, timer / 15);
        const radius = entity.radius || 16;
        const yOffset = -radius - 15 - (60 - timer) * 0.8; // Float upward faster

        ctx.save();

        // Color based on type
        let color = '#00ff00'; // Green for kicks
        let fontSize = 16;

        if (type === 'goal') {
            color = '#ffdd00'; // Gold for goals
            fontSize = 24; // Much larger for goals
        } else if (type === 'progress') {
            color = '#88ff88'; // Light green for progress
        }

        ctx.globalAlpha = opacity;

        // Draw separate stroke and fill with better contrast settings
        ctx.font = `900 ${fontSize}px "Segoe UI", Roboto, Helvetica, Arial, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Use shadow for better visibility against any background
        ctx.shadowColor = 'black';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 1;

        const text = `+${Math.round(amount)}`;

        ctx.fillStyle = color;
        ctx.fillText(text, 0, yOffset);

        // Remove shadow for stroke to keep it crisp
        ctx.shadowColor = 'transparent';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1.5; // Thinner distinct stroke
        ctx.strokeText(text, 0, yOffset);

        ctx.restore();
    }
}
