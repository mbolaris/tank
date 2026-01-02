/**
 * Petri mode top-down renderer.
 * Draws entities based on render_hint.sprite from the backend.
 */

import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import type { EntityData } from '../../types/simulation';

/** Petri-specific render hint structure */
interface PetriRenderHint {
    style?: string;
    sprite?: 'microbe' | 'nutrient' | 'colony' | 'predator' | 'inert' | string;
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
    x: number;
    y: number;
    radius: number;
    sprite: string;
    hue: number; // Deterministic hue from entity ID
    energy?: number;
    poker_effect_state?: PokerEffectState;
    birth_effect_timer?: number;
}

/** Scene data for Petri rendering */
interface PetriScene {
    width: number;
    height: number;
    entities: PetriEntity[];
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
    if (rawEntities && Array.isArray(rawEntities)) {
        rawEntities.forEach((e: EntityData) => {
            const hint = e.render_hint as PetriRenderHint | undefined;
            const sprite = hint?.sprite ?? 'unknown';
            const radius = Math.max(e.width, e.height) / 2;

            entities.push({
                id: e.id,
                x: e.x,
                y: e.y,
                radius,
                sprite,
                hue: idToHue(e.id),
                energy: e.energy,
                poker_effect_state: e.poker_effect_state,
                birth_effect_timer: e.birth_effect_timer,
            });
        });
    }

    return {
        width: 1088,
        height: 612,
        entities,
    };
}


export class PetriTopDownRenderer implements Renderer {
    id = "petri-topdown";

    dispose() {
        // No heavy resources to dispose
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
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
        ctx.strokeStyle = "#30363d";
        ctx.lineWidth = 3;
        ctx.strokeRect(0, 0, scene.width, scene.height);

        // Subtle grid pattern (like microscope grid)
        ctx.strokeStyle = "rgba(48, 54, 61, 0.5)";
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

        // Draw entities
        scene.entities.forEach(entity => {
            this.drawEntity(ctx, entity);

            // Draw HUD elements (energy bars) if enabled
            if (showEffects && entity.energy !== undefined && (entity.sprite === 'microbe' || entity.sprite === 'colony' || entity.sprite === 'predator')) {
                const barWidth = Math.max(entity.radius * 2, 20);
                this.drawEnhancedEnergyBar(
                    ctx,
                    entity.x - barWidth / 2,
                    entity.y - entity.radius - 10,
                    barWidth,
                    entity.energy
                );
            }

            // Draw selection ring
            if (options.selectedEntityId === entity.id) {
                ctx.save();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.arc(entity.x, entity.y, entity.radius + 4, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }

            // Draw poker effects (arrows from loser to winner)
            if (showEffects && entity.poker_effect_state) {
                this.drawPokerEffect(ctx, entity, scene.entities);
            }

            // Draw birth effect
            if (showEffects && entity.birth_effect_timer && entity.birth_effect_timer > 0) {
                this.drawBirthEffect(ctx, entity.x, entity.y, entity.birth_effect_timer);
            }
        });

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

    /** Microbe: circle with internal organelle-like details */
    private drawMicrobe(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 8);
        const hue = entity.hue;

        // Outer membrane
        ctx.fillStyle = `hsla(${hue}, 60%, 50%, 0.8)`;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();

        // Inner cytoplasm
        ctx.fillStyle = `hsla(${hue}, 40%, 60%, 0.6)`;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.7, 0, Math.PI * 2);
        ctx.fill();

        // Nucleus (deterministic position from ID)
        const nucleusOffsetX = ((entity.id % 7) - 3) * (r * 0.1);
        const nucleusOffsetY = ((entity.id % 5) - 2) * (r * 0.1);
        ctx.fillStyle = `hsla(${(hue + 180) % 360}, 50%, 40%, 0.9)`;
        ctx.beginPath();
        ctx.arc(nucleusOffsetX, nucleusOffsetY, r * 0.3, 0, Math.PI * 2);
        ctx.fill();

        // Small organelles (vacuoles)
        ctx.fillStyle = `hsla(${(hue + 60) % 360}, 40%, 70%, 0.5)`;
        const organelleCount = (entity.id % 3) + 1;
        for (let i = 0; i < organelleCount; i++) {
            const angle = (entity.id * 1.618 + i * 2.1) % (Math.PI * 2);
            const dist = r * 0.4;
            ctx.beginPath();
            ctx.arc(Math.cos(angle) * dist, Math.sin(angle) * dist, r * 0.12, 0, Math.PI * 2);
            ctx.fill();
        }

        // Membrane highlight
        ctx.strokeStyle = `hsla(${hue}, 70%, 70%, 0.4)`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.stroke();
    }

