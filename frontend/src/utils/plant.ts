/**
 * L-System fractal plant rendering utilities.
 *
 * This module generates fractal plant shapes using L-system grammar rules
 * inherited from the plant's genome.
 */

import type {
    PlantGenomeData,
    FractalSegment,
    FractalLeaf,
    PlantRenderCache,
    FloralGenome,
} from './plants/types';

import {
    getGenomeSignature,
    hslToRgb,
} from './plants/helpers';

import {
    generateLSystemString,
    interpretLSystem,
    groupSegmentsByThickness,
    appendSegments,
    createLeafPaths,
} from './plants/lsystem';

import {
    mandelbrotCache,
    claudeCache,
    antigravityCache,
    gptCache,
} from './plants/textures';

import {
    sonnetCache,
    gptCodexCache,
    renderGptCodexPlant,
    renderSonnetPlant,
} from './plants/renderers';

import {
    spiralFlowerPathCache,
} from './plants/nectar';

// Re-export type definitions
export type { PlantGenomeData, FloralGenome };

// Re-export L-system generation & interpretation
export { generateLSystemString, interpretLSystem };

// Re-export specific plant renderers (kept for legacy support or testing)
export {
    _renderMandelbrotPlant,
    _renderClaudePlant,
    _renderAntigravityPlant,
    _renderGptPlant,
} from './plants/renderers';

// Re-export nectar rendering
export { renderPlantNectar } from './plants/nectar';

// Module-level cache keyed by plant id to avoid flickering when plants drift
const plantCache = new Map<number, PlantRenderCache>();

/**
 * Remove cached plant geometry/texture entries for plants that no longer exist.
 * Without pruning, the caches can grow unbounded when the simulation spawns
 * and deletes many plants, eventually exhausting browser memory.
 */
export function prunePlantCaches(activePlantIds: Iterable<number>): void {
    const activeIds = new Set(activePlantIds);

    const caches = [
        plantCache,
        mandelbrotCache,
        claudeCache,
        antigravityCache,
        gptCache,
        sonnetCache,
        gptCodexCache,
    ];

    for (const cache of caches) {
        for (const id of cache.keys()) {
            if (!activeIds.has(id)) {
                // Best-effort release of native-backed resources
                const entry = cache.get(id) as unknown as Record<string, unknown>;
                if (entry) {
                    const texture = entry.texture;
                    if (texture && texture instanceof HTMLCanvasElement) {
                        try {
                            texture.width = 0;
                        } catch {
                            /* ignore */
                        }
                    }
                    try {
                        if (Array.isArray(entry.segments)) entry.segments.length = 0;
                        if (Array.isArray(entry.sortedSegments)) entry.sortedSegments.length = 0;
                        if (Array.isArray(entry.leaves)) entry.leaves.length = 0;
                    } catch {
                        /* ignore */
                    }
                }
                cache.delete(id);
            }
        }
    }
}

/**
 * Diagnostic helper: return sizes of each internal cache (useful for leak investigation)
 */
export function getPlantCacheSizes(): Record<string, number> {
    return {
        plantCache: plantCache.size,
        mandelbrotCache: mandelbrotCache.size,
        claudeCache: claudeCache.size,
        antigravityCache: antigravityCache.size,
        gptCache: gptCache.size,
        sonnetCache: sonnetCache.size,
        gptCodexCache: gptCodexCache.size,
        spiralFlowerPathCache: spiralFlowerPathCache.size,
    };
}

/**
 * Clear ALL plant caches to forcibly release texture memory.
 * This is useful for periodic cleanup to prevent memory growth during long sessions.
 * Plants will regenerate their cached data on the next render.
 */
