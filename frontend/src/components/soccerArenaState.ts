import type { SoccerLeagueLiveState, SoccerMatchState } from '../types/simulation';

export interface SoccerMatchPresentationFields {
    play_mode?: string;
    paused?: boolean;
    skip_reason?: string;
}

export type SoccerPresentationMatch = SoccerMatchState & SoccerMatchPresentationFields;
type SoccerLeaguePresentationState = SoccerLeagueLiveState & { skip_reason?: string };

export type ArenaPresentation = 'empty' | 'loading' | 'live' | 'paused' | 'halftime' | 'finished' | 'disconnected' | 'skipped' | 'error';
export type ArenaConnectionState = 'connected' | 'loading' | 'disconnected' | 'error';

export interface ArenaStateInput {
    liveState: SoccerLeagueLiveState | null;
    connectionState?: ArenaConnectionState;
    errorMessage?: string | null;
    previousPresentation?: ArenaPresentation;
    lastArrivalMs?: number;
    nowMs?: number;
}

export interface ArenaViewState {
    presentation: ArenaPresentation;
    match: SoccerMatchState | null;
    unknownStage?: string;
    skippedReason?: string;
    errorMessage?: string;
    staleLabel?: string;
}

const KNOWN_PLAY_MODES: Record<string, ArenaPresentation> = {
    before_kick_off: 'loading',
    kick_off_left: 'live',
    kick_off_right: 'live',
    play_on: 'live',
    goal_kick: 'live',
    free_kick: 'live',
    corner_kick: 'live',
    kick_in: 'live',
    half_time: 'halftime',
    halftime: 'halftime',
    time_over: 'finished',
    game_over: 'finished',
    paused: 'paused',
};

/** The websocket statuses TankView exposes. */
export type WebSocketConnectionStatus = 'connecting' | 'live' | 'reconnecting';

export interface ConnectionMappingInput {
    connectionStatus: WebSocketConnectionStatus | string;
    schemaError?: string | null;
    /** Whether any usable payload has been received yet. */
    hasState?: boolean;
}

/**
 * Map the real websocket state onto an arena presentation state.
 *
 * The arena used to default to 'connected', so a reconnecting socket kept
 * rendering its last frame as though it were live. Every branch is explicit
 * here precisely so stale data can never be presented as live.
 */
export function arenaStateFromConnection(input: ConnectionMappingInput): ArenaConnectionState {
    // A schema error means the payload itself cannot be trusted; it outranks
    // whatever the socket thinks, and is never shown as a normal live match.
    if (input.schemaError) return 'error';
    if (input.connectionStatus === 'live') return 'connected';
    // Reconnecting with a prior payload holds the last frame, labelled stale.
    // Reconnecting with nothing to hold is still just waiting.
    if (input.connectionStatus === 'reconnecting') return input.hasState ? 'disconnected' : 'loading';
    if (input.connectionStatus === 'connecting') return 'loading';
    return input.hasState ? 'disconnected' : 'loading';
}

export function humanizeSkipReason(reason: string | undefined): string {
    if (!reason) return 'The scheduled match was skipped before kickoff.';
    const normalized = reason.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    if (normalized.includes('fish')) return `The match was skipped because there were not enough eligible fish (${normalized}).`;
    if (normalized.includes('eligible') || normalized.includes('participant') || normalized.includes('roster')) {
        return `The match was skipped because the roster was not eligible (${normalized}).`;
    }
    return `The match was skipped: ${normalized}.`;
}

/**
 * "Reconnecting… last update 14s ago".
 *
 * Both times are browser monotonic and presentation-only. Without a recorded
 * arrival there is no honest age to quote, so the label says so rather than
 * inventing 0s.
 */
export function formatStaleLabel(lastArrivalMs?: number, nowMs?: number): string {
    if (lastArrivalMs === undefined) return 'Reconnecting… last update unknown';
    const elapsedMs = (nowMs ?? performance.now()) - lastArrivalMs;
    const seconds = Math.max(0, Math.floor(elapsedMs / 1000));
    return `Reconnecting… last update ${seconds}s ago`;
}

export function resolvePlayMode(
    playMode: string | undefined,
    previousPresentation: ArenaPresentation = 'live',
): { presentation: ArenaPresentation; unknownStage?: string } {
    if (!playMode) return { presentation: previousPresentation };
    const known = KNOWN_PLAY_MODES[playMode.toLowerCase()];
    if (known) return { presentation: known };
    return {
        presentation: previousPresentation === 'empty' || previousPresentation === 'error' ? 'loading' : previousPresentation,
        unknownStage: `UNKNOWN: ${playMode}`,
    };
}

export function deriveArenaState(input: ArenaStateInput): ArenaViewState {
    const connectionState = input.connectionState ?? 'connected';
    const isPresentationSnapshot = !input.liveState?.active_match && Boolean(input.liveState?.presentation_match);
    const match = input.liveState?.active_match ?? input.liveState?.presentation_match ?? null;
    const presentationMatch = match as SoccerPresentationMatch | null;
    const presentationLeague = input.liveState as SoccerLeaguePresentationState | null;

    if (connectionState === 'error' || input.errorMessage) {
        return { presentation: 'error', match: null, errorMessage: input.errorMessage ?? 'The arena could not load this match.' };
    }
    if (connectionState === 'disconnected') {
        const staleLabel = formatStaleLabel(input.lastArrivalMs, input.nowMs);
        if (!match) {
            return { presentation: 'disconnected', match: null, staleLabel };
        }
        return { presentation: 'disconnected', match, staleLabel };
    }
    if (connectionState === 'loading' && !match) {
        return { presentation: 'loading', match: null };
    }
    if (presentationLeague?.skip_reason && !match) {
        return { presentation: 'skipped', match: null, skippedReason: humanizeSkipReason(presentationLeague.skip_reason) };
    }
    if (!match) {
        return { presentation: connectionState === 'loading' ? 'loading' : 'empty', match: null };
    }
    if (presentationMatch?.skip_reason) {
        return { presentation: 'skipped', match: null, skippedReason: humanizeSkipReason(presentationMatch.skip_reason) };
    }

    if (isPresentationSnapshot || match.game_over || presentationMatch?.play_mode === 'time_over' || presentationMatch?.play_mode === 'game_over') {
        return { presentation: 'finished', match };
    }
    if (presentationMatch?.paused) return { presentation: 'paused', match };
    const mode = resolvePlayMode(presentationMatch?.play_mode, input.previousPresentation ?? 'live');
    return { ...mode, match };
}
