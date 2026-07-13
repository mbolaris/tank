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
    subject: 'engine_baseline';
    config_hash: string;
    mean: number;
    wandering_mean: number;
    perfect_mean: number;
    confidence_interval: [number, number];
    range: [number, number];
    average_food: number;
    average_energy: number;
    metadata: {
        seeds: number[];
        per_seed: Record<string, ForagingGymResult>;
    };
}