    /** Nutrient: small scattered dots/grains */
    private drawNutrient(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 4);
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

    /** Colony: clustered circles (for plants) */
    private drawColony(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 10);
        const hue = 140; // Green for colonies

        // Main colony body
        ctx.fillStyle = `hsla(${hue}, 50%, 40%, 0.7)`;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.6, 0, Math.PI * 2);
        ctx.fill();

        // Surrounding cells
        const cellCount = (entity.id % 4) + 4;
        for (let i = 0; i < cellCount; i++) {
            const angle = (i / cellCount) * Math.PI * 2 + (entity.id * 0.3);
            const dist = r * 0.5;
            const cellR = r * 0.35 + ((entity.id + i) % 3) * 2;

            ctx.fillStyle = `hsla(${hue + (i * 10) % 40}, 45%, 45%, 0.6)`;
            ctx.beginPath();
            ctx.arc(Math.cos(angle) * dist, Math.sin(angle) * dist, cellR, 0, Math.PI * 2);
            ctx.fill();
        }

        // Border
        ctx.strokeStyle = `hsla(${hue}, 40%, 50%, 0.5)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.stroke();
    }

    /** Predator: angular/spiky shape */
    private drawPredator(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 10);
        const hue = 0; // Red for predators

        // Draw spiky shape
        ctx.fillStyle = `hsla(${hue}, 70%, 50%, 0.8)`;
        ctx.beginPath();
        const spikes = 6;
        for (let i = 0; i < spikes * 2; i++) {
            const angle = (i / (spikes * 2)) * Math.PI * 2 - Math.PI / 2;
            const spikeR = (i % 2 === 0) ? r : r * 0.5;
            const x = Math.cos(angle) * spikeR;
            const y = Math.sin(angle) * spikeR;
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.closePath();
        ctx.fill();

        // Inner core
        ctx.fillStyle = `hsla(${hue}, 60%, 35%, 0.9)`;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.35, 0, Math.PI * 2);
        ctx.fill();

        // Eyes (two dots)
        ctx.fillStyle = "#fff";
        ctx.beginPath();
        ctx.arc(-r * 0.15, -r * 0.1, r * 0.08, 0, Math.PI * 2);
        ctx.arc(r * 0.15, -r * 0.1, r * 0.08, 0, Math.PI * 2);
        ctx.fill();
    }

    /** Inert: gray blob (for castles/obstacles) */
    private drawInert(ctx: CanvasRenderingContext2D, entity: PetriEntity) {
        const r = Math.max(entity.radius, 12);

        // Gray stone-like appearance
        ctx.fillStyle = "rgba(100, 100, 105, 0.7)";
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.fill();

        // Texture lines
        ctx.strokeStyle = "rgba(60, 60, 65, 0.5)";
        ctx.lineWidth = 1;
        for (let i = 0; i < 3; i++) {
            const angle = (entity.id + i * 1.2) % (Math.PI * 2);
            ctx.beginPath();
            ctx.moveTo(Math.cos(angle) * r * 0.3, Math.sin(angle) * r * 0.3);
            ctx.lineTo(Math.cos(angle) * r * 0.8, Math.sin(angle) * r * 0.8);
            ctx.stroke();
        }
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
