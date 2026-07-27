
import { getFishPath, getEyePosition, getPatternOpacity, type FishParams } from '../utils/fishTemplates';
import type { FishGenomeData } from '../types/simulation';
import { hslToRgbString } from '../utils/renderer_sprites';
import { drawMicrobeAvatar } from './shared/microbeAvatar';

// --- Path Cache ---
const pathCache = new Map<string, Path2D>();
const MAX_PATH_CACHE_SIZE = 500;

/**
 * Clear the avatar path cache to release memory.
 * Paths will be regenerated on demand.
 * Call this periodically during long sessions to prevent unbounded memory growth.
 */
export function clearAvatarPathCache(): void {
    pathCache.clear();
    entityFacingLeft.clear();
}

/**
 * Get the current size of the avatar path cache (for diagnostics).
 */
export function getAvatarPathCacheSize(): number {
    return pathCache.size;
}

function getPath(pathString: string): Path2D {
    if (typeof Path2D === 'undefined') return null as unknown as Path2D;
    
    // Automatic cleanup if cache grows too large
    if (pathCache.size > MAX_PATH_CACHE_SIZE) {
        pathCache.clear();
    }
    
    let path = pathCache.get(pathString);
    if (!path) {
        path = new Path2D(pathString);
        pathCache.set(pathString, path);
    }
    return path;
}

// --- SVG Fish Rendering ---

function drawFishPattern(ctx: CanvasRenderingContext2D, params: FishParams, baseSize: number, color: string, opacity: number) {
    const width = baseSize * params.body_aspect;
    const height = baseSize;
    if (opacity <= 0) return;

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;

    const fishPathStr = getFishPath(params, baseSize);
    const fishPath = getPath(fishPathStr);
    ctx.clip(fishPath);

    switch (params.pattern_type) {
        case 0: // Stripes
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(width * 0.3, height * 0.2);
            ctx.lineTo(width * 0.3, height * 0.8);
            ctx.moveTo(width * 0.5, height * 0.2);
            ctx.lineTo(width * 0.5, height * 0.8);
            ctx.moveTo(width * 0.7, height * 0.2);
            ctx.lineTo(width * 0.7, height * 0.8);
            ctx.stroke();
            break;
        case 1: // Spots
            [
                { x: width * 0.4, y: height * 0.35 },
                { x: width * 0.6, y: height * 0.4 },
                { x: width * 0.5, y: height * 0.6 },
                { x: width * 0.7, y: height * 0.65 },
            ].forEach(spot => {
                ctx.beginPath();
                ctx.arc(spot.x, spot.y, 3, 0, Math.PI * 2);
                ctx.fill();
            });
            break;
        case 2: { // Solid
            const path = getPath(getFishPath(params, baseSize));
            ctx.globalAlpha = opacity * 0.6;
            ctx.fill(path);
            break;
        }
        case 3: { // Gradient
            const gradient = ctx.createLinearGradient(0, 0, width, 0);
            gradient.addColorStop(0, color);
            gradient.addColorStop(1, 'transparent');
            ctx.fillStyle = gradient;
            const gradPath = getPath(getFishPath(params, baseSize));
            ctx.fill(gradPath);
            break;
        }
        case 4: // Chevron
            ctx.lineWidth = 2;
            ctx.beginPath();
            [0.3, 0.5, 0.7].forEach(xRel => {
                const xBase = width * xRel;
                [0.25, 0.5, 0.75].forEach(yRel => {
                    const yBase = height * yRel;
                    const size = 4;
                    ctx.moveTo(xBase, yBase - size);
                    ctx.lineTo(xBase - size, yBase);
                    ctx.lineTo(xBase, yBase + size);
                });
            });
            ctx.stroke();
            break;
        case 5: // Scales
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            [0.3, 0.5, 0.7].forEach(xRel => {
                [0.25, 0.5, 0.75].forEach((yRel, row) => {
                    const xBase = width * xRel + ((row % 2) * width * 0.1);
                    const yBase = height * yRel;
                    const radius = 5;
                    ctx.moveTo(xBase + radius, yBase);
                    ctx.arc(xBase, yBase, radius, 0, Math.PI);
                });
            });
            ctx.stroke();
            break;
    }
    ctx.restore();
}

// --- Stable Facing State Cache ---
const entityFacingLeft = new Map<number, boolean>();
const MIN_FLIP_SPEED = 0.15; // Tailored for soccer/petri speed scales, since max speed is ~1.05

function getStableFacingLeft(entityId: number, velX?: number, team?: string): boolean {
    const defaultFacing = team === 'right'; // Right team starts facing left
    const previousFacing = entityFacingLeft.get(entityId) ?? defaultFacing;

    if (velX === undefined || Math.abs(velX) < MIN_FLIP_SPEED) {
        return previousFacing;
    }

    const facingLeft = velX < 0;
    entityFacingLeft.set(entityId, facingLeft);
    return facingLeft;
}

