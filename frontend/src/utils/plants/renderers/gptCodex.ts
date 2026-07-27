import type { PlantGenomeData, FractalSegment, FractalLeaf, PlantRenderCache } from '../types';
import { getGenomeSignature, hslToRgb, hslToRgbTuple, seededRandom } from '../helpers';
import { generateLSystemString, interpretLSystem } from '../lsystem';

export const gptCodexCache = new Map<number, PlantRenderCache>();

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
