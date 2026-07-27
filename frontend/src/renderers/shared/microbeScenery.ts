/**
 * The non-fish inhabitants of the top-down views: the predator (crabs) and the
 * inert substrate (castles and other obstacles). Both were duplicated between
 * the tank and petri renderers.
 *
 * The two copies had drifted apart before they were merged here, so each
 * creature takes a small style record rather than being silently unified —
 * see `TANK_PREDATOR_STYLE` / `PETRI_PREDATOR_STYLE`. Collapse them to one
 * style when the two views are meant to agree; until then the flags are an
 * honest record of a difference that already exists on screen.
 */

import { clamp, roundRectPath, seededRand, movementAngle, wobblyBlobPath } from './canvasPrimitives';

export interface MicrobePredatorStyle {
    /** Cross-hatch across the capsid head. */
    facetLines: boolean;
    /** Pulsing rings along the tail sheath. */
    tailRings: boolean;
    /** Modulate the tail-fibre wiggle by the same pulse that drives the rings. */
    pumpedFibers: boolean;
    /** Dark aperture dot over the head. */
    coreDot: boolean;
}

export const TANK_PREDATOR_STYLE: MicrobePredatorStyle = {
    facetLines: true,
    tailRings: true,
    pumpedFibers: false,
    coreDot: false,
};

export const PETRI_PREDATOR_STYLE: MicrobePredatorStyle = {
    facetLines: false,
    tailRings: false,
    pumpedFibers: true,
    coreDot: true,
};

export interface MicrobePredatorSpec {
    entityId: number;
    radius: number;
    velX?: number;
    velY?: number;
    /** Drives the menace pulse and the tail animation. */
    timeMs: number;
    style: MicrobePredatorStyle;
}

/**
 * Bacteriophage / protozoan predator hybrid: reads as "microbe predator" at a
 * glance and stays deterministic per id. Drawn centred on the current origin.
 */
