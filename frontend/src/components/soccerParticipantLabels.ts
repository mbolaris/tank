import type { SoccerMatchState, SoccerParticipant } from '../types/simulation';
import { sidesAreSwapped } from '../renderers/soccer/sideAssignment';

/** §6.8: the roster name, falling back through the identity namespaces (§10.2). */
export function participantLabel(participant: SoccerParticipant): string {
    if (participant.display_name) return participant.display_name;
    if (participant.policy_label) return participant.policy_label;
    if (participant.fish_id !== undefined) return `Fish #${participant.fish_id}`;
    return participant.participant_id;
}

/** §6.8: "Gen 41 · ↑#91", or "founder" for a fish with no recorded parent. */
export function lineageLabel(participant: SoccerParticipant): string | null {
    const parts: string[] = [];
    if (participant.generation !== undefined) parts.push(`Gen ${participant.generation}`);
    if (participant.avatar_kind === 'fish') {
        parts.push(
            participant.parent_id === undefined || participant.parent_id === null
                ? 'founder'
                : `↑#${participant.parent_id}`,
        );
    }
    return parts.length ? parts.join(' · ') : null;
}

/**
 * The display name for a side.
 *
 * Home/away is a **label resolved here** (§10.4 rule 2); the render path stays
 * left/right throughout, so a half swap is a label change and an
 * attack-direction flip, never a change of side identity. The swap itself is
 * read through `sidesAreSwapped` so this and the role derivation can never
 * disagree about which half a team is in.
 */
export function sideDisplayName(match: SoccerMatchState | null, side: 'left' | 'right'): string {
    if (!match) return side === 'left' ? 'Left' : 'Right';
    const isHome = sidesAreSwapped(match) ? side === 'right' : side === 'left';
    if (isHome) return match.home_name || match.home_id || 'Home';
    return match.away_name || match.away_id || 'Away';
}
