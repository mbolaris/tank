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

export function humanizeSkipReason(reason: string | undefined): string {
    if (!reason) return 'The scheduled match was skipped before kickoff.';
    const normalized = reason.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    if (normalized.includes('fish')) return `The match was skipped because there were not enough eligible fish (${normalized}).`;
    if (normalized.includes('eligible') || normalized.includes('participant') || normalized.includes('roster')) {
        return `The match was skipped because the roster was not eligible (${normalized}).`;
    }
    return `The match was skipped: ${normalized}.`;
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
    const match = input.liveState?.active_match ?? null;
    const presentationMatch = match as SoccerPresentationMatch | null;
    const presentationLeague = input.liveState as SoccerLeaguePresentationState | null;

    if (connectionState === 'error' || input.errorMessage) {
        return { presentation: 'error', match: null, errorMessage: input.errorMessage ?? 'The arena could not load this match.' };
    }
    if (connectionState === 'disconnected') {
        return { presentation: 'disconnected', match, staleLabel: 'Last update is stale · reconnecting' };
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

    if (match.game_over) return { presentation: 'finished', match };
    if (presentationMatch?.paused) return { presentation: 'paused', match };
    const mode = resolvePlayMode(presentationMatch?.play_mode, input.previousPresentation ?? 'live');
    return { ...mode, match };
}
