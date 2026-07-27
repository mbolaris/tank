/**
 * The gene-driven microbe avatar: one implementation for the tank top-down
 * view, the petri dish and the standalone avatar renderer (poker portraits,
 * soccer players), which each carried their own copy before this module.
 *
 * Everything visible is read from the genome, so the drawing doubles as the
 * phenotype: body shape from `template_id`/`body_aspect`, colour from
 * `color_hue`, nucleus from `eye_size`, cilia from `fin_size`, flagellum from
 * `tail_size`, speckling from `pattern_type`/`pattern_intensity`. Read-only —
 * it never mutates the genome it is handed.
 */

import type { FishGenomeData } from '../../types/simulation';
import {
    capsulePath,
    clamp,
    genomeHueDegrees,
    movementAngle,
    seededRand,
    wobblyBlobPath,
} from './canvasPrimitives';

export interface MicrobeAvatarSpec {
    entityId: number;
    radius: number;
    velX?: number;
    velY?: number;
    genome?: FishGenomeData | null;
    /**
     * Lineage depth. Older generations read slightly more saturated, which
     * makes an established lineage visible at a glance. Omit where generation
     * is unknown (portrait rendering) to draw at baseline saturation.
     */
    generation?: number;
    /**
     * Draw the phenotype legibility cues for behavioural traits
     * (docs/EVOLVABILITY.md sec 3.5). Off for portraits, where there is no
     * world context to read them against.
     */
    traitCues?: boolean;
}

/** Fixed per-strategy hues for the food-approach family ring. */
const FOOD_APPROACH_FAMILY_HUES = [200, 130, 20, 280, 50, 320];

/**
 * Draws the organism centred on the current origin. The caller owns
 * translation; this owns rotation.
 */
export function drawMicrobeAvatar(ctx: CanvasRenderingContext2D, spec: MicrobeAvatarSpec) {
    const { entityId, genome } = spec;
    const templateId = genome?.template_id ?? (entityId % 6);
    const hueDeg = genomeHueDegrees(genome, entityId);

    const r = clamp(Math.max(spec.radius, 10), 10, 26);
    const finSize = genome?.fin_size ?? 1;
    const tailSize = genome?.tail_size ?? 1;
    const bodyAspect = genome?.body_aspect ?? 1;
    const eyeSize = genome?.eye_size ?? 1;
    const patternIntensity = clamp(genome?.pattern_intensity ?? 0, 0, 1);
    const patternType = genome?.pattern_type ?? 0;

    // Seeded from the visual genes, so a mutation that changes how a fish looks
    // also re-rolls its speckle layout, while an unchanged genome is stable.
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
    const moveAngle = movementAngle(spec.velX, spec.velY, rand);

    ctx.save();
    ctx.rotate(moveAngle);

    const wobble = 0.06 + patternIntensity * 0.08;
    const shapeKind = templateId % 6;
    const bodyPath = (radius: number, wob: number) => {
        if (shapeKind === 2 || shapeKind === 5) capsulePath(ctx, radius * 0.9, bodyAspect);
        else wobblyBlobPath(ctx, radius, rand, wob);
    };

    bodyPath(r, wobble);

    // Outer membrane gradient.
    const genSatBoost = clamp((spec.generation ?? 0) / 25, 0, 1) * 18;
    const membrane = ctx.createRadialGradient(r * 0.25, -r * 0.25, r * 0.1, 0, 0, r * 1.1);
    membrane.addColorStop(0, `hsla(${hueDeg}, ${70 + genSatBoost}%, 62%, 0.95)`);
    membrane.addColorStop(0.6, `hsla(${hueDeg}, ${60 + genSatBoost}%, 48%, 0.88)`);
    membrane.addColorStop(1, `hsla(${(hueDeg + 20) % 360}, ${55 + genSatBoost}%, 34%, 0.85)`);
    ctx.fillStyle = membrane;
    ctx.fill();

    // Cytoplasm
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.scale(0.78, 0.78);
    bodyPath(r, wobble * 0.65);
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

    drawPatternOverlay(ctx, { r, hueDeg, patternType, patternIntensity, rand });
    drawCilia(ctx, { r, hueDeg, finSize, patternIntensity, rand });
    drawFlagellum(ctx, { r, hueDeg, tailSize, rand });

    // Membrane highlight
    ctx.strokeStyle = `hsla(${hueDeg}, 80%, 78%, 0.35)`;
    ctx.lineWidth = 1.5;
    bodyPath(r, wobble * 0.8);
    ctx.stroke();

    if (spec.traitCues) {
        drawTraitCues(ctx, { genome, r, hueDeg, rand });
    }

    ctx.restore();
}

interface PatternArgs {
    r: number;
    hueDeg: number;
    patternType: number;
    patternIntensity: number;
    rand: () => number;
}

/** Speckling/banding overlay selected by `pattern_type`. */
function drawPatternOverlay(ctx: CanvasRenderingContext2D, args: PatternArgs) {
    const { r, hueDeg, patternType, patternIntensity, rand } = args;

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
}

