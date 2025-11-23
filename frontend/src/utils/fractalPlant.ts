/**
 * L-System fractal plant rendering utilities.
 *
 * This module generates fractal plant shapes using L-system grammar rules
 * inherited from the plant's genome.
 */

export interface PlantGenomeData {
    axiom: string;
    angle: number;
    length_ratio: number;
    branch_probability: number;
    curve_factor: number;
    color_hue: number;
    color_saturation: number;
    stem_thickness: number;
    leaf_density: number;
    fractal_type?:
    | 'lsystem'
    | 'cosmic_fern'
    | 'claude'
    | 'antigravity'
    | 'gpt'
    | 'gpt_codex'
    | 'gemini'
    | 'sonnet';
    production_rules: Array<{
        input: string;
        output: string;
        prob: number;
    }>;
}

interface TurtleState {
    x: number;
    y: number;
    angle: number;
    length: number;
    thickness: number;
}

interface FractalSegment {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    thickness: number;
    depth: number;
    kind?: 'root' | 'branch';
}

interface FractalLeaf {
    x: number;
    y: number;
    angle: number;
    size: number;
}

interface MandelbrotCacheEntry {
    signature: string;
    texture: HTMLCanvasElement;
}

/**
 * Cache for plant rendering to avoid regenerating L-system every frame.
 */
interface PlantRenderCache {
    iterations: number;
    // sizeMultiplier is no longer needed in cache as we scale the context
    signature: string;
    segments: FractalSegment[];
    leaves: FractalLeaf[];
    sortedSegments: FractalSegment[];
}

// Module-level cache keyed by plant id to avoid flickering when plants drift
const plantCache = new Map<number, PlantRenderCache>();
const mandelbrotCache = new Map<number, MandelbrotCacheEntry>();
const claudeCache = new Map<number, MandelbrotCacheEntry>();
const antigravityCache = new Map<number, MandelbrotCacheEntry>();
const gptCache = new Map<number, MandelbrotCacheEntry>();
const sonnetCache = new Map<number, PlantRenderCache>();
const gptCodexCache = new Map<number, PlantRenderCache>();

/**
 * Create a stable signature for a genome so cache invalidation happens when traits change.
 */
function getGenomeSignature(genome: PlantGenomeData): string {
    const ruleSignature = genome.production_rules
        .map((rule) => `${rule.input}:${rule.output}:${rule.prob}`)
        .join('|');

    return [
        genome.axiom,
        genome.angle,
        genome.length_ratio,
        genome.branch_probability,
        genome.curve_factor,
        genome.fractal_type ?? 'lsystem',
        genome.color_hue,
        genome.color_saturation,
        genome.stem_thickness,
        genome.leaf_density,
        ruleSignature,
    ].join(';');
}

/**
 * Seeded random for deterministic plant generation.
 */
function seededRandom(seed: number): number {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
}

function generateMandelbrotTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
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
            imageData.data[idx + 3] = Math.floor(alpha * 255);
        }
    }

    ctx.putImageData(imageData, 0, 0);

    // Mask the harsh square into an organic blossom silhouette with lobed leaves
    ctx.save();
    ctx.beginPath();
    const centerX = size / 2;
    const centerY = size * 0.6;
    const baseRadius = size * 0.46;
    const lobes = 5;
    for (let i = 0; i <= 160; i++) {
        const t = (i / 160) * Math.PI * 2;
        const ripple = Math.sin(t * lobes) * 0.12 + Math.sin(t * lobes * 2) * 0.04;
        const radius = baseRadius * (0.82 + ripple);
        const x = centerX + Math.cos(t) * radius;
        const y = centerY + Math.sin(t) * radius * 0.92;
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.closePath();
    ctx.globalCompositeOperation = 'destination-in';
    ctx.fillStyle = '#fff';
    ctx.fill();

    // Add strong midrib and secondary veins to reinforce the plant feel
    ctx.globalCompositeOperation = 'overlay';
    ctx.lineCap = 'round';
    const midrib = ctx.createLinearGradient(centerX, centerY + baseRadius * 0.2, centerX, centerY - baseRadius * 0.8);
    midrib.addColorStop(0, 'rgba(255, 255, 255, 0.05)');
    midrib.addColorStop(1, 'rgba(255, 255, 255, 0.12)');
    ctx.strokeStyle = midrib;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY + baseRadius * 0.3);
    ctx.quadraticCurveTo(centerX + baseRadius * 0.05, centerY - baseRadius * 0.1, centerX, centerY - baseRadius * 0.75);
    ctx.stroke();

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    ctx.lineWidth = 1.5;
    for (let branch = -3; branch <= 3; branch++) {
        const offset = branch * 0.2 * baseRadius;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY - baseRadius * 0.05 + branch * 2);
        ctx.quadraticCurveTo(
            centerX + offset * 0.65,
            centerY - baseRadius * (0.3 + Math.abs(branch) * 0.08),
            centerX + offset,
            centerY - baseRadius * (0.62 + Math.abs(branch) * 0.06)
        );
        ctx.stroke();
    }

    // Dewy sheen on the upper leaf surface
    ctx.globalCompositeOperation = 'lighter';
    const dew = ctx.createRadialGradient(centerX - baseRadius * 0.15, centerY - baseRadius * 0.55, 2, centerX, centerY, baseRadius);
    dew.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
    dew.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = dew;
    ctx.beginPath();
    ctx.arc(centerX, centerY - baseRadius * 0.4, baseRadius * 0.9, 0, Math.PI * 2);
    ctx.fill();

    // Soft edge halo to blend into the water background
    const halo = ctx.createRadialGradient(centerX, centerY - baseRadius * 0.28, baseRadius * 0.24, centerX, centerY, baseRadius);
    halo.addColorStop(0, 'rgba(255, 255, 255, 0.08)');
    halo.addColorStop(1, 'rgba(255, 255, 255, 0)');
    ctx.fillStyle = halo;
    ctx.globalCompositeOperation = 'lighter';
    ctx.beginPath();
    ctx.arc(centerX, centerY - baseRadius * 0.08, baseRadius, 0, Math.PI * 2);
    ctx.fill();

    return canvas;
}

/**
 * Generate a Claude Julia set texture with golden spiral aesthetics.
 * Uses a Julia set with parameters that create elegant spiraling patterns,
 * combined with golden ratio proportions and warm amber coloring.
 */
function generateClaudeTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
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

    // Golden ratio for aesthetic proportions
    const phi = 1.618033988749895;

    // Julia set constants for beautiful spiral patterns
    // These parameters create elegant double-spiral structures
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
            // Creates flowing amber to gold to cream transitions
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
 * Features swirling violet vortex patterns that appear to defy gravity.
 */
function generateAntigravityTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
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

    // Burning Ship fractal variant - creates asymmetric "flame" patterns
    for (let py = 0; py < size; py++) {
        const cy = (py / size) * 3.0 - 1.5;
        for (let px = 0; px < size; px++) {
            const cx = (px / size) * 3.0 - 2.0;
            let zx = 0;
            let zy = 0;
            let iter = 0;

            // Burning Ship iteration with absolute values
            while (zx * zx + zy * zy <= 4 && iter < maxIterations) {
                const temp = zx * zx - zy * zy + cx;
                zy = Math.abs(2 * zx * zy) + cy;
                zx = Math.abs(temp);
                iter++;
            }

            const mix = iter / maxIterations;
            // Inverted coloring for "antigravity" feel
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

    // Add ethereal glow effect
    const centerX = size / 2;
    const centerY = size / 2;

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
 * Features interconnected nodes and electric cyan/blue coloring.
 */
function generateGptTexture(genome: PlantGenomeData, cacheKey: number): HTMLCanvasElement {
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

    // Tricorn fractal - creates interesting branching structures
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
            // Electric color palette with slight variation per plant
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

/**
 * Apply L-system production rules to generate the fractal string.
 */
export function generateLSystemString(
    axiom: string,
    rules: Array<{ input: string; output: string; prob: number }>,
    iterations: number,
    seed: number = 12345
): string {
    let current = axiom;

    // Build rules map
    const ruleMap = new Map<string, Array<{ output: string; prob: number }>>();
    for (const rule of rules) {
        if (!ruleMap.has(rule.input)) {
            ruleMap.set(rule.input, []);
        }
        ruleMap.get(rule.input)!.push({ output: rule.output, prob: rule.prob });
    }

    // Apply rules for each iteration
    let seedCounter = seed;
    for (let i = 0; i < iterations; i++) {
        let next = '';
        for (const char of current) {
            const options = ruleMap.get(char);
            if (options && options.length > 0) {
                // Choose based on probability
                const totalProb = options.reduce((sum, o) => sum + o.prob, 0);
                seedCounter++;
                let roll = seededRandom(seedCounter) * totalProb;
                let chosen = char;
                for (const opt of options) {
                    roll -= opt.prob;
                    if (roll <= 0) {
                        chosen = opt.output;
                        break;
                    }
                }
                next += chosen;
            } else {
                next += char;
            }
        }
        current = next;
    }

    return current;
}

/**
 * Interpret an L-system string into drawable segments and leaves.
 */
export function interpretLSystem(
    lsystemString: string,
    baseAngle: number,
    lengthRatio: number,
    curveFactor: number,
    stemThickness: number,
    leafDensity: number,
    baseLength: number = 15,
    startX: number = 0,
    startY: number = 0,
    seed: number = 12345
): { segments: FractalSegment[]; leaves: FractalLeaf[] } {
    const segments: FractalSegment[] = [];
    const leaves: FractalLeaf[] = [];
    const stateStack: TurtleState[] = [];

    // Initial turtle state (pointing up)
    let state: TurtleState = {
        x: startX,
        y: startY,
        angle: -90, // Point upward (0 = right, -90 = up)
        length: baseLength,
        thickness: stemThickness * 3,
    };

    let depth = 0;
    let seedCounter = seed;

    for (const char of lsystemString) {
        switch (char) {
            case 'F':
            case 'R': {
                const dx = Math.cos((state.angle * Math.PI) / 180) * state.length;
                const dy = Math.sin((state.angle * Math.PI) / 180) * state.length;
                const newX = state.x + dx;
                const newY = state.y + dy;

                const isRoot = char === 'R';
                segments.push({
                    x1: state.x,
                    y1: state.y,
                    x2: newX,
                    y2: newY,
                    thickness: isRoot ? state.thickness * 1.1 : state.thickness,
                    depth: depth,
                    kind: isRoot ? 'root' : 'branch',
                });

                state.x = newX;
                state.y = newY;

                // Roots avoid leaves; branches may sprout them
                if (!isRoot) {
                    seedCounter++;
                    if (seededRandom(seedCounter) < leafDensity * 0.3) {
                        seedCounter++;
                        leaves.push({
                            x: state.x,
                            y: state.y,
                            angle: state.angle,
                            size: 3 + seededRandom(seedCounter) * 4,
                        });
                    }
                }
                break;
            }

            case 'f': {
                const fdx = Math.cos((state.angle * Math.PI) / 180) * state.length;
                const fdy = Math.sin((state.angle * Math.PI) / 180) * state.length;
                state.x += fdx;
                state.y += fdy;
                break;
            }

            case '+':
                seedCounter++;
                state.angle += baseAngle + curveFactor * (seededRandom(seedCounter) - 0.5) * 20;
                break;

            case '-':
                seedCounter++;
                state.angle -= baseAngle + curveFactor * (seededRandom(seedCounter) - 0.5) * 20;
                break;

            case '&': {
                seedCounter++;
                // Downward bend for aerial roots
                state.angle += baseAngle * 0.45 + curveFactor * (seededRandom(seedCounter) - 0.5) * 18;
                break;
            }

            case '[':
                stateStack.push({ ...state });
                depth++;
                state.length *= lengthRatio;
                state.thickness *= 0.7;
                break;

            case ']':
                if (stateStack.length > 0) {
                    seedCounter++;
                    if (seededRandom(seedCounter) < leafDensity) {
                        seedCounter++;
                        leaves.push({
                            x: state.x,
                            y: state.y,
                            angle: state.angle,
                            size: 4 + seededRandom(seedCounter) * 5,
                        });
                    }
                    state = stateStack.pop()!;
                    depth--;
                }
                break;

            case '|':
                state.angle += 180;
                break;
        }
    }

    return { segments, leaves };
}

/**
 * Convert HSL to RGB color string.
 */
function hslToRgb(h: number, s: number, l: number): string {
    let r: number, g: number, b: number;

    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p: number, q: number, t: number): number => {
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

    return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

function hslToRgbTuple(h: number, s: number, l: number): [number, number, number] {
    let r: number, g: number, b: number;

    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p: number, q: number, t: number): number => {
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

/**
 * Render a fractal plant to a canvas context.
 */
export function renderFractalPlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    iterations: number,
    elapsedTime: number,
    nectarReady: boolean = false
): void {
    const fractalType = genome.fractal_type ?? 'lsystem';
    // Cosmic Fern uses standard L-system rendering, so we let it fall through
    if (fractalType === 'cosmic_fern') {
        // Fall through to default L-system renderer
    } else if ((fractalType as any) === 'mandelbrot') {
        // Legacy support or if we want to keep the code for reference
        renderMandelbrotPlant(ctx, plantId, genome, x, y, sizeMultiplier, elapsedTime, nectarReady);
        return;
    }
    // claude, antigravity, and gpt fall through to default L-system renderer
    if (fractalType === 'gpt_codex') {
        renderGptCodexPlant(
            ctx,
            plantId,
            genome,
            x,
            y,
            sizeMultiplier,
            iterations,
            elapsedTime,
            nectarReady
        );
        return;
    }
    if (fractalType === 'sonnet') {
        renderSonnetPlant(ctx, plantId, genome, x, y, sizeMultiplier, iterations, elapsedTime, nectarReady);
        return;
    }

    // Use plant id for caching so geometry stays stable even if position jitters
    const cacheKey = plantId;
    const genomeSignature = `${iterations}:${getGenomeSignature(genome)}`;
    const cached = plantCache.get(cacheKey);

    let segments: FractalSegment[];
    let leaves: FractalLeaf[];
    let sortedSegments: FractalSegment[];

    // Only regenerate geometry when iterations change (size is handled by scaling)
    const needsRegeneration = !cached || cached.signature !== genomeSignature;

    if (needsRegeneration) {
        // Generate deterministic L-system string using cache key as seed
        const lsystemString = generateLSystemString(
            genome.axiom,
            genome.production_rules,
            iterations,
            cacheKey
        );

        // Calculate base length for canonical size (sizeMultiplier = 1.0)
        // We will scale the context to match the actual size
        const baseLength = 10 + 1.0 * 12;

        // Interpret L-system into drawable elements (sway applied later)
        const result = interpretLSystem(
            lsystemString,
            genome.angle,
            genome.length_ratio,
            genome.curve_factor,
            genome.stem_thickness,
            genome.leaf_density,
            baseLength,
            0, // Generate at (0,0) relative
            0, // Generate at (0,0) relative
            cacheKey
        );

        segments = result.segments;
        leaves = result.leaves;
        sortedSegments = [...segments].sort((a, b) => a.depth - b.depth);

        plantCache.set(cacheKey, {
            iterations,
            signature: genomeSignature,
            segments,
            leaves,
            sortedSegments,
        });
    } else {
        segments = cached!.segments;
        leaves = cached!.leaves;
        sortedSegments = cached!.sortedSegments;
    }

    // Apply organic multi-frequency swaying similar to raster plant sprites
    // The root stays fixed at (x, y) - only rotation is applied so the plant sways
    // naturally with its base anchored
    const plantSeed = plantId * 17 + x * 0.5 + y * 0.3;
    const primarySway = Math.sin(elapsedTime * 0.0005 + plantSeed * 0.01) * 5;
    const secondarySway = Math.sin(elapsedTime * 0.0012 + plantSeed * 0.02) * 2.5;
    const tertiarySway = Math.sin(elapsedTime * 0.0008 + plantSeed * 0.015) * 1.5;
    const swayAngle = primarySway + secondarySway + tertiarySway;
    const swayRad = (swayAngle * Math.PI) / 180;

    // Get colors from genome
    const stemColor = hslToRgb(genome.color_hue, genome.color_saturation * 0.8, 0.25);
    const leafColor = hslToRgb(genome.color_hue, genome.color_saturation, 0.4);
    const highlightColor = hslToRgb(genome.color_hue, genome.color_saturation * 0.6, 0.55);

    ctx.save();

    // Apply transformations:
    // 1. Translate to plant root position (fixed point)
    ctx.translate(x, y);
    // 2. Apply sway rotation around the root
    ctx.rotate(swayRad);
    // 3. Scale based on size multiplier
    ctx.scale(sizeMultiplier, sizeMultiplier);

    // Note: We don't translate back because we want to draw relative to (0,0)
    // which is now at (x,y) with rotation and scaling applied.
    // The geometry was generated at (0,0).

    // Draw shadow
    ctx.save();
    ctx.globalAlpha = 0.15;
    ctx.translate(3, 3);

    for (const seg of segments) {
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = seg.thickness + 1;
        ctx.lineCap = 'round';
        ctx.stroke();
    }
    ctx.restore();

    // Draw stem segments (back to front by depth)
    for (const seg of sortedSegments) {
        // Main stem stroke
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.strokeStyle = stemColor;
        ctx.lineWidth = seg.thickness;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Highlight stroke
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.strokeStyle = highlightColor;
        ctx.lineWidth = seg.thickness * 0.4;
        ctx.lineCap = 'round';
        ctx.stroke();
    }

    // Draw leaves
    for (const leaf of leaves) {
        ctx.save();
        ctx.translate(leaf.x, leaf.y);
        ctx.rotate((leaf.angle * Math.PI) / 180 + Math.PI / 2);

        // Leaf shape (ellipse)
        ctx.beginPath();
        ctx.ellipse(0, -leaf.size / 2, leaf.size * 0.4, leaf.size, 0, 0, Math.PI * 2);
        ctx.fillStyle = leafColor;
        ctx.fill();

        // Leaf vein
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(0, -leaf.size);
        ctx.strokeStyle = highlightColor;
        ctx.lineWidth = 0.5;
        ctx.stroke();

        ctx.restore();
    }

    // Draw nectar glow if ready
    if (nectarReady) {
        // Find topmost point
        let topY = 0; // Relative to (0,0)
        for (const seg of segments) {
            topY = Math.min(topY, seg.y1, seg.y2);
        }

        // Pulsing glow
        const pulse = 0.5 + Math.sin(elapsedTime * 0.005) * 0.3;

        ctx.beginPath();
        const gradient = ctx.createRadialGradient(0, topY - 10, 0, 0, topY - 10, 20);
        gradient.addColorStop(0, `rgba(255, 220, 100, ${pulse})`);
        gradient.addColorStop(0.5, `rgba(255, 200, 50, ${pulse * 0.5})`);
        gradient.addColorStop(1, 'rgba(255, 180, 0, 0)');
        ctx.arc(0, topY - 10, 20, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Nectar droplet
        ctx.beginPath();
        ctx.arc(0, topY - 10, 6, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 220, 100, ${0.8 + pulse * 0.2})`;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255, 255, 200, 0.8)';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    ctx.restore();
}

function renderMandelbrotPlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    elapsedTime: number,
    nectarReady: boolean
): void {
    const cacheKey = plantId;
    const signature = getGenomeSignature(genome);
    const cached = mandelbrotCache.get(cacheKey);

    let texture: HTMLCanvasElement;

    if (!cached || cached.signature !== signature) {
        texture = generateMandelbrotTexture(genome, cacheKey);
        mandelbrotCache.set(cacheKey, { signature, texture });
    } else {
        texture = cached.texture;
    }

    const baseWidth = 140;
    const baseHeight = 160;
    const width = baseWidth * sizeMultiplier;
    const height = baseHeight * sizeMultiplier;

    // Gentle sway
    const sway = Math.sin(elapsedTime * 0.0009 + plantId * 0.7) * 3.5;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((sway * Math.PI) / 180);

    // Draw glowing stem anchor with a subtle vine curl
    const [sr, sg, sb] = hslToRgbTuple(genome.color_hue ?? 0.35, genome.color_saturation ?? 0.9, 0.33);
    const stemGradient = ctx.createLinearGradient(0, 0, 0, -height * 0.55);
    stemGradient.addColorStop(0, `rgba(${sr}, ${sg}, ${sb}, 0.78)`);
    stemGradient.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.12)`);
    ctx.fillStyle = stemGradient;
    ctx.beginPath();
    ctx.moveTo(-width * 0.08, -height * 0.15);
    ctx.quadraticCurveTo(-width * 0.12, -height * 0.4, 0, -height * 0.65);
    ctx.quadraticCurveTo(width * 0.12, -height * 0.35, width * 0.08, -height * 0.02);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = `rgba(${sr}, ${sg}, ${sb}, 0.42)`;
    ctx.lineWidth = width * 0.038;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(0, -height * 0.08);
    ctx.quadraticCurveTo(width * 0.16, -height * 0.38, width * 0.02, -height * 0.68);
    ctx.quadraticCurveTo(-width * 0.18, -height * 0.45, -width * 0.02, -height * 0.18);
    ctx.stroke();

    // Curling tendrils that cradle the fractal leaf
    ctx.strokeStyle = `rgba(${sr}, ${sg}, ${sb}, 0.28)`;
    ctx.lineWidth = width * 0.018;
    const tendrilArc = height * 0.35;
    for (let i = -1; i <= 1; i += 2) {
        ctx.beginPath();
        ctx.moveTo(i * width * 0.1, -height * 0.15);
        ctx.quadraticCurveTo(i * width * 0.35, -height * 0.35, i * width * 0.12, -height * 0.65);
        ctx.quadraticCurveTo(i * width * 0.3, -height * 0.9, i * width * 0.08, -height * 0.95);
        ctx.stroke();

        // small vine curl at the end
        ctx.beginPath();
        ctx.arc(i * width * 0.08, -height * 0.95, tendrilArc * 0.08, Math.PI * 0.3, Math.PI * 1.4, i === 1);
        ctx.stroke();
    }

    // Leaf fronds hugging the Mandelbrot bloom
    ctx.fillStyle = `rgba(${sr}, ${sg}, ${sb}, 0.35)`;
    for (let i = -2; i <= 2; i++) {
        const angle = (i * 11 * Math.PI) / 180;
        const leafHeight = height * 0.19 + Math.abs(i) * 5;
        ctx.save();
        ctx.translate(0, -height * 0.38 + i * 10);
        ctx.rotate(angle);
        ctx.beginPath();
        ctx.ellipse(
            width * 0.14,
            -leafHeight * 0.12,
            width * 0.13,
            leafHeight,
            10 * (Math.PI / 180),
            0,
            Math.PI * 2
        );
        ctx.fill();

        // Draw a light midrib for each cradle leaf
        ctx.strokeStyle = `rgba(${sr}, ${sg}, ${sb}, 0.55)`;
        ctx.lineWidth = width * 0.006;
        ctx.beginPath();
        ctx.moveTo(width * 0.14, -leafHeight * 0.12);
        ctx.quadraticCurveTo(width * 0.05, -leafHeight * 0.35, -width * 0.02, -leafHeight * 0.6);
        ctx.stroke();
        ctx.restore();
    }

    // Draw Mandelbrot texture with a petiole bridge into the stem
    ctx.save();
    ctx.translate(0, -height * 0.04);
    ctx.drawImage(texture, -width / 2, -height, width, height);

    // Petiole sheen to make the fractal bloom read as a living leaf
    const petiole = ctx.createLinearGradient(0, -height * 0.1, 0, -height * 0.8);
    petiole.addColorStop(0, `rgba(${sr}, ${sg}, ${sb}, 0.3)`);
    petiole.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.05)`);
    ctx.strokeStyle = petiole;
    ctx.lineWidth = width * 0.02;
    ctx.beginPath();
    ctx.moveTo(0, -height * 0.12);
    ctx.quadraticCurveTo(0, -height * 0.4, 0, -height * 0.82);
    ctx.stroke();
    ctx.restore();

    // Highlight aura with a softer botanical glow
    const [ar, ag, ab] = hslToRgbTuple(genome.color_hue ?? 0.35, genome.color_saturation ?? 0.85, 0.58);
    const aura = ctx.createRadialGradient(0, -height * 0.8, 12, 0, -height * 0.82, width * 0.7);
    aura.addColorStop(0, `rgba(${ar}, ${ag}, ${ab}, 0.28)`);
    aura.addColorStop(0.4, `rgba(${ar}, ${ag}, ${ab}, 0.12)`);
    aura.addColorStop(1, `rgba(${ar}, ${ag}, ${ab}, 0)`);
    ctx.fillStyle = aura;
    ctx.fillRect(-width / 2, -height, width, height);

    if (nectarReady) {
        const pulse = 0.6 + Math.sin(elapsedTime * 0.005) * 0.25;
        const topY = -height * 0.9;
        ctx.beginPath();
        const glow = ctx.createRadialGradient(0, topY, 4, 0, topY, 28);
        glow.addColorStop(0, `rgba(255, 230, 150, ${pulse})`);
        glow.addColorStop(0.6, `rgba(255, 200, 120, ${pulse * 0.7})`);
        glow.addColorStop(1, 'rgba(255, 180, 100, 0)');
        ctx.arc(0, topY, 16, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(0, topY, 7, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 240, 200, ${0.7 + pulse * 0.3})`;
        ctx.fill();
    }

    ctx.restore();
}

/**
 * Render a Claude plant with golden Julia set spiral aesthetics.
 * Features warm amber colors, Fibonacci spiral arrangement, and glowing particle effects.
 */
function renderClaudePlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    elapsedTime: number,
    nectarReady: boolean
): void {
    const cacheKey = plantId;
    const signature = getGenomeSignature(genome);
    const cached = claudeCache.get(cacheKey);

    let texture: HTMLCanvasElement;

    if (!cached || cached.signature !== signature) {
        texture = generateClaudeTexture(genome, cacheKey);
        claudeCache.set(cacheKey, { signature, texture });
    } else {
        texture = cached.texture;
    }

    const baseWidth = 160;
    const baseHeight = 180;
    const width = baseWidth * sizeMultiplier;
    const height = baseHeight * sizeMultiplier;

    // Golden ratio for aesthetic calculations
    const phi = 1.618033988749895;

    // Elegant swaying motion using multiple harmonics
    const primarySway = Math.sin(elapsedTime * 0.0007 + plantId * 0.5) * 4;
    const secondarySway = Math.sin(elapsedTime * 0.0013 + plantId * 0.8) * 2;
    const breathe = 1 + Math.sin(elapsedTime * 0.001 + plantId * 0.3) * 0.02;
    const sway = primarySway + secondarySway;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((sway * Math.PI) / 180);

    // Get colors from genome
    const [sr, sg, sb] = hslToRgbTuple(genome.color_hue ?? 0.11, genome.color_saturation ?? 0.85, 0.4);
    const [lr, lg, lb] = hslToRgbTuple(genome.color_hue ?? 0.11, genome.color_saturation ?? 0.85, 0.55);

    // Draw elegant curved stem with golden spiral influence
    const stemGradient = ctx.createLinearGradient(0, 0, 0, -height * 0.5);
    stemGradient.addColorStop(0, `rgba(${sr}, ${sg}, ${sb}, 0.85)`);
    stemGradient.addColorStop(0.5, `rgba(${sr}, ${sg}, ${sb}, 0.6)`);
    stemGradient.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.2)`);

    // Main stem with slight curve
    ctx.strokeStyle = stemGradient;
    ctx.lineWidth = width * 0.06;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(0, 0);
    const stemCurve = Math.sin(elapsedTime * 0.0005) * 5;
    ctx.quadraticCurveTo(stemCurve, -height * 0.3, 0, -height * 0.55);
    ctx.stroke();

    // Inner stem highlight
    ctx.strokeStyle = `rgba(${lr}, ${lg}, ${lb}, 0.4)`;
    ctx.lineWidth = width * 0.025;
    ctx.beginPath();
    ctx.moveTo(0, -height * 0.05);
    ctx.quadraticCurveTo(stemCurve * 0.8, -height * 0.28, 0, -height * 0.52);
    ctx.stroke();

    // Fibonacci spiral leaves along stem using golden angle
    const goldenAngle = Math.PI * (3 - Math.sqrt(5)); // ~137.5 degrees
    const leafCount = 8;

    for (let i = 0; i < leafCount; i++) {
        const t = i / leafCount;
        const leafY = -height * (0.1 + t * 0.4);
        const leafAngle = i * goldenAngle;
        const leafSize = width * (0.12 - t * 0.04) * breathe;
        const leafX = stemCurve * t;

        // Animate leaf sway individually
        const leafSway = Math.sin(elapsedTime * 0.002 + i * phi) * 0.2;

        ctx.save();
        ctx.translate(leafX, leafY);
        ctx.rotate(leafAngle + leafSway);

        // Draw golden leaf
        const leafGrad = ctx.createRadialGradient(leafSize * 0.5, 0, 0, leafSize * 0.5, 0, leafSize);
        leafGrad.addColorStop(0, `rgba(${lr}, ${lg}, ${lb}, 0.7)`);
        leafGrad.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.3)`);

        ctx.fillStyle = leafGrad;
        ctx.beginPath();
        ctx.ellipse(leafSize * 0.5, 0, leafSize, leafSize * 0.4, 0, 0, Math.PI * 2);
        ctx.fill();

        // Leaf vein
        ctx.strokeStyle = `rgba(255, 240, 200, 0.3)`;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(leafSize * 0.9, 0);
        ctx.stroke();

        ctx.restore();
    }

    // Draw the Julia set bloom texture
    const bloomY = -height * 0.75;
    const bloomScale = breathe;
    ctx.save();
    ctx.translate(0, bloomY);
    ctx.scale(bloomScale, bloomScale);
    ctx.drawImage(texture, -width / 2, -height * 0.35, width, width);
    ctx.restore();

    // Animated sparkle particles in Fibonacci pattern
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const sparkleTime = elapsedTime * 0.001;

    for (let i = 0; i < 8; i++) {
        const angle = i * goldenAngle + sparkleTime * 0.5;
        const baseRadius = width * 0.25 + (i / 8) * width * 0.15;
        const radiusPulse = Math.sin(elapsedTime * 0.003 + i * phi) * width * 0.05;
        const radius = baseRadius + radiusPulse;

        const sparkleX = Math.cos(angle) * radius;
        const sparkleY = bloomY + Math.sin(angle) * radius * 0.6;
        const sparkleAlpha = 0.4 + Math.sin(elapsedTime * 0.005 + i * 2) * 0.3;
        const sparkleSize = 3 + Math.sin(elapsedTime * 0.004 + i) * 1.5;

        const sparkle = ctx.createRadialGradient(sparkleX, sparkleY, 0, sparkleX, sparkleY, sparkleSize);
        sparkle.addColorStop(0, `rgba(255, 250, 230, ${sparkleAlpha})`);
        sparkle.addColorStop(0.5, `rgba(255, 230, 180, ${sparkleAlpha * 0.5})`);
        sparkle.addColorStop(1, `rgba(255, 200, 120, 0)`);

        ctx.beginPath();
        ctx.arc(sparkleX, sparkleY, sparkleSize, 0, Math.PI * 2);
        ctx.fillStyle = sparkle;
        ctx.fill();
    }
    ctx.restore();

    // Outer glow aura
    const [ar, ag, ab] = hslToRgbTuple(genome.color_hue ?? 0.11, genome.color_saturation ?? 0.85, 0.6);
    const aura = ctx.createRadialGradient(0, bloomY, width * 0.15, 0, bloomY, width * 0.6);
    aura.addColorStop(0, `rgba(${ar}, ${ag}, ${ab}, 0.2)`);
    aura.addColorStop(0.5, `rgba(${ar}, ${ag}, ${ab}, 0.08)`);
    aura.addColorStop(1, `rgba(${ar}, ${ag}, ${ab}, 0)`);
    ctx.fillStyle = aura;
    ctx.fillRect(-width / 2, -height, width, height);

    // Nectar ready indicator
    if (nectarReady) {
        const pulse = 0.7 + Math.sin(elapsedTime * 0.006) * 0.3;
        const topY = bloomY - width * 0.3;

        // Golden nectar glow
        ctx.beginPath();
        const glow = ctx.createRadialGradient(0, topY, 5, 0, topY, 30);
        glow.addColorStop(0, `rgba(255, 245, 200, ${pulse})`);
        glow.addColorStop(0.4, `rgba(255, 225, 150, ${pulse * 0.7})`);
        glow.addColorStop(0.7, `rgba(255, 200, 100, ${pulse * 0.4})`);
        glow.addColorStop(1, 'rgba(255, 180, 80, 0)');
        ctx.arc(0, topY, 25, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        // Nectar droplet with sparkle
        ctx.beginPath();
        ctx.arc(0, topY, 8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 245, 210, ${0.85 + pulse * 0.15})`;
        ctx.fill();

        // Highlight
        ctx.beginPath();
        ctx.arc(-2, topY - 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 250, 0.9)';
        ctx.fill();
    }

    ctx.restore();
}

/**
 * Render an Antigravity plant with ethereal violet vortex patterns.
 */
function renderAntigravityPlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    elapsedTime: number,
    nectarReady: boolean
): void {
    const cacheKey = plantId;
    const signature = getGenomeSignature(genome);
    const cached = antigravityCache.get(cacheKey);

    let texture: HTMLCanvasElement;

    if (!cached || cached.signature !== signature) {
        texture = generateAntigravityTexture(genome, cacheKey);
        antigravityCache.set(cacheKey, { signature, texture });
    } else {
        texture = cached.texture;
    }

    const baseWidth = 150;
    const baseHeight = 170;
    const width = baseWidth * sizeMultiplier;
    const height = baseHeight * sizeMultiplier;

    // Ethereal floating sway - slower and more dreamlike
    const primarySway = Math.sin(elapsedTime * 0.0006 + plantId * 0.4) * 5;
    const secondarySway = Math.sin(elapsedTime * 0.001 + plantId * 0.7) * 2.5;
    const sway = primarySway + secondarySway;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((sway * Math.PI) / 180);

    const [sr, sg, sb] = hslToRgbTuple(genome.color_hue ?? 0.78, genome.color_saturation ?? 0.9, 0.4);
    const [lr, lg, lb] = hslToRgbTuple(genome.color_hue ?? 0.78, genome.color_saturation ?? 0.9, 0.6);

    // Ethereal stem with floating effect
    const stemGradient = ctx.createLinearGradient(0, 0, 0, -height * 0.5);
    stemGradient.addColorStop(0, `rgba(${sr}, ${sg}, ${sb}, 0.7)`);
    stemGradient.addColorStop(0.5, `rgba(${sr}, ${sg}, ${sb}, 0.5)`);
    stemGradient.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.2)`);

    ctx.strokeStyle = stemGradient;
    ctx.lineWidth = width * 0.05;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(0, 0);
    const stemWobble = Math.sin(elapsedTime * 0.0008) * 6;
    ctx.bezierCurveTo(stemWobble, -height * 0.2, -stemWobble, -height * 0.4, 0, -height * 0.55);
    ctx.stroke();

    // Floating crystal-like leaves
    for (let i = 0; i < 6; i++) {
        const t = i / 6;
        const leafY = -height * (0.1 + t * 0.45);
        const leafAngle = (i * Math.PI * 2) / 6 + Math.sin(elapsedTime * 0.002 + i) * 0.3;
        const leafSize = width * (0.1 - t * 0.03);

        ctx.save();
        ctx.translate(0, leafY);
        ctx.rotate(leafAngle);

        // Diamond-shaped leaves
        ctx.beginPath();
        ctx.moveTo(leafSize, 0);
        ctx.lineTo(0, leafSize * 0.4);
        ctx.lineTo(-leafSize * 0.3, 0);
        ctx.lineTo(0, -leafSize * 0.4);
        ctx.closePath();

        const leafGrad = ctx.createLinearGradient(-leafSize * 0.3, 0, leafSize, 0);
        leafGrad.addColorStop(0, `rgba(${lr}, ${lg}, ${lb}, 0.3)`);
        leafGrad.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.6)`);
        ctx.fillStyle = leafGrad;
        ctx.fill();

        ctx.restore();
    }

    // Draw the Burning Ship texture
    const bloomY = -height * 0.72;
    ctx.drawImage(texture, -width / 2, bloomY - height * 0.35, width, width);

    // Vortex glow aura
    const aura = ctx.createRadialGradient(0, bloomY, width * 0.1, 0, bloomY, width * 0.55);
    aura.addColorStop(0, `rgba(${lr}, ${lg}, ${lb}, 0.25)`);
    aura.addColorStop(0.5, `rgba(${sr}, ${sg}, ${sb}, 0.1)`);
    aura.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0)`);
    ctx.fillStyle = aura;
    ctx.fillRect(-width / 2, -height, width, height);

    // Floating particles rising upward (antigravity effect)
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 8; i++) {
        const particlePhase = (elapsedTime * 0.001 + i * 0.5) % 2;
        const particleY = bloomY + (1 - particlePhase) * height * 0.4;
        const particleX = Math.sin(elapsedTime * 0.002 + i * 1.5) * width * 0.2;
        const particleAlpha = Math.sin(particlePhase * Math.PI) * 0.6;

        const particle = ctx.createRadialGradient(particleX, particleY, 0, particleX, particleY, 4);
        particle.addColorStop(0, `rgba(220, 180, 255, ${particleAlpha})`);
        particle.addColorStop(1, `rgba(180, 120, 220, 0)`);
        ctx.beginPath();
        ctx.arc(particleX, particleY, 4, 0, Math.PI * 2);
        ctx.fillStyle = particle;
        ctx.fill();
    }
    ctx.restore();

    if (nectarReady) {
        const pulse = 0.65 + Math.sin(elapsedTime * 0.005) * 0.3;
        const topY = bloomY - width * 0.25;

        ctx.beginPath();
        const glow = ctx.createRadialGradient(0, topY, 4, 0, topY, 25);
        glow.addColorStop(0, `rgba(220, 180, 255, ${pulse})`);
        glow.addColorStop(0.5, `rgba(180, 140, 220, ${pulse * 0.6})`);
        glow.addColorStop(1, 'rgba(150, 100, 200, 0)');
        ctx.arc(0, topY, 20, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(0, topY, 7, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(230, 200, 255, ${0.8 + pulse * 0.2})`;
        ctx.fill();
    }

    ctx.restore();
}

function drawCodexSegment(
    ctx: CanvasRenderingContext2D,
    segment: FractalSegment,
    sizeMultiplier: number,
    stroke: string,
    accent: string,
    striate: boolean,
    detailScale: number
): void {
    const sx1 = segment.x1 * sizeMultiplier;
    const sy1 = segment.y1 * sizeMultiplier;
    const sx2 = segment.x2 * sizeMultiplier;
    const sy2 = segment.y2 * sizeMultiplier;

    const dx = sx2 - sx1;
    const dy = sy2 - sy1;
    const length = Math.max(1, Math.hypot(dx, dy));
    const nx = -dy / length;
    const ny = dx / length;

    ctx.strokeStyle = stroke;
    ctx.lineWidth = segment.thickness * sizeMultiplier * (0.45 + 0.3 * detailScale);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(sx1, sy1);
    ctx.lineTo(sx2, sy2);
    ctx.stroke();

    if (!striate || ctx.lineWidth < 2 || detailScale < 0.45) {
        return;
    }

    ctx.strokeStyle = accent;
    ctx.lineWidth = Math.max(1, ctx.lineWidth * (0.25 + 0.25 * detailScale));
    const stripeBase = Math.max(2, Math.floor((length / Math.max(6, ctx.lineWidth * 2)) * detailScale));
    const cappedStripes = Math.min(10, stripeBase);
    for (let i = 0; i < cappedStripes; i++) {
        const t = i / cappedStripes;
        const offset = (i % 2 === 0 ? 1 : -1) * ctx.lineWidth * 0.45;
        const px = sx1 + dx * t;
        const py = sy1 + dy * t;
        ctx.beginPath();
        ctx.moveTo(px + nx * offset, py + ny * offset);
        ctx.lineTo(px + nx * offset * 0.25, py + ny * offset * 0.25);
        ctx.stroke();
    }
}

function renderGptCodexPlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    iterations: number,
    elapsedTime: number,
    nectarReady: boolean
): void {
    const cacheKey = plantId;
    const genomeSignature = `${iterations}:${getGenomeSignature(genome)}`;
    const cached = gptCodexCache.get(cacheKey);

    let segments: FractalSegment[];
    let leaves: FractalLeaf[];
    let sortedSegments: FractalSegment[];

    const needsRegeneration = !cached || cached.signature !== genomeSignature;

    if (needsRegeneration) {
        const lsystemString = generateLSystemString(
            genome.axiom,
            genome.production_rules,
            iterations,
            cacheKey
        );

        const baseLength = 12 + 1.0 * 10;
        const result = interpretLSystem(
            lsystemString,
            genome.angle + (seededRandom(cacheKey) - 0.5) * 6,
            genome.length_ratio,
            genome.curve_factor,
            genome.stem_thickness,
            genome.leaf_density,
            baseLength,
            0,
            0,
            cacheKey
        );

        segments = result.segments;
        leaves = result.leaves;
        sortedSegments = [...segments].sort((a, b) => a.depth - b.depth);

        gptCodexCache.set(cacheKey, {
            iterations,
            signature: genomeSignature,
            segments,
            leaves,
            sortedSegments,
        });
    } else {
        segments = cached!.segments;
        leaves = cached!.leaves;
        sortedSegments = cached!.sortedSegments;
    }

    const complexityScore = segments.length + leaves.length * 0.5;
    const detailScale = Math.max(0.35, Math.min(1, 500 / Math.max(1, complexityScore)));

    const swayPrimary = Math.sin(elapsedTime * 0.0008 + plantId * 0.4) * 2.5;
    const swaySecondary = Math.sin(elapsedTime * 0.0014 + plantId * 0.7) * 1.5;
    const sway = swayPrimary + swaySecondary;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((sway * Math.PI) / 180);

    const baseHue = genome.color_hue ?? 0.34;
    const accentHue = Math.min(1, baseHue + 0.22);
    const [tr, tg, tb] = hslToRgbTuple(baseHue, genome.color_saturation ?? 0.75, 0.32);
    const [rr, rg, rb] = hslToRgbTuple(baseHue - 0.02, (genome.color_saturation ?? 0.75) * 0.95, 0.28);
    const [ar, ag, ab] = hslToRgbTuple(accentHue, (genome.color_saturation ?? 0.75) * 0.9, 0.55);
    const trunkColor = `rgba(${tr}, ${tg}, ${tb}, 0.9)`;
    const rootColor = `rgba(${rr}, ${rg}, ${rb}, 0.95)`;
    const barkAccent = `rgba(${ar}, ${ag}, ${ab}, ${nectarReady ? 0.9 : 0.65})`;
    const leafColor = hslToRgb(baseHue + 0.03, genome.color_saturation ?? 0.78, 0.42);
    const leafHighlight = hslToRgb(accentHue, (genome.color_saturation ?? 0.78) * 0.9, 0.58);

    // Draw branches then roots to keep canopy readable
    for (const seg of sortedSegments) {
        const isRoot = seg.kind === 'root';
        const stroke = isRoot ? rootColor : trunkColor;
        const accent = isRoot ? rootColor : barkAccent;
        drawCodexSegment(
            ctx,
            seg,
            sizeMultiplier,
            stroke,
            accent,
            seg.thickness * sizeMultiplier > 3,
            detailScale
        );
    }

    // Pulsing nectar nodes along junctions
    if (nectarReady) {
        const pulse = 0.6 + 0.4 * (Math.sin(elapsedTime * 0.006 + plantId) * 0.5 + 0.5);
        ctx.fillStyle = `rgba(${ar}, ${ag}, ${ab}, ${0.45 * pulse})`;
        const nodeStride = Math.max(
            4,
            Math.floor(sortedSegments.length / 14) * Math.max(1, Math.round(1 / detailScale))
        );
        for (let i = 0; i < sortedSegments.length; i += nodeStride) {
            const seg = sortedSegments[i];
            const px = (seg.x2 + seg.x1) * 0.5 * sizeMultiplier;
            const py = (seg.y2 + seg.y1) * 0.5 * sizeMultiplier;
            ctx.beginPath();
            ctx.ellipse(px, py, 4 * pulse, 4 * pulse, 0, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // Broad leaves with subtle oscillation
    const leafSway = Math.sin(elapsedTime * 0.001 + plantId * 0.3) * 6;
    const leafStep = Math.max(1, Math.round(1 / detailScale));
    for (let i = 0; i < leaves.length; i += leafStep) {
        const leaf = leaves[i];
        ctx.save();
        ctx.translate(leaf.x * sizeMultiplier, leaf.y * sizeMultiplier);
        ctx.rotate(((leaf.angle + leafSway) * Math.PI) / 180);
        ctx.scale(sizeMultiplier * 1.15, sizeMultiplier * 1.15);

        const grad = ctx.createLinearGradient(-leaf.size, 0, leaf.size, 0);
        grad.addColorStop(0, `${leafColor}`);
        grad.addColorStop(1, `${leafHighlight}`);
        ctx.fillStyle = grad;

        ctx.beginPath();
        ctx.ellipse(0, 0, leaf.size * 1.2, leaf.size * 0.65, 0, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    ctx.restore();
}

/**
 * Render a GPT plant with neural network-inspired electric cyan patterns.
 */
function renderGptPlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    elapsedTime: number,
    nectarReady: boolean
): void {
    const cacheKey = plantId;
    const signature = getGenomeSignature(genome);
    const cached = gptCache.get(cacheKey);

    let texture: HTMLCanvasElement;

    if (!cached || cached.signature !== signature) {
        texture = generateGptTexture(genome, cacheKey);
        gptCache.set(cacheKey, { signature, texture });
    } else {
        texture = cached.texture;
    }

    const baseWidth = 155;
    const baseHeight = 175;
    const width = baseWidth * sizeMultiplier;
    const height = baseHeight * sizeMultiplier;

    // Quick, electric sway
    const primarySway = Math.sin(elapsedTime * 0.0009 + plantId * 0.6) * 3.5;
    const secondarySway = Math.sin(elapsedTime * 0.0018 + plantId * 0.9) * 1.8;
    const sway = primarySway + secondarySway;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((sway * Math.PI) / 180);

    const [sr, sg, sb] = hslToRgbTuple(genome.color_hue ?? 0.52, genome.color_saturation ?? 0.9, 0.35);
    const [lr, lg, lb] = hslToRgbTuple(genome.color_hue ?? 0.52, genome.color_saturation ?? 0.9, 0.55);

    // Neural network stem with branching
    const stemGradient = ctx.createLinearGradient(0, 0, 0, -height * 0.5);
    stemGradient.addColorStop(0, `rgba(${sr}, ${sg}, ${sb}, 0.85)`);
    stemGradient.addColorStop(0.5, `rgba(${sr}, ${sg}, ${sb}, 0.6)`);
    stemGradient.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0.25)`);

    ctx.strokeStyle = stemGradient;
    ctx.lineWidth = width * 0.055;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(0, -height * 0.55);
    ctx.stroke();

    // Branch connections (neural network style)
    ctx.strokeStyle = `rgba(${lr}, ${lg}, ${lb}, 0.3)`;
    ctx.lineWidth = width * 0.02;
    for (let i = 0; i < 4; i++) {
        const branchY = -height * (0.15 + i * 0.1);
        const branchLen = width * (0.15 - i * 0.02);
        const side = i % 2 === 0 ? 1 : -1;

        ctx.beginPath();
        ctx.moveTo(0, branchY);
        ctx.lineTo(side * branchLen, branchY - height * 0.05);
        ctx.stroke();
    }

    // Node points along stem
    ctx.fillStyle = `rgba(${lr}, ${lg}, ${lb}, 0.7)`;
    for (let i = 0; i < 5; i++) {
        const nodeY = -height * (0.1 + i * 0.1);
        ctx.beginPath();
        ctx.arc(0, nodeY, width * 0.025, 0, Math.PI * 2);
        ctx.fill();
    }

    // Draw the Tricorn fractal texture
    const bloomY = -height * 0.73;
    ctx.drawImage(texture, -width / 2, bloomY - height * 0.32, width, width);

    // Electric glow aura
    const aura = ctx.createRadialGradient(0, bloomY, width * 0.12, 0, bloomY, width * 0.5);
    aura.addColorStop(0, `rgba(${lr}, ${lg}, ${lb}, 0.22)`);
    aura.addColorStop(0.4, `rgba(${sr}, ${sg}, ${sb}, 0.1)`);
    aura.addColorStop(1, `rgba(${sr}, ${sg}, ${sb}, 0)`);
    ctx.fillStyle = aura;
    ctx.fillRect(-width / 2, -height, width, height);

    // Electric sparks
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const sparkCount = 6;
    for (let i = 0; i < sparkCount; i++) {
        const sparkPhase = (elapsedTime * 0.003 + i * 0.7) % (Math.PI * 2);
        const sparkRadius = width * 0.25 + Math.sin(sparkPhase * 2) * width * 0.08;
        const sparkAngle = (i / sparkCount) * Math.PI * 2 + elapsedTime * 0.001;
        const sparkX = Math.cos(sparkAngle) * sparkRadius;
        const sparkY = bloomY + Math.sin(sparkAngle) * sparkRadius * 0.5;
        const sparkAlpha = 0.3 + Math.sin(sparkPhase) * 0.3;

        const spark = ctx.createRadialGradient(sparkX, sparkY, 0, sparkX, sparkY, 3);
        spark.addColorStop(0, `rgba(150, 255, 255, ${sparkAlpha})`);
        spark.addColorStop(0.5, `rgba(80, 200, 240, ${sparkAlpha * 0.5})`);
        spark.addColorStop(1, 'rgba(50, 150, 200, 0)');
        ctx.beginPath();
        ctx.arc(sparkX, sparkY, 3, 0, Math.PI * 2);
        ctx.fillStyle = spark;
        ctx.fill();
    }
    ctx.restore();

    if (nectarReady) {
        const pulse = 0.7 + Math.sin(elapsedTime * 0.006) * 0.3;
        const topY = bloomY - width * 0.28;

        ctx.beginPath();
        const glow = ctx.createRadialGradient(0, topY, 5, 0, topY, 28);
        glow.addColorStop(0, `rgba(150, 255, 255, ${pulse})`);
        glow.addColorStop(0.5, `rgba(100, 220, 240, ${pulse * 0.65})`);
        glow.addColorStop(1, 'rgba(50, 180, 220, 0)');
        ctx.arc(0, topY, 22, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(0, topY, 8, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180, 255, 255, ${0.85 + pulse * 0.15})`;
        ctx.fill();

        // Electric highlight
        ctx.beginPath();
        ctx.arc(-2, topY - 2, 3, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(220, 255, 255, 0.9)';
        ctx.fill();
    }

    ctx.restore();
}

/**
 * Render a Sonnet 4.5 plant - elegant botanical fern with coral/terracotta hues.
 * Uses proper L-system rules to create actual plant-like structures.
 */
function renderSonnetPlant(
    ctx: CanvasRenderingContext2D,
    plantId: number,
    genome: PlantGenomeData,
    x: number,
    y: number,
    sizeMultiplier: number,
    iterations: number,
    elapsedTime: number,
    nectarReady: boolean
): void {
    const cacheKey = plantId;
    const genomeSignature = `${iterations}:${getGenomeSignature(genome)}`;
    const cached = sonnetCache.get(cacheKey);

    let segments: FractalSegment[];
    let leaves: FractalLeaf[];
    let sortedSegments: FractalSegment[];

    const needsRegeneration = !cached || cached.signature !== genomeSignature;

    if (needsRegeneration) {
        // Generate L-system string
        const lsystemString = generateLSystemString(
            genome.axiom,
            genome.production_rules,
            iterations,
            cacheKey
        );

        const baseLength = 10 + 1.0 * 12;

        const result = interpretLSystem(
            lsystemString,
            genome.angle,
            genome.length_ratio,
            genome.curve_factor,
            genome.stem_thickness,
            genome.leaf_density,
            baseLength,
            0,
            0,
            cacheKey
        );

        segments = result.segments;
        leaves = result.leaves;
        sortedSegments = [...segments].sort((a, b) => a.depth - b.depth);

        sonnetCache.set(cacheKey, {
            iterations,
            signature: genomeSignature,
            segments,
            leaves,
            sortedSegments,
        });
    } else {
        segments = cached!.segments;
        leaves = cached!.leaves;
        sortedSegments = cached!.sortedSegments;
    }

    // Elegant multi-frequency swaying - smoother and more graceful than base
    const plantSeed = plantId * 17 + x * 0.5 + y * 0.3;
    const primarySway = Math.sin(elapsedTime * 0.0004 + plantSeed * 0.01) * 4;
    const secondarySway = Math.sin(elapsedTime * 0.001 + plantSeed * 0.02) * 2;
    const tertiarySway = Math.sin(elapsedTime * 0.0007 + plantSeed * 0.015) * 1;
    const swayAngle = primarySway + secondarySway + tertiarySway;
    const swayRad = (swayAngle * Math.PI) / 180;

    // Coral/terracotta color palette
    const stemColor = hslToRgb(genome.color_hue, genome.color_saturation * 0.85, 0.3);
    const stemHighlight = hslToRgb(genome.color_hue, genome.color_saturation * 0.7, 0.45);
    const leafColor = hslToRgb(genome.color_hue, genome.color_saturation, 0.45);
    const leafHighlight = hslToRgb(genome.color_hue, genome.color_saturation * 0.6, 0.6);
    const [lr, lg, lb] = hslToRgbTuple(genome.color_hue, genome.color_saturation, 0.5);

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(swayRad);
    ctx.scale(sizeMultiplier, sizeMultiplier);

    // Draw soft shadow
    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.translate(4, 4);
    for (const seg of segments) {
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = seg.thickness + 2;
        ctx.lineCap = 'round';
        ctx.stroke();
    }
    ctx.restore();

    // Draw stem segments with gradient effect
    for (const seg of sortedSegments) {
        // Main stem with thickness variation
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.strokeStyle = stemColor;
        ctx.lineWidth = seg.thickness;
        ctx.lineCap = 'round';
        ctx.stroke();

        // Inner highlight for depth
        ctx.beginPath();
        ctx.moveTo(seg.x1, seg.y1);
        ctx.lineTo(seg.x2, seg.y2);
        ctx.strokeStyle = stemHighlight;
        ctx.lineWidth = seg.thickness * 0.35;
        ctx.lineCap = 'round';
        ctx.stroke();
    }

    // Draw elegant fern-like leaves
    for (const leaf of leaves) {
        ctx.save();
        ctx.translate(leaf.x, leaf.y);
        ctx.rotate((leaf.angle * Math.PI) / 180 + Math.PI / 2);

        // Add subtle individual leaf animation
        const leafSway = Math.sin(elapsedTime * 0.002 + leaf.x * 0.1) * 0.1;
        ctx.rotate(leafSway);

        // Fern frond shape - more elongated and elegant
        const leafScale = leaf.size * 1.2;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.bezierCurveTo(
            leafScale * 0.3, -leafScale * 0.2,
            leafScale * 0.5, -leafScale * 0.4,
            leafScale * 0.2, -leafScale * 0.9
        );
        ctx.bezierCurveTo(
            0, -leafScale * 0.6,
            -leafScale * 0.1, -leafScale * 0.3,
            0, 0
        );
        ctx.fillStyle = leafColor;
        ctx.fill();

        // Leaf vein
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.quadraticCurveTo(leafScale * 0.15, -leafScale * 0.4, leafScale * 0.15, -leafScale * 0.75);
        ctx.strokeStyle = leafHighlight;
        ctx.lineWidth = 0.6;
        ctx.stroke();

        ctx.restore();
    }

    // Add subtle ambient glow around the plant
    const glowIntensity = 0.08 + Math.sin(elapsedTime * 0.001) * 0.03;
    let topY = 0;
    for (const seg of segments) {
        topY = Math.min(topY, seg.y1, seg.y2);
    }
    const centerY = topY / 2;

    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const aura = ctx.createRadialGradient(0, centerY, 10, 0, centerY, 80);
    aura.addColorStop(0, `rgba(${lr}, ${lg}, ${lb}, ${glowIntensity})`);
    aura.addColorStop(0.5, `rgba(${lr}, ${lg}, ${lb}, ${glowIntensity * 0.5})`);
    aura.addColorStop(1, `rgba(${lr}, ${lg}, ${lb}, 0)`);
    ctx.fillStyle = aura;
    ctx.fillRect(-100, topY - 20, 200, -topY + 40);
    ctx.restore();

    // Draw nectar glow if ready
    if (nectarReady) {
        const pulse = 0.6 + Math.sin(elapsedTime * 0.005) * 0.35;

        ctx.beginPath();
        const gradient = ctx.createRadialGradient(0, topY - 12, 0, 0, topY - 12, 25);
        gradient.addColorStop(0, `rgba(255, 200, 160, ${pulse})`);
        gradient.addColorStop(0.4, `rgba(255, 170, 130, ${pulse * 0.6})`);
        gradient.addColorStop(1, 'rgba(255, 150, 100, 0)');
        ctx.arc(0, topY - 12, 25, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Nectar droplet with coral tint
        ctx.beginPath();
        ctx.arc(0, topY - 12, 7, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 210, 180, ${0.85 + pulse * 0.15})`;
        ctx.fill();

        // Highlight
        ctx.beginPath();
        ctx.arc(-2, topY - 14, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 245, 235, 0.9)';
        ctx.fill();
    }

    ctx.restore();
}

/**
 * Floral genome data for nectar rendering.
 */
export interface FloralGenome {
    floral_type?: string;
    floral_petals?: number;
    floral_layers?: number;
    floral_spin?: number;
    floral_hue?: number;
    floral_saturation?: number;
}

/**
 * Render plant nectar (the collectible item) with floral fractal.
 *
 * @param sourcePlantId - ID of the parent plant (for sway seed)
 * @param sourcePlantX - X position of the parent plant's center base
 * @param sourcePlantY - Y position of the parent plant's base
 * @param floralGenome - Floral genome parameters from parent plant
 */
export function renderPlantNectar(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    width: number,
    height: number,
    elapsedTime: number,
    sourcePlantId?: number,
    sourcePlantX?: number,
    sourcePlantY?: number,
    floralGenome?: FloralGenome
): void {
    ctx.save();

    // Pulsing animation
    const pulse = 1 + Math.sin(elapsedTime * 0.008) * 0.1;
    const size = Math.min(width, height) * pulse;

    let drawX = x;
    let drawY = y;

    // Apply sway offset if we have parent plant info
    // This makes the nectar sway in sync with its parent plant
    if (sourcePlantId !== undefined && sourcePlantX !== undefined && sourcePlantY !== undefined) {
        // Calculate sway using the same formula as the plant renderer
        const plantSeed = sourcePlantId * 17 + sourcePlantX * 0.5 + sourcePlantY * 0.3;
        const primarySway = Math.sin(elapsedTime * 0.0005 + plantSeed * 0.01) * 5;
        const secondarySway = Math.sin(elapsedTime * 0.0012 + plantSeed * 0.02) * 2.5;
        const tertiarySway = Math.sin(elapsedTime * 0.0008 + plantSeed * 0.015) * 1.5;
        const swayAngle = primarySway + secondarySway + tertiarySway;
        const swayRad = (swayAngle * Math.PI) / 180;

        // Calculate the distance from plant base to nectar
        const distanceFromBase = sourcePlantY - y;  // Positive since nectar is above base

        // Apply rotation offset: the nectar moves horizontally based on sway angle and distance
        // sin(angle) * distance gives the horizontal offset at the tip
        const swayOffsetX = Math.sin(swayRad) * distanceFromBase;
        // cos(angle) gives small vertical adjustment (negligible for small angles)
        const swayOffsetY = (1 - Math.cos(swayRad)) * distanceFromBase;

        drawX = x + swayOffsetX;
        drawY = y - swayOffsetY;
    }

    // Draw floral fractal based on genome
    drawFloralFractal(ctx, drawX, drawY, size, elapsedTime, floralGenome);

    ctx.restore();
}

/**
 * Draw a floral fractal based on genome parameters.
 */
function drawFloralFractal(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    size: number,
    elapsedTime: number,
    genome?: FloralGenome
): void {
    const type = genome?.floral_type ?? 'spiral';
    const petals = genome?.floral_petals ?? 5;
    const layers = genome?.floral_layers ?? 3;
    const spin = genome?.floral_spin ?? 0.3;
    // Default to amber/gold (0.12) instead of pink (0.95)
    const hue = genome?.floral_hue ?? 0.12;
    const saturation = genome?.floral_saturation ?? 0.8;

    switch (type) {
        case 'mandelbrot':
            drawMandelbrotFlower(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'dahlia':
            drawDahliaFlower(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'sunflower':
            drawSunflowerFractal(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'chrysanthemum':
            drawChrysanthemum(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'spiral':
            drawSpiralFractal(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'julia':
            drawJuliaOrb(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'vortex':
            drawVortex(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'starburst':
            drawStarburst(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'hypno':
            drawHypnoRings(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
        case 'rose':
        default:
            drawRoseCurve(ctx, x, y, size, petals, layers, spin, hue, saturation, elapsedTime);
            break;
    }
}

/**
 * Draw a rose curve (rhodonea) - classic mathematical flower.
 */
function drawRoseCurve(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    petals: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0003 * spin;
    const k = petals / 2;  // Rose curve parameter

    // Draw layers from outside in
    for (let layer = layers; layer >= 1; layer--) {
        const layerSize = size * (layer / layers) * 0.8;
        const layerLight = 0.35 + (layer / layers) * 0.25;
        const color = hslToRgb(hue, saturation, layerLight);

        ctx.beginPath();
        for (let theta = 0; theta <= Math.PI * 2; theta += 0.02) {
            const r = layerSize * Math.cos(k * theta + rotation + layer * 0.3);
            const px = x + r * Math.cos(theta);
            const py = y + r * Math.sin(theta);
            if (theta === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.7 + layer * 0.1;
        ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Center dot
    ctx.beginPath();
    ctx.arc(x, y, size * 0.08, 0, Math.PI * 2);
    ctx.fillStyle = hslToRgb(hue + 0.1, saturation, 0.7);
    ctx.fill();
}

/**
 * Draw a mandelbrot-inspired flower with fractal petals.
 */
function drawMandelbrotFlower(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    petals: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0002 * spin;

    // Draw fractal petal shapes inspired by mandelbrot boundary
    for (let layer = layers; layer >= 1; layer--) {
        const layerSize = size * (layer / layers) * 0.7;
        const layerLight = 0.3 + (layer / layers) * 0.3;

        for (let p = 0; p < petals; p++) {
            const angle = (p / petals) * Math.PI * 2 + rotation;
            const color = hslToRgb(hue + p * 0.02, saturation, layerLight);

            ctx.beginPath();
            // Create cardioid-like petal shape
            for (let t = 0; t <= Math.PI * 2; t += 0.1) {
                // Cardioid formula with modifications
                const r = layerSize * 0.3 * (1 - Math.cos(t)) * (1 + 0.3 * Math.sin(t * 3));
                const px = x + Math.cos(angle) * r * 1.5 + Math.cos(angle + t) * r * 0.5;
                const py = y + Math.sin(angle) * r * 1.5 + Math.sin(angle + t) * r * 0.5;
                if (t === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
            }
            ctx.closePath();
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.6 + layer * 0.1;
            ctx.fill();
        }
    }
    ctx.globalAlpha = 1;

    // Fractal center
    ctx.beginPath();
    ctx.arc(x, y, size * 0.1, 0, Math.PI * 2);
    const centerGrad = ctx.createRadialGradient(x, y, 0, x, y, size * 0.1);
    centerGrad.addColorStop(0, hslToRgb(hue, saturation, 0.8));
    centerGrad.addColorStop(1, hslToRgb(hue, saturation, 0.4));
    ctx.fillStyle = centerGrad;
    ctx.fill();
}

/**
 * Draw a dahlia-like flower with pointed petals.
 */
function drawDahliaFlower(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    petals: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.00025 * spin;

    // Draw layered pointed petals
    for (let layer = layers; layer >= 1; layer--) {
        const layerSize = size * (layer / layers) * 0.75;
        const petalCount = petals + (layers - layer) * 2;  // More petals in inner layers
        const layerRotation = rotation + layer * 0.15;

        for (let p = 0; p < petalCount; p++) {
            const angle = (p / petalCount) * Math.PI * 2 + layerRotation;
            const layerLight = 0.35 + (layer / layers) * 0.25;
            const color = hslToRgb(hue + layer * 0.01, saturation, layerLight);

            // Draw pointed petal
            ctx.beginPath();
            ctx.moveTo(x, y);
            const tipX = x + Math.cos(angle) * layerSize;
            const tipY = y + Math.sin(angle) * layerSize;
            const width = layerSize * 0.25;
            const cp1x = x + Math.cos(angle - 0.2) * layerSize * 0.5;
            const cp1y = y + Math.sin(angle - 0.2) * layerSize * 0.5;
            const cp2x = x + Math.cos(angle + 0.2) * layerSize * 0.5;
            const cp2y = y + Math.sin(angle + 0.2) * layerSize * 0.5;

            ctx.quadraticCurveTo(cp1x, cp1y, tipX, tipY);
            ctx.quadraticCurveTo(cp2x, cp2y, x, y);
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.75;
            ctx.fill();
        }
    }
    ctx.globalAlpha = 1;

    // Center
    ctx.beginPath();
    ctx.arc(x, y, size * 0.12, 0, Math.PI * 2);
    ctx.fillStyle = hslToRgb(hue + 0.05, saturation * 0.8, 0.65);
    ctx.fill();
}

/**
 * Draw a sunflower with fibonacci spiral pattern.
 */
function drawSunflowerFractal(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    petals: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0002 * spin;
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));  // ~137.5 degrees

    // Draw outer petals
    for (let p = 0; p < petals; p++) {
        const angle = (p / petals) * Math.PI * 2 + rotation;
        const petalLength = size * 0.8;
        const color = hslToRgb(0.12 + p * 0.005, 0.9, 0.55);  // Yellow-orange

        ctx.beginPath();
        ctx.ellipse(
            x + Math.cos(angle) * petalLength * 0.5,
            y + Math.sin(angle) * petalLength * 0.5,
            petalLength * 0.5,
            petalLength * 0.15,
            angle,
            0, Math.PI * 2
        );
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.85;
        ctx.fill();
    }

    // Draw fibonacci spiral seeds in center
    const centerSize = size * 0.35;
    const seedCount = layers * 15;
    for (let i = 0; i < seedCount; i++) {
        const angle = i * goldenAngle + rotation * 2;
        const r = centerSize * Math.sqrt(i / seedCount);
        const seedX = x + Math.cos(angle) * r;
        const seedY = y + Math.sin(angle) * r;
        const seedSize = (size * 0.03) * (1 - i / seedCount * 0.5);

        ctx.beginPath();
        ctx.arc(seedX, seedY, seedSize, 0, Math.PI * 2);
        ctx.fillStyle = hslToRgb(hue, saturation, 0.25 + (i / seedCount) * 0.2);
        ctx.globalAlpha = 0.9;
        ctx.fill();
    }
    ctx.globalAlpha = 1;
}

/**
 * Draw a chrysanthemum with many thin petals.
 */
function drawChrysanthemum(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    petals: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.00015 * spin;
    const totalPetals = petals * 3;  // Chrysanthemums have many petals

    // Draw thin curved petals in layers
    for (let layer = layers; layer >= 1; layer--) {
        const layerSize = size * (0.4 + layer / layers * 0.5);
        const layerPetals = totalPetals + (layers - layer) * 4;

        for (let p = 0; p < layerPetals; p++) {
            const angle = (p / layerPetals) * Math.PI * 2 + rotation + layer * 0.1;
            const curve = Math.sin(p * 0.5) * 0.3;
            const layerLight = 0.4 + (layer / layers) * 0.25;
            const color = hslToRgb(hue + layer * 0.015, saturation, layerLight);

            ctx.beginPath();
            ctx.moveTo(x, y);

            // Curved thin petal
            const tipX = x + Math.cos(angle + curve) * layerSize;
            const tipY = y + Math.sin(angle + curve) * layerSize;
            const cpX = x + Math.cos(angle) * layerSize * 0.6;
            const cpY = y + Math.sin(angle) * layerSize * 0.6;

            ctx.quadraticCurveTo(cpX, cpY, tipX, tipY);
            ctx.strokeStyle = color;
            ctx.lineWidth = size * 0.02 * (layer / layers);
            ctx.globalAlpha = 0.7;
            ctx.stroke();
        }
    }
    ctx.globalAlpha = 1;

    // Fluffy center
    const centerGrad = ctx.createRadialGradient(x, y, 0, x, y, size * 0.15);
    centerGrad.addColorStop(0, hslToRgb(hue + 0.05, saturation * 0.7, 0.75));
    centerGrad.addColorStop(1, hslToRgb(hue, saturation, 0.5));
    ctx.beginPath();
    ctx.arc(x, y, size * 0.15, 0, Math.PI * 2);
    ctx.fillStyle = centerGrad;
    ctx.fill();
}

/**
 * Draw a psychedelic spiral fractal.
 */
function drawSpiralFractal(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    arms: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.001 * spin;
    const numArms = Math.max(2, arms);

    // Draw spiral arms
    for (let arm = 0; arm < numArms; arm++) {
        const armAngle = (arm / numArms) * Math.PI * 2;

        ctx.beginPath();
        for (let t = 0; t < layers * 2; t += 0.05) {
            const angle = armAngle + t * 1.5 + rotation;
            const r = size * 0.1 * t;
            const px = x + Math.cos(angle) * r;
            const py = y + Math.sin(angle) * r;

            if (t === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }

        // Rainbow shift along each arm
        const armHue = (hue + arm * 0.1) % 1;
        ctx.strokeStyle = hslToRgb(armHue, saturation, 0.5);
        ctx.lineWidth = size * 0.06;
        ctx.lineCap = 'round';
        ctx.globalAlpha = 0.8;
        ctx.stroke();
    }

    // Glowing center
    const centerGrad = ctx.createRadialGradient(x, y, 0, x, y, size * 0.15);
    centerGrad.addColorStop(0, hslToRgb(hue, 1, 0.9));
    centerGrad.addColorStop(1, hslToRgb(hue, saturation, 0.3));
    ctx.beginPath();
    ctx.arc(x, y, size * 0.12, 0, Math.PI * 2);
    ctx.fillStyle = centerGrad;
    ctx.globalAlpha = 1;
    ctx.fill();
}

/**
 * Draw a Julia set inspired orb with swirling colors.
 */
function drawJuliaOrb(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    complexity: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0004 * spin;
    const iterations = Math.max(2, layers);

    // Draw concentric distorted rings
    for (let ring = iterations; ring >= 1; ring--) {
        const ringSize = size * (ring / iterations) * 0.8;
        const distortion = Math.sin(rotation * 2 + ring) * 0.3;

        ctx.beginPath();
        for (let theta = 0; theta <= Math.PI * 2; theta += 0.05) {
            // Julia-like distortion
            const wobble = Math.sin(theta * complexity + rotation) * ringSize * 0.2 * distortion;
            const r = ringSize + wobble;
            const px = x + Math.cos(theta + rotation * ring * 0.1) * r;
            const py = y + Math.sin(theta + rotation * ring * 0.1) * r;

            if (theta === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
        }
        ctx.closePath();

        // Shifting colors per ring
        const ringHue = (hue + ring * 0.08 + Math.sin(rotation) * 0.1) % 1;
        ctx.fillStyle = hslToRgb(ringHue, saturation, 0.35 + ring * 0.08);
        ctx.globalAlpha = 0.6;
        ctx.fill();
    }

    ctx.globalAlpha = 1;
}

/**
 * Draw a hypnotic vortex pattern.
 */
function drawVortex(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    arms: number, depth: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0015 * spin;
    const numArms = Math.max(3, arms);

    // Draw twisted vortex arms
    for (let arm = 0; arm < numArms; arm++) {
        const baseAngle = (arm / numArms) * Math.PI * 2;

        for (let d = 0; d < depth; d++) {
            const depthRatio = d / depth;
            const armSize = size * (1 - depthRatio * 0.7);
            const twist = rotation + depthRatio * Math.PI * 2;

            ctx.beginPath();
            const angle1 = baseAngle + twist;
            const angle2 = baseAngle + twist + (Math.PI / numArms) * 0.8;

            ctx.moveTo(x, y);
            ctx.lineTo(x + Math.cos(angle1) * armSize, y + Math.sin(angle1) * armSize);
            ctx.lineTo(x + Math.cos(angle2) * armSize * 0.7, y + Math.sin(angle2) * armSize * 0.7);
            ctx.closePath();

            const armHue = (hue + depthRatio * 0.3 + arm * 0.1) % 1;
            ctx.fillStyle = hslToRgb(armHue, saturation, 0.4 + depthRatio * 0.2);
            ctx.globalAlpha = 0.5 + depthRatio * 0.3;
            ctx.fill();
        }
    }

    // Dark center for depth
    ctx.beginPath();
    ctx.arc(x, y, size * 0.08, 0, Math.PI * 2);
    ctx.fillStyle = hslToRgb(hue, saturation * 0.5, 0.15);
    ctx.globalAlpha = 1;
    ctx.fill();
}

/**
 * Draw an exploding starburst pattern.
 */
function drawStarburst(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    rays: number, layers: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0008 * spin;
    const numRays = Math.max(5, rays * 2);
    const pulse = 1 + Math.sin(elapsedTime * 0.005) * 0.1;

    // Draw starburst rays
    for (let layer = layers; layer >= 1; layer--) {
        const layerSize = size * (layer / layers) * 0.9 * pulse;

        for (let ray = 0; ray < numRays; ray++) {
            const angle = (ray / numRays) * Math.PI * 2 + rotation;
            const isLong = ray % 2 === 0;
            const rayLength = isLong ? layerSize : layerSize * 0.6;

            ctx.beginPath();
            ctx.moveTo(x, y);
            const tipX = x + Math.cos(angle) * rayLength;
            const tipY = y + Math.sin(angle) * rayLength;

            // Sharp ray shape
            const sideAngle = 0.15;
            const sideLen = rayLength * 0.15;
            ctx.lineTo(x + Math.cos(angle - sideAngle) * sideLen, y + Math.sin(angle - sideAngle) * sideLen);
            ctx.lineTo(tipX, tipY);
            ctx.lineTo(x + Math.cos(angle + sideAngle) * sideLen, y + Math.sin(angle + sideAngle) * sideLen);
            ctx.closePath();

            const rayHue = (hue + ray * 0.03) % 1;
            ctx.fillStyle = hslToRgb(rayHue, saturation, 0.5 + layer * 0.1);
            ctx.globalAlpha = 0.7;
            ctx.fill();
        }
    }

    // Bright center
    const centerGrad = ctx.createRadialGradient(x, y, 0, x, y, size * 0.12);
    centerGrad.addColorStop(0, 'rgba(255, 255, 255, 0.95)');
    centerGrad.addColorStop(0.5, hslToRgb(hue, saturation, 0.8));
    centerGrad.addColorStop(1, hslToRgb(hue, saturation, 0.4));
    ctx.beginPath();
    ctx.arc(x, y, size * 0.1, 0, Math.PI * 2);
    ctx.fillStyle = centerGrad;
    ctx.globalAlpha = 1;
    ctx.fill();
}

/**
 * Draw hypnotic concentric rings.
 */
function drawHypnoRings(
    ctx: CanvasRenderingContext2D,
    x: number, y: number, size: number,
    segments: number, rings: number, spin: number,
    hue: number, saturation: number, elapsedTime: number
): void {
    const rotation = elapsedTime * 0.0006 * spin;
    const numRings = Math.max(3, rings * 2);
    const numSegments = Math.max(4, segments);

    // Draw alternating colored rings with segments
    for (let ring = numRings; ring >= 1; ring--) {
        const ringSize = size * (ring / numRings) * 0.85;
        const innerSize = size * ((ring - 1) / numRings) * 0.85;
        const ringRotation = rotation * (ring % 2 === 0 ? 1 : -1);

        for (let seg = 0; seg < numSegments; seg++) {
            const startAngle = (seg / numSegments) * Math.PI * 2 + ringRotation;
            const endAngle = ((seg + 1) / numSegments) * Math.PI * 2 + ringRotation;

            ctx.beginPath();
            ctx.arc(x, y, ringSize, startAngle, endAngle);
            ctx.arc(x, y, innerSize, endAngle, startAngle, true);
            ctx.closePath();

            // Alternating colors
            const segHue = (hue + (seg + ring) * 0.1) % 1;
            const lightness = (seg + ring) % 2 === 0 ? 0.45 : 0.6;
            ctx.fillStyle = hslToRgb(segHue, saturation, lightness);
            ctx.globalAlpha = 0.85;
            ctx.fill();
        }
    }

    ctx.globalAlpha = 1;
}

/**
 * Get default genome for testing.
 */
export function getDefaultPlantGenome(): PlantGenomeData {
    return {
        axiom: 'F',
        angle: 25,
        length_ratio: 0.7,
        branch_probability: 0.85,
        curve_factor: 0.1,
        color_hue: 0.33,
        color_saturation: 0.7,
        stem_thickness: 1.0,
        leaf_density: 0.6,
        production_rules: [
            { input: 'F', output: 'FF-[-F+F+F]+[+F-F-F]', prob: 0.7 },
            { input: 'F', output: 'F[-F][+F]', prob: 0.3 },
        ],
    };
}
