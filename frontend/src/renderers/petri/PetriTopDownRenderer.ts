/**
 * Petri mode top-down renderer.
 * Draws entities based on render_hint.sprite from the backend.
 *
 * The organisms themselves come from `renderers/shared/` — the same microbe,
 * predator, substrate and HUD code the tank top-down view uses. What is petri
 * specific and lives here: the circular dish geometry and clipping, the
 * perimeter remapping for plants, and the plant strategy labels.
 */

import { drawSoccerBall } from '../../utils/drawSoccerBall';
import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import type { EntityData, FishGenomeData } from '../../types/simulation';
import { idHueDegrees, seededRand } from '../shared/canvasPrimitives';
import { drawFoodSprite, PETRI_FOOD_SPRITE } from '../shared/foodAvatar';
import { drawMicrobeAvatar } from '../shared/microbeAvatar';
import {
    drawMicrobePredator,
    drawMicrobeSubstrate,
    PETRI_PREDATOR_STYLE,
} from '../shared/microbeScenery';
import {
    drawBirthEffect,
    drawDeathIndicator,
    drawEnergyBar,
    drawPokerEffect,
    drawSelectionRing,
    type PokerEffectState,
} from '../shared/topDownHud';
import { roundRectPath } from '../shared/canvasPrimitives';
import { renderPlant, prunePlantCaches } from '../../utils/plant';
import type { PlantGenomeData } from '../../utils/plant';
import { clearAvatarPathCache } from '../avatar_renderer';

/** Petri-specific render hint structure */
interface PetriDishGeometry {
    shape: 'circle';
    cx: number;
    cy: number;
    r: number;
}

/** Petri-specific render hint structure */
interface PetriRenderHint {
    style?: string;
    sprite?: 'microbe' | 'nutrient' | 'colony' | 'predator' | 'inert' | 'ball' | string;
    dish?: PetriDishGeometry;
}

/** Lightweight entity representation for Petri rendering */
interface PetriEntity {
    id: number;
    type: EntityData['type'];
    x: number;
    y: number;
    radius: number;
    sprite: string;
    hue: number; // Deterministic hue from entity ID
    vel_x?: number;
    vel_y?: number;
    energy?: number;
    food_type?: string;
    generation?: number;
    genome_data?: FishGenomeData;
    plant_genome_data?: PlantGenomeData;  // For plant fractal rendering
    perimeter_angle?: number;  // Angle from center for plants on perimeter
    death_effect_state?: { cause: string };
    poker_effect_state?: PokerEffectState;
    birth_effect_timer?: number;
    iterations?: number;
    size_multiplier?: number;
}

/** Scene data for Petri rendering */
interface PetriScene {
    width: number;
    height: number;
    entities: PetriEntity[];
    dish?: PetriDishGeometry;
}

/** Build Petri scene from snapshot */
type PetriSceneSnapshot = {
    snapshot?: {
        entities?: EntityData[];
        render_hint?: PetriRenderHint;
    };
    entities?: EntityData[];
    render_hint?: PetriRenderHint;
};

/** Display labels for the poker strategies plants can carry. */
const STRATEGY_LABELS: Record<string, string> = {
    'always_fold': 'FOLDER',
    'random': 'RANDOM',
    'loose_passive': 'PASSIVE',
    'tight_passive': 'ROCK',
    'tight_aggressive': 'TAG',
    'loose_aggressive': 'LAG',
    'balanced': 'BALANCED',
    'maniac': 'MANIAC',
    'gto_expert': 'GTO'
};

/** Fallback mapping used when a Tank snapshot is viewed through the Petri toggle. */
const DEFAULT_SPRITE_BY_TYPE: Record<string, string> = {
    fish: 'microbe',
    food: 'nutrient',
    plant: 'colony',
    plant_nectar: 'nutrient',
    crab: 'predator',
    castle: 'inert',
    ball: 'ball',
};

