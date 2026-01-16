
import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import { buildTankScene, type TankEntity } from './tankScene';
import { ImageLoader } from '../../utils/ImageLoader';
import { renderPlant, type PlantGenomeData } from '../../utils/plant';

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
        this.elapsedTime = ((frame.snapshot as any)?.snapshot?.elapsed_time ?? (frame.snapshot as any)?.elapsed_time ?? rc.nowMs) as number;
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
                    this.drawBirthEffect(ctx, entity.x, entity.y, entity.birth_effect_timer);
                }
            });

            // Pass 3: energy bars (HUD)
            scene.entities.forEach(entity => {
                if (entity.energy !== undefined && entity.kind === 'fish') {
                    const barWidth = Math.max(entity.radius * 2, 20);
                    this.drawEnhancedEnergyBar(
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

    private drawPokerEffect(ctx: CanvasRenderingContext2D, entity: TankEntity, allEntities: TankEntity[]) {
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


    private drawEntity(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        // Upgraded avatars for top-down tank view:
        // - Fish: gene-driven microbe-like avatars derived from fish physical genome
        // - Food/live food: reuse the same small tank PNG avatars as the side-view renderer
        if (entity.kind === 'fish') {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawMicrobe(ctx, entity);
            // Draw soccer effect if present (energy gain indicator)
            this.drawSoccerEffect(ctx, entity);
            ctx.restore();
        } else if (entity.kind === 'plant') {
            this.drawFractalPlant(ctx, entity);
        } else if (entity.kind === 'crab') {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawMicrobePredator(ctx, entity);
            ctx.restore();
        } else if (entity.kind === 'castle') {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawMicrobeSubstrate(ctx, entity);
            ctx.restore();
        } else if (entity.kind === 'food' || entity.kind === 'plant_nectar') {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            if (!this.drawFoodAvatar(ctx, entity)) {
                this.drawCircleFallback(ctx, entity);
            }
            ctx.restore();
        } else if (entity.kind === 'ball') {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawBall(ctx, entity);
            ctx.restore();
        } else if (entity.kind === 'goalzone') {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawGoalZone(ctx, entity);
            ctx.restore();
        } else {
            ctx.save();
            ctx.translate(entity.x, entity.y);
            this.drawCircleFallback(ctx, entity);
            ctx.restore();
        }

        // Draw heading if available
        if (entity.headingRad !== undefined && entity.kind !== 'fish' && entity.kind !== 'food' && entity.kind !== 'plant_nectar') {
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(Math.cos(entity.headingRad) * entity.radius, Math.sin(entity.headingRad) * entity.radius);
            ctx.stroke();
        }

        // Selected/Debug ring (optional, maybe check specific ID?)
        // For debugging, print small ID
        if (entity.kind === 'fish') {
            ctx.fillStyle = "#fff";
            ctx.font = `${Math.max(8, entity.radius)}px monospace`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            // ctx.fillText(entity.id.toString().slice(-2), 0, 0); 
        }

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

    private genomeHueDegrees(entity: TankEntity): number {
        const hue = entity.genome_data?.color_hue;
        if (typeof hue === 'number' && Number.isFinite(hue)) {
            return ((hue % 1) + 1) % 1 * 360;
        }
        // fallback: stable hash to hue
        return ((entity.id * 2654435761) >>> 0) % 360;
    }

    private getAnimationFrame(nowMs: number, frameCount: number): number {
        if (frameCount <= 1) return 0;
        const IMAGE_CHANGE_RATE = 500;
        return Math.floor(nowMs / IMAGE_CHANGE_RATE) % frameCount;
    }

    private getFoodImageName(entity: TankEntity): string | null {
        const FOOD_TYPE_IMAGES: Record<string, string[]> = {
            algae: ['food_algae1.png', 'food_algae2.png'],
            protein: ['food_protein1.png', 'food_protein2.png'],
            energy: ['food_energy1.png', 'food_energy2.png'],
            rare: ['food_rare1.png', 'food_rare2.png'],
            nectar: ['food_vitamin1.png', 'food_vitamin2.png'],
            live: ['food_live1.png', 'food_live2.png'],
        };
        const DEFAULT_FOOD_IMAGES = ['food_algae1.png', 'food_algae2.png'];

        const foodType = entity.kind === 'plant_nectar' ? 'nectar' : entity.food_type;
        const frames = (foodType && FOOD_TYPE_IMAGES[foodType]) ? FOOD_TYPE_IMAGES[foodType] : DEFAULT_FOOD_IMAGES;
        return frames[this.getAnimationFrame(this.lastNowMs, frames.length)] ?? null;
    }

    private drawFoodAvatar(ctx: CanvasRenderingContext2D, entity: TankEntity): boolean {
        const imageName = this.getFoodImageName(entity);
        const image = imageName ? ImageLoader.getCachedImage(imageName) : null;
        if (!image) return false;

        const isLiveFood = (entity.kind === 'food' && entity.food_type === 'live');
        const baseScale = isLiveFood ? 0.35 : 0.7;
        const pulse = isLiveFood ? (Math.sin(this.lastNowMs * 0.005) * 0.12 + 1) : 1;
        const size = this.clamp(entity.radius * 2 * baseScale * pulse, 6, 28);

        ctx.save();
        ctx.globalAlpha = isLiveFood ? 0.22 : 0.16;
        const glowHue = isLiveFood ? 130 : 55;
        const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, size * 0.95);
        grad.addColorStop(0, `hsla(${glowHue}, 90%, 60%, 0.9)`);
        grad.addColorStop(1, `hsla(${glowHue}, 90%, 60%, 0)`);
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(0, 0, size * 0.95, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        ctx.save();
        ctx.globalAlpha = 0.95;
        ctx.drawImage(image, -size / 2, -size / 2, size, size);
        ctx.restore();

        return true;
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

    private drawMicrobePredator(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        // Concept: a bacteriophage / protozoan predator hybrid.
        // Reads as "microbe predator" at a glance, and stays deterministic per id.
        const r = this.clamp(Math.max(entity.radius, 14), 14, 34);
        const rand = this.seededRand(((entity.id * 1103515245) ^ 0x9E3779B9) >>> 0);
        const angle = this.movementAngle(entity, rand);

        ctx.save();
        ctx.rotate(angle);

        // Head (icosahedral-ish capsid)
        const headR = r * 0.62;
        const headHue = 340; // magenta/red
        const menace = Math.sin(this.elapsedTime * 0.007 + entity.id * 0.01) * 0.5 + 0.5;
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

        // Spiky corona around the head (scarier silhouette)
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

        // Facet lines
        ctx.strokeStyle = `rgba(255, 255, 255, 0.22)`;
        ctx.lineWidth = Math.max(1, r * 0.04);
        ctx.beginPath();
        ctx.moveTo(-headR * 0.6, 0);
        ctx.lineTo(headR * 0.6, 0);
        ctx.moveTo(0, -headR * 0.6);
        ctx.lineTo(0, headR * 0.6);
        ctx.stroke();

        // "Eyes" (glowing slits) + "jaw" notch
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

        // Jaw / aperture
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

        // Tail rings (animated "pumping")
        const pump = Math.sin(this.elapsedTime * 0.006 + entity.id * 0.01) * 0.35 + 0.65;
        const ringCount = 3;
        ctx.strokeStyle = `rgba(255, 255, 255, 0.18)`;
        ctx.lineWidth = Math.max(1, r * 0.03);
        for (let i = 0; i < ringCount; i++) {
            const t = (i + 1) / (ringCount + 1);
            const x = -headR * 0.95 - tailLen * t;
            const rw = tailW * (0.7 + 0.3 * pump);
            ctx.beginPath();
            ctx.moveTo(x, -rw / 2);
            ctx.lineTo(x, rw / 2);
            ctx.stroke();
        }

        // Tail fibers (legs)
        const fiberCount = 5 + Math.floor(rand() * 3);
        ctx.strokeStyle = `hsla(${(headHue + 160) % 360}, 55%, 65%, 0.55)`;
        ctx.lineWidth = Math.max(1, r * 0.025);
        for (let i = 0; i < fiberCount; i++) {
            const t = (i + 1) / (fiberCount + 1);
            const baseX = -headR * 0.95 - tailLen * (0.45 + t * 0.55);
            const baseY = (t - 0.5) * tailW * 2.2;
            const wiggle = Math.sin(this.elapsedTime * 0.005 + entity.id * 0.03 + i) * (r * 0.10);
            const endX = baseX - r * (0.35 + rand() * 0.25);
            const endY = baseY + wiggle;
            ctx.beginPath();
            ctx.moveTo(baseX, baseY);
            ctx.quadraticCurveTo((baseX + endX) / 2, (baseY + endY) / 2 + wiggle * 0.6, endX, endY);
            ctx.stroke();
        }

        // "Mouth" / core dot
        // Outer glow to separate from background
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

    private drawMicrobeSubstrate(ctx: CanvasRenderingContext2D, entity: TankEntity) {
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

        // Subtle rim highlight
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.14)';
        ctx.lineWidth = Math.max(1, r * 0.04);
        this.drawWobblyBlob(ctx, r, rand, wobble * 0.75);
        ctx.stroke();

        // Pores/pits (negative space)
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

        // Growth rings / striations
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

        // Tiny embedded crystals
        ctx.save();
        ctx.globalAlpha = 0.35;
        ctx.fillStyle = 'rgba(220, 240, 255, 0.45)';
        const crystalCount = 4 + Math.floor(rand() * 4);
        for (let i = 0; i < crystalCount; i++) {
            const a = rand() * Math.PI * 2;
            const d = r * (0.15 + rand() * 0.75);
            const cx = Math.cos(a) * d;
            const cy = Math.sin(a) * d;
            const s = r * (0.05 + rand() * 0.08);
            ctx.beginPath();
            ctx.moveTo(cx, cy - s);
            ctx.lineTo(cx + s, cy);
            ctx.lineTo(cx, cy + s);
            ctx.lineTo(cx - s, cy);
            ctx.closePath();
            ctx.fill();
        }
        ctx.restore();
    }

    private drawDeathIndicator(ctx: CanvasRenderingContext2D, x: number, y: number, cause: string) {
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Background circle
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

    private drawCircleFallback(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        let color = "#fff";
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
                color = this.hashColor(entity.kind);
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(0, 0, entity.radius, 0, Math.PI * 2);
        ctx.fill();
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

    private movementAngle(entity: TankEntity, rand: () => number): number {
        const vx = entity.vel_x ?? 0;
        const vy = entity.vel_y ?? 0;
        const magSq = vx * vx + vy * vy;
        if (magSq > 0.04) return Math.atan2(vy, vx);
        return (rand() * Math.PI * 2) - Math.PI;
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
        const team = (entity as any).team; // entity is TankEntity, cast to any to access dynamic props

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
        const soccerState = (entity as any).soccer_effect_state;
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

    private drawMicrobe(ctx: CanvasRenderingContext2D, entity: TankEntity) {
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
        const shapeKind = templateId % 6;
        if (shapeKind === 2 || shapeKind === 5) {
            this.drawCapsule(ctx, r * 0.9, bodyAspect);
        } else {
            this.drawWobblyBlob(ctx, r, rand, wobble);
        }

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
        if (shapeKind === 2 || shapeKind === 5) this.drawCapsule(ctx, r * 0.9, bodyAspect);
        else this.drawWobblyBlob(ctx, r, rand, wobble * 0.8);
        ctx.stroke();

        ctx.restore();
    }

    private hashColor(str: string): string {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
        return "#" + "00000".substring(0, 6 - c.length) + c;
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
