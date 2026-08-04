import { describe, expect, it } from 'vitest';
import {
    arenaStateFromConnection,
    deriveArenaState,
    formatStaleLabel,
    humanizeSkipReason,
    resolvePlayMode,
    type SoccerMatchPresentationFields,
} from './soccerArenaState';
import type { SoccerLeagueLiveState, SoccerMatchState } from '../types/simulation';

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

const live = (overrides: Partial<SoccerLeagueLiveState> = {}): SoccerLeagueLiveState => ({
    leaderboard: [],
    availability: {},
    active_match: null,
    ...overrides,
});

describe('arenaStateFromConnection', () => {
    it('maps a connecting socket with no usable state to loading', () => {
        expect(arenaStateFromConnection({ connectionStatus: 'connecting', hasState: false })).toBe('loading');
        expect(arenaStateFromConnection({ connectionStatus: 'connecting', hasState: true })).toBe('loading');
    });

    it('maps a live socket to connected', () => {
        expect(arenaStateFromConnection({ connectionStatus: 'live', hasState: true })).toBe('connected');
    });

    it('maps reconnecting with a prior payload to disconnected', () => {
        expect(arenaStateFromConnection({ connectionStatus: 'reconnecting', hasState: true })).toBe('disconnected');
    });

    it('maps reconnecting with nothing to hold to loading', () => {
        expect(arenaStateFromConnection({ connectionStatus: 'reconnecting', hasState: false })).toBe('loading');
    });

    it('maps a schema error to error regardless of socket health', () => {
        expect(arenaStateFromConnection({ connectionStatus: 'live', schemaError: 'bad payload', hasState: true })).toBe('error');
        expect(arenaStateFromConnection({ connectionStatus: 'reconnecting', schemaError: 'bad payload', hasState: true })).toBe('error');
    });
});

describe('disconnected presentation', () => {
    const liveMatch = live({ active_match: match({ play_mode: 'play_on', frame: 400 }) });

    it('holds the last frame but labels it stale', () => {
        const state = deriveArenaState({
            liveState: liveMatch,
            connectionState: 'disconnected',
            lastArrivalMs: 1_000,
            nowMs: 15_000,
        });
        expect(state.presentation).toBe('disconnected');
        // Nothing is cleared - the stale frame stays visible.
        expect(state.match?.frame).toBe(400);
        expect(state.staleLabel).toBe('Reconnecting… last update 14s ago');
    });

    it('never presents a stale frame as live', () => {
        const state = deriveArenaState({ liveState: liveMatch, connectionState: 'disconnected' });
        expect(state.presentation).not.toBe('live');
    });

    it('clears the disconnected treatment once state is live again', () => {
        const reconnected = deriveArenaState({ liveState: liveMatch, connectionState: 'connected' });
        expect(reconnected.presentation).toBe('live');
        expect(reconnected.staleLabel).toBeUndefined();
    });

    it('shows a schema error rather than a normal live match', () => {
        const state = deriveArenaState({ liveState: liveMatch, connectionState: 'error', errorMessage: 'schema drift' });
        expect(state.presentation).toBe('error');
        expect(state.match).toBeNull();
        expect(state.errorMessage).toBe('schema drift');
    });
});

describe('formatStaleLabel', () => {
    it('counts whole seconds since the last usable payload', () => {
        expect(formatStaleLabel(1_000, 1_000)).toBe('Reconnecting… last update 0s ago');
        expect(formatStaleLabel(1_000, 15_400)).toBe('Reconnecting… last update 14s ago');
    });

    it('never reports a negative age', () => {
        expect(formatStaleLabel(5_000, 1_000)).toBe('Reconnecting… last update 0s ago');
    });

    it('says so honestly when no arrival was ever recorded', () => {
        expect(formatStaleLabel(undefined, 1_000)).toBe('Reconnecting… last update unknown');
    });
});

describe('presentation_match', () => {
    const finished = match({ game_over: true, play_mode: 'time_over', frame: 600, score: { left: 2, right: 1 } });

    it('is shown as finished when no match is active', () => {
        const state = deriveArenaState({ liveState: live({ active_match: null, presentation_match: finished }) });
        expect(state.presentation).toBe('finished');
        expect(state.match?.score).toEqual({ left: 2, right: 1 });
    });

    it('yields to a genuinely active match', () => {
        const running = match({ play_mode: 'play_on', frame: 12 });
        const state = deriveArenaState({ liveState: live({ active_match: running, presentation_match: finished }) });
        expect(state.presentation).toBe('live');
        expect(state.match?.frame).toBe(12);
    });

    it('falls back to empty once the snapshot expires', () => {
        expect(deriveArenaState({ liveState: live({ active_match: null, presentation_match: null }) }).presentation).toBe('empty');
    });

    it('is still held and labelled stale while disconnected', () => {
        const state = deriveArenaState({
            liveState: live({ presentation_match: finished }),
            connectionState: 'disconnected',
            lastArrivalMs: 0,
            nowMs: 3_000,
        });
        expect(state.presentation).toBe('disconnected');
        expect(state.match?.game_over).toBe(true);
    });
});
