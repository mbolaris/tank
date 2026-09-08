/**
 * In-world legend contract (U8b/E6), mirrored from backend/legends.py.
 *
 * A legend is a promotion inside one world's history — not a benchmark
 * champion. The `champions/` registry records reproducible best-known
 * solutions; these records mean nothing outside the tank that produced them,
 * and the two must never be presented as the same kind of claim.
 */

/** Closed set; mirrors LEGEND_KINDS. Growing it is a versioned backend change. */
export type LegendKind = 'longevity_record' | 'lineage_founder' | 'collapse_survivor';

export type LegendSubjectType = 'fish' | 'lineage';

export interface Legend {
    id: number;
    schema_version: number;
    kind: LegendKind;
    subject_type: LegendSubjectType;
    subject_id: string;
    /** Stable across reloads: derived from subject_id alone. */
    name: string;
    title: string;
    /** Why this subject qualified, in words. */
    reason: string;
    /** The measured numbers behind that reason. */
    evidence: Record<string, number | string | boolean | null>;
    frame: number;
    simulation_time: number;
}

/** Response shape from GET /api/world/{world_id}/legends. */
export interface LegendResponse {
    schema_version: number;
    world_id: string;
    kinds: LegendKind[];
    count: number;
    legends: Legend[];
}
