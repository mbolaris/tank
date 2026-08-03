import { describe, expect, it } from 'vitest';
import { deriveArenaState, humanizeSkipReason, resolvePlayMode, type SoccerMatchPresentationFields } from './soccerArenaState';
import type { SoccerMatchState } from '../types/simulation';

const match = (overrides: Partial<SoccerMatchState & SoccerMatchPresentationFields> = {}): SoccerMatchState => ({
    match_id: 'm1',
    game_over: false,
    winner_team: null,
    message: '',
    frame: 0,
    score: { left: 0, right: 0 },
    entities: [],
    ...overrides,
});

describe('soccerArenaState', () => {
    it.each([
        ['empty', { liveState: null }],
        ['loading', { liveState: null, connectionState: 'loading' as const }],
        ['disconnected', { liveState: null, connectionState: 'disconnected' as const }],
        ['error', { liveState: null, errorMessage: 'boom' }],
    ] as const)('resolves the %s state honestly', (expected, input) => {
        expect(deriveArenaState(input).presentation).toBe(expected);
    });

    it('humanizes skipped reasons without exposing a raw enum as the whole message', () => {
        expect(humanizeSkipReason('insufficient_eligible_fish')).toContain('not enough eligible fish');
        expect(humanizeSkipReason('insufficient_eligible_fish')).not.toBe('insufficient_eligible_fish');
    });

    it('holds the last presentation for an unknown play mode', () => {
        const result = resolvePlayMode('new_server_mode', 'paused');
        expect(result.presentation).toBe('paused');
        expect(result.unknownStage).toBe('UNKNOWN: new_server_mode');
        expect(result.unknownStage).not.toContain('play_on');
    });

    it('does not invent a finished state from a live play mode', () => {
        expect(deriveArenaState({ liveState: { leaderboard: [], availability: {}, active_match: match({ play_mode: 'play_on' }) } }).presentation).toBe('live');
    });
});
