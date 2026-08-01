import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { PokerLeaders, SoccerLeaders } from './MinigameLeaders';
import { TankSoccerTab } from './tank_tabs/TankSoccerTab';
import type { PokerLeaderboardEntry, SoccerFishLeaderEntry } from '../types/simulation';

function pokerEntry(overrides: Partial<PokerLeaderboardEntry>): PokerLeaderboardEntry {
    return {
        rank: 1,
        fish_id: 1,
        generation: 1,
        algorithm: 'balanced',
        energy: 100,
        age: 100,
        total_games: 10,
        wins: 5,
        losses: 4,
        ties: 1,
        win_rate: 50,
        net_energy: 42,
        roi: 1.2,
        current_streak: 1,
        best_streak: 3,
        best_hand: 'Full House',
        best_hand_rank: 6,
        showdown_win_rate: 50,
        fold_rate: 10,
        positional_advantage: 0,
        recent_win_rate: 50,
        skill_trend: 'stable',
        tank_name: 'Tank Blue',
        tank_id: 'blue',
        offspring_count: 2,
        ...overrides,
    };
}

function soccerEntry(overrides: Partial<SoccerFishLeaderEntry>): SoccerFishLeaderEntry {
    return {
        fish_id: 1,
        matches: 4,
        wins: 3,
        draws: 0,
        losses: 1,
        goals: 5,
        assists: 2,
        net_energy: 31,
        tank_name: 'Tank Blue',
        tank_id: 'blue',
        offspring_count: 3,
        ...overrides,
    };
}

describe('PokerLeaders', () => {
    it('renders compact top-5 standings without repro credits', () => {
        const leaders = [1, 2, 3, 4, 5, 6].map((id) =>
            pokerEntry({ fish_id: id, wins: 10 - id, net_energy: 100 - id })
        );
        const html = renderToString(<PokerLeaders leaders={leaders} />);

        expect(html).toContain('Poker Leaders');
        expect(html).toContain('Fish #1');
        expect(html).toContain('Fish #5');
        expect(html).not.toContain('Fish #6'); // capped to top 5
        expect(html).toContain('Tank Blue');
        expect(html).toContain('9 wins');
        expect(html).toContain('+99⚡');
        expect(html).not.toContain('offspring');
        expect(html).not.toContain('repro credit');
        expect(html).not.toContain('LOSS');
    });

    it('shows an empty state without games', () => {
        const html = renderToString(<PokerLeaders leaders={[]} />);
        expect(html).toContain('No poker games yet');
    });
});

describe('SoccerLeaders', () => {
    it('renders goals, wins and energy per fish', () => {
        const html = renderToString(
            <SoccerLeaders leaders={[soccerEntry({ fish_id: 117, goals: 5, wins: 3, net_energy: 42, tank_name: 'Tank Blue' })]} />
        );

        expect(html).toContain('Season Leaders');
        expect(html).toContain('Fish #117');
        expect(html).toContain('Tank Blue');
        expect(html).toContain('5 goals');
        expect(html).toContain('3 wins');
        expect(html).toContain('+42 net energy');
        expect(html).not.toContain('offspring');
        expect(html).not.toContain('repro credit');
    });

    it('shows an empty state without matches', () => {
        const html = renderToString(<SoccerLeaders leaders={[]} />);
        expect(html).toContain('No soccer matches yet');
    });
});

describe('TankSoccerTab', () => {
    it('shows leaders instead of the old reward log and no repro text', () => {
        const html = renderToString(
            <TankSoccerTab
                liveState={{
                    leaderboard: [],
                    availability: {},
                    active_match: null,
                    fish_leaders: [soccerEntry({ fish_id: 9 })],
                }}
                events={[]}
                currentFrame={0}
            />
        );

        expect(html).toContain('Season Leaders');
        expect(html).toContain('Fish #9');

        expect(html).not.toContain('Reward Log');
        expect(html).not.toContain('repro credit');
        expect(html).not.toContain('Repro Delta');
    });
});
