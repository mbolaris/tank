import type { PlantGenomeData } from '../types';
import { getGenomeSignature, hslToRgbTuple } from '../helpers';
import { claudeCache, generateClaudeTexture } from '../textures';

const phi = 1.618033988749895;

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
