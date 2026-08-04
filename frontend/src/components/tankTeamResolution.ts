import type { LeagueLeaderboardEntry, SoccerFishLeaderEntry, SoccerLeagueLiveState, SoccerMatchState } from '../types/simulation';

/**
 * Which league team belongs to *this* aquarium.
 *
 * The league is shared: several tank worlds and the bot teams all appear on one
 * leaderboard. Picking "the first entry whose source is tank" therefore showed
 * World A's arena whatever World B happened to be doing. Resolution now goes
 * through the authoritative `world_id` the backend attaches to each team, never
 * through a display name (which is cosmetic) or a parsed team id.
 */
export interface ResolvedTankTeam {
    teamId: string | null;
    displayName: string | null;
    /** 'A' | 'B' when the squad is identifiable, for labelling which is shown. */
    squad: string | null;
    /** True when this world fields a team but none of them is in the shown match. */
    fielded: boolean;
}

type LiveStateWithMapping = SoccerLeagueLiveState & { team_world_ids?: Record<string, string> };

const NOT_FIELDED: ResolvedTankTeam = { teamId: null, displayName: null, squad: null, fielded: false };

/** The origin world of a team, from authoritative payload fields only. */
export function teamWorldId(
    entry: Pick<LeagueLeaderboardEntry, 'team_id' | 'world_id'>,
    mapping?: Record<string, string>,
): string | null {
    if (entry.world_id) return entry.world_id;
    return mapping?.[entry.team_id] ?? null;
}

/**
 * The squad suffix (`A` / `B`) when the backend encodes one in the team id.
 *
 * Presentation only - it decides which of this world's own teams to default to
 * and how to label it. It never decides *whose* team this is; `world_id` does.
 */
function squadOf(teamId: string): string | null {
    const separator = teamId.lastIndexOf(':');
    if (separator < 0) return null;
    const suffix = teamId.slice(separator + 1);
    return suffix.length > 0 && suffix.length <= 2 ? suffix : null;
}

export function resolveWorldTeam(
    liveState: LiveStateWithMapping | null,
    worldId?: string,
): ResolvedTankTeam {
    // Without a world we cannot know whose team this is. Showing some other
    // tank's row would be worse than showing nothing.
    if (!liveState || !worldId) return NOT_FIELDED;

    const mapping = liveState.team_world_ids;
    const owned = (liveState.leaderboard ?? []).filter(
        (entry) => teamWorldId(entry, mapping) === worldId,
    );
    if (owned.length === 0) return NOT_FIELDED;

    const shownMatch: SoccerMatchState | null =
        liveState.active_match ?? liveState.presentation_match ?? null;

    // Prefer whichever of this world's teams is actually on the pitch.
    const playing = shownMatch
        ? owned.find((entry) => entry.team_id === shownMatch.home_id || entry.team_id === shownMatch.away_id)
        : undefined;

    const selected = playing ?? owned.find((entry) => squadOf(entry.team_id) === 'A') ?? owned[0];
    return {
        teamId: selected.team_id,
        displayName: selected.display_name ?? null,
        squad: squadOf(selected.team_id),
        fielded: true,
    };
}

/**
 * Restrict performers to the resolved team's own tank.
 *
 * Only applied when the payload actually carries the identity to do it: a
 * leader without a `tank_id` is kept rather than dropped, so a thin payload
 * degrades to "unfiltered" instead of to "empty".
 */
export function filterLeadersForWorld(
    leaders: readonly SoccerFishLeaderEntry[] | undefined,
    worldId?: string,
): SoccerFishLeaderEntry[] {
    const all = [...(leaders ?? [])];
    if (!worldId) return all;
    const identifiable = all.filter((leader) => leader.tank_id !== undefined);
    if (identifiable.length === 0) return all;
    return identifiable.filter((leader) => leader.tank_id === worldId);
}
