// Skill-ladder standings (frozen-ruler measurement). Mirrors
// core/skill/ladder.py::SkillLadderSummary / RungResult.

export interface SkillRung {
    rung: string;
    rung_id: string;
    metric: number;
    beaten: boolean;
    ci_95?: [number, number];
    detail?: Record<string, number>;
}

export interface SkillLadder {
    domain: string;
    benchmark_id: string;
    metric_name: string;
    skill_index: number;
    rungs_beaten: number;
    total_rungs: number;
    rungs: SkillRung[];
    notes?: string;
}

export interface SkillLaddersResponse {
    schema_version: number;
    ladders: SkillLadder[];
}

export interface ForagingGymEpisode {
    energy_collected: number;
    food_collected: number;
    energy_spent: number;
    travel_distance: number;
}

export interface ForagingGymResult {
    benchmark_id: 'tank/foraging_gym';
    seed: number;
    score: number;
    score_breakdown: {
        composable_energy_ratio: number;
        random_walk_energy_ratio: number;
        oracle_energy_ratio: number;
    };
    metadata: {
        oracle_energy: number;
        composable: ForagingGymEpisode;
        random_walk: ForagingGymEpisode;
        oracle: ForagingGymEpisode;
        skill: SkillLadder;
    };
}

export interface ForagingGymSummary {
    subject: string;
    benchmark_id: string;
    config_hash: string;
    mean: number;
    wandering_mean: number;
    perfect_mean: number;
    confidence_interval: [number, number];
    range: [number, number];
    average_food: number;
    average_food_available: number;
    average_energy: number;
    metadata: {
        seeds: number[];
        per_seed: Record<string, ForagingGymResult>;
    };
}

export interface ObservatoryData {
    status: 'success' | 'no_data';
    message?: string;
    world_id?: string;
    evaluated_at_frame?: number;
    evaluated_at_generation?: number;
    benchmark_hash?: string;
    subject?: string;
    tank_average?: number;
    best_species?: {
        name: string;
        score: number;
    };
    best_individual?: {
        id: number;
        name: string;
        score: number;
        food_collected: number;
        food_available: number;
        // The legacy composable-behavior trait and the newer pursuit-module
        // parameter measure genuinely different things and must never be
        // compared against each other - keep all four fields separate.
        legacy_prediction_skill: number;
        species_founder_legacy_prediction_skill: number;
        parent_legacy_prediction_skill?: number | null;
        pursuit_prediction_strength?: number | null;
        parent_pursuit_prediction_strength?: number | null;
        species_median: number;
        module_fingerprint: string;
        similar_fraction: number;
        score_uncertainty: number;
        sample_size: number;
    };
    engine_baseline?: number;
    wandering_mean?: number;
    perfect_mean?: number;
}

export interface SkillSnapshot {
    domain: string;
    generation: number;
    frame: number;
    subject_fish_ids: number[];
    subject_lineage_ids: string[];
    summary: SkillLadder;
    previous_score?: number | null;
    personal_best: number;
    tank_best: number;
    sample_size: number;
    timestamp: string;
}

export interface SkillSnapshotsResponse {
    schema_version: number;
    world_id: string;
    count: number;
    tank_best: number;
    latest_baseline_score_diff?: number | null;
    snapshots: SkillSnapshot[];
    breakthroughs?: SkillBreakthrough[];
}

export interface SkillBreakthrough {
    event_id: string;
    kind: string;
    source_id: string;
    frame: number;
    match_id?: string | null;
    detail?: Record<string, string | number>;
}
