import type { SoccerMatchEvent, SoccerMatchState } from '../types/simulation';
import { participantLabel } from './soccerParticipantLabels';

export type BroadcastEventKind =
    | 'kickoff'
    | 'goal'
    | 'shot'
    | 'save'
    | 'assist'
    | 'possession_change'
    | 'half_time'
    | 'full_time'
    | 'breakthrough';

export type BroadcastEvent = SoccerMatchEvent & { kind: BroadcastEventKind | string };

export type BroadcastTier = 'major' | 'notable' | 'ambient';

export interface SoccerBroadcastMatchFields {
    half?: 1 | 2;
    period_frames?: number;
    possession?: { left: number; right: number };
    ball_owner?: string | null;
    play_mode?: string;
}

export type SoccerBroadcastMatch = SoccerMatchState & SoccerBroadcastMatchFields;

export interface PresentedEvents {
    major: BroadcastEvent | null;
    notable: BroadcastEvent[];
    collapsedNotable: number;
}

export const MAJOR_EVENT_HOLD_FRAMES = 36;
export const NOTABLE_EVENT_HOLD_FRAMES = 18;
export const NOTABLE_RATE_LIMIT_FRAMES = 12;

export function eventKey(event: BroadcastEvent): string {
    return event.event_id ?? `seq:${event.seq}:frame:${event.frame}:kind:${event.kind}`;
}

export function eventTier(kind: string): BroadcastTier {
    if (kind === 'goal' || kind === 'breakthrough' || kind === 'full_time') return 'major';
    if (kind === 'kickoff' || kind === 'shot' || kind === 'save' || kind === 'half_time') return 'notable';
    return 'ambient';
}

export function dedupeEvents(events: readonly BroadcastEvent[]): BroadcastEvent[] {
    const byKey = new Map<string, BroadcastEvent>();
    for (const event of events) {
        const key = eventKey(event);
        if (!byKey.has(key)) byKey.set(key, event);
    }
    return [...byKey.values()].sort((left, right) => left.seq - right.seq || left.frame - right.frame);
}

function ageOf(event: BroadcastEvent, currentFrame: number): number {
    return currentFrame - event.frame;
}

function isVisible(event: BroadcastEvent, currentFrame: number, holdFrames: number): boolean {
    const age = ageOf(event, currentFrame);
    return age >= 0 && age <= holdFrames;
}

export function presentEvents(events: readonly BroadcastEvent[], currentFrame: number): PresentedEvents {
    const ordered = dedupeEvents(events);
    const major = ordered
        .filter((event) => (eventTier(event.kind) === 'major' || event.kind === 'half_time') && isVisible(event, currentFrame, MAJOR_EVENT_HOLD_FRAMES))
        .at(-1) ?? null;

    if (major) return { major, notable: [], collapsedNotable: 0 };

    const notableCandidates = ordered
        .filter((event) => eventTier(event.kind) === 'notable' && isVisible(event, currentFrame, NOTABLE_EVENT_HOLD_FRAMES))
        .reverse();
    const notable: BroadcastEvent[] = [];
    let collapsedNotable = 0;
    for (const event of notableCandidates) {
        const tooSoon = notable.some((accepted) => Math.abs(accepted.frame - event.frame) < NOTABLE_RATE_LIMIT_FRAMES);
        if (tooSoon || notable.length >= 2) {
            collapsedNotable += 1;
        } else {
            notable.push(event);
        }
    }
    return { major: null, notable, collapsedNotable };
}

/**
 * Whether a match event currently owns the major broadcast slot.
 *
 * The arena holds a breakthrough card back while this is true, so a goal or
 * full-time card is never covered by one.
 */
export function hasMajorMatchEvent(match: SoccerMatchState | null): boolean {
    if (!match) return false;
    const current = match as SoccerBroadcastMatch;
    return presentEvents((current.events ?? []) as BroadcastEvent[], current.frame).major !== null;
}

export function activeEffectEvent(match: SoccerBroadcastMatch | null): BroadcastEvent | null {
    if (!match?.events?.length) return null;
    const currentFrame = match.frame;
    return dedupeEvents(match.events as BroadcastEvent[])
        .filter((event) => eventTier(event.kind) !== 'ambient' && ageOf(event, currentFrame) >= 0 && ageOf(event, currentFrame) <= 4)
        .at(-1) ?? null;
}

/**
 * The name to announce for an event's actor.
 *
 * Delegates to `participantLabel` so every surface that names a player - goal
 * cards, toasts, the timeline - shares one rule. It used to reach for
 * `fish_id` directly, which named a bot after its synthetic 19-digit hash.
 */
export function participantName(match: SoccerBroadcastMatch, participantId?: string): string | null {
    if (!participantId) return null;
    const participant = match.participants?.find((item) => item.participant_id === participantId);
    if (!participant) return participantId;
    return participantLabel(participant);
}

export function teamName(match: SoccerBroadcastMatch, side?: 'left' | 'right'): string {
    if (side === 'left') return match.home_name || match.home_id || 'Home';
    if (side === 'right') return match.away_name || match.away_id || 'Away';
    return 'Arena';
}

export function eventLabel(event: BroadcastEvent): string {
    const labels: Record<string, string> = {
        kickoff: 'KICK OFF',
        shot: 'SHOT ON TARGET',
        save: 'SAVE',
        half_time: 'HALF TIME',
        full_time: 'FULL TIME',
        breakthrough: 'BREAKTHROUGH',
        possession_change: 'POSSESSION',
        assist: 'ASSIST',
        goal: 'GOAL',
    };
    return labels[event.kind] ?? event.kind.replaceAll('_', ' ').toUpperCase();
}
