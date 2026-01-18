
import { getFishPath, getEyePosition, getPatternOpacity, type FishParams } from '../utils/fishTemplates';
import type { FishGenomeData } from '../types/simulation';

// --- Shared Utilities ---

function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

function seededRand(seed: number): () => number {
    let t = seed >>> 0;
    return () => {
        t += 0x6D2B79F5;
        let x = t;
        x = Math.imul(x ^ (x >>> 15), x | 1);
        x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
        return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
}

function genomeHueDegrees(genomeData: FishGenomeData | null | undefined, entityId: number): number {
    const hue = genomeData?.color_hue;
    if (typeof hue === 'number' && Number.isFinite(hue)) {
        return ((hue % 1) + 1) % 1 * 360;
    }
    return ((entityId * 2654435761) >>> 0) % 360;
}

function movementAngle(velX: number | undefined, velY: number | undefined, rand: () => number): number {
    const vx = velX ?? 0;
    const vy = velY ?? 0;
    const magSq = vx * vx + vy * vy;
    if (magSq > 0.04) return Math.atan2(vy, vx);
    return (rand() * Math.PI * 2) - Math.PI;
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
    let r: number, g: number, b: number;
    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p: number, q: number, t: number) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        };
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

function hslToRgbString(h: number, s: number, l: number): string {
    const rgb = hslToRgb(h, s, l);
    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

// --- Path Cache ---
const pathCache = new Map<string, Path2D>();
function getPath(pathString: string): Path2D {
    if (typeof Path2D === 'undefined') return null as unknown as Path2D;
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

export function drawSVGFish(
    ctx: CanvasRenderingContext2D,
    _entityId: number,
    radius: number,
    velX: number | undefined,
    genomeData: FishGenomeData | null | undefined
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

    // Flip logic (simplified)
    const flipHorizontal = (velX ?? 0) < -0.1;

    ctx.save();

    // Position/Rotate/Flip
    // Note: SVG fish are side-view. We draw them centered.
    // If we want them to rotate to face movement direction in top-down view (like RPG markers),
    // we might want to rotate. 
    // HOWEVER, Tank view usually just flips horizontal.
    // If the user wants "Fish Tank Mode", they usually swim left/right.
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
// (Copied from microbe_renderer.ts)

function drawCapsule(ctx: CanvasRenderingContext2D, r: number, aspect: number) {
    const rx = r * clamp(aspect, 0.7, 1.6);
    const ry = r * clamp(1 / aspect, 0.7, 1.6);
    const cap = Math.min(rx, ry);

    ctx.beginPath();
    ctx.moveTo(-rx + cap, -ry);
    ctx.lineTo(rx - cap, -ry);
    ctx.quadraticCurveTo(rx, -ry, rx, -ry + cap);
    ctx.lineTo(rx, ry - cap);
    ctx.quadraticCurveTo(rx, ry, rx - cap, ry);
    ctx.lineTo(-rx + cap, ry);
    ctx.quadraticCurveTo(-rx, ry, -rx, ry - cap);
    ctx.lineTo(-rx, -ry + cap);
    ctx.quadraticCurveTo(-rx, -ry, -rx + cap, -ry);
    ctx.closePath();
}

function drawWobblyBlob(ctx: CanvasRenderingContext2D, r: number, rand: () => number, wobble: number) {
    const steps = 18;
    const points: Array<{ x: number; y: number }> = [];

    for (let i = 0; i < steps; i++) {
        const a = (i / steps) * Math.PI * 2;
        const jitter = (rand() - 0.5) * 2 * wobble;
        const rr = r * (1 + jitter);
        points.push({ x: Math.cos(a) * rr, y: Math.sin(a) * rr });
    }

    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
        const p0 = points[i];
        const p1 = points[(i + 1) % points.length];
        const midX = (p0.x + p1.x) / 2;
        const midY = (p0.y + p1.y) / 2;
        if (i === 0) ctx.moveTo(midX, midY);
        else ctx.quadraticCurveTo(p0.x, p0.y, midX, midY);
    }
    ctx.closePath();
}

export function drawMicrobe(
    ctx: CanvasRenderingContext2D,
    entityId: number,
    radius: number,
    velX: number | undefined,
    velY: number | undefined,
    genomeData: FishGenomeData | null | undefined
) {
    if (!genomeData) return;

    // If template_id is not in genome object explicitly, fallback to ID based
    const templateId = genomeData.template_id ?? (entityId % 6);
    const hueDeg = genomeHueDegrees(genomeData, entityId);

    const r = clamp(Math.max(radius, 10), 10, 26);
    const finSize = genomeData.fin_size ?? 1;
    const tailSize = genomeData.tail_size ?? 1;
    const bodyAspect = genomeData.body_aspect ?? 1;
    const eyeSize = genomeData.eye_size ?? 1;
    const patternIntensity = clamp(genomeData.pattern_intensity ?? 0, 0, 1);
    const patternType = genomeData.pattern_type ?? 0;

    const seed = (
        (entityId * 2654435761) ^
        (templateId * 374761393) ^
        (Math.floor(finSize * 1000) * 668265263) ^
        (Math.floor(tailSize * 1000) * 2246822519) ^
        (Math.floor(bodyAspect * 1000) * 3266489917) ^
        (Math.floor(eyeSize * 1000) * 234567891) ^
        (Math.floor(patternIntensity * 1000) * 198491317)
    ) >>> 0;
    const rand = seededRand(seed);
    const moveAngle = movementAngle(velX, velY, rand);

    ctx.save();
    ctx.rotate(moveAngle);

    const wobble = 0.06 + patternIntensity * 0.08;
    const shapeKind = templateId % 6;
    if (shapeKind === 2 || shapeKind === 5) {
        drawCapsule(ctx, r * 0.9, bodyAspect);
    } else {
        drawWobblyBlob(ctx, r, rand, wobble);
    }

    const membrane = ctx.createRadialGradient(r * 0.25, -r * 0.25, r * 0.1, 0, 0, r * 1.1);
    membrane.addColorStop(0, `hsla(${hueDeg}, 70%, 62%, 0.95)`);
    membrane.addColorStop(0.6, `hsla(${hueDeg}, 60%, 48%, 0.88)`);
    membrane.addColorStop(1, `hsla(${(hueDeg + 20) % 360}, 55%, 34%, 0.85)`);
    ctx.fillStyle = membrane;
    ctx.fill();

    // Cytoplasm
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.scale(0.78, 0.78);
    if (shapeKind === 2 || shapeKind === 5) {
        drawCapsule(ctx, r * 0.9, bodyAspect);
    } else {
        drawWobblyBlob(ctx, r, rand, wobble * 0.65);
    }
    ctx.fillStyle = `hsla(${(hueDeg + 10) % 360}, 45%, 60%, 0.7)`;
    ctx.fill();
    ctx.restore();

    // Nucleus (eye_size drives size)
    const nucleusR = r * clamp(0.18 + (eyeSize - 1) * 0.08, 0.14, 0.34);
    const nucleusX = (rand() - 0.5) * r * 0.35;
    const nucleusY = (rand() - 0.5) * r * 0.35;
    const nucleusGrad = ctx.createRadialGradient(nucleusX - nucleusR * 0.3, nucleusY - nucleusR * 0.3, 1, nucleusX, nucleusY, nucleusR);
    nucleusGrad.addColorStop(0, `hsla(${(hueDeg + 190) % 360}, 55%, 52%, 0.95)`);
    nucleusGrad.addColorStop(1, `hsla(${(hueDeg + 210) % 360}, 55%, 30%, 0.95)`);
    ctx.fillStyle = nucleusGrad;
    ctx.beginPath();
    ctx.arc(nucleusX, nucleusY, nucleusR, 0, Math.PI * 2);
    ctx.fill();

    // Pattern overlay
    ctx.save();
    ctx.globalAlpha = 0.25 + patternIntensity * 0.35;
    ctx.strokeStyle = `hsla(${(hueDeg + 60) % 360}, 70%, 70%, 0.8)`;
    ctx.fillStyle = `hsla(${(hueDeg + 60) % 360}, 70%, 70%, 0.6)`;

    if (patternType === 0) {
        const bands = 3 + Math.floor(patternIntensity * 4);
        ctx.lineWidth = Math.max(1, r * 0.06);
        for (let i = 0; i < bands; i++) {
            const t = (i + 1) / (bands + 1);
            const y = (t - 0.5) * r * 1.2;
            ctx.beginPath();
            ctx.moveTo(-r * 0.7, y);
            ctx.quadraticCurveTo(0, y + (rand() - 0.5) * r * 0.25, r * 0.7, y);
            ctx.stroke();
        }
    } else if (patternType === 1) {
        const vacuoles = 3 + Math.floor(patternIntensity * 8);
        for (let i = 0; i < vacuoles; i++) {
            const a = rand() * Math.PI * 2;
            const d = r * (0.1 + rand() * 0.55);
            const vx = Math.cos(a) * d;
            const vy = Math.sin(a) * d;
            const vr = r * (0.06 + rand() * 0.12) * (0.5 + patternIntensity);
            ctx.beginPath();
            ctx.arc(vx, vy, vr, 0, Math.PI * 2);
            ctx.fill();
        }
    } else if (patternType === 2) {
        ctx.globalAlpha *= 0.9;
        const overlay = ctx.createRadialGradient(0, 0, r * 0.1, 0, 0, r);
        overlay.addColorStop(0, `hsla(${(hueDeg + 30) % 360}, 80%, 70%, 0.0)`);
        overlay.addColorStop(1, `hsla(${(hueDeg + 30) % 360}, 80%, 25%, 0.65)`);
        ctx.fillStyle = overlay;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.95, 0, Math.PI * 2);
        ctx.fill();
    } else {
        const granules = 10 + Math.floor(patternIntensity * 24);
        ctx.globalAlpha *= 0.55;
        for (let i = 0; i < granules; i++) {
            const a = rand() * Math.PI * 2;
            const d = r * rand() * 0.8;
            const gx = Math.cos(a) * d;
            const gy = Math.sin(a) * d;
            ctx.fillStyle = `hsla(${(hueDeg + 120 + rand() * 40) % 360}, 55%, 65%, 0.45)`;
            ctx.beginPath();
            ctx.arc(gx, gy, r * (0.02 + rand() * 0.05), 0, Math.PI * 2);
            ctx.fill();
        }
    }
    ctx.restore();

    // Cilia/flagella
    const ciliaCount = clamp(Math.floor(6 + finSize * 5), 6, 14);
    ctx.save();
    ctx.globalAlpha = 0.25 + patternIntensity * 0.25;
    ctx.strokeStyle = `hsla(${(hueDeg + 30) % 360}, 60%, 80%, 0.9)`;
    ctx.lineWidth = Math.max(1, r * 0.035);
    for (let i = 0; i < ciliaCount; i++) {
        const a = (i / ciliaCount) * Math.PI * 2 + (rand() - 0.5) * 0.25;
        const len = r * (0.18 + rand() * 0.22) * clamp(finSize, 0.6, 1.6);
        const sx = Math.cos(a) * (r * 0.92);
        const sy = Math.sin(a) * (r * 0.92);
        const ex = Math.cos(a) * (r * 0.92 + len);
        const ey = Math.sin(a) * (r * 0.92 + len);
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.quadraticCurveTo((sx + ex) / 2, (sy + ey) / 2 + (rand() - 0.5) * r * 0.08, ex, ey);
        ctx.stroke();
    }
    ctx.restore();

    // Primary flagellum
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.strokeStyle = `hsla(${(hueDeg + 150) % 360}, 55%, 72%, 0.85)`;
    ctx.lineWidth = Math.max(1, r * 0.05);
    const tailLen = r * (0.9 + tailSize * 0.8);
    ctx.beginPath();
    ctx.moveTo(-r * 0.95, 0);
    ctx.bezierCurveTo(
        -r * 0.95 - tailLen * 0.25,
        r * (rand() - 0.5) * 0.8,
        -r * 0.95 - tailLen * 0.65,
        r * (rand() - 0.5) * 1.2,
        -r * 0.95 - tailLen,
        r * (rand() - 0.5) * 0.9
    );
    ctx.stroke();
    ctx.restore();

    // Membrane highlight
    ctx.strokeStyle = `hsla(${hueDeg}, 80%, 78%, 0.35)`;
    ctx.lineWidth = 1.5;
    if (shapeKind === 2 || shapeKind === 5) drawCapsule(ctx, r * 0.9, bodyAspect);
    else drawWobblyBlob(ctx, r, rand, wobble * 0.8);
    ctx.stroke();

    ctx.restore();
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
    forceMicrobe: boolean = false
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
        drawSVGFish(ctx, entityId, radius, velX, genomeData);
    } else {
        drawMicrobe(ctx, entityId, radius, velX, velY, genomeData);
    }
}
