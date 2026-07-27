/**
 * A fixed, fully-populated world snapshot for renderer trace tests.
 *
 * Every branch the top-down renderers dispatch on is represented exactly once:
 * each entity kind, both food-image paths, a poker loss and a poker tie, a death
 * cause, a birth effect and a soccer effect. Values are hand-picked constants —
 * nothing here is derived from a live simulation, so the trace stays stable.
 */

import type { EntityData, FishGenomeData, PlantGenomeData } from '../../types/simulation';

export const FIXTURE_NOW_MS = 12_345;
export const FIXTURE_SELECTED_ID = 1;

const genome = (overrides: Partial<FishGenomeData> = {}): FishGenomeData => ({
    speed: 1.2,
    size: 1,
    color_hue: 0.42,
    template_id: 1,
    fin_size: 1.1,
    tail_size: 0.9,
    body_aspect: 1.3,
    eye_size: 1.2,
    pattern_intensity: 0.65,
    pattern_type: 0,
    aggression: 0.4,
    pursuit_aggression: 0.5,
    hunting_stamina: 0.7,
    prediction_skill: 0.3,
    behavior: { food_approach: 2 },
    ...overrides,
});

const plantGenome: PlantGenomeData = {
    axiom: 'F',
    angle: 25,
    length_ratio: 0.6,
    branch_probability: 0.5,
    curve_factor: 1,
    color_hue: 0.3,
    color_saturation: 0.8,
    stem_thickness: 2,
    leaf_density: 0.5,
    // Drives the petri view's strategy label pill.
    strategy_type: 'tight_aggressive',
    aggression: 0.6,
    bluff_frequency: 0.2,
    risk_tolerance: 0.4,
    base_energy_rate: 0.5,
    growth_efficiency: 0.7,
    nectar_threshold_ratio: 0.3,
    fitness_score: 1.5,
    production_rules: [{ input: 'F', output: 'F[+F]F', prob: 1.0 }],
};

/**
 * Four fish covering the shape/pattern branches of the microbe avatar
 * (`template_id % 6` selects blob vs capsule; `pattern_type` selects the four
 * pattern overlays) plus the effect overlays.
 */
const fish: EntityData[] = [
    {
        id: 1,
        type: 'fish',
        x: 120,
        y: 80,
        width: 32,
        height: 24,
        vel_x: 1.4,
        vel_y: -0.6,
        energy: 72,
        generation: 12,
        genome_data: genome({ template_id: 1, pattern_type: 0 }),
        birth_effect_timer: 40,
    },
    {
        id: 2,
        type: 'fish',
        x: 300,
        y: 200,
        width: 28,
        height: 22,
        vel_x: 0,
        vel_y: 0,
        energy: 45,
        generation: 3,
        genome_data: genome({ template_id: 2, pattern_type: 1, color_hue: 0.77 }),
        poker_effect_state: { status: 'lost', amount: 18, target_id: 3, target_type: 'fish' },
    },
    {
        id: 3,
        type: 'fish',
        x: 340,
        y: 240,
        width: 30,
        height: 26,
        vel_x: -0.9,
        vel_y: 0.3,
        energy: 20,
        generation: 31,
        genome_data: genome({ template_id: 5, pattern_type: 2, color_hue: 0.05 }),
        death_effect_state: { cause: 'starvation' },
        soccer_effect_state: { type: 'goal', amount: 25, timer: 42 },
    },
    {
        id: 4,
        type: 'fish',
        x: 700,
        y: 400,
        width: 26,
        height: 20,
        vel_x: 0.2,
        vel_y: 0.9,
        energy: 91,
        generation: 0,
        genome_data: genome({ template_id: 3, pattern_type: 3, color_hue: 0.9 }),
        poker_effect_state: { status: 'tie', amount: 0 },
    },
];

const others: EntityData[] = [
    { id: 10, type: 'food', x: 200, y: 150, width: 12, height: 12, food_type: 'protein' },
    { id: 11, type: 'food', x: 260, y: 170, width: 14, height: 14, food_type: 'live' },
    {
        id: 12,
        type: 'plant',
        x: 500,
        y: 520,
        width: 60,
        height: 70,
        genome: plantGenome,
        size_multiplier: 0.8,
        iterations: 1,
    },
    {
        id: 13,
        type: 'plant_nectar',
        x: 520,
        y: 470,
        width: 10,
        height: 10,
        source_plant_id: 12,
    },
    { id: 14, type: 'crab', x: 820, y: 500, width: 40, height: 30, vel_x: -1.1, vel_y: 0.2 },
    { id: 15, type: 'castle', x: 900, y: 430, width: 70, height: 80 },
    { id: 16, type: 'ball', x: 544, y: 306, width: 20, height: 20, vel_x: 0.8, vel_y: -0.4 },
    { id: 17, type: 'goal_zone', x: 60, y: 306, width: 60, height: 60, team: 'left' },
    { id: 18, type: 'decorative_rock', x: 400, y: 560, width: 24, height: 18 },
];

export const FIXTURE_ENTITIES: EntityData[] = [...fish, ...others];

/** Shaped like the live wire payload the renderers receive. */
export function buildFixtureSnapshot() {
    return {
        snapshot: {
            entities: FIXTURE_ENTITIES,
            elapsed_time: 9_876,
            render_hint: {
                dish: { shape: 'circle' as const, cx: 544, cy: 306, r: 296 },
            },
        },
    };
}
