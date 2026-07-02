import type { PlantGenomeData, MandelbrotCacheEntry } from './types';
import { hslToRgbTuple } from './helpers';

// Module-level caches
export const mandelbrotCache = new Map<number, MandelbrotCacheEntry>();
export const claudeCache = new Map<number, MandelbrotCacheEntry>();
export const antigravityCache = new Map<number, MandelbrotCacheEntry>();
export const gptCache = new Map<number, MandelbrotCacheEntry>();

const phi = 1.618033988749895;

/**
 * Generate a Mandelbrot set texture.
 */
export function generateMandelbrotTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
    const canvas = document.createElement('canvas');
    const size = 160;
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    const imageData = ctx.createImageData(size, size);
    const maxIterations = 44;
    const baseHue = genome.color_hue ?? 0.33; // default to chlorophyll greens
    const saturation = genome.color_saturation ?? 0.82;

    // Soft petiole-inspired gradient so the Mandelbrot sits in a leafy cup
    const cupGradient = ctx.createRadialGradient(size / 2, size * 0.65, size * 0.05, size / 2, size * 0.6, size * 0.48);
    cupGradient.addColorStop(0, 'rgba(255, 255, 255, 0.05)');
    cupGradient.addColorStop(1, 'rgba(0, 0, 0, 0.05)');
    ctx.fillStyle = cupGradient;
    ctx.fillRect(0, 0, size, size);

    for (let py = 0; py < size; py++) {
        const cy = (py / size) * 2.4 - 1.2; // Range [-1.2, 1.2]
        for (let px = 0; px < size; px++) {
            const cx = (px / size) * 3.0 - 2.1; // Range [-2.1, 0.9]
            let zx = 0;
            let zy = 0;
            let iter = 0;

            while (zx * zx + zy * zy <= 4 && iter < maxIterations) {
                const temp = zx * zx - zy * zy + cx;
                zy = 2 * zx * zy + cy;
                zx = temp;
                iter++;
            }

            const mix = iter / maxIterations;
            const hue = (baseHue + mix * 0.18 + cacheKey * 0.0001) % 1;
            const lightness = iter === maxIterations ? 0.16 : 0.22 + mix * 0.55;
            const [r, g, b] = hslToRgbTuple(hue, saturation, lightness);

            // Leaf taper mask keeps tips narrow and keeps the belly of the set plump
            const maskX = (px - size / 2) / (size / 2);
            const maskY = py / size;
            const sideFalloff = Math.pow(Math.abs(maskX), 1.6) * 0.7;
            const tipFalloff = Math.pow(maskY, 1.5) * 0.22;
            const alphaBase = 1 - sideFalloff - tipFalloff;

            // Use a second-order derivative of the orbit to carve vein-like striations
            const veinPulse = Math.sin((zx * 8 + zy * 6) * 0.5);
            const veinLift = Math.max(0, veinPulse) * 0.25;
            const alpha = Math.max(0, Math.min(1, alphaBase + veinLift));

            const idx = (py * size + px) * 4;
            imageData.data[idx] = r;
            imageData.data[idx + 1] = g;
            imageData.data[idx + 2] = b;
            imageData.data[idx + 3] = Math.floor(Math.max(0, alpha) * 255);
        }
    }

    ctx.putImageData(imageData, 0, 0);
    return canvas;
}

/**
 * Generate a Claude Julia set texture with golden spiral aesthetics.
 */
