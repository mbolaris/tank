/**
 * Shared player types for the network dashboard's poker readouts.
 *
 * Auto-evaluation reports players in two shapes: the live `players` array on
 * the snapshot, and the richer per-hand entries inside `performance_history`.
 * TankCard renders whichever is available, so it needs the union; the chart
 * only ever sees history entries.
 */

import type { AutoEvaluatePlayerStats, PokerPerformanceSnapshot } from '../../types/simulation';

/** Player data from poker performance snapshots */
export type SnapshotPlayer = PokerPerformanceSnapshot['players'][number];

export type AutoEvalPlayer = AutoEvaluatePlayerStats | SnapshotPlayer;
