/**
 * Petri mode top-down renderer.
 * Draws entities based on render_hint.sprite from the backend.
 */

import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import type { EntityData } from '../../types/simulation';
import type { FishGenomeData } from '../../types/simulation';
import { ImageLoader } from '../../utils/ImageLoader';
import { renderPlant } from '../../utils/plant';
import type { PlantGenomeData } from '../../utils/plant';

// Food type image mappings (matching the main tank renderer / core/constants.py)
const PETRI_FOOD_TYPE_IMAGES: Record<string, string[]> = {
    algae: ['food_algae1.png', 'food_algae2.png'],
    protein: ['food_protein1.png', 'food_protein2.png'],
    energy: ['food_energy1.png', 'food_energy2.png'],
    rare: ['food_rare1.png', 'food_rare2.png'],
    nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
    live: ['food_live1.png', 'food_live2.png'],
};

const PETRI_DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

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
    sprite?: 'microbe' | 'nutrient' | 'colony' | 'predator' | 'inert' | string;
    dish?: PetriDishGeometry;
}

/** Poker effect state */
interface PokerEffectState {
    status: string;
    amount: number;
    target_id?: number;
    target_type?: string;
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
    genome_data?: FishGenomeData;
    plant_genome_data?: PlantGenomeData;  // For plant fractal rendering
    perimeter_angle?: number;  // Angle from center for plants on perimeter
    death_effect_state?: { cause: string };
    poker_effect_state?: PokerEffectState;
    birth_effect_timer?: number;
}

/** Scene data for Petri rendering */
interface PetriScene {
    width: number;
    height: number;
    entities: PetriEntity[];
    dish?: PetriDishGeometry;
}

/** Generate deterministic hue from entity ID */
function idToHue(id: number): number {
    // Simple hash to spread IDs across hue spectrum
    const hash = ((id * 2654435761) >>> 0) % 360;
    return hash;
}