export function generateClaudeTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
    const canvas = document.createElement('canvas');
    const size = 160;
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    const imageData = ctx.createImageData(size, size);
    const maxIterations = 50;
    const baseHue = genome.color_hue ?? 0.11; // Golden/amber
    const saturation = genome.color_saturation ?? 0.85;

    // Julia set constants for beautiful spiral patterns
    const cReal = -0.4 + (cacheKey % 100) * 0.001;
    const cImag = 0.6 + (cacheKey % 50) * 0.002;

    for (let py = 0; py < size; py++) {
        const zy0 = (py / size) * 3.2 - 1.6; // Range [-1.6, 1.6]
        for (let px = 0; px < size; px++) {
            const zx0 = (px / size) * 3.2 - 1.6; // Range [-1.6, 1.6]
            let zx = zx0;
            let zy = zy0;
            let iter = 0;

            // Julia set iteration
            while (zx * zx + zy * zy <= 4 && iter < maxIterations) {
                const temp = zx * zx - zy * zy + cReal;
                zy = 2 * zx * zy + cImag;
                zx = temp;
                iter++;
            }

            // Smooth coloring using continuous potential
            let smoothIter = iter;
            if (iter < maxIterations) {
                const logZn = Math.log(zx * zx + zy * zy) / 2;
                const nu = Math.log(logZn / Math.log(2)) / Math.log(2);
                smoothIter = iter + 1 - nu;
            }

            const mix = smoothIter / maxIterations;

            // Golden color palette with warm gradients
            let hue: number, lightness: number;
            if (iter === maxIterations) {
                // Inside the Julia set - deep golden core
                hue = baseHue;
                lightness = 0.15 + Math.sin(zx * 5) * 0.05;
            } else {
                // Outside - spiral arms with golden gradients
                hue = (baseHue + mix * 0.12 + Math.sin(mix * Math.PI * 2) * 0.04) % 1;
                lightness = 0.3 + mix * 0.5;
            }

            const [r, g, b] = hslToRgbTuple(hue, saturation, lightness);

            // Organic mask - flower-like silhouette with golden ratio proportions
            const centerX = size / 2;
            const centerY = size / 2;
            const dx = (px - centerX) / (size / 2);
            const dy = (py - centerY) / (size / 2);
            const dist = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx);

            // Fibonacci-inspired petal shape (5 petals for phi relation)
            const petalCount = 5;
            const petalWave = Math.cos(angle * petalCount) * 0.15;
            const spiralWave = Math.sin(angle * 3 + dist * 8) * 0.08;
            const maxRadius = 0.85 + petalWave + spiralWave;

            let alpha = 1 - Math.pow(dist / maxRadius, 2.5);
            alpha = Math.max(0, Math.min(1, alpha));

            // Add radial fade for soft edges
            if (dist > maxRadius * 0.7) {
                alpha *= 1 - (dist - maxRadius * 0.7) / (maxRadius * 0.3);
            }

            const idx = (py * size + px) * 4;
            imageData.data[idx] = r;
            imageData.data[idx + 1] = g;
            imageData.data[idx + 2] = b;
            imageData.data[idx + 3] = Math.floor(Math.max(0, alpha) * 255);
        }
    }

    ctx.putImageData(imageData, 0, 0);

    // Add inner glow effect for depth
    const centerX = size / 2;
    const centerY = size / 2;
    const glowRadius = size * 0.35;

    ctx.save();
    ctx.globalCompositeOperation = 'overlay';
    const innerGlow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, glowRadius);
    innerGlow.addColorStop(0, 'rgba(255, 240, 200, 0.3)');
    innerGlow.addColorStop(0.5, 'rgba(255, 220, 150, 0.15)');
    innerGlow.addColorStop(1, 'rgba(255, 200, 100, 0)');
    ctx.fillStyle = innerGlow;
    ctx.fillRect(0, 0, size, size);
    ctx.restore();

    // Add sparkle points using golden angle distribution
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const goldenAngle = Math.PI * (3 - Math.sqrt(5)); // ~137.5 degrees

    for (let i = 0; i < 12; i++) {
        const angle = i * goldenAngle;
        const radius = size * 0.2 + (i / 12) * size * 0.25;
        const sparkleX = centerX + Math.cos(angle) * radius;
        const sparkleY = centerY + Math.sin(angle) * radius;
        const sparkleSize = 2 + Math.sin(i * phi) * 1.5;

        const sparkleGrad = ctx.createRadialGradient(sparkleX, sparkleY, 0, sparkleX, sparkleY, sparkleSize * 2);
        sparkleGrad.addColorStop(0, 'rgba(255, 255, 240, 0.6)');
        sparkleGrad.addColorStop(0.5, 'rgba(255, 230, 180, 0.3)');
        sparkleGrad.addColorStop(1, 'rgba(255, 200, 120, 0)');

        ctx.beginPath();
        ctx.arc(sparkleX, sparkleY, sparkleSize * 2, 0, Math.PI * 2);
        ctx.fillStyle = sparkleGrad;
        ctx.fill();
    }
    ctx.restore();

    // Soft outer halo
    const halo = ctx.createRadialGradient(centerX, centerY, size * 0.3, centerX, centerY, size * 0.5);
    halo.addColorStop(0, 'rgba(255, 220, 150, 0.1)');
    halo.addColorStop(1, 'rgba(255, 200, 100, 0)');
    ctx.fillStyle = halo;
    ctx.globalCompositeOperation = 'lighter';
    ctx.beginPath();
    ctx.arc(centerX, centerY, size * 0.5, 0, Math.PI * 2);
    ctx.fill();

    return canvas;
}

