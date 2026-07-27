import type { PlantGenomeData, FractalSegment, FractalLeaf, PlantRenderCache } from '../types';
import { getGenomeSignature, hslToRgb, hslToRgbTuple } from '../helpers';
import { generateLSystemString, interpretLSystem } from '../lsystem';

export const sonnetCache = new Map<number, PlantRenderCache>();

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
