/**
 * Canvas rendering utilities for the simulation using actual game images
 * Enhanced with particle effects, shadows, and visual polish
 *
 * The Renderer coordinates per-entity dispatch and owns the per-entity
 * caches; the heavier drawing routines live in focused modules:
 * - renderer_background.ts: water gradient, light rays, particles, seabed
 * - renderer_effects.ts: poker/birth/death overlays, energy bars, shadow/glow
 * - renderer_sprites.ts: image blits, hue tinting, HSL utils, frame timing
 * - renderer_svg_fish.ts: parametric fish body/pattern/eye drawing
 */

import type { EntityData } from '../types/simulation';
import { renderResourcePatch } from './renderResourcePatch';
import { ImageLoader } from './ImageLoader';
import { type FishParams } from './fishTemplates';
import {
    prunePlantCaches as prunePlantCachesUtil,
    renderPlant as renderPlantUtil,
    renderPlantNectar as renderPlantNectarUtil,
    type PlantGenomeData,
} from './plant';
import { drawSoccerBall } from './drawSoccerBall';
import { BackgroundRenderer } from './renderer_background';
import {
    drawBirthEffect,
    drawDeathEffect,
    drawEnhancedEnergyBar,
    drawGlow,
    drawPokerStatus,
    drawShadow,
} from './renderer_effects';
import { SpriteTinter, drawImage, getAnimationFrame } from './renderer_sprites';
import { drawSVGFishBody } from './renderer_svg_fish';

// Food type image mappings (matching core/constants.py)
const FOOD_TYPE_IMAGES: Record<string, string[]> = {
    algae: ['food_algae1.png', 'food_algae2.png'],
    protein: ['food_protein1.png', 'food_protein2.png'],
    energy: ['food_energy1.png', 'food_energy2.png'],
    rare: ['food_rare1.png', 'food_rare2.png'],
    nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
    live: ['food_live1.png', 'food_live2.png'], // Live food uses energy images but with special effects
};

const DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

const DEFAULT_FISH_IMAGES = ['george1.png', 'george2.png'];

// Minimum horizontal velocity magnitude before we flip the fish sprite.
// This prevents tiny back-and-forth movement from rapidly changing direction.
const MIN_FLIP_SPEED = 0.5;

export class Renderer {
    public ctx: CanvasRenderingContext2D;
    private background = new BackgroundRenderer();
    private tinter = new SpriteTinter();
    private entityFacingLeft: Map<number, boolean> = new Map();
    // Track when poker effects started for each entity (for one-time animation)
    private pokerEffectStartTime: Map<number, number> = new Map();

    // Track live instances to help detect leaked Renderer objects
    private static _instances = 0;

    // Cache for Path2D objects to avoid recreating them every frame
    private pathCache: Map<string, Path2D> = new Map();

    constructor(ctx: CanvasRenderingContext2D) {
        this.ctx = ctx;
        Renderer._instances += 1;
    }

    /** Number of live Renderer instances (for diagnostics) */
    static get instanceCount() {
        return Renderer._instances;
    }

    /** Dispose any large references so GC can reclaim memory when canvas unmounts */
    dispose() {
        this.tinter.dispose();
        this.background.reset();

        // Clear maps that may grow over time
        this.entityFacingLeft.clear();
        this.pokerEffectStartTime.clear();
        this.pathCache.clear();

        Renderer._instances = Math.max(0, Renderer._instances - 1);
    }

    /**
     * Get or create a cached Path2D for a given SVG path string
     */
    private getPath(pathString: string): Path2D {
        // Path2D is not available in some testing environments (JSDOM without canvas), fallback safely
        if (typeof Path2D === 'undefined') {
            return null as unknown as Path2D;
        }

        let path = this.pathCache.get(pathString);
        if (!path) {
            path = new Path2D(pathString);
            this.pathCache.set(pathString, path);
        }
        return path;
    }