/**
 * Generate an Antigravity texture with inverse fractal patterns.
 */
export function generateAntigravityTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
    const canvas = document.createElement('canvas');
    const size = 150;
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    const imageData = ctx.createImageData(size, size);
    const maxIterations = 45;
    const baseHue = genome.color_hue ?? 0.78; // Violet
    const saturation = genome.color_saturation ?? 0.9;

    // Burning Ship fractal variant
    for (let py = 0; py < size; py++) {
        const cy = (py / size) * 3.0 - 1.5;
        for (let px = 0; px < size; px++) {
            const cx = (px / size) * 3.0 - 2.0;
            let zx = 0;
            let zy = 0;
            let iter = 0;

            while (zx * zx + zy * zy <= 4 && iter < maxIterations) {
                const temp = zx * zx - zy * zy + cx;
                zy = Math.abs(2 * zx * zy) + cy;
                zx = Math.abs(temp);
                iter++;
            }

            const mix = iter / maxIterations;
            const hue = (baseHue + (1 - mix) * 0.15 + cacheKey * 0.00005) % 1;
            const lightness = iter === maxIterations ? 0.08 : 0.2 + mix * 0.6;
            const [r, g, b] = hslToRgbTuple(hue, saturation, lightness);

            // Inverted radial mask (brighter at edges)
            const centerX = size / 2;
            const centerY = size / 2;
            const dx = (px - centerX) / (size / 2);
            const dy = (py - centerY) / (size / 2);
            const dist = Math.sqrt(dx * dx + dy * dy);

            // Swirling pattern
            const angle = Math.atan2(dy, dx);
            const swirl = Math.sin(angle * 5 + dist * 8) * 0.12;
            const maxRadius = 0.9 + swirl;

            let alpha = 1 - Math.pow(dist / maxRadius, 2);
            alpha = Math.max(0, Math.min(1, alpha));

            const idx = (py * size + px) * 4;
            imageData.data[idx] = r;
            imageData.data[idx + 1] = g;
            imageData.data[idx + 2] = b;
            imageData.data[idx + 3] = Math.floor(alpha * 255);
        }
    }

    ctx.putImageData(imageData, 0, 0);

    const centerX = size / 2;
    const centerY = size / 2;

    // Add ethereal glow effect
    ctx.save();
    ctx.globalCompositeOperation = 'overlay';
    const vortexGlow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, size * 0.4);
    vortexGlow.addColorStop(0, 'rgba(200, 150, 255, 0.4)');
    vortexGlow.addColorStop(0.5, 'rgba(150, 100, 220, 0.2)');
    vortexGlow.addColorStop(1, 'rgba(100, 50, 180, 0)');
    ctx.fillStyle = vortexGlow;
    ctx.fillRect(0, 0, size, size);
    ctx.restore();

    // Floating particle effect
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 10; i++) {
        const angle = (i / 10) * Math.PI * 2;
        const radius = size * 0.2 + (i % 3) * size * 0.1;
        const px = centerX + Math.cos(angle) * radius;
        const py = centerY + Math.sin(angle) * radius;

        const particle = ctx.createRadialGradient(px, py, 0, px, py, 4);
        particle.addColorStop(0, 'rgba(220, 180, 255, 0.7)');
        particle.addColorStop(1, 'rgba(180, 120, 220, 0)');
        ctx.beginPath();
        ctx.arc(px, py, 4, 0, Math.PI * 2);
        ctx.fillStyle = particle;
        ctx.fill();
    }
    ctx.restore();

    return canvas;
}

/**
 * Generate a GPT texture with neural network-inspired patterns.
 */
