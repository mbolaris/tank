import type { FloralGenome } from './types';
import { hslToRgb } from './helpers';

// Cache for spiral paths
export const spiralFlowerPathCache = new Map<string, Path2D[]>();

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
    const pathKey = `${numArms}:${layers}`;
    let armPaths = spiralFlowerPathCache.get(pathKey);

    if (!armPaths && typeof Path2D !== 'undefined') {
        armPaths = [];
        for (let arm = 0; arm < numArms; arm++) {
            const armAngle = (arm / numArms) * Math.PI * 2;
            const path = new Path2D();
            for (let t = 0; t < layers * 2; t += 0.05) {
                const angle = armAngle + t * 1.5;
                const r = 0.1 * t;
                const px = Math.cos(angle) * r;
                const py = Math.sin(angle) * r;
                if (t === 0) path.moveTo(px, py);
                else path.lineTo(px, py);
            }
            armPaths.push(path);
        }
        if (spiralFlowerPathCache.size >= 100) {
            spiralFlowerPathCache.clear();
        }
        spiralFlowerPathCache.set(pathKey, armPaths);
    }

    // Draw spiral arms
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rotation);
    ctx.scale(size, size);
    for (let arm = 0; arm < numArms; arm++) {
        const armAngle = (arm / numArms) * Math.PI * 2;

        if (!armPaths) {
            ctx.beginPath();
            for (let t = 0; t < layers * 2; t += 0.05) {
                const angle = armAngle + t * 1.5;
                const r = 0.1 * t;
                const px = Math.cos(angle) * r;
                const py = Math.sin(angle) * r;

                if (t === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
            }
        }

        // Rainbow shift along each arm
        const armHue = (hue + arm * 0.1) % 1;
        ctx.strokeStyle = hslToRgb(armHue, saturation, 0.5);
        ctx.lineWidth = 0.06;
        ctx.lineCap = 'round';
        ctx.globalAlpha = 0.8;
        if (armPaths) {
            ctx.stroke(armPaths[arm]);
        } else {
            ctx.stroke();
        }
    }
    ctx.restore();

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
export function drawHypnoRings(
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
