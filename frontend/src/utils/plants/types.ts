/**
 * Shared type definitions for fractal plant rendering.
 */

export interface PlantGenomeData {
    axiom: string;
    angle: number;
    length_ratio: number;
    branch_probability: number;
    curve_factor: number;
    color_hue: number;
    color_saturation: number;
    stem_thickness: number;
    leaf_density: number;
    type?:
    | 'lsystem'
    | 'cosmic_fern'
    | 'mandelbrot'
    | 'claude'
    | 'antigravity'
    | 'gpt'
    | 'gpt_codex'
    | 'gemini'
    | 'sonnet'
    | 'baseline';
    production_rules: Array<{
        input: string;
        output: string;
        prob: number;
    }>;
    strategy_type?: string;
}

export interface TurtleState {
    x: number;
    y: number;
    angle: number;
    length: number;
    thickness: number;
}

export interface FractalSegment {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    thickness: number;
    depth: number;
    kind?: 'root' | 'branch';
}

export interface FractalLeaf {
    x: number;
    y: number;
    angle: number;
    size: number;
}

export interface MandelbrotCacheEntry {
    signature: string;
    texture: HTMLCanvasElement;
}

export interface PlantRenderCache {
    iterations: number;
    signature: string;
    segments: FractalSegment[];
    leaves: FractalLeaf[];
    sortedSegments: FractalSegment[];
    segmentGroups?: Array<{ thickness: number; segments: FractalSegment[]; path?: Path2D }>;
    leafPath?: Path2D;
    veinPath?: Path2D;
}

/**
 * Floral genome data for nectar rendering.
 */
export interface FloralGenome {
    floral_type?: string;
    floral_petals?: number;
    floral_layers?: number;
    floral_spin?: number;
    floral_hue?: number;
    floral_saturation?: number;
}
