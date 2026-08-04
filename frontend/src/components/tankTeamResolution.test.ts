import { describe, expect, it } from 'vitest';
import type { LeagueLeaderboardEntry, SoccerLeagueLiveState, SoccerMatchState } from '../types/simulation';
import { filterLeadersForWorld, resolveWorldTeam, teamWorldId } from './tankTeamResolution';

function team(team_id: string, display_name: string, world_id?: string): LeagueLeaderboardEntry {
    return {
        team_id,
        display_name,
        source: world_id ? 'tank' : 'bot',
        world_id,
        matches_played: 4,
        wins: 2,
        draws: 1,
        losses: 1,
        gf: 6,
        ga: 4,
        points: 7,
        rating: 1200,
    };
}

/** Two tank worlds plus a bot team, all sharing one leaderboard. */
const LEADERBOARD = [
    team('world-b:A', 'World B A Team', 'world-b'),
    team('world-a:A', 'World A A Team', 'world-a'),
    team('world-a:B', 'World A B Team', 'world-a'),
    team('world-b:B', 'World B B Team', 'world-b'),
    team('Bot:Balanced', 'Bot Balanced'),
];

function liveState(overrides: Partial<SoccerLeagueLiveState> = {}): SoccerLeagueLiveState {
    return {
        leaderboard: LEADERBOARD,
        availability: {},
        active_match: null,
        team_positions: { 'world-a:A': 2, 'world-b:A': 1 },
        ...overrides,
    } as SoccerLeagueLiveState;
}

function shownMatch(home: string, away: string): SoccerMatchState {
    return {
        match_id: 'm-1',
        game_over: false,
        winner_team: null,
        message: '',
        frame: 10,
        score: { left: 0, right: 0 },
        entities: [],
        home_id: home,
        away_id: away,
    };
}

describe('resolveWorldTeam', () => {
    it('gives each arena its own world team, never a neighbour tank', () => {
        expect(resolveWorldTeam(liveState(), 'world-a').teamId).toBe('world-a:A');
        expect(resolveWorldTeam(liveState(), 'world-b').teamId).toBe('world-b:A');
        expect(resolveWorldTeam(liveState(), 'world-a').displayName).toBe('World A A Team');
        expect(resolveWorldTeam(liveState(), 'world-b').displayName).toBe('World B A Team');
    });

    it('defaults to the A team and labels the squad', () => {
        const resolved = resolveWorldTeam(liveState(), 'world-a');
        expect(resolved.squad).toBe('A');
        expect(resolved.fielded).toBe(true);
    });

    it('selects the B team when it is the one actually playing', () => {
        const resolved = resolveWorldTeam(
            liveState({ active_match: shownMatch('world-a:B', 'Bot:Balanced') }),
            'world-a',
        );
        expect(resolved.teamId).toBe('world-a:B');
        expect(resolved.squad).toBe('B');
    });

    it('follows a retained full-time snapshot when no match is live', () => {
        const resolved = resolveWorldTeam(
            liveState({ active_match: null, presentation_match: shownMatch('Bot:Balanced', 'world-a:B') }),
            'world-a',
        );
        expect(resolved.teamId).toBe('world-a:B');
    });

    it('falls back to the A team when the shown match involves other worlds', () => {
        const resolved = resolveWorldTeam(
            liveState({ active_match: shownMatch('world-b:A', 'Bot:Balanced') }),
            'world-a',
        );
        expect(resolved.teamId).toBe('world-a:A');
    });

    it('reports not fielded rather than falling back to a different tank', () => {
        const resolved = resolveWorldTeam(liveState(), 'world-c');
        expect(resolved).toEqual({ teamId: null, displayName: null, squad: null, fielded: false });
    });

    it('never attributes a bot team to a world', () => {
        const botsOnly = liveState({ leaderboard: [team('Bot:Balanced', 'Bot Balanced')] });
        expect(resolveWorldTeam(botsOnly, 'world-a').fielded).toBe(false);
    });

    it('resolves through the team_world_ids mapping when entries lack world_id', () => {
        const legacy = liveState({
            leaderboard: [
                { ...team('world-a:A', 'World A A Team', 'world-a'), world_id: undefined },
                { ...team('world-b:A', 'World B A Team', 'world-b'), world_id: undefined },
            ],
            team_world_ids: { 'world-a:A': 'world-a', 'world-b:A': 'world-b' },
        } as Partial<SoccerLeagueLiveState>);
        expect(resolveWorldTeam(legacy, 'world-a').teamId).toBe('world-a:A');
        expect(resolveWorldTeam(legacy, 'world-b').teamId).toBe('world-b:A');
    });

    it('shows nothing rather than guessing when the mapping is missing entirely', () => {
        const unmapped = liveState({
            leaderboard: [{ ...team('world-a:A', 'World A A Team', 'world-a'), world_id: undefined }],
        } as Partial<SoccerLeagueLiveState>);
        expect(resolveWorldTeam(unmapped, 'world-a').fielded).toBe(false);
    });

    it('returns not fielded without a world id or live state', () => {
        expect(resolveWorldTeam(liveState(), undefined).fielded).toBe(false);
        expect(resolveWorldTeam(null, 'world-a').fielded).toBe(false);
    });
});

describe('teamWorldId', () => {
    it('prefers the entry field, then the mapping, then nothing', () => {
        expect(teamWorldId({ team_id: 'x:A', world_id: 'w1' })).toBe('w1');
        expect(teamWorldId({ team_id: 'x:A' }, { 'x:A': 'w2' })).toBe('w2');
        expect(teamWorldId({ team_id: 'x:A' })).toBeNull();
    });
});

describe('filterLeadersForWorld', () => {
    const leaders = [
        { fish_id: 1, tank_id: 'world-a', matches: 2, wins: 1, draws: 0, losses: 1, goals: 3, assists: 1, net_energy: 5 },
        { fish_id: 2, tank_id: 'world-b', matches: 2, wins: 2, draws: 0, losses: 0, goals: 9, assists: 0, net_energy: 8 },
    ];

    it('keeps only this world performers when identity is present', () => {
        expect(filterLeadersForWorld(leaders, 'world-a').map((l) => l.fish_id)).toEqual([1]);
        expect(filterLeadersForWorld(leaders, 'world-b').map((l) => l.fish_id)).toEqual([2]);
    });

    it('degrades to unfiltered rather than empty when the payload lacks tank ids', () => {
        const thin = [{ fish_id: 3, matches: 1, wins: 1, draws: 0, losses: 0, goals: 1, assists: 0, net_energy: 1 }];
        expect(filterLeadersForWorld(thin, 'world-a')).toHaveLength(1);
    });

    it('returns everything when no world is given', () => {
        expect(filterLeadersForWorld(leaders, undefined)).toHaveLength(2);
        expect(filterLeadersForWorld(undefined, 'world-a')).toHaveLength(0);
    });
});