function buildPetriScene(snapshot: PetriSceneSnapshot): PetriScene {
    const entities: PetriEntity[] = [];

    const rawEntities = snapshot.snapshot?.entities ?? snapshot.entities;
    const dish = snapshot.snapshot?.render_hint?.dish ?? snapshot.render_hint?.dish;

    // Dish geometry for position remapping (fallback constants)
    const worldWidth = 1088;
    const worldHeight = 612;
    const rimMargin = 2;
    const dishCx = worldWidth / 2;  // center x (544)
    const dishCy = worldHeight / 2;  // center y (306)
    const dishR = (Math.min(worldWidth, worldHeight) / 2) - rimMargin;   // radius (296)

    if (rawEntities && Array.isArray(rawEntities)) {
        rawEntities.forEach((e: EntityData) => {
            const hint = e.render_hint as PetriRenderHint | undefined;
            const sprite = hint?.sprite ?? DEFAULT_SPRITE_BY_TYPE[e.type] ?? 'unknown';
            const radius = Math.max(e.width, e.height) / 2 * (e.type === 'plant' ? 0.35 : 0.5); // Scale down for Petri view

            let x = e.x + e.width / 2;
            let y = e.y + e.height / 2;
            let perimeterAngle: number | undefined = undefined;

            // Remap plants from bottom of tank to circle perimeter
            // BUT: If we have an authoritative dish from backend, TRUST server positions.
            // Only remap if we are faking Petri mode on a Tank snapshot (no dish hint).
            if (e.type === 'plant') {
                if (dish) {
                    // TRUST SERVER: Backend has already placed plants on the perimeter (radial_inward).
                    // We just need to calculate the angle for rotation/growth direction.
                    perimeterAngle = Math.atan2(y - dish.cy, x - dish.cx);
                } else {
                    // LEGACY/FALLBACK: Remap from bottom of rectangular tank to circle.
                    // Convert x position (0 to worldWidth) to angle around circle
                    const angle = (x / worldWidth) * Math.PI * 2 - Math.PI / 2;  // Start at top
                    x = dishCx + Math.cos(angle) * (dishR - 20);  // Slightly inside the edge
                    y = dishCy + Math.sin(angle) * (dishR - 20);
                    perimeterAngle = angle;
                }
            }

            entities.push({
                id: e.id,
                type: e.type,
                x,
                y,
                radius,
                sprite,
                hue: idHueDegrees(e.id),
                vel_x: e.vel_x,
                vel_y: e.vel_y,
                energy: e.energy,
                food_type: e.food_type,
                generation: e.generation,
                genome_data: e.genome_data,
                plant_genome_data: e.type === 'plant' ? e.genome : undefined,
                size_multiplier: e.size_multiplier,
                iterations: e.iterations,
                perimeter_angle: perimeterAngle,
                death_effect_state: e.death_effect_state,
                poker_effect_state: e.poker_effect_state,
                birth_effect_timer: e.birth_effect_timer,
            });
        });
    }

    // Default circular dish for Petri mode (centered in the world)
    // Used when switching via frontend toggle without backend petri data
    const defaultDish: PetriDishGeometry = {
        shape: 'circle',
        cx: worldWidth / 2,
        cy: worldHeight / 2,
        r: (Math.min(worldWidth, worldHeight) / 2) - rimMargin,  // 296
    };

    return {
        width: 1088,
        height: 612,
        entities,
        dish: dish ?? defaultDish,  // Use default if no dish geometry from backend
    };
}


export class PetriTopDownRenderer implements Renderer {
    id = "petri-topdown";
    private lastNowMs: number = 0;