    /**
     * Drop orientation cache entries for entities that no longer exist.
     * Prevents unbounded growth when the simulation spawns many short-lived
     * entities (e.g., food), which can otherwise exhaust browser memory over
     * time.
     */
    pruneEntityFacingCache(activeEntityIds: Iterable<number>, pokerActiveIds?: Set<number>) {
        const activeIds = new Set(activeEntityIds);
        for (const cachedId of this.entityFacingLeft.keys()) {
            if (!activeIds.has(cachedId)) {
                this.entityFacingLeft.delete(cachedId);
            }
        }
        // Also prune poker effect start times
        // We delete if:
        // 1. Entity no longer exists (removed from tank)
        // 2. Entity exists but no longer has a poker effect (pokerActiveIds provided and ID missing)
        for (const cachedId of this.pokerEffectStartTime.keys()) {
            if (!activeIds.has(cachedId)) {
                this.pokerEffectStartTime.delete(cachedId);
            } else if (pokerActiveIds && !pokerActiveIds.has(cachedId)) {
                this.pokerEffectStartTime.delete(cachedId);
            }
        }

        // Periodic maintenance of path cache (simple LRU-like safety)
        // If cache gets too big (e.g. many different fish sizes/params), clear it
        if (this.pathCache.size > 2000) {
            this.pathCache.clear();
        }
    }

    /**
     * Trim plant render caches for plants that are no longer in the scene.
     */
    prunePlantCaches(activePlantIds: Iterable<number>) {
        prunePlantCachesUtil(activePlantIds);
    }

    /**
     * Clear the Path2D cache to release memory.
     * Paths will be regenerated on demand.
     */
    clearPathCache() {
        this.pathCache.clear();
    }

    clear(width: number, height: number, timeOfDay?: string, showDecorative: boolean = true) {
        this.background.draw(this.ctx, width, height, timeOfDay, showDecorative);
    }

    renderEntity(entity: EntityData, elapsedTime: number, allEntities?: EntityData[], showEffects: boolean = true) {
        switch (entity.type) {
            case 'fish':
                this.renderFish(entity, elapsedTime, allEntities, showEffects);
                break;
            case 'food':
                this.renderFood(entity, elapsedTime);
                break;
            case 'resource_patch':
                renderResourcePatch(this.ctx, entity);
                break;
            case 'plant':
                this.renderPlant(entity, elapsedTime, allEntities, showEffects);
                break;
            case 'crab':
                this.renderCrab(entity, elapsedTime);
                break;
            case 'castle':
                this.renderCastle(entity);
                break;
            case 'plant_nectar':
                this.renderPlantNectar(entity, elapsedTime);
                break;
            case 'ball':
                this.renderBall(entity);
                break;
            case 'goal_zone':
                this.renderGoalZone(entity);
                break;
        }
    }

    private renderBall(entity: EntityData) {
        const { ctx } = this;
        // In side view, entity.x/y are top-left coordinates.
        // entity.width is diameter.
        // We need to calculate radius and center.
        const radius = entity.radius || (entity.width ? entity.width / 2 : 10);
        const cx = entity.x + radius;
        const cy = entity.y + radius;

        // Use velocity for simple rotation
        let rotation = 0;
        if (entity.vel_x || entity.vel_y) {
            rotation = (entity.x / radius);
        }

        drawSoccerBall(ctx, cx, cy, radius, rotation);
    }

    private renderGoalZone(entity: EntityData) {
        const { ctx } = this;
        const radius = entity.radius || 30;
        const team = entity.team;
        const isLeft = team === 'left';
        const color = isLeft ? 'rgba(255, 100, 100, 0.3)' : 'rgba(100, 100, 255, 0.3)';
        const borderColor = isLeft ? '#ff4444' : '#4444ff';

        ctx.save();
        ctx.translate(entity.x, entity.y); // Center (assuming backend sends center coords)

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

        ctx.restore();
    }

    private getStableFacingLeft(entityId: number, velX?: number): boolean {
        const previousFacing = this.entityFacingLeft.get(entityId) ?? false;

        if (velX === undefined || Math.abs(velX) < MIN_FLIP_SPEED) {
            return previousFacing;
        }

        const facingLeft = velX < 0;
        this.entityFacingLeft.set(entityId, facingLeft);
        return facingLeft;
    }

