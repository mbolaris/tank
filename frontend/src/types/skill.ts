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
