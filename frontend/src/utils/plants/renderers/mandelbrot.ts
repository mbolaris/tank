import type { PlantGenomeData } from '../types';
import { getGenomeSignature, hslToRgbTuple } from '../helpers';
import { mandelbrotCache, generateMandelbrotTexture } from '../textures';

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
