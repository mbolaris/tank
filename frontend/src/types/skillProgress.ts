/**
 * Skill-progress contract, mirrored from `core/research/skill_progress.py`.
 *
 * The verdict set is deliberately wider than the three states the panel is
 * named for. `no_data` and `at_ceiling` exist because without them the honest
 * answer would have to be a lie: a domain that has never been measured is not
 * stalled, and one that beats every rung on its ruler is the opposite of
 * stalled.
 */

export type SkillVerdict =
    | 'progressing'
    | 'possibly_progressing'
    | 'stalled'
    | 'at_ceiling'
    | 'no_data';

export interface SkillProgressDomain {
    domain: string;
    verdict: SkillVerdict;
    /** One sentence naming the numbers the verdict rests on. */
    reason: string;
    samples: number;
    earlier_mean: number | null;
    recent_mean: number | null;
    delta: number | null;
    /** Sampling noise the delta was judged against. */
    standard_error: number | null;
    generation_span: number;
    ceiling_share: number;
}

export interface SkillProgressResponse {
    schema_version?: number;
    world_id?: string;
    domains?: SkillProgressDomain[];
    status?: string;
    message?: string;
}
