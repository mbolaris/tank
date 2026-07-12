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
    detail_error?: string;
}
