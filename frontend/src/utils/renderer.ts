/**
 * Canvas rendering utilities for the simulation using actual game images
 * Enhanced with particle effects, shadows, and visual polish
 */

import type { EntityData } from '../types/simulation';
import { ImageLoader } from './ImageLoader';
import { getFishPath, getEyePosition, getPatternOpacity, type FishParams } from './fishTemplates';
import {
    prunePlantCaches as prunePlantCachesUtil,
    renderPlant as renderPlantUtil,
    renderPlantNectar as renderPlantNectarUtil,
    type PlantGenomeData,
} from './plant';

// Animation constants
const IMAGE_CHANGE_RATE = 500; // milliseconds

// Particle system constants
const PARTICLE_COUNT = 30;
const PARTICLE_SIZE_MIN = 1;
const PARTICLE_SIZE_RANGE = 3;
const PARTICLE_SPEED_MIN = 0.1;
const PARTICLE_SPEED_RANGE = 0.3;
const PARTICLE_OPACITY_MIN = 0.1;
const PARTICLE_OPACITY_RANGE = 0.4;
const PARTICLE_WOBBLE_INCREMENT = 0.02;
const PARTICLE_WOBBLE_AMPLITUDE = 0.5;
const PARTICLE_BOUNDS_MARGIN = 10;

// Background gradient stops
const GRADIENT_STOP_1 = 0.3;
const GRADIENT_STOP_2 = 0.6;

// Light ray constants
const LIGHT_RAY_COUNT = 4;
const CAUSTICS_SPEED = 0.0005;
const CAUSTICS_AMPLITUDE = 30;
const WOBBLE_SPEED = 0.0003;
const WOBBLE_AMPLITUDE = 15;

// Seabed constants
const SEABED_MIN_HEIGHT = 50;
const SEABED_HEIGHT_RATIO = 0.12;
const SEABED_TEXTURE_SPACING = 40;
const SEABED_ROCK_SIZE_MIN = 4;
const SEABED_ROCK_SIZE_RANGE = 8;
const SEABED_TEXTURE_OPACITY = 0.2;

// Particle highlight constants
const PARTICLE_HIGHLIGHT_OPACITY_MULTIPLIER = 0.6;
const PARTICLE_HIGHLIGHT_OFFSET_RATIO = 0.3;
const PARTICLE_HIGHLIGHT_SIZE_RATIO = 0.4;

interface TimeOfDayPalette {
    gradientTop: string;
    gradientMid: string;
    gradientDeep: string;
    overlayColor: string;
    overlayAlpha: number;
    rayColorMain: string;
    rayColorSecondary: string;
    rayOpacityMain: number;
    rayOpacitySecondary: number;
    seabedTop: string;
    seabedMid: string;
    seabedBottom: string;
    particleColor: string;
}

// Food type image mappings (matching core/constants.py)
const FOOD_TYPE_IMAGES: Record<string, string[]> = {
    algae: ['food_algae1.png', 'food_algae2.png'],
    protein: ['food_protein1.png', 'food_protein2.png'],
    energy: ['food_energy1.png', 'food_energy2.png'],
    rare: ['food_rare1.png', 'food_rare2.png'],
    nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
    live: ['food_live1.png', 'food_live2.png'], // Live food uses energy images but with special effects
};

// Default food images for unknown types
const DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

// Default fish images for fallback rendering
const DEFAULT_FISH_IMAGES = ['george1.png', 'george2.png'];

// Minimum horizontal velocity magnitude before we flip the fish sprite.
// This prevents tiny back-and-forth movement from rapidly changing direction.
const MIN_FLIP_SPEED = 0.5;

// Particle system for ambient water effects
interface Particle {
    x: number;
    y: number;
    size: number;
    speed: number;
    opacity: number;
    wobble: number;
}

export class Renderer {
    public ctx: CanvasRenderingContext2D;
    private particles: Particle[] = [];
    private initialized = false;
    private currentPalette: TimeOfDayPalette | null = null;
    private entityFacingLeft: Map<number, boolean> = new Map();
    // Track when poker effects started for each entity (for one-time animation)
    private pokerEffectStartTime: Map<number, number> = new Map();
    // Reusable offscreen canvas for tinting operations to avoid allocating
    // a new canvas per entity draw which can cause memory pressure.
    private _tintCanvas: HTMLCanvasElement | null = null;
    private _tintCtx: CanvasRenderingContext2D | null = null;
    // Cache for seabed rocks to prevent shimmering
    private seabedRocks: { x: number, y: number, size: number }[] = [];
    private seabedWidth: number = 0;

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
        // Drop references to offscreen canvas/context
        if (this._tintCtx) {
            // Clear canvas contents to free ImageBitmap backing if any
            try {
                this._tintCtx.canvas.width = 0;
                this._tintCtx = null;
            } catch {
                this._tintCtx = null;
            }
        }
        if (this._tintCanvas) {
            try {
                this._tintCanvas.width = 0;
            } catch {
                /* ignore */
            }
            this._tintCanvas = null;
        }

        // Clear maps that may grow over time
        this.entityFacingLeft.clear();
        this.pokerEffectStartTime.clear();
        this.pathCache.clear();
        this.seabedRocks = [];

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

