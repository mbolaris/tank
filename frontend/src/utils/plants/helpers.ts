import type { PlantGenomeData } from './types';

/**
 * Seeded random for deterministic plant generation.
 */
export function seededRandom(seed: number): number {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
}

/**
 * HSL color space conversion to CSS RGB string.
 */
export function hslToRgb(h: number, s: number, l: number): string {
    let r: number, g: number, b: number;

    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p: number, q: number, t: number): number => {
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

    return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

/**
 * HSL color space conversion to RGB number tuple.
 */
export function hslToRgbTuple(h: number, s: number, l: number): [number, number, number] {
    let r: number, g: number, b: number;

    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p: number, q: number, t: number): number => {
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

/**
 * Create a stable signature for a genome so cache invalidation happens when traits change.
 */
export function getGenomeSignature(genome: PlantGenomeData): string {
    const rules = genome.production_rules ?? [];
    const ruleSignature = rules
        .map((rule) => `${rule.input}:${rule.output}:${rule.prob}`)
        .join('|');

    return [
        genome.axiom,
        genome.angle,
        genome.length_ratio,
        genome.branch_probability,
        genome.curve_factor,
        genome.type ?? 'lsystem',
        genome.color_hue,
        genome.color_saturation,
        genome.stem_thickness,
        genome.leaf_density,
        ruleSignature,
    ].join(';');
}
