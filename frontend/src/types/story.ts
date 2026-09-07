/**
 * Story-event contract (E3/U6) - the deterministic world facts the detectors
 * measure, mirrored from backend/story_events.py.
 *
 * These live outside `simulation.ts` on purpose: that module is the websocket
 * payload contract, and story events arrive over REST
 * (GET /api/world/{id}/story-events) on their own cadence and schema version.
 */

import type { CommentarySeverity } from './simulation';
/**
 * The closed set of detector outputs. Mirrors EVENT_TYPES in
 * backend/story_events.py; growing it is a versioned backend change.
 */
export type StoryEventType =
    | 'population_danger'
    | 'population_recovered'
    | 'generation_milestone'
    | 'lineage_dominant';

/**
 * One structured world fact. Mirrors the schema v1 record in
 * backend/story_events.py.
 *
 * Note there is deliberately **no wall-clock field**: every value is a function
 * of the simulation sample that produced it, so a re-run yields byte-identical
 * records. Order by `id`; place in time with `frame` / `simulation_time`.
 */
export interface StoryEvent {
    id: number;
    schema_version: number;
    event_type: StoryEventType;
    frame: number;
    simulation_time: number;
    /** Shares the Board's closed severity set so one surface can render both. */
    severity: CommentarySeverity;
    title: string;
    entity_ids: number[];
    lineage_ids: string[];
    metrics_before: Record<string, number | string | boolean | null>;
    metrics_after: Record<string, number | string | boolean | null>;
    detector_name: string;
    detector_threshold: Record<string, number | string | boolean | null>;
    /**
     * Set only when retained replay data actually exists for this event.
     * Nothing wires replay segments to events yet, so this is always null
     * today - never offer a "watch" affordance unless it resolves.
     */
    replay_ref: string | null;
}

/**
 * Response shape from GET /api/world/{world_id}/story-events.
 */
export interface StoryEventResponse {
    schema_version: number;
    world_id: string;
    event_types: StoryEventType[];
    last_observed_frame: number;
    count: number;
    events: StoryEvent[];
}
