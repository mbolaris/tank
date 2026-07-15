/**
 * Parametric (SVG-path) fish body rendering: body shape, genome-driven
 * pattern overlays, and the eye. Extracted from utils/renderer.ts
 * (god-class ratchet harvest); behavior is unchanged.
 *
 * The Path2D cache stays with the caller (it is shared with other renderers
 * and pruned centrally), so these functions take a `getPath` lookup.
 */

import { getFishPath, getEyePosition, getPatternOpacity, type FishParams } from './fishTemplates';
import { hslToRgbString } from './renderer_sprites';

export type PathLookup = (pathString: string) => Path2D;

export function drawFishPattern(
    ctx: CanvasRenderingContext2D,
    getPath: PathLookup,
    params: FishParams,
    baseSize: number,
    color: string,
    opacity: number
) {
    const width = baseSize * params.body_aspect;
    const height = baseSize;
    if (opacity <= 0) {
        return;
    }

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;

    // Clip to fish body shape to prevent pattern overflow
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

        case 2: { // Solid (darker overlay)
            const path = getPath(getFishPath(params, baseSize));
            ctx.globalAlpha = opacity * 0.6; // Increased from 0.5 for better visibility
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

        case 4: // Chevron (<<)
            ctx.lineWidth = 2;
            ctx.beginPath();
            // Draw 3 columns of chevrons
            [0.3, 0.5, 0.7].forEach(xRel => {
                const xBase = width * xRel;
                [0.25, 0.5, 0.75].forEach(yRel => {
                    const yBase = height * yRel;
                    const size = 4;
                    ctx.moveTo(xBase, yBase - size);
                    ctx.lineTo(xBase - size, yBase); // Point left
                    ctx.lineTo(xBase, yBase + size);
                });
            });
            ctx.stroke();
            break;

        case 5: // Scales (overlapping arcs)
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            // Draw 3 rows of scale arcs
            [0.3, 0.5, 0.7].forEach(xRel => {
                [0.25, 0.5, 0.75].forEach((yRel, row) => {
                    const xBase = width * xRel + ((row % 2) * width * 0.1); // Offset alternate rows
                    const yBase = height * yRel;
                    const radius = 5;
                    ctx.moveTo(xBase + radius, yBase);
                    ctx.arc(xBase, yBase, radius, 0, Math.PI); // Bottom half of circle
                });
            });
            ctx.stroke();
            break;
    }

    ctx.restore();
}

/**
 * Draw the parametric fish body (shape, pattern, eye) centered on the
 * entity's box. Overlays (energy bar, poker status, birth/death effects)
 * remain the caller's responsibility since they are shared with the
 * image-based fallback fish.
 */
export function drawSVGFishBody(
    ctx: CanvasRenderingContext2D,
    getPath: PathLookup,
    fishParams: FishParams,
    x: number,
    y: number,
    scaledSize: number,
    flipHorizontal: boolean
) {
    ctx.save();

    // Position and flip
    ctx.translate(x + scaledSize / 2, y + scaledSize / 2);
    if (flipHorizontal) {
        ctx.scale(-1, 1);
    }
    ctx.translate(-scaledSize / 2, -scaledSize / 2);

    // Get base color from hue
    const baseColor = hslToRgbString(fishParams.color_hue, 0.7, 0.6);
    const patternColor = hslToRgbString(fishParams.color_hue, 0.8, 0.3);

    // Get SVG path for the fish body
    const fishPath = getFishPath(fishParams, scaledSize);

    // Draw fish body
    const path = getPath(fishPath);

    // Fill with base color
    ctx.fillStyle = baseColor;
    ctx.fill(path);

    // Stroke outline
    ctx.strokeStyle = hslToRgbString(fishParams.color_hue, 0.8, 0.4);
    ctx.lineWidth = 1.5;
    ctx.stroke(path);

    // Draw pattern if applicable
    const patternOpacity = getPatternOpacity(fishParams.pattern_intensity, 0.8);
    if (patternOpacity > 0) {
        drawFishPattern(ctx, getPath, fishParams, scaledSize, patternColor, patternOpacity);
    }

    // Draw eye
    const eyePos = getEyePosition(fishParams, scaledSize);
    const eyeRadius = 3 * fishParams.eye_size;

    // Eye white
    ctx.fillStyle = 'white';
    ctx.beginPath();
    ctx.arc(eyePos.x, eyePos.y, eyeRadius, 0, Math.PI * 2);
    ctx.fill();

    // Eye pupil
    ctx.fillStyle = 'black';
    ctx.beginPath();
    ctx.arc(eyePos.x, eyePos.y, eyeRadius * 0.5, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
}
