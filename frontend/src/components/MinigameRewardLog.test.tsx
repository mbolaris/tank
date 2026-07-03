import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { PokerRewardLog, SoccerRewardLog } from './MinigameRewardLog';
import type { PokerEventData, SoccerEventData } from '../types/simulation';

const soccerEvent: SoccerEventData = {
    frame: 100,
    match_id: 'm1',
    match_counter: 1,
    winner_team: 'left',
    score_left: 2,
    score_right: 1,
    frames: 1800,
    energy_deltas: { '7': 6.5, '9': -5.0 },
    repro_credit_deltas: { '7': 2.0 },
    teams: { left: [7], right: [9] },
};

const pokerEvent: PokerEventData = {
    frame: 200,
    winner_id: 12,
    loser_id: 4,
    winner_hand: 'Full House',
    loser_hand: 'Pair',
    energy_transferred: 8.0,
    message: 'Fish #12 beats Fish #4 with Full House! (+8.0 energy)',
    energy_deltas: { '12': 8.0, '4': -8.0 },
    repro_credit_deltas: { '12': 2.0 },
    pot: 16.0,
    house_cut: 1.5,
    reproduction: { parent_id: 12, baby_id: 33 },
};

describe('SoccerRewardLog', () => {
    it('lists per-fish energy and repro credit rewards for a match', () => {
        const html = renderToString(<SoccerRewardLog events={[soccerEvent]} currentFrame={160} />);

        expect(html).toContain('Fish #7');
        expect(html).toContain('+6.5⚡');
        expect(html).toContain('repro credits');
        expect(html).toContain('Fish #9');
        expect(html).toContain('-5.0⚡');
        expect(html).toContain('Left win 2-1');
    });

    it('shows an empty state without events', () => {
        const html = renderToString(<SoccerRewardLog events={[]} currentFrame={0} />);
        expect(html).toContain('No match rewards yet');
    });
});

describe('PokerRewardLog', () => {
    it('lists per-fish rewards including reproduction earned', () => {
        const html = renderToString(<PokerRewardLog events={[pokerEvent]} currentFrame={230} />);

        expect(html).toContain('Fish #12');
        expect(html).toContain('+8.0⚡');
        expect(html).toContain('repro credits');
        expect(html).toContain('baby #33');
        expect(html).toContain('Fish #4');
        expect(html).toContain('-8.0⚡');
    });

    it('skips events that carry no per-fish reward detail', () => {
        const legacyEvent: PokerEventData = {
            frame: 10,
            winner_id: 1,
            loser_id: 2,
            winner_hand: 'Pair',
            loser_hand: 'High Card',
            energy_transferred: 3.0,
            message: 'Fish #1 beats Fish #2',
        };
        const html = renderToString(<PokerRewardLog events={[legacyEvent]} currentFrame={20} />);
        expect(html).toContain('No table rewards yet');
    });
});