export function drawSVGFish(
    ctx: CanvasRenderingContext2D,
    entityId: number,
    radius: number,
    velX: number | undefined,
    genomeData: FishGenomeData | null | undefined,
    team?: string
) {
    if (!genomeData) return;

    // Map genome data to FishParams
    const fishParams: FishParams = {
        fin_size: genomeData.fin_size || 1.0,
        tail_size: genomeData.tail_size || 1.0,
        body_aspect: genomeData.body_aspect || 1.0,
        eye_size: genomeData.eye_size || 1.0,
        pattern_intensity: genomeData.pattern_intensity || 0.5,
        pattern_type: genomeData.pattern_type || 0,
        color_hue: genomeData.color_hue || 0.5,
        size: genomeData.size || 1.0,
        template_id: genomeData.template_id || 0,
    };

    // Calculate dimensions
    // Note: radius in soccer = width/2 roughly? 
    // The renderer usually takes box width/height.
    // Here we use radius * 2 as base size.
    const baseSize = radius * 2;
    const sizeModifier = fishParams.size;
    const scaledSize = baseSize * sizeModifier;

    // Flip based on velocity direction with stability for low speeds
    const flipHorizontal = getStableFacingLeft(entityId, velX, team);

    ctx.save();

    // Position/Rotate/Flip
    // Note: SVG fish are side-view. We draw them centered.
    // If we want them to rotate to face movement direction in top-down view (like RPG markers),
    // we might want to rotate. 
    // HOWEVER, Tank view usually just flips horizontal.
    // If the user wants "Tank Mode", they usually swim left/right.
    // But this is top-down soccer...
    // If I rotate them, they look like flat paper cutouts spinning.
    // If I don't rotate, they always face left/right. This is standard side-scroller look.
    // TankTopDownRenderer.ts uses `flipHorizontal` primarily for images.
    // RenderSVGFish in Renderer.ts also uses `flipHorizontal`.
    // So we invoke flipHorizontal.  We do NOT rotate by vel_y.

    if (flipHorizontal) {
        ctx.scale(-1, 1);
    }

    // Centering: SVG paths usually specialized. 
    // renderer.ts renders at x,y (top left).
    // drawSVGFish in renderer.ts translates to center!
    // We are already translated to entity center in Soccer renderer.
    // So we just translate by -size/2 to align center.
    ctx.translate(-scaledSize / 2, -scaledSize / 2);

    const baseColor = hslToRgbString(fishParams.color_hue, 0.7, 0.6);
    const patternColor = hslToRgbString(fishParams.color_hue, 0.8, 0.3);

    const fishPath = getFishPath(fishParams, scaledSize);
    const path = getPath(fishPath);

    ctx.fillStyle = baseColor;
    ctx.fill(path);

    ctx.strokeStyle = hslToRgbString(fishParams.color_hue, 0.8, 0.4);
    ctx.lineWidth = 1.5;
    ctx.stroke(path);

    const patternOpacity = getPatternOpacity(fishParams.pattern_intensity, 0.8);
    if (patternOpacity > 0) {
        drawFishPattern(ctx, fishParams, scaledSize, patternColor, patternOpacity);
    }

    const eyePos = getEyePosition(fishParams, scaledSize);
    const eyeRadius = 3 * fishParams.eye_size;

    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(eyePos.x, eyePos.y, eyeRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = 'black';
    ctx.beginPath();
    ctx.arc(eyePos.x, eyePos.y, eyeRadius * 0.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
}

// --- Microbe Rendering ---

/**
 * Portrait-mode microbe: the shared gene-driven avatar without the world-facing
 * extras. Generation shading and the behavioural trait cues are omitted because
 * a portrait has no world context to read them against.
 */
export function drawMicrobe(
    ctx: CanvasRenderingContext2D,
    entityId: number,
    radius: number,
    velX: number | undefined,
    velY: number | undefined,
    genomeData: FishGenomeData | null | undefined
) {
    if (!genomeData) return;

    drawMicrobeAvatar(ctx, {
        entityId,
        radius,
        velX,
        velY,
        genome: genomeData,
    });
}

/**
 * Main avatar rendering entry point.
 * Selects between SVG Fish (Tank style) and Microbe (Dish style) based on genome data.
 * 
 * @param forceMicrobe - If true, always render as microbe (for Petri dish mode)
 */
export function drawAvatar(
    ctx: CanvasRenderingContext2D,
    entityId: number,
    radius: number,
    velX: number | undefined,
    velY: number | undefined,
    genomeData: FishGenomeData | null | undefined,
    forceMicrobe: boolean = false,
    team?: string
) {
    if (!genomeData) return;

    // Force microbe rendering for Petri dish mode
    if (forceMicrobe) {
        drawMicrobe(ctx, entityId, radius, velX, velY, genomeData);
        return;
    }

    // Check if we should render as SVG fish
    // If template_id is defined, we prefer SVG fish
    if (genomeData.template_id !== undefined && genomeData.template_id !== null) {
        drawSVGFish(ctx, entityId, radius, velX, genomeData, team);
    } else {
        drawMicrobe(ctx, entityId, radius, velX, velY, genomeData);
    }
}