export function drawMicrobePredator(ctx: CanvasRenderingContext2D, spec: MicrobePredatorSpec) {
    const { entityId, timeMs, style } = spec;
    const r = clamp(Math.max(spec.radius, 14), 14, 34);
    const rand = seededRand(((entityId * 1103515245) ^ 0x9E3779B9) >>> 0);
    const angle = movementAngle(spec.velX, spec.velY, rand);

    ctx.save();
    ctx.rotate(angle);

    // Head (icosahedral-ish capsid)
    const headR = r * 0.62;
    const headHue = 340; // magenta/red
    const menace = Math.sin(timeMs * 0.007 + entityId * 0.01) * 0.5 + 0.5;
    const headGrad = ctx.createRadialGradient(headR * 0.2, -headR * 0.2, 1, 0, 0, headR);
    headGrad.addColorStop(0, `hsla(${headHue}, 90%, ${58 + menace * 6}%, 0.98)`);
    headGrad.addColorStop(0.7, `hsla(${(headHue + 5) % 360}, 85%, 34%, 0.98)`);
    headGrad.addColorStop(1, `hsla(${(headHue + 15) % 360}, 70%, 18%, 0.98)`);
    ctx.fillStyle = headGrad;

    const sides = 6;
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
        const a = (i / sides) * Math.PI * 2 - Math.PI / 2;
        const rr = headR * (i % 2 === 0 ? 1 : 0.92);
        const x = Math.cos(a) * rr;
        const y = Math.sin(a) * rr;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fill();

    // Spiky corona around the head (scarier silhouette)
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = `hsla(${(headHue + 10) % 360}, 85%, 35%, 0.85)`;
    const spikes = 10;
    for (let i = 0; i < spikes; i++) {
        const a = (i / spikes) * Math.PI * 2 + menace * 0.2;
        const inner = headR * 0.95;
        const outer = headR * (1.25 + (rand() - 0.5) * 0.15);
        ctx.beginPath();
        ctx.moveTo(Math.cos(a) * inner, Math.sin(a) * inner);
        ctx.lineTo(Math.cos(a + 0.08) * outer, Math.sin(a + 0.08) * outer);
        ctx.lineTo(Math.cos(a - 0.08) * outer, Math.sin(a - 0.08) * outer);
        ctx.closePath();
        ctx.fill();
    }
    ctx.restore();

    if (style.facetLines) {
        ctx.strokeStyle = `rgba(255, 255, 255, 0.22)`;
        ctx.lineWidth = Math.max(1, r * 0.04);
        ctx.beginPath();
        ctx.moveTo(-headR * 0.6, 0);
        ctx.lineTo(headR * 0.6, 0);
        ctx.moveTo(0, -headR * 0.6);
        ctx.lineTo(0, headR * 0.6);
        ctx.stroke();
    }

    drawPredatorFace(ctx, r, headR, menace);

    // Tail core
    const tailLen = r * (0.9 + rand() * 0.35);
    const tailW = r * 0.18;
    const tailGrad = ctx.createLinearGradient(0, 0, -tailLen, 0);
    tailGrad.addColorStop(0, `hsla(${headHue}, 70%, 45%, 0.95)`);
    tailGrad.addColorStop(1, `hsla(${(headHue + 40) % 360}, 55%, 28%, 0.95)`);
    ctx.fillStyle = tailGrad;
    ctx.beginPath();
    roundRectPath(ctx, -headR * 0.95 - tailLen, -tailW / 2, tailLen, tailW, tailW / 2);
    ctx.fill();

    const pump = Math.sin(timeMs * 0.006 + entityId * 0.01) * 0.35 + 0.65;

    if (style.tailRings) {
        const ringCount = 3;
        ctx.strokeStyle = `rgba(255, 255, 255, 0.18)`;
        ctx.lineWidth = Math.max(1, r * 0.03);
        for (let i = 0; i < ringCount; i++) {
            const t = (i + 1) / (ringCount + 1);
            const x = -headR * 0.95 - tailLen * t;
            const rw = tailW * (0.7 + 0.3 * pump);
            ctx.beginPath();
            ctx.moveTo(x, -rw / 2);
            ctx.lineTo(x, rw / 2);
            ctx.stroke();
        }
    }

    // Tail fibers (legs)
    const fiberCount = 5 + Math.floor(rand() * 3);
    const fiberPump = style.pumpedFibers ? pump : 1;
    ctx.strokeStyle = `hsla(${(headHue + 160) % 360}, 55%, 65%, 0.55)`;
    ctx.lineWidth = Math.max(1, r * 0.025);
    for (let i = 0; i < fiberCount; i++) {
        const t = (i + 1) / (fiberCount + 1);
        const baseX = -headR * 0.95 - tailLen * (0.45 + t * 0.55);
        const baseY = (t - 0.5) * tailW * 2.2;
        const wiggle = Math.sin(timeMs * 0.005 + entityId * 0.03 + i) * (r * 0.10) * fiberPump;
        const endX = baseX - r * (0.35 + rand() * 0.25);
        const endY = baseY + wiggle;
        ctx.beginPath();
        ctx.moveTo(baseX, baseY);
        ctx.quadraticCurveTo((baseX + endX) / 2, (baseY + endY) / 2 + wiggle * 0.6, endX, endY);
        ctx.stroke();
    }

    if (style.coreDot) {
        ctx.fillStyle = `rgba(10, 10, 16, 0.45)`;
        ctx.beginPath();
        ctx.arc(headR * 0.1, headR * 0.15, headR * 0.22, 0, Math.PI * 2);
        ctx.fill();
    }

    // Outer glow to separate from background
    ctx.globalAlpha = 0.12;
    const glow = ctx.createRadialGradient(0, 0, headR * 0.2, 0, 0, r * 1.3);
    glow.addColorStop(0, `rgba(255, 40, 90, ${0.7 + menace * 0.25})`);
    glow.addColorStop(1, 'rgba(255, 90, 160, 0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(0, 0, r * 1.3, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
}

/** Glowing eye slits and the jaw aperture. Consumes no randomness. */
function drawPredatorFace(
    ctx: CanvasRenderingContext2D,
    r: number,
    headR: number,
    menace: number
) {
    ctx.save();
    const eyeY = -headR * 0.10;
    const eyeSpread = headR * 0.28;
    const eyeLen = headR * (0.22 + menace * 0.08);
    ctx.strokeStyle = `rgba(255, 40, 80, ${0.65 + menace * 0.25})`;
    ctx.lineWidth = Math.max(1.5, r * 0.06);
    ctx.lineCap = 'round';
    ctx.shadowColor = 'rgba(255, 50, 90, 0.8)';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.moveTo(-eyeSpread - eyeLen / 2, eyeY);
    ctx.lineTo(-eyeSpread + eyeLen / 2, eyeY + headR * 0.05);
    ctx.moveTo(eyeSpread - eyeLen / 2, eyeY);
    ctx.lineTo(eyeSpread + eyeLen / 2, eyeY + headR * 0.05);
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Jaw / aperture
    ctx.fillStyle = 'rgba(10, 10, 16, 0.55)';
    ctx.beginPath();
    ctx.moveTo(headR * 0.10, headR * 0.42);
    ctx.lineTo(-headR * 0.16, headR * 0.20);
    ctx.lineTo(headR * 0.32, headR * 0.20);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
}

export interface MicrobeSubstrateSpec {
    entityId: number;
    radius: number;
    /** Embedded mineral flecks. Drawn last, so enabling it moves nothing else. */
    crystals: boolean;
}

/**
 * Porous agar/mineral substrate with pits and growth rings: the top-down
 * stand-in for castles and other inert obstacles. Drawn centred on the current
 * origin; the caller owns save/restore.
 */
export function drawMicrobeSubstrate(ctx: CanvasRenderingContext2D, spec: MicrobeSubstrateSpec) {
    const r = clamp(Math.max(spec.radius, 18), 18, 60);
    const rand = seededRand(((spec.entityId * 2246822519) ^ 0xB5297A4D) >>> 0);
    const wobble = 0.10;

    // Base blob
    wobblyBlobPath(ctx, r, rand, wobble);
    const baseGrad = ctx.createRadialGradient(r * 0.2, -r * 0.2, 1, 0, 0, r * 1.1);
    baseGrad.addColorStop(0, 'rgba(150, 200, 210, 0.65)');
    baseGrad.addColorStop(0.6, 'rgba(95, 135, 150, 0.70)');
    baseGrad.addColorStop(1, 'rgba(45, 70, 85, 0.75)');
    ctx.fillStyle = baseGrad;
    ctx.fill();

    // Subtle rim highlight
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.14)';
    ctx.lineWidth = Math.max(1, r * 0.04);
    wobblyBlobPath(ctx, r, rand, wobble * 0.75);
    ctx.stroke();

    // Pores/pits (negative space)
    const pitCount = clamp(Math.floor(6 + r * 0.12), 6, 14);
    ctx.save();
    ctx.globalCompositeOperation = 'destination-out';
    ctx.globalAlpha = 0.65;
    for (let i = 0; i < pitCount; i++) {
        const a = rand() * Math.PI * 2;
        const d = r * (0.10 + rand() * 0.75);
        const px = Math.cos(a) * d;
        const py = Math.sin(a) * d;
        const pr = r * (0.06 + rand() * 0.10);
        ctx.beginPath();
        ctx.arc(px, py, pr, 0, Math.PI * 2);
        ctx.fill();
    }
    ctx.restore();

    // Growth rings / striations
    ctx.save();
    ctx.globalAlpha = 0.20;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.22)';
    ctx.lineWidth = Math.max(1, r * 0.02);
    const rings = 3 + Math.floor(rand() * 3);
    for (let i = 0; i < rings; i++) {
        const rr = r * (0.35 + i * 0.18);
        ctx.beginPath();
        ctx.ellipse(0, 0, rr, rr * (0.82 + rand() * 0.2), rand() * 0.8, 0, Math.PI * 2);
        ctx.stroke();
    }
    ctx.restore();

    if (!spec.crystals) return;

    // Tiny embedded crystals
    ctx.save();
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = 'rgba(220, 240, 255, 0.45)';
    const crystalCount = 4 + Math.floor(rand() * 4);
    for (let i = 0; i < crystalCount; i++) {
        const a = rand() * Math.PI * 2;
        const d = r * (0.15 + rand() * 0.75);
        const cx = Math.cos(a) * d;
        const cy = Math.sin(a) * d;
        const s = r * (0.05 + rand() * 0.08);
        ctx.beginPath();
        ctx.moveTo(cx, cy - s);
        ctx.lineTo(cx + s, cy);
        ctx.lineTo(cx, cy + s);
        ctx.lineTo(cx - s, cy);
        ctx.closePath();
        ctx.fill();
    }
    ctx.restore();
}
