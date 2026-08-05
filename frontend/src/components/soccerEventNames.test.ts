import { describe, expect, it } from 'vitest';

import { participantName, type SoccerBroadcastMatch } from './soccerEvents';
import type { SoccerParticipant } from '../types/simulation';

/**
 * Every surface that names an event's actor - goal cards, toasts, the
 * timeline - goes through `participantName`, so the rule for what a player is
 * called has to live there rather than in each caller.
 */

function participant(overrides: Partial<SoccerParticipant> & Pick<SoccerParticipant, 'participant_id' | 'side' | 'uniform_number' | 'avatar_kind'>): SoccerParticipant {
    return { team_id: overrides.side, ...overrides };
}

function match(participants: SoccerParticipant[]): SoccerBroadcastMatch {
    return {
        match_id: 'm1',
        game_over: false,
        winner_team: null,
        message: 'live',
        frame: 10,
        score: { left: 0, right: 0 },
        entities: [],
        participants,
    } as SoccerBroadcastMatch;
}

describe('participantName', () => {
    it('names a tank fish by its fish id', () => {
        const state = match([participant({ participant_id: 'left_1', side: 'left', uniform_number: 1, avatar_kind: 'fish', fish_id: 284 })]);
        expect(participantName(state, 'left_1')).toBe('Fish #284');
    });

    it('does not name a bot after its synthetic fish id', () => {
        // `BotEntity.fish_id = abs(hash(bot_id))`. In Tactical and Analysis the
        // timeline is the only event surface, so a bot goal announced this way
        // would be the whole story the viewer gets.
        const state = match([
            participant({
                participant_id: 'right_2',
                side: 'right',
                uniform_number: 2,
                avatar_kind: 'bot',
                fish_id: 4882397523792860000,
            }),
        ]);
        expect(participantName(state, 'right_2')).toBe('Right #2');
    });

    it('names an external RCSS participant by side and number', () => {
        const state = match([participant({ participant_id: 'left_7', side: 'left', uniform_number: 7, avatar_kind: 'external' })]);
        expect(participantName(state, 'left_7')).toBe('Left #7');
    });

    it('prefers a policy label for a frozen reference', () => {
        const state = match([participant({ participant_id: 'right_1', side: 'right', uniform_number: 1, avatar_kind: 'reference', policy_label: 'Chase & Shoot' })]);
        expect(participantName(state, 'right_1')).toBe('Chase & Shoot');
    });

    it('falls back to the raw id for an actor missing from the roster', () => {
        expect(participantName(match([]), 'ghost_9')).toBe('ghost_9');
    });

    it('is null when there is no actor at all', () => {
        expect(participantName(match([]), undefined)).toBeNull();
    });
});
