import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { LineupPanel } from './LineupPanel';
import { PlayerCard } from './PlayerCard';
import { lineageLabel, participantLabel, sideDisplayName } from './soccerParticipantLabels';
import type { SoccerMatchState, SoccerParticipant } from '../types/simulation';

function participant(overrides: Partial<SoccerParticipant> & Pick<SoccerParticipant, 'participant_id' | 'side' | 'uniform_number'>): SoccerParticipant {
    return {
        team_id: overrides.side,
        avatar_kind: 'fish',
        ...overrides,
    };
}

function match(participants: SoccerParticipant[], overrides: Partial<SoccerMatchState> = {}): SoccerMatchState {
    return {
        match_id: 'match-1',
        game_over: false,
        winner_team: null,
        message: 'live',
        frame: 30,
        score: { left: 0, right: 0 },
        entities: [],
        participants,
        home_name: 'World 1A',
        away_name: 'Reef Delta',
        ...overrides,
    };
}

const squad = [
    participant({ participant_id: 'left_1', side: 'left', uniform_number: 1, fish_id: 284, generation: 41, parent_id: 91 }),
    participant({ participant_id: 'left_2', side: 'left', uniform_number: 2, fish_id: 91, generation: 39 }),
    participant({ participant_id: 'right_1', side: 'right', uniform_number: 1, avatar_kind: 'reference', policy_label: 'Chase & Shoot' }),
];

describe('participant labels', () => {
    it('prefers a display name, then a policy label, then the fish id', () => {
        expect(participantLabel(participant({ participant_id: 'left_1', side: 'left', uniform_number: 1, display_name: 'Nemo' }))).toBe('Nemo');
        expect(participantLabel(squad[2])).toBe('Chase & Shoot');
        expect(participantLabel(squad[0])).toBe('Fish #284');
        expect(participantLabel(participant({ participant_id: 'left_9', side: 'left', uniform_number: 9 }))).toBe('Left #9');
    });

    it('does not name a bot after a synthetic fish id', () => {
        // The live league hands bot participants ids like 4882397523792860000;
        // "Fish #4882397523792860000" overflows the row and claims a lineage
        // the participant does not have.
        const bot = participant({
            participant_id: 'right_2',
            side: 'right',
            uniform_number: 2,
            avatar_kind: 'bot',
            fish_id: 4882397523792860000,
        });
        expect(participantLabel(bot)).toBe('Right #2');
    });

    it('names an external RCSS participant by its side and number', () => {
        const external = participant({ participant_id: 'left_7', side: 'left', uniform_number: 7, avatar_kind: 'external' });
        expect(participantLabel(external)).toBe('Left #7');
    });

    it('reads a fish with no recorded parent as a founder, not as missing data', () => {
        expect(lineageLabel(squad[0])).toBe('Gen 41 · ↑#91');
        expect(lineageLabel(squad[1])).toBe('Gen 39 · founder');
    });

    it('does not claim lineage for a frozen reference policy', () => {
        expect(lineageLabel(squad[2])).toBeNull();
    });

    it('resolves home and away as labels over the left/right render sides', () => {
        expect(sideDisplayName(match(squad), 'left')).toBe('World 1A');
        expect(sideDisplayName(match(squad), 'right')).toBe('Reef Delta');
    });

    it('follows the teams across a half swap', () => {
        const swapped = match(squad, { sides_swapped: true });
        expect(sideDisplayName(swapped, 'left')).toBe('Reef Delta');
        expect(sideDisplayName(swapped, 'right')).toBe('World 1A');
    });

    it('infers the swap from the half for payloads predating sides_swapped', () => {
        const secondHalf = match(squad, { half: 2 });
        expect(sideDisplayName(secondHalf, 'left')).toBe('Reef Delta');
    });
});

describe('LineupPanel', () => {
    const render = (selectedParticipantId: string | null, roles = {}) =>
        renderToString(
            <LineupPanel
                match={match(squad)}
                roles={roles}
                selectedParticipantId={selectedParticipantId}
                onSelect={() => undefined}
            />,
        );

    it('lists every participant on the wire, keyed on participant_id', () => {
        const html = render(null);
        expect(html).toContain('data-testid="lineup-row-left_1"');
        expect(html).toContain('data-testid="lineup-row-left_2"');
        expect(html).toContain('data-testid="lineup-row-right_1"');
        // React SSR inserts a `<!-- -->` marker between adjacent expressions,
        // so the count and its unit cannot be matched as one string.
        expect(html).toMatch(/3<!-- --> players/);
    });

    it('marks the selected row, and only that row', () => {
        const html = render('left_2');
        const pressed = [...html.matchAll(/data-testid="lineup-row-(\w+)"/g)];
        expect(pressed).toHaveLength(3);
        // aria-pressed precedes data-testid on the same element.
        expect(html).toMatch(/aria-pressed="true"[^>]*data-testid="lineup-row-left_2"/);
        expect(html).not.toMatch(/aria-pressed="true"[^>]*data-testid="lineup-row-left_1"/);
    });

    it('tags a reference participant as frozen instead of giving it a derived role', () => {
        const html = render(null, { right_1: 'F', left_1: 'D' });
        expect(html).toContain('FROZEN');
        // The reference row shows the frozen tag in place of a role glyph.
        expect(html).not.toMatch(/right_1"[\s\S]*?_role_[\s\S]*?<\/button>/);
        expect(html).toMatch(/Avg generation <!-- -->40\.0/);
    });

    it('says so plainly when no squad is on the pitch', () => {
        const html = renderToString(
            <LineupPanel match={null} roles={{}} selectedParticipantId={null} onSelect={() => undefined} />,
        );
        expect(html).toContain('No squad is on the pitch yet');
    });
});

describe('PlayerCard', () => {
    it('omits a field the wire did not carry rather than showing it empty', () => {
        const html = renderToString(<PlayerCard participant={squad[1]} role="M" meanX={-12.34} />);
        expect(html).toContain('Fish #91');
        expect(html).toContain('Middle third');
        expect(html).toContain('-12.3 m');
        // Exactly the rows the fixture can support - nothing rendered blank.
        const keys = [...html.matchAll(/_cardKey_\w+">([^<]+)</g)].map((entry) => entry[1]);
        expect(keys).toEqual(['Kind', 'Lineage', 'Fish id', 'Role', 'Mean x']);
    });

    it('drops rows whose data the participant lacks', () => {
        const html = renderToString(<PlayerCard participant={squad[2]} />);
        const keys = [...html.matchAll(/_cardKey_\w+">([^<]+)</g)].map((entry) => entry[1]);
        expect(keys).toEqual(['Kind']);
    });

    it('does not show a bot its synthetic fish id', () => {
        const bot = participant({
            participant_id: 'right_2',
            side: 'right',
            uniform_number: 2,
            avatar_kind: 'bot',
            fish_id: 4882397523792860000,
        });
        const html = renderToString(<PlayerCard participant={bot} />);
        expect(html).not.toContain('4882397523792860000');
        expect([...html.matchAll(/_cardKey_\w+">([^<]+)</g)].map((entry) => entry[1])).toEqual(['Kind']);
    });

    it('names the participant kind for a non-fish player', () => {
        const html = renderToString(<PlayerCard participant={squad[2]} />);
        expect(html).toContain('Frozen reference');
    });
});