/** Build Petri scene from snapshot */
function buildPetriScene(snapshot: any): PetriScene {
    const entities: PetriEntity[] = [];

    const rawEntities = snapshot.snapshot?.entities ?? snapshot.entities;
    const dish = snapshot.render_hint?.dish as PetriDishGeometry | undefined;

    // Dish geometry for position remapping (fallback constants)
    const dishCx = 544;  // center x
    const dishCy = 306;  // center y  
    const dishR = 380;   // radius
    const worldWidth = 1088;

    if (rawEntities && Array.isArray(rawEntities)) {
        rawEntities.forEach((e: EntityData) => {
            const hint = e.render_hint as PetriRenderHint | undefined;
            // Map entity types to petri sprites (fallback for frontend toggle)
            const defaultSpriteMap: Record<string, string> = {
                fish: 'microbe',
                food: 'nutrient',
                plant: 'colony',
                plant_nectar: 'nutrient',
                crab: 'predator',
                castle: 'inert',
            };
            const sprite = hint?.sprite ?? defaultSpriteMap[e.type] ?? 'unknown';
            const radius = Math.max(e.width, e.height) / 2 * 0.5;  // Scale down for Petri view

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
                hue: idToHue(e.id),
                vel_x: e.vel_x,
                vel_y: e.vel_y,
                energy: e.energy,
                food_type: e.food_type,
                genome_data: e.genome_data,
                plant_genome_data: e.type === 'plant' ? (e as any).genome as PlantGenomeData | undefined : undefined,
                perimeter_angle: perimeterAngle,
                death_effect_state: (e as any).death_effect_state as { cause: string } | undefined,
                poker_effect_state: e.poker_effect_state,
                birth_effect_timer: e.birth_effect_timer,
            });
        });
    }

    // Default circular dish for Petri mode (centered in the world)
    // Used when switching via frontend toggle without backend petri data
    const defaultDish: PetriDishGeometry = {
        shape: 'circle',
        cx: 544,  // Half of 1088
        cy: 306,  // Half of 612
        r: 380,   // Large enough to encompass rectangular bounds
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
        // No heavy resources to dispose
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        this.lastNowMs = rc.nowMs;
        const scene = buildPetriScene(frame.snapshot);
        const options = frame.options ?? {};
        const showEffects = options.showEffects ?? true;

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

        // Draw petri dish border (circular feel)
        if (scene.dish && scene.dish.shape === 'circle') {
            const { cx, cy, r } = scene.dish;

            // Clip to circle so entities outside don't show (optional but clean)
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.clip();

            // Draw dish background (faint glass tint)
            ctx.fillStyle = "rgba(20, 30, 40, 0.4)";
            ctx.fill();

            // Draw border
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
        } else {
            // Fallback to rectangle
            ctx.strokeStyle = "#30363d";
            ctx.lineWidth = 3;
            ctx.strokeRect(0, 0, scene.width, scene.height);
        }

        // Subtle grid pattern (like microscope grid)
        ctx.strokeStyle = "rgba(48, 54, 61, 0.3)";
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        // Only draw grid inside the circle if we have one
        if (scene.dish) {
            // Optimization: could limit loops to bounding box of circle
        }
        for (let x = 0; x <= scene.width; x += 50) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, scene.height);
        }
        for (let y = 0; y <= scene.height; y += 50) {
            ctx.moveTo(0, y);
            ctx.lineTo(scene.width, y);
        }
        ctx.stroke();

        // Draw entities
        // Pass 1: base entities (lowest layer)
        scene.entities.forEach(entity => {
            this.drawEntity(ctx, entity);
        });

        if (showEffects) {
            // Pass 2: birth effects (above entities)
            scene.entities.forEach(entity => {
                if (entity.birth_effect_timer && entity.birth_effect_timer > 0) {
                    this.drawBirthEffect(ctx, entity.x, entity.y, entity.birth_effect_timer);
                }
            });

            // Pass 3: energy bars (HUD)
            scene.entities.forEach(entity => {
                if (entity.energy !== undefined && (entity.sprite === 'microbe' || entity.sprite === 'predator')) {
                    const barWidth = Math.max(entity.radius * 2, 20);
                    this.drawEnhancedEnergyBar(
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
                    this.drawDeathIndicator(ctx, entity.x, entity.y - entity.radius - 16, cause);
                }
            });
        }

        // Pass 5: poker arrows/bubbles (HUD)
        if (showEffects) {
            scene.entities.forEach(entity => {
                if (entity.poker_effect_state) {
                    this.drawPokerEffect(ctx, entity, scene.entities);
                }
            });
        }

        // Pass 6: selection ring (HUD, top-most)
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

    private drawPokerEffect(ctx: CanvasRenderingContext2D, entity: PetriEntity, allEntities: PetriEntity[]) {
        const state = entity.poker_effect_state;
        if (!state) return;

        // Only draw for 'lost' status (Loser draws the arrow pointing to Winner)
        if (state.status === 'lost' && state.target_id !== undefined) {
            const target = allEntities.find(e => e.id === state.target_id);
            if (!target) return;

            // Check distance - if too far, skip rendering
            const dx = target.x - entity.x;
            const dy = target.y - entity.y;
            const distSq = dx * dx + dy * dy;
            if (distSq > 120 * 120) return;

            ctx.save();

            // Draw the main line (solid)
            ctx.beginPath();
            ctx.moveTo(entity.x, entity.y);
            ctx.lineTo(target.x, target.y);

            // Glow effect
            ctx.shadowColor = '#4ade80';
            ctx.shadowBlur = 10;
            ctx.strokeStyle = '#4ade80';
            ctx.lineWidth = 3;
            ctx.stroke();

            // Draw arrow head at Winner (end of arrow)
            const angle = Math.atan2(target.y - entity.y, target.x - entity.x);
            const headLen = 15;

            ctx.setLineDash([]);
            ctx.fillStyle = '#4ade80';
            ctx.beginPath();
            ctx.moveTo(target.x, target.y);
            ctx.lineTo(
                target.x - headLen * Math.cos(angle - Math.PI / 6),
                target.y - headLen * Math.sin(angle - Math.PI / 6)
            );
            ctx.lineTo(
                target.x - headLen * Math.cos(angle + Math.PI / 6),
                target.y - headLen * Math.sin(angle + Math.PI / 6)
            );
            ctx.closePath();
            ctx.fill();

            // Red dot on loser
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#ff0000';
            ctx.beginPath();
            ctx.arc(entity.x, entity.y, 5, 0, Math.PI * 2);
            ctx.fill();

            // Energy amount label
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const midX = (entity.x + target.x) / 2;
            const midY = (entity.y + target.y) / 2;
            ctx.fillText(`${state.amount.toFixed(0)}`, midX, midY - 8);

            ctx.restore();
        } else if (state.status === 'tie') {
            // Draw TIE bubble
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
            ctx.beginPath();
            if ((ctx as any).roundRect) {
                (ctx as any).roundRect(entity.x - 25, entity.y - entity.radius - 25, 50, 20, 10);
            } else {
                ctx.rect(entity.x - 25, entity.y - entity.radius - 25, 50, 20);
            }
            ctx.fill();
            ctx.fillStyle = '#fbbf24';
            ctx.font = 'bold 12px Arial';
            ctx.fillText('TIE', entity.x, entity.y - entity.radius - 15);
            ctx.restore();
        }
    }

    private drawBirthEffect(ctx: CanvasRenderingContext2D, x: number, y: number, timerRemaining: number) {
        const maxDuration = 60;
        const progress = 1 - (timerRemaining / maxDuration);

        ctx.save();

        // Particle burst
        if (progress < 0.6) {
            const particleCount = 8;
            const burstProgress = Math.min(1, progress / 0.6);

            for (let i = 0; i < particleCount; i++) {
                const angle = (Math.PI * 2 * i) / particleCount;
                const distance = burstProgress * 25;
                const particleX = x + Math.cos(angle) * distance;
                const particleY = y + Math.sin(angle) * distance;
                const size = 3 * (1 - burstProgress);
                const alpha = (1 - burstProgress) * 0.8;

                const colors = ['#ff69b4', '#ffd700', '#87ceeb', '#98fb98'];
                ctx.globalAlpha = alpha;
                ctx.fillStyle = colors[i % colors.length];
                ctx.beginPath();
                ctx.arc(particleX, particleY, size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        ctx.restore();
    }


    private drawEntity(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        ctx.save();
        ctx.translate(entity.x, entity.y);

        switch (entity.sprite) {
            case 'microbe':
                this.drawMicrobe(ctx, entity);
                break;
            case 'nutrient':
                this.drawNutrient(ctx, entity);
                break;
            case 'colony':
                this.drawColony(ctx, entity);
                break;
            case 'predator':
                this.drawPredator(ctx, entity);
                break;
            case 'inert':
                this.drawInert(ctx, entity);
                break;
            default:
                this.drawFallback(ctx, entity);
        }

        ctx.restore();
    }

    private clamp(value: number, min: number, max: number): number {
        return Math.max(min, Math.min(max, value));
    }

    private seededRand(seed: number): () => number {
        let t = seed >>> 0;
        return () => {
            t += 0x6D2B79F5;
            let x = t;
            x = Math.imul(x ^ (x >>> 15), x | 1);
            x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
            return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
        };
    }

    private genomeHueDegrees(entity: PetriEntity): number {
        const hue = entity.genome_data?.color_hue;
        if (typeof hue === 'number' && Number.isFinite(hue)) {
            return ((hue % 1) + 1) % 1 * 360;
        }
        return entity.hue;
    }

    private getAnimationFrame(nowMs: number, frameCount: number): number {
        if (frameCount <= 1) return 0;
        const IMAGE_CHANGE_RATE = 500;
        return Math.floor(nowMs / IMAGE_CHANGE_RATE) % frameCount;
    }

    private getFoodImageName(entity: PetriEntity): string | null {
        const foodType = entity.type === 'plant_nectar' ? 'nectar' : entity.food_type;
        const frames = (foodType && PETRI_FOOD_TYPE_IMAGES[foodType])
            ? PETRI_FOOD_TYPE_IMAGES[foodType]
            : PETRI_DEFAULT_FOOD_IMAGES;
        return frames[this.getAnimationFrame(this.lastNowMs, frames.length)] ?? null;
    }

    private drawWobblyBlob(ctx: CanvasRenderingContext2D, r: number, rand: () => number, wobble: number) {
        const steps = 18;
        const points: Array<{ x: number; y: number }> = [];

        for (let i = 0; i < steps; i++) {
            const a = (i / steps) * Math.PI * 2;
            const jitter = (rand() - 0.5) * 2 * wobble;
            const rr = r * (1 + jitter);
            points.push({ x: Math.cos(a) * rr, y: Math.sin(a) * rr });
        }

        ctx.beginPath();
        for (let i = 0; i < points.length; i++) {
            const p0 = points[i];
            const p1 = points[(i + 1) % points.length];
            const midX = (p0.x + p1.x) / 2;
            const midY = (p0.y + p1.y) / 2;
            if (i === 0) ctx.moveTo(midX, midY);
            else ctx.quadraticCurveTo(p0.x, p0.y, midX, midY);
        }
        ctx.closePath();
    }

    private drawCapsule(ctx: CanvasRenderingContext2D, r: number, aspect: number) {
        const rx = r * this.clamp(aspect, 0.7, 1.6);
        const ry = r * this.clamp(1 / aspect, 0.7, 1.6);
        const cap = Math.min(rx, ry);

        ctx.beginPath();
        ctx.moveTo(-rx + cap, -ry);
        ctx.lineTo(rx - cap, -ry);
        ctx.quadraticCurveTo(rx, -ry, rx, -ry + cap);
        ctx.lineTo(rx, ry - cap);
        ctx.quadraticCurveTo(rx, ry, rx - cap, ry);
        ctx.lineTo(-rx + cap, ry);
        ctx.quadraticCurveTo(-rx, ry, -rx, ry - cap);
        ctx.lineTo(-rx, -ry + cap);
        ctx.quadraticCurveTo(-rx, -ry, -rx + cap, -ry);
        ctx.closePath();
    }

    private movementAngle(entity: PetriEntity, rand: () => number): number {
        const vx = entity.vel_x ?? 0;
        const vy = entity.vel_y ?? 0;
        const magSq = vx * vx + vy * vy;
        if (magSq > 0.04) return Math.atan2(vy, vx);
        return (rand() * Math.PI * 2) - Math.PI;
    }

    /** Microbe: gene-driven microbe avatar (derived from fish physical genes). */
    private drawMicrobe(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const genome = entity.genome_data;
        const templateId = genome?.template_id ?? (entity.id % 6);
        const hueDeg = this.genomeHueDegrees(entity);

        const r = this.clamp(Math.max(entity.radius, 10), 10, 26);
        const finSize = genome?.fin_size ?? 1;
        const tailSize = genome?.tail_size ?? 1;
        const bodyAspect = genome?.body_aspect ?? 1;
        const eyeSize = genome?.eye_size ?? 1;
        const patternIntensity = this.clamp(genome?.pattern_intensity ?? 0, 0, 1);
        const patternType = genome?.pattern_type ?? 0;

        const seed = (
            (entity.id * 2654435761) ^
            (templateId * 374761393) ^
            (Math.floor(finSize * 1000) * 668265263) ^
            (Math.floor(tailSize * 1000) * 2246822519) ^
            (Math.floor(bodyAspect * 1000) * 3266489917) ^
            (Math.floor(eyeSize * 1000) * 234567891) ^
            (Math.floor(patternIntensity * 1000) * 198491317)
        ) >>> 0;
        const rand = this.seededRand(seed);
        const moveAngle = this.movementAngle(entity, rand);

        ctx.save();
        ctx.rotate(moveAngle);

        const wobble = 0.06 + patternIntensity * 0.08;

        // Shape (derived from template_id/body_aspect)
        const shapeKind = templateId % 6;
        if (shapeKind === 2 || shapeKind === 5) {
            this.drawCapsule(ctx, r * 0.9, bodyAspect);
        } else {
            this.drawWobblyBlob(ctx, r, rand, wobble);
        }

        // Outer membrane gradient
        const membrane = ctx.createRadialGradient(r * 0.25, -r * 0.25, r * 0.1, 0, 0, r * 1.1);
        membrane.addColorStop(0, `hsla(${hueDeg}, 70%, 62%, 0.95)`);
        membrane.addColorStop(0.6, `hsla(${hueDeg}, 60%, 48%, 0.88)`);
        membrane.addColorStop(1, `hsla(${(hueDeg + 20) % 360}, 55%, 34%, 0.85)`);
        ctx.fillStyle = membrane;
        ctx.fill();

        // Cytoplasm
        ctx.save();
        ctx.globalAlpha = 0.55;
        ctx.scale(0.78, 0.78);
        if (shapeKind === 2 || shapeKind === 5) {
            this.drawCapsule(ctx, r * 0.9, bodyAspect);
        } else {
            this.drawWobblyBlob(ctx, r, rand, wobble * 0.65);
        }
        ctx.fillStyle = `hsla(${(hueDeg + 10) % 360}, 45%, 60%, 0.7)`;
        ctx.fill();
        ctx.restore();

        // Nucleus (eye_size drives size)
        const nucleusR = r * this.clamp(0.18 + (eyeSize - 1) * 0.08, 0.14, 0.34);
        const nucleusX = (rand() - 0.5) * r * 0.35;
        const nucleusY = (rand() - 0.5) * r * 0.35;
        const nucleusGrad = ctx.createRadialGradient(nucleusX - nucleusR * 0.3, nucleusY - nucleusR * 0.3, 1, nucleusX, nucleusY, nucleusR);
        nucleusGrad.addColorStop(0, `hsla(${(hueDeg + 190) % 360}, 55%, 52%, 0.95)`);
        nucleusGrad.addColorStop(1, `hsla(${(hueDeg + 210) % 360}, 55%, 30%, 0.95)`);
        ctx.fillStyle = nucleusGrad;
        ctx.beginPath();
        ctx.arc(nucleusX, nucleusY, nucleusR, 0, Math.PI * 2);
        ctx.fill();

        // Pattern overlay (pattern_type/intensity mirrored from fish)
        ctx.save();
        ctx.globalAlpha = 0.25 + patternIntensity * 0.35;
        ctx.strokeStyle = `hsla(${(hueDeg + 60) % 360}, 70%, 70%, 0.8)`;
        ctx.fillStyle = `hsla(${(hueDeg + 60) % 360}, 70%, 70%, 0.6)`;

        if (patternType === 0) {
            const bands = 3 + Math.floor(patternIntensity * 4);
            ctx.lineWidth = Math.max(1, r * 0.06);
            for (let i = 0; i < bands; i++) {
                const t = (i + 1) / (bands + 1);
                const y = (t - 0.5) * r * 1.2;
                ctx.beginPath();
                ctx.moveTo(-r * 0.7, y);
                ctx.quadraticCurveTo(0, y + (rand() - 0.5) * r * 0.25, r * 0.7, y);
                ctx.stroke();
            }
        } else if (patternType === 1) {
            const vacuoles = 3 + Math.floor(patternIntensity * 8);
            for (let i = 0; i < vacuoles; i++) {
                const a = rand() * Math.PI * 2;
                const d = r * (0.1 + rand() * 0.55);
                const vx = Math.cos(a) * d;
                const vy = Math.sin(a) * d;
                const vr = r * (0.06 + rand() * 0.12) * (0.5 + patternIntensity);
                ctx.beginPath();
                ctx.arc(vx, vy, vr, 0, Math.PI * 2);
                ctx.fill();
            }
        } else if (patternType === 2) {
            ctx.globalAlpha *= 0.9;
            const overlay = ctx.createRadialGradient(0, 0, r * 0.1, 0, 0, r);
            overlay.addColorStop(0, `hsla(${(hueDeg + 30) % 360}, 80%, 70%, 0.0)`);
            overlay.addColorStop(1, `hsla(${(hueDeg + 30) % 360}, 80%, 25%, 0.65)`);
            ctx.fillStyle = overlay;
            ctx.beginPath();
            ctx.arc(0, 0, r * 0.95, 0, Math.PI * 2);
            ctx.fill();
        } else {
            const granules = 10 + Math.floor(patternIntensity * 24);
            ctx.globalAlpha *= 0.55;
            for (let i = 0; i < granules; i++) {
                const a = rand() * Math.PI * 2;
                const d = r * rand() * 0.8;
                const gx = Math.cos(a) * d;
                const gy = Math.sin(a) * d;
                ctx.fillStyle = `hsla(${(hueDeg + 120 + rand() * 40) % 360}, 55%, 65%, 0.45)`;
                ctx.beginPath();
                ctx.arc(gx, gy, r * (0.02 + rand() * 0.05), 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();

        // Cilia/flagella (fin_size/tail_size mirrored from fish)
        const ciliaCount = this.clamp(Math.floor(6 + finSize * 5), 6, 14);
        ctx.save();
        ctx.globalAlpha = 0.25 + patternIntensity * 0.25;
        ctx.strokeStyle = `hsla(${(hueDeg + 30) % 360}, 60%, 80%, 0.9)`;
        ctx.lineWidth = Math.max(1, r * 0.035);
        for (let i = 0; i < ciliaCount; i++) {
            const a = (i / ciliaCount) * Math.PI * 2 + (rand() - 0.5) * 0.25;
            const len = r * (0.18 + rand() * 0.22) * this.clamp(finSize, 0.6, 1.6);
            const sx = Math.cos(a) * (r * 0.92);
            const sy = Math.sin(a) * (r * 0.92);
            const ex = Math.cos(a) * (r * 0.92 + len);
            const ey = Math.sin(a) * (r * 0.92 + len);
            ctx.beginPath();
            ctx.moveTo(sx, sy);
            ctx.quadraticCurveTo((sx + ex) / 2, (sy + ey) / 2 + (rand() - 0.5) * r * 0.08, ex, ey);
            ctx.stroke();
        }
        ctx.restore();

        // Primary flagellum at the "back" (tail_size)
        ctx.save();
        ctx.globalAlpha = 0.5;
        ctx.strokeStyle = `hsla(${(hueDeg + 150) % 360}, 55%, 72%, 0.85)`;
        ctx.lineWidth = Math.max(1, r * 0.05);
        const tailLen = r * (0.9 + tailSize * 0.8);
        ctx.beginPath();
        ctx.moveTo(-r * 0.95, 0);
        ctx.bezierCurveTo(
            -r * 0.95 - tailLen * 0.25,
            r * (rand() - 0.5) * 0.8,
            -r * 0.95 - tailLen * 0.65,
            r * (rand() - 0.5) * 1.2,
            -r * 0.95 - tailLen,
            r * (rand() - 0.5) * 0.9
        );
        ctx.stroke();
        ctx.restore();

        // Membrane highlight
        ctx.strokeStyle = `hsla(${hueDeg}, 80%, 78%, 0.35)`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([]);
        if (shapeKind === 2 || shapeKind === 5) this.drawCapsule(ctx, r * 0.9, bodyAspect);
        else this.drawWobblyBlob(ctx, r, rand, wobble * 0.8);
        ctx.stroke();

        ctx.restore();
    }

    /** Nutrient: reuses the tank's small food avatars (PNG) when available. */
    private drawNutrient(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 4);
        const imageName = this.getFoodImageName(entity);
        const image = imageName ? ImageLoader.getCachedImage(imageName) : null;

        if (image) {
            const isLiveFood = (entity.type === 'food' && entity.food_type === 'live');
            const baseScale = isLiveFood ? 0.35 : 0.7;

            const pulse = isLiveFood ? (Math.sin(this.lastNowMs * 0.005) * 0.12 + 1) : 1;
            const size = this.clamp(r * 2 * baseScale * pulse, 6, 26);

            // Subtle glow to match tank "small avatar" feel
            ctx.save();
            ctx.globalAlpha = isLiveFood ? 0.22 : 0.16;
            const glowHue = isLiveFood ? 130 : 55;
            const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, size * 0.9);
            grad.addColorStop(0, `hsla(${glowHue}, 90%, 60%, 0.9)`);
            grad.addColorStop(1, `hsla(${glowHue}, 90%, 60%, 0)`);
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(0, 0, size * 0.9, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();

            ctx.save();
            ctx.globalAlpha = 0.95;
            ctx.drawImage(image, -size / 2, -size / 2, size, size);
            ctx.restore();
            return;
        }

        // Fallback: scattered dots/grains (no image cache yet)
        const hue = 120; // Greenish for nutrients

        // Draw as scattered dots
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

            // Scale down for Petri view
            const sizeMultiplier = 0.6;
            const iterations = 3;

            // renderPlant draws at (x, y) position, but we're already translated
            // So draw at origin and let the transform handle positioning
            renderPlant(ctx, entity.id, genome, 0, 0, sizeMultiplier, iterations, this.lastNowMs, false);

            ctx.restore();
        } else {
            // Fallback: simple algae blob if no plant genome
            const r = Math.max(entity.radius, 8) * 1.2;
            const rand = this.seededRand(entity.id * 12345);
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
    }

    /** Predator: angular/spiky shape */
    private drawPredator(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        // Concept: bacteriophage / protozoan predator hybrid (microbe-appropriate predator).
        const r = this.clamp(Math.max(entity.radius, 14), 14, 34);
        const rand = this.seededRand(((entity.id * 1103515245) ^ 0x9E3779B9) >>> 0);
        const angle = this.movementAngle(entity, rand);

        ctx.save();
        ctx.rotate(angle);

        const headR = r * 0.62;
        const headHue = 340;
        const menace = Math.sin(this.lastNowMs * 0.007 + entity.id * 0.01) * 0.5 + 0.5;
        const headGrad = ctx.createRadialGradient(headR * 0.2, -headR * 0.2, 1, 0, 0, headR);
        headGrad.addColorStop(0, `hsla(${headHue}, 90%, ${58 + menace * 6}%, 0.98)`);
        headGrad.addColorStop(0.7, `hsla(${(headHue + 5) % 360}, 85%, 34%, 0.98)`);
        headGrad.addColorStop(1, `hsla(${(headHue + 15) % 360}, 70%, 18%, 0.98)`);
        ctx.fillStyle = headGrad;

        const sides = 6;
        ctx.beginPath();
        for (let i = 0; i < sides; i++) {
            const a = (i / sides) * Math.PI * 2 - Math.PI / 2;
            const rr = headR * (i % 2 === 0 ? 1 : 0.92);
            const x = Math.cos(a) * rr;
            const y = Math.sin(a) * rr;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fill();

        // Spiky corona
        ctx.save();
        ctx.globalAlpha = 0.55;
        ctx.fillStyle = `hsla(${(headHue + 10) % 360}, 85%, 35%, 0.85)`;
        const spikes = 10;
        for (let i = 0; i < spikes; i++) {
            const a = (i / spikes) * Math.PI * 2 + menace * 0.2;
            const inner = headR * 0.95;
            const outer = headR * (1.25 + (rand() - 0.5) * 0.15);
            ctx.beginPath();
            ctx.moveTo(Math.cos(a) * inner, Math.sin(a) * inner);
            ctx.lineTo(Math.cos(a + 0.08) * outer, Math.sin(a + 0.08) * outer);
            ctx.lineTo(Math.cos(a - 0.08) * outer, Math.sin(a - 0.08) * outer);
            ctx.closePath();
            ctx.fill();
        }
        ctx.restore();

        // Eyes + jaw
        ctx.save();
        const eyeY = -headR * 0.10;
        const eyeSpread = headR * 0.28;
        const eyeLen = headR * (0.22 + menace * 0.08);
        ctx.strokeStyle = `rgba(255, 40, 80, ${0.65 + menace * 0.25})`;
        ctx.lineWidth = Math.max(1.5, r * 0.06);
        ctx.lineCap = 'round';
        ctx.shadowColor = 'rgba(255, 50, 90, 0.8)';
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.moveTo(-eyeSpread - eyeLen / 2, eyeY);
        ctx.lineTo(-eyeSpread + eyeLen / 2, eyeY + headR * 0.05);
        ctx.moveTo(eyeSpread - eyeLen / 2, eyeY);
        ctx.lineTo(eyeSpread + eyeLen / 2, eyeY + headR * 0.05);
        ctx.stroke();
        ctx.shadowBlur = 0;

        ctx.fillStyle = 'rgba(10, 10, 16, 0.55)';
        ctx.beginPath();
        ctx.moveTo(headR * 0.10, headR * 0.42);
        ctx.lineTo(-headR * 0.16, headR * 0.20);
        ctx.lineTo(headR * 0.32, headR * 0.20);
        ctx.closePath();
        ctx.fill();
        ctx.restore();

        // Tail core
        const tailLen = r * (0.9 + rand() * 0.35);
        const tailW = r * 0.18;
        const tailGrad = ctx.createLinearGradient(0, 0, -tailLen, 0);
        tailGrad.addColorStop(0, `hsla(${headHue}, 70%, 45%, 0.95)`);
        tailGrad.addColorStop(1, `hsla(${(headHue + 40) % 360}, 55%, 28%, 0.95)`);
        ctx.fillStyle = tailGrad;
        ctx.beginPath();
        if ((ctx as any).roundRect) {
            (ctx as any).roundRect(-headR * 0.95 - tailLen, -tailW / 2, tailLen, tailW, tailW / 2);
        } else {
            ctx.rect(-headR * 0.95 - tailLen, -tailW / 2, tailLen, tailW);
        }
        ctx.fill();

        // Tail fibers
        const fiberCount = 5 + Math.floor(rand() * 3);
        const pump = Math.sin(this.lastNowMs * 0.006 + entity.id * 0.01) * 0.35 + 0.65;
        ctx.strokeStyle = `hsla(${(headHue + 160) % 360}, 55%, 65%, 0.55)`;
        ctx.lineWidth = Math.max(1, r * 0.025);
        for (let i = 0; i < fiberCount; i++) {
            const t = (i + 1) / (fiberCount + 1);
            const baseX = -headR * 0.95 - tailLen * (0.45 + t * 0.55);
            const baseY = (t - 0.5) * tailW * 2.2;
            const wiggle = Math.sin(this.lastNowMs * 0.005 + entity.id * 0.03 + i) * (r * 0.10) * pump;
            const endX = baseX - r * (0.35 + rand() * 0.25);
            const endY = baseY + wiggle;
            ctx.beginPath();
            ctx.moveTo(baseX, baseY);
            ctx.quadraticCurveTo((baseX + endX) / 2, (baseY + endY) / 2 + wiggle * 0.6, endX, endY);
            ctx.stroke();
        }

        // Core dot
        ctx.fillStyle = `rgba(10, 10, 16, 0.45)`;
        ctx.beginPath();
        ctx.arc(headR * 0.1, headR * 0.15, headR * 0.22, 0, Math.PI * 2);
        ctx.fill();

        // Glow
        ctx.globalAlpha = 0.12;
        const glow = ctx.createRadialGradient(0, 0, headR * 0.2, 0, 0, r * 1.3);
        glow.addColorStop(0, `rgba(255, 40, 90, ${0.7 + menace * 0.25})`);
        glow.addColorStop(1, 'rgba(255, 90, 160, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(0, 0, r * 1.3, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    /** Inert: gray blob (for castles/obstacles) */
    private drawInert(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        // Concept: porous agar/mineral substrate with pits + growth rings.
        const r = this.clamp(Math.max(entity.radius, 18), 18, 60);
        const rand = this.seededRand(((entity.id * 2246822519) ^ 0xB5297A4D) >>> 0);
        const wobble = 0.10;

        // Base blob
        this.drawWobblyBlob(ctx, r, rand, wobble);
        const baseGrad = ctx.createRadialGradient(r * 0.2, -r * 0.2, 1, 0, 0, r * 1.1);
        baseGrad.addColorStop(0, 'rgba(150, 200, 210, 0.65)');
        baseGrad.addColorStop(0.6, 'rgba(95, 135, 150, 0.70)');
        baseGrad.addColorStop(1, 'rgba(45, 70, 85, 0.75)');
        ctx.fillStyle = baseGrad;
        ctx.fill();

        // Rim highlight
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.14)';
        ctx.lineWidth = Math.max(1, r * 0.04);
        this.drawWobblyBlob(ctx, r, rand, wobble * 0.75);
        ctx.stroke();

        // Pores (negative)
        const pitCount = this.clamp(Math.floor(6 + r * 0.12), 6, 14);
        ctx.save();
        ctx.globalCompositeOperation = 'destination-out';
        ctx.globalAlpha = 0.65;
        for (let i = 0; i < pitCount; i++) {
            const a = rand() * Math.PI * 2;
            const d = r * (0.10 + rand() * 0.75);
            const px = Math.cos(a) * d;
            const py = Math.sin(a) * d;
            const pr = r * (0.06 + rand() * 0.10);
            ctx.beginPath();
            ctx.arc(px, py, pr, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();

        // Growth rings
        ctx.save();
        ctx.globalAlpha = 0.20;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
        ctx.lineWidth = Math.max(1, r * 0.02);
        const rings = 3 + Math.floor(rand() * 3);
        for (let i = 0; i < rings; i++) {
            const rr = r * (0.35 + i * 0.18);
            ctx.beginPath();
            ctx.ellipse(0, 0, rr, rr * (0.82 + rand() * 0.2), rand() * 0.8, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.restore();
    }

    private drawDeathIndicator(ctx: CanvasRenderingContext2D, x: number, y: number, cause: string) {
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        ctx.fillStyle = 'rgba(0, 0, 0, 0.65)';
        ctx.beginPath();
        ctx.arc(x, y, 12, 0, Math.PI * 2);
        ctx.fill();

        switch (cause) {
            case 'starvation': {
                ctx.strokeStyle = '#60a5fa';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(x - 4, y + 4);
                ctx.lineTo(x + 4, y - 4);
                ctx.stroke();
                break;
            }
            case 'old_age': {
                ctx.fillStyle = '#a0a0a0';
                ctx.beginPath();
                ctx.moveTo(x - 5, y - 6);
                ctx.lineTo(x + 5, y - 6);
                ctx.lineTo(x, y);
                ctx.closePath();
                ctx.fill();
                ctx.beginPath();
                ctx.moveTo(x - 5, y + 6);
                ctx.lineTo(x + 5, y + 6);
                ctx.lineTo(x, y);
                ctx.closePath();
                ctx.fill();
                break;
            }
            case 'predation': {
                ctx.strokeStyle = '#ff4444';
                ctx.lineWidth = 2;
                ctx.lineCap = 'round';
                ctx.beginPath();
                ctx.moveTo(x - 5, y - 5);
                ctx.lineTo(x - 1, y + 5);
                ctx.moveTo(x, y - 5);
                ctx.lineTo(x, y + 5);
                ctx.moveTo(x + 5, y - 5);
                ctx.lineTo(x + 1, y + 5);
                ctx.stroke();
                break;
            }
            case 'migration': {
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
            }
            default: {
                ctx.fillStyle = '#888888';
                ctx.font = 'bold 14px Arial';
                ctx.fillText('?', x, y);
            }
        }

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

    private drawEnhancedEnergyBar(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, energy: number) {
        const barHeight = 4;
        const barWidth = width;
        const padding = 1;

        // Background with border
        ctx.save();
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        const radius = 2;
        ctx.beginPath();
        if ((ctx as any).roundRect) {
            (ctx as any).roundRect(x, y, barWidth, barHeight, radius);
        } else {
            ctx.rect(x, y, barWidth, barHeight);
        }
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

        const barFillWidth = Math.max(0, (barWidth - padding * 2) * (energy / 100));

        if (barFillWidth > 0) {
            // Glow effect
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 4;

            // Gradient fill
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
}
