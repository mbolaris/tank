/**
 * Unit tests for WebSocket update normalization.
 * Ensures mode_id and view_mode are preserved from server updates.
 */

import { describe, it, expect } from 'vitest';
import type { SimulationUpdate, DeltaUpdate } from '../types/simulation';

/**
 * Pure function to normalize a WorldUpdatePayload into SimulationUpdate format.
 * This mirrors the normalization logic in useWebSocket.ts.
 */
export function normalizeWorldUpdate(data: Record<string, unknown>): SimulationUpdate {
    const update = data as unknown as SimulationUpdate;

    // Copy nested snapshot fields to top level
    if (update.snapshot) {
        update.frame = update.snapshot.frame;
        update.elapsed_time = update.snapshot.elapsed_time;
        update.entities = update.snapshot.entities;
        update.stats = update.snapshot.stats;
        update.poker_events = update.snapshot.poker_events;
        update.poker_leaderboard = update.snapshot.poker_leaderboard;
        update.auto_evaluation = update.snapshot.auto_evaluation;
    }

    // Preserve mode fields with defaults
    update.view_mode = update.view_mode ?? 'side';
    update.mode_id = update.mode_id ?? 'tank';

    return update;
}

describe('WebSocket Update Normalization', () => {
    it('should preserve mode_id and view_mode from server update', () => {
        const serverPayload = {
            type: 'update' as const,
            world_id: 'test-world',
            world_type: 'petri',
            view_mode: 'topdown',
            mode_id: 'petri',
            snapshot: {
                frame: 100,
                elapsed_time: 10.5,
                entities: [],
                stats: {} as any,
                poker_events: [],
                poker_leaderboard: [],
            },
        };

        const result = normalizeWorldUpdate(serverPayload);

        expect(result.view_mode).toBe('topdown');
        expect(result.mode_id).toBe('petri');
        expect(result.world_type).toBe('petri');
    });

    it('should default view_mode to "side" when missing', () => {
        const serverPayload = {
            type: 'update' as const,
            world_id: 'test-world',
            // view_mode is missing
            mode_id: 'tank',
            snapshot: {
                frame: 1,
                elapsed_time: 0,
                entities: [],
                stats: {} as any,
                poker_events: [],
                poker_leaderboard: [],
            },
        };

        const result = normalizeWorldUpdate(serverPayload);

        expect(result.view_mode).toBe('side');
    });

    it('should default mode_id to "tank" when missing', () => {
        const serverPayload = {
            type: 'update' as const,
            world_id: 'test-world',
            view_mode: 'side',
            // mode_id is missing
            snapshot: {
                frame: 1,
                elapsed_time: 0,
                entities: [],
                stats: {} as any,
                poker_events: [],
                poker_leaderboard: [],
            },
        };

        const result = normalizeWorldUpdate(serverPayload);

        expect(result.mode_id).toBe('tank');
    });

    it('should normalize nested snapshot fields to top level', () => {
        const serverPayload = {
            type: 'update' as const,
            world_id: 'test-world',
            snapshot: {
                frame: 42,
                elapsed_time: 3.14,
                entities: [{ id: 1, type: 'fish', x: 10, y: 20, width: 5, height: 5 }],
                stats: { frame: 42, population: 1 } as any,
                poker_events: [],
                poker_leaderboard: [],
            },
        };

        const result = normalizeWorldUpdate(serverPayload);

        expect(result.frame).toBe(42);
        expect(result.elapsed_time).toBe(3.14);
        expect(result.entities).toHaveLength(1);
        expect(result.entities![0].id).toBe(1);
    });

    it('should handle payloads without snapshot', () => {
        const legacyPayload = {
            type: 'update' as const,
            world_id: 'legacy-world',
            frame: 10,
            elapsed_time: 1.0,
            entities: [],
            stats: {} as any,
            // No snapshot, view_mode, or mode_id
        };

        const result = normalizeWorldUpdate(legacyPayload);

        // Should get defaults
        expect(result.view_mode).toBe('side');
        expect(result.mode_id).toBe('tank');
        // Original fields should be preserved
        expect(result.frame).toBe(10);
    });
});