    private initParticles() {
        if (this.initialized) return;
        this.initialized = true;

        // Create ambient floating particles (bubbles, debris)
        const width = this.ctx.canvas.width;
        const height = this.ctx.canvas.height;

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            this.particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                size: Math.random() * PARTICLE_SIZE_RANGE + PARTICLE_SIZE_MIN,
                speed: Math.random() * PARTICLE_SPEED_RANGE + PARTICLE_SPEED_MIN,
                opacity: Math.random() * PARTICLE_OPACITY_RANGE + PARTICLE_OPACITY_MIN,
                wobble: Math.random() * Math.PI * 2,
            });
        }
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

    private getTimeOfDayPalette(timeOfDay?: string): TimeOfDayPalette {
        const key = timeOfDay?.toLowerCase() ?? 'day';

        switch (key) {
            case 'night':
                return {
                    gradientTop: '#041124',
                    gradientMid: '#06233b',
                    gradientDeep: '#04192c',
                    overlayColor: '#021423',
                    overlayAlpha: 0.35,
                    rayColorMain: '#4dd5ff',
                    rayColorSecondary: '#6be0ff',
                    rayOpacityMain: 0.03,
                    rayOpacitySecondary: 0.06,
                    seabedTop: 'rgba(120, 95, 60, 0.15)',
                    seabedMid: 'rgba(135, 105, 65, 0.24)',
                    seabedBottom: 'rgba(100, 80, 55, 0.35)',
                    particleColor: '#7bb6d4',
                };
            case 'dawn':
                return {
                    gradientTop: '#16324f',
                    gradientMid: '#1f5674',
                    gradientDeep: '#1d3c5a',
                    overlayColor: '#f7c392',
                    overlayAlpha: 0.12,
                    rayColorMain: '#ffd27f',
                    rayColorSecondary: '#ffb070',
                    rayOpacityMain: 0.14,
                    rayOpacitySecondary: 0.2,
                    seabedTop: 'rgba(200, 165, 105, 0.18)',
                    seabedMid: 'rgba(210, 175, 115, 0.32)',
                    seabedBottom: 'rgba(165, 135, 90, 0.4)',
                    particleColor: '#b2d8ff',
                };
            case 'dusk':
                return {
                    gradientTop: '#0f2640',
                    gradientMid: '#1b3e63',
                    gradientDeep: '#16324f',
                    overlayColor: '#f0937c',
                    overlayAlpha: 0.16,
                    rayColorMain: '#ff9e7d',
                    rayColorSecondary: '#ffb38d',
                    rayOpacityMain: 0.12,
                    rayOpacitySecondary: 0.18,
                    seabedTop: 'rgba(195, 150, 95, 0.18)',
                    seabedMid: 'rgba(205, 160, 105, 0.3)',
                    seabedBottom: 'rgba(160, 125, 80, 0.4)',
                    particleColor: '#9ac8ec',
                };
            case 'day':
            default:
                return {
                    gradientTop: '#0a3350',
                    gradientMid: '#0d4a6b',
                    gradientDeep: '#0e2f46',
                    overlayColor: '#8ce0ff',
                    overlayAlpha: 0.08,
                    rayColorMain: '#5de5ff',
                    rayColorSecondary: '#7cf0ff',
                    rayOpacityMain: 0.12,
                    rayOpacitySecondary: 0.18,
                    seabedTop: 'rgba(180, 145, 85, 0.15)',
                    seabedMid: 'rgba(200, 160, 95, 0.3)',
                    seabedBottom: 'rgba(160, 130, 75, 0.4)',
                    particleColor: '#8dd5ef',
                };
        }
    }

    clear(width: number, height: number, timeOfDay?: string, showDecorative: boolean = true) {
        this.initParticles();
        const time = Date.now();
        const palette = this.getTimeOfDayPalette(timeOfDay);
        this.currentPalette = palette;

        // Enhanced ocean gradient with more depth
        const gradient = this.ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, palette.gradientTop);
        gradient.addColorStop(GRADIENT_STOP_1, palette.gradientMid);
        gradient.addColorStop(GRADIENT_STOP_2, palette.gradientDeep);
        gradient.addColorStop(1, palette.gradientDeep);
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, width, height);

        // Animated light rays with caustics effect
        if (showDecorative) {
            this.ctx.save();
            const causticsOffset = Math.sin(time * CAUSTICS_SPEED) * CAUSTICS_AMPLITUDE;
            for (let i = 0; i < LIGHT_RAY_COUNT; i += 1) {
                const baseX = (width / LIGHT_RAY_COUNT) * i + causticsOffset;
                const wobble = Math.sin(time * WOBBLE_SPEED + i) * WOBBLE_AMPLITUDE;

                // Main light ray
                this.ctx.globalAlpha = palette.rayOpacityMain;
                this.ctx.beginPath();
                this.ctx.moveTo(baseX + 60 + wobble, 0);
                this.ctx.lineTo(baseX + 180 + wobble, 0);
                this.ctx.lineTo(baseX + wobble, height);
                this.ctx.closePath();
                const rayGradient = this.ctx.createLinearGradient(baseX, 0, baseX, height);
                rayGradient.addColorStop(0, palette.rayColorMain);
                rayGradient.addColorStop(0.6, palette.rayColorMain);
                rayGradient.addColorStop(1, 'rgba(61, 213, 255, 0)');
                this.ctx.fillStyle = rayGradient;
                this.ctx.fill();

                // Secondary highlight for caustics
                this.ctx.globalAlpha = palette.rayOpacitySecondary;
                this.ctx.beginPath();
                this.ctx.moveTo(baseX + 80 + wobble * 1.5, 0);
                this.ctx.lineTo(baseX + 120 + wobble * 1.5, 0);
                this.ctx.lineTo(baseX + 40 + wobble, height * 0.4);
                this.ctx.closePath();
                this.ctx.fillStyle = palette.rayColorSecondary;
                this.ctx.fill();
            }
            this.ctx.restore();
        }

        // Apply subtle global overlay for time-of-day mood
        if (palette.overlayAlpha > 0) {
            this.ctx.save();
            this.ctx.globalAlpha = palette.overlayAlpha;
            this.ctx.fillStyle = palette.overlayColor;
            this.ctx.fillRect(0, 0, width, height);
            this.ctx.restore();
        }

        // Update and draw floating particles
        if (showDecorative) {
            this.updateParticles(width, height);
            this.drawParticles();
        }

        // Enhanced seabed with texture
        const seabedHeight = Math.max(SEABED_MIN_HEIGHT, height * SEABED_HEIGHT_RATIO);
        const seabedY = height - seabedHeight;

        // Seabed gradient with more depth
        const seabedGradient = this.ctx.createLinearGradient(0, seabedY, 0, height);
        seabedGradient.addColorStop(0, palette.seabedTop);
        seabedGradient.addColorStop(0.5, palette.seabedMid);
        seabedGradient.addColorStop(1, palette.seabedBottom);
        this.ctx.fillStyle = seabedGradient;
        this.ctx.fillRect(0, seabedY, width, seabedHeight);

        // Add seabed texture (rocks/pebbles) - Stabilized (cached)
        this.ctx.save();
        this.ctx.globalAlpha = SEABED_TEXTURE_OPACITY;

        // Re-generate if width changes or not initialized
        if (this.seabedRocks.length === 0 || this.seabedWidth !== width) {
            this.seabedRocks = [];
            this.seabedWidth = width;
            for (let x = 0; x < width; x += SEABED_TEXTURE_SPACING) {
                const rockSize = Math.random() * SEABED_ROCK_SIZE_RANGE + SEABED_ROCK_SIZE_MIN;
                const rockX = x + Math.random() * 30;
                const rockY = seabedY + seabedHeight * 0.6 + Math.random() * 15;
                this.seabedRocks.push({ x: rockX, y: rockY, size: rockSize });
            }
        }

        // Render cached rocks
        this.ctx.fillStyle = '#8b6f47';
        for (const rock of this.seabedRocks) {
            this.ctx.beginPath();
            this.ctx.ellipse(rock.x, rock.y, rock.size, rock.size * 0.7, 0, 0, Math.PI * 2);
            this.ctx.fill();
        }
        this.ctx.restore();
    }

    private updateParticles(width: number, height: number) {
        for (const particle of this.particles) {
            // Float upward
            particle.y -= particle.speed;

            // Wobble side to side
            particle.wobble += PARTICLE_WOBBLE_INCREMENT;
            particle.x += Math.sin(particle.wobble) * PARTICLE_WOBBLE_AMPLITUDE;

            // Reset if out of bounds
            if (particle.y < -PARTICLE_BOUNDS_MARGIN) {
                particle.y = height + PARTICLE_BOUNDS_MARGIN;
                particle.x = Math.random() * width;
            }
            if (particle.x < -PARTICLE_BOUNDS_MARGIN) particle.x = width + PARTICLE_BOUNDS_MARGIN;
            if (particle.x > width + PARTICLE_BOUNDS_MARGIN) particle.x = -PARTICLE_BOUNDS_MARGIN;
        }
    }

    private drawParticles() {
        this.ctx.save();
        const particleColor = this.currentPalette?.particleColor ?? '#8dd5ef';
        for (const particle of this.particles) {
            this.ctx.globalAlpha = particle.opacity;
            this.ctx.fillStyle = particleColor;

            // Draw bubble with highlight
            this.ctx.beginPath();
            this.ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            this.ctx.fill();

            // Highlight
            this.ctx.globalAlpha = particle.opacity * PARTICLE_HIGHLIGHT_OPACITY_MULTIPLIER;
            this.ctx.fillStyle = '#ffffff';
            this.ctx.beginPath();
            this.ctx.arc(
                particle.x - particle.size * PARTICLE_HIGHLIGHT_OFFSET_RATIO,
                particle.y - particle.size * PARTICLE_HIGHLIGHT_OFFSET_RATIO,
                particle.size * PARTICLE_HIGHLIGHT_SIZE_RATIO,
                0,
                Math.PI * 2
            );
            this.ctx.fill();
        }
        this.ctx.restore();
    }

    renderEntity(entity: EntityData, elapsedTime: number, allEntities?: EntityData[], showEffects: boolean = true) {
        switch (entity.type) {
            case 'fish':
                this.renderFish(entity, elapsedTime, allEntities, showEffects);
                break;
            case 'food':
                this.renderFood(entity, elapsedTime);
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
            case 'goalzone':
                this.renderGoalZone(entity);
                break;
        }
    }

    private renderBall(entity: EntityData) {
        const { ctx } = this;
        const radius = entity.radius || (entity.width ? entity.width / 2 : 10);

        ctx.save();
        ctx.translate(entity.x + radius, entity.y + radius); // Center

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

        // Rotation (if velocity available)
        // For now just static pattern
        for (let i = 0; i < 5; i++) {
            const angle = (Math.PI * 2 * i) / 5;
            const px = Math.cos(angle) * (radius * 0.7);
            const py = Math.sin(angle) * (radius * 0.7);
            ctx.beginPath();
            ctx.arc(px, py, radius * 0.25, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();
    }

    private renderGoalZone(entity: EntityData) {
        const { ctx } = this;
        const radius = entity.radius || 30;
        const color = (entity as any).team === 'A' ? 'rgba(255, 100, 100, 0.3)' : 'rgba(100, 100, 255, 0.3)';
        const borderColor = (entity as any).team === 'A' ? '#ff4444' : '#4444ff';

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
        const imageIndex = this.getAnimationFrame(elapsedTime, DEFAULT_FISH_IMAGES.length);
        const imageName = DEFAULT_FISH_IMAGES[imageIndex];
        const image = ImageLoader.getCachedImage(imageName);

        if (!image) return;

        const sizeModifier = genome_data?.size || 1.0;
        const scaledWidth = width * sizeModifier;
        const scaledHeight = height * sizeModifier;
        const flipHorizontal = this.getStableFacingLeft(fish.id, vel_x);

        this.drawShadow(x + scaledWidth / 2, y + scaledHeight, scaledWidth * 0.8, scaledHeight * 0.3);

        const energy = fish.energy !== undefined ? fish.energy : 100;
        const maxEnergy = fish.max_energy || 100;
        const reproductionThreshold = maxEnergy * 0.7; // 70% of max energy

        if (energy > reproductionThreshold) {
            this.drawGlow(x + scaledWidth / 2, y + scaledHeight / 2, scaledWidth * 0.7, energy, maxEnergy);
        }

        ctx.save();
        if (genome_data?.color_hue !== undefined) {
            this.drawImageWithColorTint(image, x, y, scaledWidth, scaledHeight, flipHorizontal, genome_data.color_hue);
        } else {
            this.drawImage(image, x, y, scaledWidth, scaledHeight, flipHorizontal);
        }
        ctx.restore();

        if (showEffects && fish.energy !== undefined) {
            this.drawEnhancedEnergyBar(x, y - 12, scaledWidth, fish.energy);
        }


        if (showEffects && fish.poker_effect_state) {
            this.renderPokerStatus(
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
            this.renderBirthEffect(x + scaledWidth / 2, y, fish.birth_effect_timer);
        }
    }

    private renderPokerStatus(
        entityId: number,
        x: number,
        y: number,
        state: { status: string; amount: number; target_id?: number; target_type?: string },
        allEntities?: EntityData[],
        entityX?: number,
        entityY?: number
    ) {
        const { ctx } = this;

        // If we have a target ID and it's a loss, draw an arrow FROM Loser (entity) TO Winner (target)
        // This visualizes energy flowing from the loser to the winner
        if (state.target_id !== undefined && state.target_type !== undefined && allEntities && entityX !== undefined && entityY !== undefined) {

            // Only draw for 'lost' status (Loser draws the arrow pointing to Winner)
            // This ensures we handle multiple losers correctly (one arrow per loser)
            // and avoids double-drawing (since we ignore 'won' status)
            if (state.status === 'lost') {
                const target = allEntities.find(e => e.id === state.target_id && e.type === state.target_type);

                if (target) {
                    // Calculate target center (Winner position)
                    const targetX = target.x + target.width / 2;
                    const targetY = target.y + target.height / 2;

                    // Track when this poker effect started for one-time animation
                    const now = Date.now();
                    if (!this.pokerEffectStartTime.has(entityId)) {
                        this.pokerEffectStartTime.set(entityId, now);
                    }
                    const startTime = this.pokerEffectStartTime.get(entityId)!;
                    const elapsed = now - startTime;
                    const animationDuration = 1000; // 1 second animation

                    // Calculate progress (0 to 1, clamped)
                    const progress = Math.min(elapsed / animationDuration, 1);

                    // If animation is complete, clear the tracking and don't render
                    if (progress >= 1) {
                        // Animation complete - do NOT delete here.
                        // We wait for the backend to clear the state, handled by pruneEntityFacingCache
                        return;
                    }


                    // Check distance - if too far, stop rendering to prevent "stretching" artifact
                    // Use 120px (1.5x max poker distance) as cutoff
                    const dx = targetX - entityX;
                    const dy = targetY - entityY;
                    const distSq = dx * dx + dy * dy;
                    if (distSq > 120 * 120) {
                        return;
                    }

                    // Arrow direction: Loser (entity) -> Winner (target)
                    // Energy flows from the loser to the winner
                    const startX = entityX!;  // Loser position (arrow origin)
                    const startY = entityY!;
                    const endX = targetX;     // Winner position (arrow destination)
                    const endY = targetY;

                    // Draw green energy arrow
                    ctx.save();

                    // Draw the main line (solid)
                    ctx.beginPath();
                    ctx.moveTo(startX, startY);
                    ctx.lineTo(endX, endY);

                    // Glow effect
                    ctx.shadowColor = '#4ade80';
                    ctx.shadowBlur = 10;
                    ctx.strokeStyle = '#4ade80';
                    ctx.lineWidth = 3;
                    ctx.stroke();



                    // Draw arrow head at Winner (end of arrow, where energy flows to)
                    const angle = Math.atan2(endY - startY, endX - startX);
                    const headLen = 15;

                    ctx.setLineDash([]);
                    ctx.fillStyle = '#4ade80';
                    ctx.beginPath();
                    ctx.moveTo(endX, endY);
                    ctx.lineTo(
                        endX - headLen * Math.cos(angle - Math.PI / 6),
                        endY - headLen * Math.sin(angle - Math.PI / 6)
                    );
                    ctx.lineTo(
                        endX - headLen * Math.cos(angle + Math.PI / 6),
                        endY - headLen * Math.sin(angle + Math.PI / 6)
                    );
                    ctx.closePath();
                    ctx.fill();

                    // Red dot on loser (start of arrow, where energy is lost from)
                    ctx.shadowBlur = 0;
                    ctx.fillStyle = '#ff0000';
                    ctx.beginPath();
                    ctx.arc(startX, startY, 5, 0, Math.PI * 2);
                    ctx.fill();

                    // Draw energy amount moving along the line (one-time animation)
                    const particleX = startX + (endX - startX) * progress;
                    const particleY = startY + (endY - startY) * progress;

                    ctx.fillStyle = '#ffffff';
                    ctx.font = 'bold 14px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    // Show amount (e.g. "120")
                    ctx.fillText(`${state.amount.toFixed(0)}`, particleX, particleY - 10);

                    ctx.restore();

                    // Return early as we've handled the visual
                    return;
                }
            }
        }

        // For 'won' and 'lost', we have returned above if target exists.
        // If we represent a tie, show the bubble.
        if (state.status !== 'tie') {
            return;
        }

        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = 'bold 20px Arial';

        // Draw background bubble for TIE
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.beginPath();
        const text = 'TIE';
        const bubbleWidth = 60;

        ctx.roundRect(x - bubbleWidth / 2, y - 15, bubbleWidth, 30, 15);
        ctx.fill();

        // Tie text
        ctx.fillStyle = '#fbbf24'; // Amber
        ctx.font = 'bold 18px Arial';
        ctx.fillText(text, x, y);

        ctx.restore();
    }

    private renderBirthEffect(x: number, y: number, timerRemaining: number) {
        const { ctx } = this;
        const maxDuration = 60; // Max frames (2 seconds at 30fps)
        const progress = 1 - (timerRemaining / maxDuration); // 0 to 1

        ctx.save();

        // === HEARTS === //
        // Float 3-5 hearts upward with fade out
        const heartCount = 4;
        for (let i = 0; i < heartCount; i++) {
            const heartProgress = Math.min(1, (progress * 1.5) - (i * 0.1)); // Stagger appearance
            if (heartProgress <= 0) continue;

            const heartX = x + (Math.sin((i + progress) * 2) * 15); // Wobble side to side
            const heartY = y - (heartProgress * 40) - (i * 8); // Float upward
            const heartSize = 8 + (i * 2);
            const alpha = (1 - heartProgress) * 0.9; // Fade out as they rise

            ctx.globalAlpha = alpha;
            ctx.fillStyle = '#ff69b4'; // Hot pink

            // Draw heart shape
            ctx.beginPath();
            const topCurveHeight = heartSize * 0.3;
            ctx.moveTo(heartX, heartY + topCurveHeight);
            // Left curve
            ctx.bezierCurveTo(
                heartX, heartY,
                heartX - heartSize / 2, heartY,
                heartX - heartSize / 2, heartY + topCurveHeight
            );
            ctx.bezierCurveTo(
                heartX - heartSize / 2, heartY + (heartSize + topCurveHeight) / 2,
                heartX, heartY + (heartSize + topCurveHeight) / 1.5,
                heartX, heartY + heartSize
            );
            // Right curve
            ctx.bezierCurveTo(
                heartX, heartY + (heartSize + topCurveHeight) / 1.5,
                heartX + heartSize / 2, heartY + (heartSize + topCurveHeight) / 2,
                heartX + heartSize / 2, heartY + topCurveHeight
            );
            ctx.bezierCurveTo(
                heartX + heartSize / 2, heartY,
                heartX, heartY,
                heartX, heartY + topCurveHeight
            );
            ctx.fill();
        }

        // === PARTICLE BURST === //
        // Explosion of colorful particles at the start
        if (progress < 0.6) { // Show particles only for first 60% of animation
            const particleCount = 12;
            const burstProgress = Math.min(1, progress / 0.6); // 0 to 1 over first 60%

            for (let i = 0; i < particleCount; i++) {
                const angle = (Math.PI * 2 * i) / particleCount;
                const distance = burstProgress * 35; // Expand outward
                const particleX = x + Math.cos(angle) * distance;
                const particleY = y + Math.sin(angle) * distance;
                const size = 4 * (1 - burstProgress); // Shrink as they expand
                const alpha = (1 - burstProgress) * 0.8; // Fade out

                // Use different colors for each particle
                const colors = ['#ff69b4', '#ffd700', '#87ceeb', '#98fb98', '#ff6b6b'];
                const particleColor = colors[i % colors.length];

                ctx.globalAlpha = alpha;
                ctx.fillStyle = particleColor;
                ctx.shadowColor = particleColor;
                ctx.shadowBlur = 5;
                ctx.beginPath();
                ctx.arc(particleX, particleY, size, 0, Math.PI * 2);
                ctx.fill();
            }
            ctx.shadowBlur = 0;
        }

        ctx.restore();
    }

    private renderDeathEffect(x: number, y: number, cause: string) {
        const { ctx } = this;

        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.font = 'bold 16px Arial';

        // Draw a semi-transparent background circle
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.beginPath();
        ctx.arc(x, y, 12, 0, Math.PI * 2);
        ctx.fill();

        // Draw icon based on death cause
        switch (cause) {
            case 'starvation':
                // Empty stomach icon (circle with line through)
                ctx.strokeStyle = '#ff6b6b';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(x - 4, y + 4);
                ctx.lineTo(x + 4, y - 4);
                ctx.stroke();
                break;

            case 'old_age':
                // Hourglass-like icon
                ctx.fillStyle = '#a0a0a0';
                ctx.beginPath();
                // Top triangle
                ctx.moveTo(x - 5, y - 6);
                ctx.lineTo(x + 5, y - 6);
                ctx.lineTo(x, y);
                ctx.closePath();
                ctx.fill();
                // Bottom triangle
                ctx.beginPath();
                ctx.moveTo(x - 5, y + 6);
                ctx.lineTo(x + 5, y + 6);
                ctx.lineTo(x, y);
                ctx.closePath();
                ctx.fill();
                break;

            case 'predation':
                // Claw marks icon
                ctx.strokeStyle = '#ff4444';
                ctx.lineWidth = 2;
                ctx.lineCap = 'round';
                // Three diagonal claw marks
                ctx.beginPath();
                ctx.moveTo(x - 5, y - 5);
                ctx.lineTo(x - 1, y + 5);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(x, y - 5);
                ctx.lineTo(x, y + 5);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(x + 5, y - 5);
                ctx.lineTo(x + 1, y + 5);
                ctx.stroke();
                break;

            case 'migration':
                // Arrow icon (leaving)
                ctx.fillStyle = '#4da6ff';
                ctx.beginPath();
                ctx.moveTo(x + 6, y);
                ctx.lineTo(x - 2, y - 5);
                ctx.lineTo(x - 2, y - 2);
                ctx.lineTo(x - 6, y - 2);
                ctx.lineTo(x - 6, y + 2);
                ctx.lineTo(x - 2, y + 2);
                ctx.lineTo(x - 2, y + 5);
                ctx.closePath();
                ctx.fill();
                break;

            default:
                // Question mark for unknown
                ctx.fillStyle = '#888888';
                ctx.fillText('?', x, y);
                break;
        }

        ctx.restore();
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
            this.drawGlow(x + scaledSize / 2, y + scaledSize / 2, scaledSize * 0.7, energy, maxEnergy);
        }

        ctx.save();

        // Position and flip
        ctx.translate(x + scaledSize / 2, y + scaledSize / 2);
        if (flipHorizontal) {
            ctx.scale(-1, 1);
        }
        ctx.translate(-scaledSize / 2, -scaledSize / 2);

        // Get base color from hue
        const baseColor = this.hslToRgbString(fishParams.color_hue, 0.7, 0.6);
        const patternColor = this.hslToRgbString(fishParams.color_hue, 0.8, 0.3);

        // Get SVG path for the fish body
        const fishPath = getFishPath(fishParams, scaledSize);

        // Draw fish body
        const path = this.getPath(fishPath);

        // Fill with base color
        ctx.fillStyle = baseColor;
        ctx.fill(path);

        // Stroke outline
        ctx.strokeStyle = this.hslToRgbString(fishParams.color_hue, 0.8, 0.4);
        ctx.lineWidth = 1.5;
        ctx.stroke(path);

        // Draw pattern if applicable
        const patternOpacity = getPatternOpacity(fishParams.pattern_intensity, 0.8);
        if (patternOpacity > 0) {
            this.drawFishPattern(fishParams, scaledSize, patternColor, patternOpacity);
        }

        // Draw eye
        const eyePos = getEyePosition(fishParams, scaledSize);
        const eyeRadius = 3 * fishParams.eye_size;

        // Eye white
        ctx.fillStyle = 'white';
        ctx.beginPath();
        ctx.arc(eyePos.x, eyePos.y, eyeRadius, 0, Math.PI * 2);
        ctx.fill();

        // Eye pupil
        ctx.fillStyle = 'black';
        ctx.beginPath();
        ctx.arc(eyePos.x, eyePos.y, eyeRadius * 0.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();

        // Draw enhanced energy bar
        if (showEffects && fish.energy !== undefined) {
            this.drawEnhancedEnergyBar(x, y - 12, scaledSize, fish.energy);
        }

        if (showEffects && fish.poker_effect_state) {
            this.renderPokerStatus(
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
            this.renderBirthEffect(x + scaledSize / 2, y, fish.birth_effect_timer);
        }

        // Death effect (cause indicator icon)
        if (fish.death_effect_state) {
            this.renderDeathEffect(x + scaledSize / 2, y - 10, fish.death_effect_state.cause);
        }
    }

    private drawFishPattern(params: FishParams, baseSize: number, color: string, opacity: number) {
        const { ctx } = this;
        const width = baseSize * params.body_aspect;
        const height = baseSize;
        if (opacity <= 0) {
            return;
        }

        ctx.save();
        ctx.globalAlpha = opacity;
        ctx.strokeStyle = color;
        ctx.fillStyle = color;

        // Clip to fish body shape to prevent pattern overflow
        const fishPathStr = getFishPath(params, baseSize);
        const fishPath = this.getPath(fishPathStr);
        ctx.clip(fishPath);

        switch (params.pattern_type) {
            case 0: // Stripes
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.moveTo(width * 0.3, height * 0.2);
                ctx.lineTo(width * 0.3, height * 0.8);
                ctx.moveTo(width * 0.5, height * 0.2);
                ctx.lineTo(width * 0.5, height * 0.8);
                ctx.moveTo(width * 0.7, height * 0.2);
                ctx.lineTo(width * 0.7, height * 0.8);
                ctx.stroke();
                break;

            case 1: // Spots
                [
                    { x: width * 0.4, y: height * 0.35 },
                    { x: width * 0.6, y: height * 0.4 },
                    { x: width * 0.5, y: height * 0.6 },
                    { x: width * 0.7, y: height * 0.65 },
                ].forEach(spot => {
                    ctx.beginPath();
                    ctx.arc(spot.x, spot.y, 3, 0, Math.PI * 2);
                    ctx.fill();
                });
                break;

            case 2: { // Solid (darker overlay)
                const path = this.getPath(getFishPath(params, baseSize));
                ctx.globalAlpha = opacity * 0.6; // Increased from 0.5 for better visibility
                ctx.fill(path);
                break;
            }

            case 3: { // Gradient
                const gradient = ctx.createLinearGradient(0, 0, width, 0);
                gradient.addColorStop(0, color);
                gradient.addColorStop(1, 'transparent');
                ctx.fillStyle = gradient;
                const gradPath = this.getPath(getFishPath(params, baseSize));
                ctx.fill(gradPath);
                break;
            }

            case 4: // Chevron (<<)
                ctx.lineWidth = 2;
                ctx.beginPath();
                // Draw 3 columns of chevrons
                [0.3, 0.5, 0.7].forEach(xRel => {
                    const xBase = width * xRel;
                    [0.25, 0.5, 0.75].forEach(yRel => {
                        const yBase = height * yRel;
                        const size = 4;
                        ctx.moveTo(xBase, yBase - size);
                        ctx.lineTo(xBase - size, yBase); // Point left
                        ctx.lineTo(xBase, yBase + size);
                    });
                });
                ctx.stroke();
                break;

            case 5: // Scales (overlapping arcs)
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                // Draw 3 rows of scale arcs
                [0.3, 0.5, 0.7].forEach(xRel => {
                    [0.25, 0.5, 0.75].forEach((yRel, row) => {
                        const xBase = width * xRel + ((row % 2) * width * 0.1); // Offset alternate rows
                        const yBase = height * yRel;
                        const radius = 5;
                        ctx.moveTo(xBase + radius, yBase);
                        ctx.arc(xBase, yBase, radius, 0, Math.PI); // Bottom half of circle
                    });
                });
                ctx.stroke();
                break;
        }

        ctx.restore();
    }

    private hslToRgbString(h: number, s: number, l: number): string {
        const rgb = this.hslToRgb(h, s, l);
        return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    }

    private drawShadow(x: number, y: number, width: number, height: number) {
        const { ctx } = this;
        ctx.save();
        ctx.globalAlpha = 0.15;
        ctx.fillStyle = '#000000';
        ctx.beginPath();
        ctx.ellipse(x, y, width / 2, height / 2, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    private drawGlow(x: number, y: number, size: number, energy: number, maxEnergy: number = 100) {
        const { ctx } = this;
        const threshold = maxEnergy * 0.7;
        const range = maxEnergy - threshold;
        const intensity = Math.max(0, Math.min(1, (energy - threshold) / range));

        ctx.save();
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
        gradient.addColorStop(0, `rgba(100, 220, 255, ${0.15 * intensity})`);
        gradient.addColorStop(0.5, `rgba(80, 200, 240, ${0.08 * intensity})`);
        gradient.addColorStop(1, 'rgba(60, 180, 220, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    private renderFood(food: EntityData, elapsedTime: number) {
        const { x, y, width, height, food_type } = food;

        // Get animation frames for this food type
        const imageFiles = food_type
            ? FOOD_TYPE_IMAGES[food_type] || DEFAULT_FOOD_IMAGES
            : DEFAULT_FOOD_IMAGES;
        const imageIndex = this.getAnimationFrame(elapsedTime, imageFiles.length);
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
        this.drawShadow(x + width / 2, y + height, scaledWidth * 0.6, scaledHeight * 0.2);

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
        this.drawImage(image, x + offsetX, y + offsetY, scaledWidth, scaledHeight, false);
    }

    // Unified plant rendering now uses renderFractalPlant. Legacy static plant renderer removed.

    private renderCrab(crab: EntityData, elapsedTime: number) {
        const { x, y, width, height, vel_x = 1, can_hunt = true } = crab;
        const { ctx } = this;

        // Get animation frames for crab
        const imageFiles = ['crab1.png', 'crab2.png'];
        const imageIndex = this.getAnimationFrame(elapsedTime, imageFiles.length);
        const imageName = imageFiles[imageIndex];
        const image = ImageLoader.getCachedImage(imageName);

        if (!image) return;

        // Draw shadow
        this.drawShadow(x + width / 2, y + height, width * 0.7, height * 0.25);

        // Flip based on velocity
        const flipHorizontal = vel_x < 0;

        // If crab is on cooldown (can't hunt), dim it slightly
        if (!can_hunt) {
            ctx.save();
            ctx.globalAlpha = 0.6;
        }

        this.drawImage(image, x, y, width, height, flipHorizontal);

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
        this.drawImage(image, x, y, width, height, false);
    }

    private drawImage(
        image: HTMLImageElement,
        x: number,
        y: number,
        width: number,
        height: number,
        flipHorizontal: boolean
    ) {
        const { ctx } = this;

        if (flipHorizontal) {
            ctx.save();
            ctx.translate(x + width, y);
            ctx.scale(-1, 1);
            ctx.drawImage(image, 0, 0, width, height);
            ctx.restore();
        } else {
            ctx.drawImage(image, x, y, width, height);
        }
    }

    private drawImageWithColorTint(
        image: HTMLImageElement,
        x: number,
        y: number,
        width: number,
        height: number,
        flipHorizontal: boolean,
        colorHue: number
    ) {
        const { ctx } = this;

        // Reuse a single offscreen canvas/context for tinting to avoid
        // allocating a new canvas on every draw call which can lead to
        // memory growth in some browsers.
        if (!this._tintCanvas) {
            this._tintCanvas = document.createElement('canvas');
        }
        if (!this._tintCtx) {
            this._tintCtx = this._tintCanvas.getContext('2d');
        }
        if (!this._tintCtx || !this._tintCanvas) return;

        const tempCtx = this._tintCtx;
        const tempCanvas = this._tintCanvas;

        // Resize offscreen canvas only when necessary to avoid frequent reallocs
        if (tempCanvas.width !== image.width || tempCanvas.height !== image.height) {
            tempCanvas.width = image.width;
            tempCanvas.height = image.height;
        }

        // Clear previous content
        tempCtx.clearRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Draw original image
        if (flipHorizontal) {
            tempCtx.save();
            tempCtx.translate(tempCanvas.width, 0);
            tempCtx.scale(-1, 1);
            tempCtx.drawImage(image, 0, 0);
            tempCtx.restore();
        } else {
            tempCtx.drawImage(image, 0, 0);
        }

        // Apply color tint using multiply blend mode
        const tintColor = this.hslToRgb(colorHue / 360, 0.7, 0.6);
        tempCtx.globalCompositeOperation = 'multiply';
        tempCtx.fillStyle = `rgb(${tintColor[0]}, ${tintColor[1]}, ${tintColor[2]})`;
        tempCtx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

        // Restore original alpha
        tempCtx.globalCompositeOperation = 'destination-in';
        if (flipHorizontal) {
            tempCtx.save();
            tempCtx.translate(tempCanvas.width, 0);
            tempCtx.scale(-1, 1);
            tempCtx.drawImage(image, 0, 0);
            tempCtx.restore();
        } else {
            tempCtx.drawImage(image, 0, 0);
        }

        // Draw tinted image to main canvas
        ctx.drawImage(tempCanvas, x, y, width, height);
    }

    private hslToRgb(h: number, s: number, l: number): [number, number, number] {
        let r: number, g: number, b: number;

        if (s === 0) {
            r = g = b = l;
        } else {
            const hue2rgb = (p: number, q: number, t: number) => {
                if (t < 0) t += 1;
                if (t > 1) t -= 1;
                if (t < 1 / 6) return p + (q - p) * 6 * t;
                if (t < 1 / 2) return q;
                if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
                return p;
            };

            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1 / 3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1 / 3);
        }

        return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
    }

    private drawEnhancedEnergyBar(x: number, y: number, width: number, energy: number) {
        const { ctx } = this;
        const barHeight = 6;
        const barWidth = width;
        const padding = 1;

        // Background with border
        ctx.save();
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        const radius = 2;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, radius);
        ctx.fill();
        ctx.stroke();

        // Energy bar with gradient
        let colorStart: string, colorEnd: string, glowColor: string;
        if (energy < 30) {
            colorStart = '#ff6b6b';
            colorEnd = '#ef4444';
            glowColor = 'rgba(239, 68, 68, 0.5)';
        } else if (energy < 60) {
            colorStart = '#ffd93d';
            colorEnd = '#fbbf24';
            glowColor = 'rgba(251, 191, 36, 0.5)';
        } else {
            colorStart = '#6bffb8';
            colorEnd = '#4ade80';
            glowColor = 'rgba(74, 222, 128, 0.5)';
        }

        const barFillWidth = (barWidth - padding * 2) * (energy / 100);

        if (barFillWidth > 0) {
            // Glow effect
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 8;

            // Gradient fill
            const gradient = ctx.createLinearGradient(x, y, x + barFillWidth, y);
            gradient.addColorStop(0, colorStart);
            gradient.addColorStop(1, colorEnd);
            ctx.fillStyle = gradient;

            ctx.beginPath();
            ctx.roundRect(x + padding, y + padding, barFillWidth, barHeight - padding * 2, radius - 1);
            ctx.fill();

            // Highlight on top
            ctx.shadowBlur = 0;
            ctx.globalAlpha = 0.4;
            const highlightGradient = ctx.createLinearGradient(x, y, x, y + barHeight / 2);
            highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
            highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
            ctx.fillStyle = highlightGradient;
            ctx.fillRect(x + padding, y + padding, barFillWidth, barHeight / 3);
        }

        ctx.restore();
    }

    private getAnimationFrame(elapsedTime: number, frameCount: number): number {
        if (frameCount <= 1) return 0;
        return Math.floor(elapsedTime / IMAGE_CHANGE_RATE) % frameCount;
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
        this.drawShadow(x + width / 2, baseY + 5, width * 0.8, height * 0.15);

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
            this.renderPokerStatus(
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
            const labelY = baseY + 5;

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