export function generateGptTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
    const canvas = document.createElement('canvas');
    const size = 155;
    canvas.width = size;
    canvas.height = size;

    const ctx = canvas.getContext('2d');
    if (!ctx) return canvas;

    const imageData = ctx.createImageData(size, size);
    const maxIterations = 42;
    const baseHue = genome.color_hue ?? 0.52; // Cyan/teal
    const saturation = genome.color_saturation ?? 0.9;

    // Tricorn fractal
    for (let py = 0; py < size; py++) {
        const cy = (py / size) * 3.2 - 1.6;
        for (let px = 0; px < size; px++) {
            const cx = (px / size) * 3.2 - 1.8;
            let zx = 0;
            let zy = 0;
            let iter = 0;

            // Tricorn iteration (conjugate of z)
            while (zx * zx + zy * zy <= 4 && iter < maxIterations) {
                const temp = zx * zx - zy * zy + cx;
                zy = -2 * zx * zy + cy; // Negative for conjugate
                zx = temp;
                iter++;
            }

            // Smooth coloring
            let smoothIter = iter;
            if (iter < maxIterations) {
                const logZn = Math.log(zx * zx + zy * zy) / 2;
                const nu = Math.log(logZn / Math.log(2)) / Math.log(2);
                smoothIter = iter + 1 - nu;
            }

            const mix = smoothIter / maxIterations;
            const hue = (baseHue + mix * 0.1 + Math.sin(mix * Math.PI * 3) * 0.05 + cacheKey * 0.00003) % 1;
            const lightness = iter === maxIterations ? 0.12 : 0.25 + mix * 0.55;
            const [r, g, b] = hslToRgbTuple(hue, saturation, lightness);

            // Neural network-like node pattern mask
            const centerX = size / 2;
            const centerY = size / 2;
            const dx = (px - centerX) / (size / 2);
            const dy = (py - centerY) / (size / 2);
            const dist = Math.sqrt(dx * dx + dy * dy);
            const angle = Math.atan2(dy, dx);

            // Hexagonal pattern for "network nodes"
            const hexWave = Math.cos(angle * 6) * 0.1;
            const maxRadius = 0.85 + hexWave;

            let alpha = 1 - Math.pow(dist / maxRadius, 2.2);
            alpha = Math.max(0, Math.min(1, alpha));

            const idx = (py * size + px) * 4;
            imageData.data[idx] = r;
            imageData.data[idx + 1] = g;
            imageData.data[idx + 2] = b;
            imageData.data[idx + 3] = Math.floor(alpha * 255);
        }
    }

    ctx.putImageData(imageData, 0, 0);

    const centerX = size / 2;
    const centerY = size / 2;

    // Neural connection lines
    ctx.save();
    ctx.globalCompositeOperation = 'overlay';
    ctx.strokeStyle = 'rgba(100, 220, 255, 0.15)';
    ctx.lineWidth = 1;
    const nodeCount = 8;
    for (let i = 0; i < nodeCount; i++) {
        const angle1 = (i / nodeCount) * Math.PI * 2;
        const r1 = size * 0.25;
        const x1 = centerX + Math.cos(angle1) * r1;
        const y1 = centerY + Math.sin(angle1) * r1;

        for (let j = i + 1; j < nodeCount; j++) {
            const angle2 = (j / nodeCount) * Math.PI * 2;
            const r2 = size * 0.25;
            const x2 = centerX + Math.cos(angle2) * r2;
            const y2 = centerY + Math.sin(angle2) * r2;

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }
    }
    ctx.restore();

    // Electric glow effect
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const glow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, size * 0.4);
    glow.addColorStop(0, 'rgba(100, 255, 255, 0.3)');
    glow.addColorStop(0.4, 'rgba(50, 200, 230, 0.15)');
    glow.addColorStop(1, 'rgba(0, 150, 200, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, size, size);

    // Node sparkles
    for (let i = 0; i < 12; i++) {
        const angle = (i / 12) * Math.PI * 2;
        const radius = size * 0.2 + (i % 4) * size * 0.08;
        const nx = centerX + Math.cos(angle) * radius;
        const ny = centerY + Math.sin(angle) * radius;

        const nodeGrad = ctx.createRadialGradient(nx, ny, 0, nx, ny, 5);
        nodeGrad.addColorStop(0, 'rgba(150, 255, 255, 0.8)');
        nodeGrad.addColorStop(0.5, 'rgba(80, 200, 240, 0.4)');
        nodeGrad.addColorStop(1, 'rgba(50, 150, 200, 0)');
        ctx.beginPath();
        ctx.arc(nx, ny, 5, 0, Math.PI * 2);
        ctx.fillStyle = nodeGrad;
        ctx.fill();
    }
    ctx.restore();

    return canvas;
}
