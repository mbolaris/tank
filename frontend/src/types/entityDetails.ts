/**
 * On-demand entity detail payload returned by the `get_entity_details`
 * WebSocket command (fish inspector, U4/E1).
 *
 * The 30fps broadcast intentionally strips these heavy fields; the inspector
 * requests them for a single entity instead. Mirrors the payload built in
 * backend/runner/hooks/entity_details_mixin.py.
 */

export interface EntityDetailsLineage {
    parent_id: number | null;
    is_soup_spawn: boolean;
}

export interface EntityDetailsBehavior {
    algorithm: string | null;
    behavior_id: string | null;
    parameters: Record<string, number | string> | null;
    lens?: EntityDetailsBehaviorLens;
    movement_intent?: EntityDetailsMovementIntent | null;
}

export interface EntityDetailsMovementIntent {
    chosen: {
        velocity: [number, number];
        kind: string;
        urgency: number;
        confidence: number;
        target_id: number | null;
        source: string;
    } | null;
    /** Lower-priority sources skipped to preserve deterministic arbitration. */
    suppressed_sources: string[];
}

export interface EntityDetailsBehaviorLens {
    intent: string;
    target: string | null;
    inputs: Record<string, unknown>;
    outputs: Record<string, unknown>;
    explanations: Record<string, Record<string, unknown>>;
    output: unknown;
    contributions: Record<string, number>;
    cancellation?: number;
    fingerprint: string;
    graph: {
        nodes: Array<{ id: string; type: string; parameters: Record<string, unknown> }>;
        connections: Array<{ source: string; target: string; port: string }>;
        output: string;
    };
}

export interface EntityDetailsGames {
    poker: { eligible: boolean; cooldown_frames: number };
    soccer: { ball_present: boolean; eligible: boolean };
}

export interface EntityDetailsReproduction {
    overflow_energy_bank: number;
    is_gravid: boolean;
}

export interface EntityDetailsTaxonomy {
    taxon_id: string;
    common_name: string;
    scientific_name: string;
    status: 'provisional' | 'established' | 'extinct' | string;
    strain_id: string | null;
}

export type EntityEnergyStatus = 'critical' | 'hungry' | 'content' | 'full';

export interface ParameterEvolutionData {
    current: number;
    parent: number | null;
    species_median: number;
    percentile: number;
    carriers_count: number;
    carriers_pct: number;
    trend: 'increasing' | 'declining' | 'stable';
}

export interface EntityDetailsPursuitModule {
    name: string;
    used_for: string[];
    parameters: {
        speed_multiplier: number;
        prediction_strength: number;
        max_prediction_horizon: number;
        pursuit_commitment: number;
    };
    parameters_evolution?: {
        speed_multiplier: ParameterEvolutionData;
        prediction_strength: ParameterEvolutionData;
        max_prediction_horizon: ParameterEvolutionData;
        pursuit_commitment: ParameterEvolutionData;
    } | null;
    current_target: string | null;
    /** Raw, non-predictive offset to the current target (world units). */
    target_vector: [number, number] | null;
    /** The module's predicted-intercept steering output (world-unit direction). */
    aim_vector: [number, number] | null;
    inherited_from: number | null;
}

export interface EntityDetails {
    id: number;
    type: string;
    frame: number;
    // Present for fish; absent for plants/crabs/castles (which get energy only).
    fish_id?: number | null;
    energy?: number;
    max_energy?: number;
    energy_ratio?: number;
    status?: EntityEnergyStatus;
    age?: number;
    max_age?: number;
    life_stage?: string | null;
    generation?: number;
    species?: string | null;
    taxonomy?: EntityDetailsTaxonomy | null;
    lineage?: EntityDetailsLineage;
    behavior?: EntityDetailsBehavior;
    traits?: Record<string, number>;
    games?: EntityDetailsGames;
    reproduction?: EntityDetailsReproduction;
    modules?: EntityDetailsPursuitModule | null;
    target_memory?: EntityDetailsTargetMemory | null;
    detail_error?: string;
}

export interface EntityDetailsTargetMemoryDomain {
    domain: string;
    action: string;
    action_raw: string | null;
    remembering: string;
    last_seen: string;
    last_seen_frames: number;
    confidence: string;
    confidence_raw: number;
    predicted_location: string;
    predicted_offset: number;
    switch_threshold: string;
    memory_duration: number;
    last_seen_position: [number, number];
    predicted_position: [number, number];
    search_vector: [number, number];
    influencing_movement: boolean;
}

export interface EntityDetailsTargetMemoryRecentEvent {
    domain: string;
    action: string;
    from_target: number | null;
    to_target: number | null;
    age_frames: number;
}

export interface EntityDetailsTargetMemory {
    domains: {
        food?: EntityDetailsTargetMemoryDomain;
        ball?: EntityDetailsTargetMemoryDomain;
    };
    recent_event: EntityDetailsTargetMemoryRecentEvent | null;
}