    private renderFish(fish: EntityData, elapsedTime: number, allEntities?: EntityData[], showEffects: boolean = true) {
        const { ctx } = this;
        const { x, y, width, height, vel_x = 1, genome_data } = fish;

        // Use SVG-based parametric fish rendering if genome_data is available
        if (genome_data && genome_data.template_id !== undefined) {
            this.renderSVGFish(fish, allEntities, showEffects);
            return;
        }

        // Fallback to image-based rendering
        const imageIndex = getAnimationFrame(elapsedTime, DEFAULT_FISH_IMAGES.length);
        const imageName = DEFAULT_FISH_IMAGES[imageIndex];
        const image = ImageLoader.getCachedImage(imageName);

        if (!image) return;

        const sizeModifier = genome_data?.size || 1.0;
        const scaledWidth = width * sizeModifier;
        const scaledHeight = height * sizeModifier;
        const flipHorizontal = this.getStableFacingLeft(fish.id, vel_x);

        drawShadow(ctx, x + scaledWidth / 2, y + scaledHeight, scaledWidth * 0.8, scaledHeight * 0.3);

        const energy = fish.energy !== undefined ? fish.energy : 100;
        const maxEnergy = fish.max_energy || 100;
        const reproductionThreshold = maxEnergy * 0.7; // 70% of max energy

        if (energy > reproductionThreshold) {
            drawGlow(ctx, x + scaledWidth / 2, y + scaledHeight / 2, scaledWidth * 0.7, energy, maxEnergy);
        }

        ctx.save();
        if (genome_data?.color_hue !== undefined) {
            this.tinter.drawImageWithColorTint(ctx, image, x, y, scaledWidth, scaledHeight, flipHorizontal, genome_data.color_hue);
        } else {
            drawImage(ctx, image, x, y, scaledWidth, scaledHeight, flipHorizontal);
        }
        ctx.restore();

        if (showEffects && fish.energy !== undefined) {
            drawEnhancedEnergyBar(ctx, x, y - 12, scaledWidth, fish.energy);
        }


        if (showEffects && fish.poker_effect_state) {
            drawPokerStatus(
                ctx,
                this.pokerEffectStartTime,
                fish.id,
                x + scaledWidth / 2,
                y - 25,
                fish.poker_effect_state,
                allEntities,
                x + scaledWidth / 2,
                y + scaledHeight / 2
            );
        }

        // Birth effect (hearts + particle burst)
        if (fish.birth_effect_timer && fish.birth_effect_timer > 0) {
            drawBirthEffect(ctx, x + scaledWidth / 2, y, fish.birth_effect_timer);
        }
    }

    private renderSVGFish(fish: EntityData, allEntities?: EntityData[], showEffects: boolean = true) {
        const { ctx } = this;
        const { x, y, width, height, vel_x = 1, genome_data } = fish;

        if (!genome_data) return;

        // Prepare fish parameters
        const fishParams: FishParams = {
            fin_size: genome_data.fin_size || 1.0,
            tail_size: genome_data.tail_size || 1.0,
            body_aspect: genome_data.body_aspect || 1.0,
            eye_size: genome_data.eye_size || 1.0,
            pattern_intensity: genome_data.pattern_intensity || 0.5,
            pattern_type: genome_data.pattern_type || 0,
            color_hue: genome_data.color_hue || 0.5,
            size: genome_data.size || 1.0,
            template_id: genome_data.template_id || 0,
        };

        // Calculate fish dimensions
        const baseSize = Math.max(width, height);
        const sizeModifier = fishParams.size;
        const scaledSize = baseSize * sizeModifier;

        // Flip based on velocity direction with stability for low speeds
        const flipHorizontal = this.getStableFacingLeft(fish.id, vel_x);

        // Shadow removed - now on plants instead

        // Draw glow effect based on energy
        const energy = fish.energy !== undefined ? fish.energy : 100;
        const maxEnergy = fish.max_energy || 100;
        const reproductionThreshold = maxEnergy * 0.7; // 70% of max energy

        if (energy > reproductionThreshold) {
            drawGlow(ctx, x + scaledSize / 2, y + scaledSize / 2, scaledSize * 0.7, energy, maxEnergy);
        }

        drawSVGFishBody(
            ctx,
            (pathString) => this.getPath(pathString),
            fishParams,
            x,
            y,
            scaledSize,
            flipHorizontal
        );

        // Draw enhanced energy bar
        if (showEffects && fish.energy !== undefined) {
            drawEnhancedEnergyBar(ctx, x, y - 12, scaledSize, fish.energy);
        }

        if (showEffects && fish.poker_effect_state) {
            drawPokerStatus(
                ctx,
                this.pokerEffectStartTime,
                fish.id,
                x + scaledSize / 2,
                y - 25,
                fish.poker_effect_state,
                allEntities,
                x + scaledSize / 2,
                y + scaledSize / 2
            );
        }

        // Birth effect (hearts + particle burst)
        if (fish.birth_effect_timer && fish.birth_effect_timer > 0) {
            drawBirthEffect(ctx, x + scaledSize / 2, y, fish.birth_effect_timer);
        }

        // Death effect (cause indicator icon)
        if (fish.death_effect_state) {
            drawDeathEffect(ctx, x + scaledSize / 2, y - 10, fish.death_effect_state.cause);
        }
    }

