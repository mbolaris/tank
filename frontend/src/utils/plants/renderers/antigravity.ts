import type { PlantGenomeData } from '../types';
import { getGenomeSignature, hslToRgbTuple } from '../helpers';
import { antigravityCache, generateAntigravityTexture } from '../textures';

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