export function clearAllPlantCaches(): void {
    const caches = [
        plantCache,
        mandelbrotCache,
        claudeCache,
        antigravityCache,
        gptCache,
        sonnetCache,
        gptCodexCache,
    ];

    for (const cache of caches) {
        for (const entry of cache.values()) {
            const typedEntry = entry as unknown as Record<string, unknown>;
            const texture = typedEntry.texture;
            if (texture && texture instanceof HTMLCanvasElement) {
                try {
                    texture.width = 0;
                } catch {
                    /* ignore */
                }
            }
            try {
                if (Array.isArray(typedEntry.segments)) typedEntry.segments.length = 0;
                if (Array.isArray(typedEntry.sortedSegments)) typedEntry.sortedSegments.length = 0;
                if (Array.isArray(typedEntry.leaves)) typedEntry.leaves.length = 0;
            } catch {
                /* ignore */
            }
        }
        cache.clear();
    }
    spiralFlowerPathCache.clear();
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

/**
 * Main dispatch entry point to render a fractal plant.
 */
export function renderPlant(
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
    const fractalType = genome.type ?? 'lsystem';
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
    let segmentGroups: Array<{ thickness: number; segments: FractalSegment[]; path?: Path2D }>;
    let leafPath: Path2D | undefined;
    let veinPath: Path2D | undefined;

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
        segmentGroups = groupSegmentsByThickness(sortedSegments);
        ({ leafPath, veinPath } = createLeafPaths(leaves));

        plantCache.set(cacheKey, {
            iterations,
            signature: genomeSignature,
            segments,
            leaves,
            sortedSegments,
            segmentGroups,
            leafPath,
            veinPath,
        });
    } else {
        segments = cached!.segments;
        leaves = cached!.leaves;
        sortedSegments = cached!.sortedSegments;
        segmentGroups = cached!.segmentGroups ?? groupSegmentsByThickness(sortedSegments);
        leafPath = cached!.leafPath;
        veinPath = cached!.veinPath;
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

    // Fallback: if no segments were generated, draw a simple stem
    if (segments.length === 0) {
        const stemHeight = 40;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(0, -stemHeight);
        ctx.strokeStyle = stemColor;
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.stroke();

        ctx.beginPath();
        ctx.ellipse(0, -stemHeight - 5, 8, 12, 0, 0, Math.PI * 2);
        ctx.fillStyle = leafColor;
        ctx.fill();

        ctx.restore();
        return;
    }

    // Draw shadow
    ctx.save();
    ctx.globalAlpha = 0.15;
    ctx.translate(3, 3);

    for (const group of segmentGroups) {
        ctx.strokeStyle = '#000';
        ctx.lineWidth = group.thickness + 1;
        ctx.lineCap = 'round';
        if (group.path) {
            ctx.stroke(group.path);
        } else {
            ctx.beginPath();
            appendSegments(ctx, group.segments);
            ctx.stroke();
        }
    }
    ctx.restore();

    // Draw stem segments (back to front by depth)
    for (const group of segmentGroups) {
        ctx.strokeStyle = stemColor;
        ctx.lineWidth = group.thickness;
        ctx.lineCap = 'round';
        if (group.path) {
            ctx.stroke(group.path);
        } else {
            ctx.beginPath();
            appendSegments(ctx, group.segments);
            ctx.stroke();
        }

        ctx.strokeStyle = highlightColor;
        ctx.lineWidth = group.thickness * 0.4;
        ctx.lineCap = 'round';
        if (group.path) {
            ctx.stroke(group.path);
        } else {
            ctx.beginPath();
            appendSegments(ctx, group.segments);
            ctx.stroke();
        }
    }

    // Draw leaves and veins in consolidated paths.
    ctx.fillStyle = leafColor;
    if (leafPath) {
        ctx.fill(leafPath);
    } else {
        ctx.beginPath();
        for (const leaf of leaves) {
            const rotation = (leaf.angle * Math.PI) / 180 + Math.PI / 2;
            const centerX = leaf.x + Math.sin(rotation) * leaf.size / 2;
            const centerY = leaf.y - Math.cos(rotation) * leaf.size / 2;
            const radiusX = leaf.size * 0.4;
            const radiusY = leaf.size;
            ctx.moveTo(
                centerX + Math.cos(rotation) * radiusX,
                centerY + Math.sin(rotation) * radiusX
            );
            ctx.ellipse(
                centerX,
                centerY,
                radiusX,
                radiusY,
                rotation,
                0,
                Math.PI * 2
            );
        }
        ctx.fill();
    }
    ctx.strokeStyle = highlightColor;
    ctx.lineWidth = 0.5;
    if (veinPath) {
        ctx.stroke(veinPath);
    } else {
        ctx.beginPath();
        for (const leaf of leaves) {
            const rotation = (leaf.angle * Math.PI) / 180 + Math.PI / 2;
            ctx.moveTo(leaf.x, leaf.y);
            ctx.lineTo(
                leaf.x + Math.sin(rotation) * leaf.size,
                leaf.y - Math.cos(rotation) * leaf.size
            );
        }
        ctx.stroke();
    }

    // Draw nectar glow if ready
    if (nectarReady) {
        let topY = 0;
        for (const seg of segments) {
            topY = Math.min(topY, seg.y1, seg.y2);
        }

        const pulse = 0.5 + Math.sin(elapsedTime * 0.005) * 0.3;

        ctx.beginPath();
        const gradient = ctx.createRadialGradient(0, topY - 10, 0, 0, topY - 10, 20);
        gradient.addColorStop(0, `rgba(255, 220, 100, ${pulse})`);
        gradient.addColorStop(0.5, `rgba(255, 200, 50, ${pulse * 0.5})`);
        gradient.addColorStop(1, 'rgba(255, 180, 0, 0)');
        ctx.arc(0, topY - 10, 20, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

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
