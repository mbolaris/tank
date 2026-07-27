import type { PlantGenomeData } from '../types';
import { getGenomeSignature, hslToRgbTuple } from '../helpers';
import { gptCache, generateGptTexture } from '../textures';

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