    dispose() {
        // Clear avatar path cache to release memory
        clearAvatarPathCache();
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        this.lastNowMs = rc.nowMs;
        const scene = buildPetriScene(frame.snapshot);
        const options = frame.options ?? {};
        const showEffects = options.showEffects ?? true;

        // Prune plant caches for plants no longer in scene to prevent memory leaks
        prunePlantCaches(
            scene.entities.filter(e => e.sprite === 'colony').map(e => e.id)
        );

        // Dark petri dish background
        ctx.fillStyle = "#0d1117";
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

        // --- CLIPPED CONTENT BLOCK ---
        ctx.save();
        if (scene.dish && scene.dish.shape === 'circle') {
            const { cx, cy, r } = scene.dish;

            // Clip to circle so entities/grid outside the glass don't show
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.clip();

            // Draw dish background (faint glass tint)
            ctx.fillStyle = "rgba(20, 30, 40, 0.4)";
            ctx.fill();
        }

        // Subtle grid pattern (like microscope grid)
        ctx.strokeStyle = "rgba(48, 54, 61, 0.3)";
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        for (let x = 0; x <= scene.width; x += 50) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, scene.height);
        }
        for (let y = 0; y <= scene.height; y += 50) {
            ctx.moveTo(0, y);
            ctx.lineTo(scene.width, y);
        }
        ctx.stroke();

        // Pass 1: base entities (lowest layer)
        scene.entities.forEach(entity => {
            this.drawEntity(ctx, entity);
        });

        ctx.restore(); // End Clipping block

        // --- UNCLIPPED CONTENT BLOCK (HUD, Borders, Effects) ---

        this.drawDishRim(ctx, scene);

        if (showEffects) {
            // Pass 2: birth effects (above entities)
            scene.entities.forEach(entity => {
                if (entity.birth_effect_timer && entity.birth_effect_timer > 0) {
                    drawBirthEffect(ctx, entity.x, entity.y, entity.birth_effect_timer);
                }
            });

            // Pass 3: energy bars (HUD)
            scene.entities.forEach(entity => {
                if (entity.energy !== undefined && (entity.sprite === 'microbe' || entity.sprite === 'predator')) {
                    const barWidth = Math.max(entity.radius * 2, 20);
                    drawEnergyBar(
                        ctx,
                        entity.x - barWidth / 2,
                        entity.y - entity.radius - 10,
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

            // Pass 6: plant strategy labels (HUD)
            scene.entities.forEach(entity => {
                if (entity.sprite === 'colony' && entity.plant_genome_data?.strategy_type) {
                    this.drawStrategyLabel(ctx, entity);
                }
            });
        }

        // Pass 7: selection ring (HUD, top-most)
        if (options.selectedEntityId !== undefined && options.selectedEntityId !== null) {
            const selected = scene.entities.find(e => e.id === options.selectedEntityId);
            if (selected) {
                drawSelectionRing(ctx, selected.x, selected.y, selected.radius);
            }
        }

        ctx.restore();
    }

    /** Glass rim of the dish, drawn unclipped so the stroke isn't half-eaten. */
    private drawDishRim(ctx: CanvasRenderingContext2D, scene: PetriScene) {
        if (!scene.dish || scene.dish.shape !== 'circle') {
            // Fallback to rectangle
            ctx.strokeStyle = "#30363d";
            ctx.lineWidth = 3;
            ctx.strokeRect(0, 0, scene.width, scene.height);
            return;
        }

        const { cx, cy, r } = scene.dish;

        ctx.strokeStyle = "#404850";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.stroke();

        // Inner rim highlight
        ctx.strokeStyle = "rgba(100, 120, 140, 0.3)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, r - 3, 0, Math.PI * 2);
        ctx.stroke();
    }

    private drawStrategyLabel(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const genome = entity.plant_genome_data;
        if (!genome || !genome.strategy_type) return;

        ctx.save();
        ctx.font = 'bold 8px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        const label = STRATEGY_LABELS[genome.strategy_type] || genome.strategy_type;

        // Draw background pill
        const labelWidth = ctx.measureText(label).width + 6;
        const labelHeight = 11;

        // Position radially outward from the root (toward the dish edge)
        const angle = entity.perimeter_angle ?? 0;
        const offsetDist = 14;
        const lx = entity.x + Math.cos(angle) * offsetDist;
        const ly = entity.y + Math.sin(angle) * offsetDist;

        ctx.translate(lx, ly);

        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.beginPath();
        roundRectPath(ctx, -labelWidth / 2, -labelHeight / 2, labelWidth, labelHeight, 2);
        ctx.fill();

        // Draw text
        ctx.fillStyle = '#fff';
        ctx.fillText(label, 0, 0);

        ctx.restore();
    }

    private drawEntity(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        ctx.save();
        ctx.translate(entity.x, entity.y);

        switch (entity.sprite) {
            case 'microbe':
                drawMicrobeAvatar(ctx, {
                    entityId: entity.id,
                    radius: entity.radius,
                    velX: entity.vel_x,
                    velY: entity.vel_y,
                    genome: entity.genome_data,
                    generation: entity.generation,
                    traitCues: true,
                });
                break;
            case 'nutrient':
                this.drawNutrient(ctx, entity);
                break;
            case 'colony':
                this.drawColony(ctx, entity);
                break;
            case 'predator':
                drawMicrobePredator(ctx, {
                    entityId: entity.id,
                    radius: entity.radius,
                    velX: entity.vel_x,
                    velY: entity.vel_y,
                    timeMs: this.lastNowMs,
                    style: PETRI_PREDATOR_STYLE,
                });
                break;
            case 'inert':
                drawMicrobeSubstrate(ctx, {
                    entityId: entity.id,
                    radius: entity.radius,
                    crystals: false,
                });
                break;
            case 'ball':
                this.drawBall(ctx, entity);
                break;
            default:
                this.drawFallback(ctx, entity);
        }

        ctx.restore();
    }

    private drawBall(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        // Use shared soccer ball renderer
        // Ensure minimum perceptible size
        const radius = Math.max(entity.radius, 8);

        // Use rotation from velocity if available, or just spin slowly
        let rotation = 0;
        if (entity.vel_x || entity.vel_y) {
            rotation = (this.lastNowMs * 0.005) % (Math.PI * 2);
        }

        drawSoccerBall(ctx, 0, 0, radius, rotation);
    }

    /** Nutrient: reuses the tank's small food avatars (PNG) when available. */
    private drawNutrient(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const drawn = drawFoodSprite(ctx, {
            radius: entity.radius,
            foodType: entity.type === 'plant_nectar' ? 'nectar' : entity.food_type,
            isLive: entity.type === 'food' && entity.food_type === 'live',
            nowMs: this.lastNowMs,
            style: PETRI_FOOD_SPRITE,
        });
        if (drawn) return;

        // Fallback: scattered dots/grains (no image cache yet)
        const r = Math.max(entity.radius, 4);
        const hue = 120; // Greenish for nutrients

        const dotCount = Math.min(5, Math.max(2, Math.floor(r / 2)));
        ctx.fillStyle = `hsla(${hue}, 60%, 55%, 0.8)`;

        for (let i = 0; i < dotCount; i++) {
            const angle = (entity.id * 0.618 + i * 1.2) % (Math.PI * 2);
            const dist = (i === 0) ? 0 : r * 0.4 * ((entity.id + i) % 3 + 1) / 3;
            const dotSize = r * 0.3 * (1 - i * 0.1);
            ctx.beginPath();
            ctx.arc(Math.cos(angle) * dist, Math.sin(angle) * dist, Math.max(dotSize, 2), 0, Math.PI * 2);
            ctx.fill();
        }

        // Subtle glow
        ctx.fillStyle = `hsla(${hue}, 50%, 60%, 0.2)`;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.8, 0, Math.PI * 2);
        ctx.fill();
    }

    /** Colony: uses fractal plant rendering - plants grow inward from dish perimeter */
    private drawColony(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        // If we have plant genome data, use the full fractal plant renderer
        const genome = entity.plant_genome_data;

        if (genome) {
            // Rotate so plant grows inward from perimeter (pointing toward center)
            const angle = entity.perimeter_angle ?? 0;
            // Local "up" is negative Y (0, -1). We want to rotate to point Inward.
            // Edge Normal is 'angle'. Inward is 'angle + PI'.
            // To rotate (0, -1) to (cos(a+PI), sin(a+PI)):
            // We need rotation = angle - PI/2.
            const inwardRotation = angle - Math.PI / 2;

            ctx.save();
            ctx.rotate(inwardRotation);

            // Scale down for Petri view - much smaller than Tank side-view
            // Backend size_multiplier is usually 0.3 (small) to 1.5 (large)
            const petriScaleFactor = 0.35;
            const sizeMultiplier = (entity.size_multiplier ?? 1.0) * petriScaleFactor;
            const iterations = entity.iterations ?? 3;

            // renderPlant draws at (x, y) position, but we're already translated
            // So draw at origin and let the transform handle positioning
            renderPlant(ctx, entity.id, genome, 0, 0, sizeMultiplier, iterations, this.lastNowMs, false);

            ctx.restore();
            return;
        }

        // Fallback: simple algae blob if no plant genome
        const r = Math.max(entity.radius, 8) * 1.2;
        const rand = seededRand(entity.id * 12345);
        const hue = 100 + (entity.id % 60);

        ctx.save();

        // Simple organic blob
        ctx.beginPath();
        const points = 6;
        for (let i = 0; i <= points; i++) {
            const a = (i / points) * Math.PI * 2;
            const wobble = 0.8 + rand() * 0.3;
            const px = Math.cos(a) * r * wobble;
            const py = Math.sin(a) * r * wobble;
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();

        const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
        grad.addColorStop(0, `hsla(${hue}, 65%, 45%, 0.9)`);
        grad.addColorStop(1, `hsla(${hue + 10}, 45%, 25%, 0.7)`);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.restore();
    }

    /** Fallback: small neutral dot */
    private drawFallback(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 5);

        ctx.fillStyle = `hsla(${entity.hue}, 30%, 50%, 0.6)`;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = `hsla(${entity.hue}, 40%, 40%, 0.4)`;
        ctx.lineWidth = 1;
        ctx.stroke();
    }
}