    private renderFood(food: EntityData, elapsedTime: number) {
        const { x, y, width, height, food_type } = food;

        // Get animation frames for this food type
        const imageFiles = food_type
            ? FOOD_TYPE_IMAGES[food_type] || DEFAULT_FOOD_IMAGES
            : DEFAULT_FOOD_IMAGES;
        const imageIndex = getAnimationFrame(elapsedTime, imageFiles.length);
        const imageName = imageFiles[imageIndex];
        const image = ImageLoader.getCachedImage(imageName);

        if (!image) return;

        // Make food images smaller (0.7x scale for normal food, 0.35x for live food)
        const isLiveFood = food_type === 'live';
        const foodScale = isLiveFood ? 0.35 : 0.7;
        const scaledWidth = width * foodScale;
        const scaledHeight = height * foodScale;
        // Center the smaller food at original position
        const offsetX = (width - scaledWidth) / 2;
        const offsetY = (height - scaledHeight) / 2;

        // Draw subtle shadow
        drawShadow(this.ctx, x + width / 2, y + height, scaledWidth * 0.6, scaledHeight * 0.2);

        // Live food gets special visual treatment
        if (isLiveFood) {
            // Pulsing animation for live food
            const pulse = Math.sin(elapsedTime * 0.005) * 0.3 + 0.7;
            const cx = x + width / 2;
            const cy = y + height / 2;
            const planktonSeed = (x + y) * 0.01;

            // Simple translucent body for zooplankton
            this.ctx.save();
            this.ctx.globalAlpha = 0.4 * pulse;
            const bodyGlow = this.ctx.createRadialGradient(cx, cy, 0, cx, cy, scaledWidth * 0.8);
            bodyGlow.addColorStop(0, '#aaffaa');
            bodyGlow.addColorStop(0.6, '#6ad86a');
            bodyGlow.addColorStop(1, 'rgba(106, 216, 106, 0)');
            this.ctx.fillStyle = bodyGlow;
            this.ctx.beginPath();
            this.ctx.arc(cx, cy, scaledWidth * 0.8, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.restore();

            // Simple appendages for zooplankton (4 appendages)
            this.ctx.save();
            this.ctx.lineWidth = 0.8;
            this.ctx.strokeStyle = `rgba(140, 220, 140, ${0.35 * pulse})`;
            for (let i = 0; i < 4; i++) {
                const angle = (Math.PI * 2 * i) / 4 + pulse * 0.3;
                const sway = Math.sin(elapsedTime * 0.003 + planktonSeed + i) * 2;
                const length = scaledWidth * 0.5;
                const startX = cx + Math.cos(angle) * (scaledWidth * 0.3);
                const startY = cy + Math.sin(angle) * (scaledWidth * 0.3);
                const endX = cx + Math.cos(angle) * length + sway;
                const endY = cy + Math.sin(angle) * length + sway * 0.5;

                this.ctx.beginPath();
                this.ctx.moveTo(startX, startY);
                this.ctx.lineTo(endX, endY);
                this.ctx.stroke();
            }
            this.ctx.restore();

            // Simple central highlight
            this.ctx.save();
            this.ctx.fillStyle = `rgba(255, 255, 255, ${0.4 * pulse})`;
            this.ctx.beginPath();
            this.ctx.arc(cx, cy, scaledWidth * 0.15, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.restore();
        } else {
            // Normal food gets subtle glow
            this.ctx.save();
            this.ctx.globalAlpha = 0.2;
            const gradient = this.ctx.createRadialGradient(
                x + width / 2,
                y + height / 2,
                0,
                x + width / 2,
                y + height / 2,
                scaledWidth * 0.6
            );
            gradient.addColorStop(0, '#ffeb3b');
            gradient.addColorStop(1, 'rgba(255, 235, 59, 0)');
            this.ctx.fillStyle = gradient;
            this.ctx.beginPath();
            this.ctx.arc(x + width / 2, y + height / 2, scaledWidth * 0.6, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.restore();
        }

        // Food images don't flip
        drawImage(this.ctx, image, x + offsetX, y + offsetY, scaledWidth, scaledHeight, false);
    }

    // Unified plant rendering now uses renderFractalPlant. Legacy static plant renderer removed.

    private renderCrab(crab: EntityData, elapsedTime: number) {
        const { x, y, width, height, vel_x = 1, can_hunt = true } = crab;
        const { ctx } = this;

        // Get animation frames for crab
        const imageFiles = ['crab1.png', 'crab2.png'];
        const imageIndex = getAnimationFrame(elapsedTime, imageFiles.length);
        const imageName = imageFiles[imageIndex];
        const image = ImageLoader.getCachedImage(imageName);

        if (!image) return;

        // Draw shadow
        drawShadow(ctx, x + width / 2, y + height, width * 0.7, height * 0.25);

        // Flip based on velocity
        const flipHorizontal = vel_x < 0;

        // If crab is on cooldown (can't hunt), dim it slightly
        if (!can_hunt) {
            ctx.save();
            ctx.globalAlpha = 0.6;
        }

        drawImage(ctx, image, x, y, width, height, flipHorizontal);

        if (!can_hunt) {
            ctx.restore();
        }
    }

    private renderCastle(castle: EntityData) {
        const { x, y, width, height } = castle;

        const imageName = 'castle-improved.png';
        const image = ImageLoader.getCachedImage(imageName);

        if (!image) return;

        // Castles don't flip or animate
        drawImage(this.ctx, image, x, y, width, height, false);
    }

    private renderPlant(plant: EntityData, elapsedTime: number, allEntities?: EntityData[], showEffects: boolean = true) {
        const { ctx } = this;
        const { x, y, width, height } = plant;

        // Get plant genome data
        const genome = plant.genome as PlantGenomeData | undefined;
        if (!genome) {
            // Fallback: draw a simple stem if no genome
            ctx.save();
            ctx.strokeStyle = '#2d5a2d';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(x, y + height);  // Start at bottom of plant
            ctx.lineTo(x, y);           // Draw up to top
            ctx.stroke();
            ctx.restore();
            return;
        }

        // Get plant properties
        const sizeMultiplier = plant.size_multiplier ?? 1.0;
        const iterations = plant.iterations ?? 3;
        const nectarReady = plant.nectar_ready ?? false;

        // Position plant at its root spot (base is at y + height)
        // The backend now ensures y = root_y - height, so y + height = root_y
        const baseY = y + height;

        // Draw shadow for fractal plant
        drawShadow(ctx, x + width / 2, baseY + 5, width * 0.8, height * 0.15);

        // Render using the unified plant utility
        renderPlantUtil(
            ctx,
            plant.id,
            genome,
            x + width / 2,  // Center X
            baseY,          // Base Y (bottom of plant)
            sizeMultiplier,
            iterations,
            elapsedTime,
            nectarReady
        );

        // Render poker effect if present
        if (showEffects && plant.poker_effect_state) {
            drawPokerStatus(
                ctx,
                this.pokerEffectStartTime,
                plant.id,
                x + width / 2,
                y - 25,
                plant.poker_effect_state,
                allEntities,
                x + width / 2,
                y + height / 2
            );
        }

        // Render strategy type label for baseline plants (hidden when HUD is hidden)
        if (showEffects && genome.strategy_type) {
            ctx.save();
            ctx.font = 'bold 9px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';

            // Get display-friendly label
            const strategyLabels: Record<string, string> = {
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
            const label = strategyLabels[genome.strategy_type] || genome.strategy_type;

            // Draw background pill
            const labelWidth = ctx.measureText(label).width + 8;
            const labelX = x + width / 2;
            const staggerOffset = (plant.id % 3) * 15;
            const labelY = baseY - 20 - staggerOffset;

            ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
            ctx.beginPath();
            ctx.roundRect(labelX - labelWidth / 2, labelY, labelWidth, 14, 3);
            ctx.fill();

            // Draw text
            ctx.fillStyle = '#fff';
            ctx.fillText(label, labelX, labelY + 2);
            ctx.restore();
        }

        // Plants no longer display an energy/health meter in the UI.
    }

    /**
     * Render plant nectar (collectible item).
     */
    private renderPlantNectar(nectar: EntityData, elapsedTime: number) {
        const {
            x, y, width, height,
            source_plant_id, source_plant_x, source_plant_y,
            floral_type, floral_petals, floral_layers,
            floral_spin, floral_hue, floral_saturation
        } = nectar;

        // Render using the plant nectar utility with sway and floral genome parameters
        renderPlantNectarUtil(
            this.ctx,
            x + width / 2,
            y + height / 2,
            width,
            height,
            elapsedTime,
            source_plant_id,
            source_plant_x,
            source_plant_y,
            {
                floral_type,
                floral_petals,
                floral_layers,
                floral_spin,
                floral_hue,
                floral_saturation
            }
        );
    }

    // Note: plant energy bars intentionally removed per product request.
}
