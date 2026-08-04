import type { SoccerMatchState } from '../../types/simulation';

/**
 * Which team *identity* occupies which physical half, and which way each attacks.
 *
 * Team identity (home / away) is fixed for the match. The side a team occupies
 * is not: the engine swaps halves at half time. Whoever stands on the left
 * always attacks right, so the arrows are a property of the side, while the
 * names are a property of the team.
 */
export interface SideAssignment {
    /** Team identity occupying the left half of the pitch. */
    leftTeam: 'home' | 'away';
    /** Team identity occupying the right half of the pitch. */
    rightTeam: 'home' | 'away';
    leftLabel: string;
    rightLabel: string;
    /** Attack direction of the left-side occupant. Always +1 (towards +x). */
    leftAttackDirection: 1;
    /** Attack direction of the right-side occupant. Always -1 (towards -x). */
    rightAttackDirection: -1;
}

type SideSource = Pick<SoccerMatchState, 'home_name' | 'home_id' | 'away_name' | 'away_id' | 'half' | 'sides_swapped'>;

function homeLabel(state: SideSource): string {
    return state.home_name || state.home_id || 'HOME';
}

function awayLabel(state: SideSource): string {
    return state.away_name || state.away_id || 'AWAY';
}

/**
 * True once the teams have changed ends.
 *
 * `sides_swapped` is the engine's own side-swap flag and wins when present.
 * `half === 2` is the fallback for payloads predating that field. Anything
 * missing or unrecognised defaults conservatively to the first half rather
 * than guessing from the score, the player arrays, or the display names.
 */
export function sidesAreSwapped(state: SideSource | null | undefined): boolean {
    if (!state) return false;
    if (typeof state.sides_swapped === 'boolean') return state.sides_swapped;
    return state.half === 2;
}

export function resolveSideAssignment(state: SideSource | null | undefined): SideAssignment {
    const swapped = sidesAreSwapped(state);
    const home = state ? homeLabel(state) : 'HOME';
    const away = state ? awayLabel(state) : 'AWAY';
    return {
        leftTeam: swapped ? 'away' : 'home',
        rightTeam: swapped ? 'home' : 'away',
        leftLabel: swapped ? away : home,
        rightLabel: swapped ? home : away,
        leftAttackDirection: 1,
        rightAttackDirection: -1,
    };
}