interface CiliaArgs {
    r: number;
    hueDeg: number;
    finSize: number;
    patternIntensity: number;
    rand: () => number;
}

/** Fringe of cilia around the membrane; count and length follow `fin_size`. */
function drawCilia(ctx: CanvasRenderingContext2D, args: CiliaArgs) {
    const { r, hueDeg, finSize, patternIntensity, rand } = args;
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
}

interface FlagellumArgs {
    r: number;
    hueDeg: number;
    tailSize: number;
    rand: () => number;
}

/** Primary flagellum trailing off the back; length follows `tail_size`. */
function drawFlagellum(ctx: CanvasRenderingContext2D, args: FlagellumArgs) {
    const { r, hueDeg, tailSize, rand } = args;

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
}

interface TraitCueArgs {
    genome: FishGenomeData | null | undefined;
    r: number;
    hueDeg: number;
    rand: () => number;
}

/**
 * Phenotype legibility cues for traits selection is currently acting on but
 * that have no other visual presence (docs/EVOLVABILITY.md sec 3.5). Drawn
 * after the membrane/pattern/cilia/tail passes so it consumes only the tail end
 * of the seeded rand() sequence and leaves the organism itself unchanged.
 */
function drawTraitCues(ctx: CanvasRenderingContext2D, args: TraitCueArgs) {
    const { genome, r, hueDeg, rand } = args;

    // Aggression -> outer glow aura, red-shifted with intensity
    const aggression = clamp(genome?.aggression ?? 0, 0, 1);
    if (aggression > 0.05) {
        const auraHue = hueDeg * (1 - aggression);
        const auraR = r * (1.15 + aggression * 0.35);
        ctx.save();
        ctx.globalAlpha = 0.15 + aggression * 0.35;
        const auraGrad = ctx.createRadialGradient(0, 0, r * 0.9, 0, 0, auraR);
        auraGrad.addColorStop(0, `hsla(${auraHue}, 90%, 55%, 0.55)`);
        auraGrad.addColorStop(1, `hsla(${auraHue}, 90%, 50%, 0)`);
        ctx.fillStyle = auraGrad;
        ctx.beginPath();
        ctx.arc(0, 0, auraR, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    // Prediction_skill -> forward sensory cone (narrower & longer as skill rises)
    const predictionSkill = clamp(genome?.prediction_skill ?? 0, 0, 1);
    if (predictionSkill > 0.05) {
        const coneLen = r * (0.8 + predictionSkill * 2.2);
        const coneHalfAngle = 0.55 - predictionSkill * 0.28;
        ctx.save();
        ctx.globalAlpha = 0.1 + predictionSkill * 0.22;
        const coneGrad = ctx.createLinearGradient(r * 0.9, 0, r * 0.9 + coneLen, 0);
        coneGrad.addColorStop(0, `hsla(${(hueDeg + 200) % 360}, 80%, 75%, 0.8)`);
        coneGrad.addColorStop(1, `hsla(${(hueDeg + 200) % 360}, 80%, 75%, 0)`);
        ctx.fillStyle = coneGrad;
        ctx.beginPath();
        ctx.moveTo(r * 0.9, 0);
        ctx.lineTo(r * 0.9 + coneLen, -Math.sin(coneHalfAngle) * coneLen);
        ctx.lineTo(r * 0.9 + coneLen, Math.sin(coneHalfAngle) * coneLen);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    // Hunting_stamina -> trailing bubble stream behind the organism
    const huntingStamina = clamp(genome?.hunting_stamina ?? 0, 0, 1);
    if (huntingStamina > 0.05) {
        const bubbleCount = Math.floor(huntingStamina * 5);
        ctx.save();
        ctx.globalAlpha = 0.35;
        ctx.fillStyle = `hsla(${(hueDeg + 190) % 360}, 40%, 85%, 0.7)`;
        for (let i = 0; i < bubbleCount; i++) {
            const t = (i + 1) / (bubbleCount + 1);
            const bx = -r * (1.3 + t * 2.1) + (rand() - 0.5) * r * 0.3;
            const by = (rand() - 0.5) * r * 0.7 * (1 + t);
            const br = r * (0.06 + rand() * 0.05) * (1 - t * 0.4);
            ctx.beginPath();
            ctx.arc(bx, by, br, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.restore();
    }

    // Food-approach family: a dashed ring at a fixed per-strategy hue, independent
    // of the individual's own color_hue (which stays the mate-choice signal).
    const foodApproach = genome?.behavior?.food_approach ?? 0;
    const familyHue = FOOD_APPROACH_FAMILY_HUES[foodApproach % FOOD_APPROACH_FAMILY_HUES.length];
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.strokeStyle = `hsla(${familyHue}, 75%, 65%, 0.9)`;
    ctx.lineWidth = Math.max(1, r * 0.045);
    ctx.setLineDash([r * 0.18, r * 0.12]);
    ctx.beginPath();
    ctx.arc(0, 0, r * 1.08, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
}
