/**
 * Water background rendering: ocean gradient, animated light rays, ambient
 * particles, and the textured seabed. Extracted from utils/renderer.ts
 * (god-class ratchet harvest); behavior is unchanged.
 */

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

export interface TimeOfDayPalette {
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

// Particle system for ambient water effects
interface Particle {
    x: number;
    y: number;
    size: number;
    speed: number;
    opacity: number;
    wobble: number;
}

export function getTimeOfDayPalette(timeOfDay?: string): TimeOfDayPalette {
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

/**
 * Owns the mutable background state (particles, cached seabed rocks, current
 * palette) that used to live on the Renderer god class.
 */
export class BackgroundRenderer {
    private particles: Particle[] = [];
    private initialized = false;
    private currentPalette: TimeOfDayPalette | null = null;
    // Cache for seabed rocks to prevent shimmering
    private seabedRocks: { x: number, y: number, size: number }[] = [];
    private seabedWidth: number = 0;

    /** Drop cached state so GC can reclaim memory when the canvas unmounts. */
    reset() {
        this.particles = [];
        this.initialized = false;
        this.currentPalette = null;
        this.seabedRocks = [];
        this.seabedWidth = 0;
    }

    private initParticles(ctx: CanvasRenderingContext2D) {
        if (this.initialized) return;
        this.initialized = true;

        // Create ambient floating particles (bubbles, debris)
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;

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

    /** Clear the canvas and draw the full water background for this frame. */
    draw(
        ctx: CanvasRenderingContext2D,
        width: number,
        height: number,
        timeOfDay?: string,
        showDecorative: boolean = true
    ) {
        this.initParticles(ctx);
        const time = Date.now();
        const palette = getTimeOfDayPalette(timeOfDay);
        this.currentPalette = palette;

        // Enhanced ocean gradient with more depth
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, palette.gradientTop);
        gradient.addColorStop(GRADIENT_STOP_1, palette.gradientMid);
        gradient.addColorStop(GRADIENT_STOP_2, palette.gradientDeep);
        gradient.addColorStop(1, palette.gradientDeep);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);

        // Animated light rays with caustics effect
        if (showDecorative) {
            ctx.save();
            const causticsOffset = Math.sin(time * CAUSTICS_SPEED) * CAUSTICS_AMPLITUDE;
            for (let i = 0; i < LIGHT_RAY_COUNT; i += 1) {
                const baseX = (width / LIGHT_RAY_COUNT) * i + causticsOffset;
                const wobble = Math.sin(time * WOBBLE_SPEED + i) * WOBBLE_AMPLITUDE;

                // Main light ray
                ctx.globalAlpha = palette.rayOpacityMain;
                ctx.beginPath();
                ctx.moveTo(baseX + 60 + wobble, 0);
                ctx.lineTo(baseX + 180 + wobble, 0);
                ctx.lineTo(baseX + wobble, height);
                ctx.closePath();
                const rayGradient = ctx.createLinearGradient(baseX, 0, baseX, height);
                rayGradient.addColorStop(0, palette.rayColorMain);
                rayGradient.addColorStop(0.6, palette.rayColorMain);
                rayGradient.addColorStop(1, 'rgba(61, 213, 255, 0)');
                ctx.fillStyle = rayGradient;
                ctx.fill();

                // Secondary highlight for caustics
                ctx.globalAlpha = palette.rayOpacitySecondary;
                ctx.beginPath();
                ctx.moveTo(baseX + 80 + wobble * 1.5, 0);
                ctx.lineTo(baseX + 120 + wobble * 1.5, 0);
                ctx.lineTo(baseX + 40 + wobble, height * 0.4);
                ctx.closePath();
                ctx.fillStyle = palette.rayColorSecondary;
                ctx.fill();
            }
            ctx.restore();
        }

        // Apply subtle global overlay for time-of-day mood
        if (palette.overlayAlpha > 0) {
            ctx.save();
            ctx.globalAlpha = palette.overlayAlpha;
            ctx.fillStyle = palette.overlayColor;
            ctx.fillRect(0, 0, width, height);
            ctx.restore();
        }

        // Update and draw floating particles
        if (showDecorative) {
            this.updateParticles(width, height);
            this.drawParticles(ctx);
        }

        // Enhanced seabed with texture
        const seabedHeight = Math.max(SEABED_MIN_HEIGHT, height * SEABED_HEIGHT_RATIO);
        const seabedY = height - seabedHeight;

        // Seabed gradient with more depth
        const seabedGradient = ctx.createLinearGradient(0, seabedY, 0, height);
        seabedGradient.addColorStop(0, palette.seabedTop);
        seabedGradient.addColorStop(0.5, palette.seabedMid);
        seabedGradient.addColorStop(1, palette.seabedBottom);
        ctx.fillStyle = seabedGradient;
        ctx.fillRect(0, seabedY, width, seabedHeight);

        // Add seabed texture (rocks/pebbles) - Stabilized (cached)
        ctx.save();
        ctx.globalAlpha = SEABED_TEXTURE_OPACITY;

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
        ctx.fillStyle = '#8b6f47';
        for (const rock of this.seabedRocks) {
            ctx.beginPath();
            ctx.ellipse(rock.x, rock.y, rock.size, rock.size * 0.7, 0, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
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

    private drawParticles(ctx: CanvasRenderingContext2D) {
        ctx.save();
        const particleColor = this.currentPalette?.particleColor ?? '#8dd5ef';
        for (const particle of this.particles) {
            ctx.globalAlpha = particle.opacity;
            ctx.fillStyle = particleColor;

            // Draw bubble with highlight
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fill();

            // Highlight
            ctx.globalAlpha = particle.opacity * PARTICLE_HIGHLIGHT_OPACITY_MULTIPLIER;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(
                particle.x - particle.size * PARTICLE_HIGHLIGHT_OFFSET_RATIO,
                particle.y - particle.size * PARTICLE_HIGHLIGHT_OFFSET_RATIO,
                particle.size * PARTICLE_HIGHLIGHT_SIZE_RATIO,
                0,
                Math.PI * 2
            );
            ctx.fill();
        }
        ctx.restore();
    }
}
