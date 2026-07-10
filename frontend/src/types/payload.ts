/**
 * Named wire-payload shapes shared by the backend contract tests and UI types.
 *
 * Kept separate from simulation.ts so the large application-facing type catalog
 * stays within its file-size ratchet while these transport concerns evolve.
 */

import type {
    AutoEvaluateStats,
    EntityData,
    MetricsHistory,
    MetricsSample,
    PokerEventData,
    PokerLeaderboardEntry,
    SoccerEventData,
    SoccerLeagueLiveState,
    StatsData,
} from './simulation';

export interface FullStateSnapshot {
    frame: number;
    elapsed_time: number;
    entities: EntityData[];
    stats: StatsData;
    poker_events: PokerEventData[];
    soccer_events: SoccerEventData[];
    soccer_league_live?: SoccerLeagueLiveState | null;
    poker_leaderboard: PokerLeaderboardEntry[];
    auto_evaluation?: AutoEvaluateStats;
    render_hint?: Record<string, unknown>;
    metrics_history?: MetricsHistory | null;
}

export interface DeltaEntityUpdate {
    id: number;
    x: number;
    y: number;
    vel_x: number;
    vel_y: number;
    poker_effect_state?: EntityData['poker_effect_state'];
    birth_effect_timer?: number;
    death_effect_state?: EntityData['death_effect_state'];
    soccer_effect_state?: EntityData['soccer_effect_state'];
}

export interface DeltaStateSnapshot {
    frame: number;
    elapsed_time: number;
    updates: DeltaEntityUpdate[];
    added: EntityData[];
    removed: number[];
    poker_events: PokerEventData[];
    soccer_events?: SoccerEventData[];
    soccer_league_live?: SoccerLeagueLiveState | null;
    stats?: StatsData;
    render_hint?: Record<string, unknown>;
    new_metrics_sample?: MetricsSample | null;
}
