import type { PlantGenomeData, FractalSegment, FractalLeaf, PlantRenderCache } from './types';
import { getGenomeSignature, hslToRgb, hslToRgbTuple, seededRandom } from './helpers';
import { generateLSystemString, interpretLSystem } from './lsystem';
import {
    mandelbrotCache,
    claudeCache,
    antigravityCache,
    gptCache,
    generateMandelbrotTexture,
    generateClaudeTexture,
    generateAntigravityTexture,
    generateGptTexture,
} from './textures';

// Caches for the L-system-based renderers
export const sonnetCache = new Map<number, PlantRenderCache>();
export const gptCodexCache = new Map<number, PlantRenderCache>();

const phi = 1.618033988749895;

/**
 * Legacy mandelbrot plant renderer - kept for potential future use
 */
export function _renderMandelbrotPlant(
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
 */
export function _renderClaudePlant(
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
        const leafY = -height * (0.1 + t * 0.45);
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
export function _renderAntigravityPlant(
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
        glow.addColorStop(0.5, `rgba(180, 140, 220, ${pulse * 0.65})`);
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

/**
 * Draw segment helper for GPT Codex renderer.
 */
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

/**
 * Render a GPT Codex plant.
 */
export function renderGptCodexPlant(
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
 * Render a GPT plant.
 */
export function _renderGptPlant(
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
 * Render a Sonnet plant.
 */
export function renderSonnetPlant(
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

    // Elegant multi-frequency swaying
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

        // Fern frond shape
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
