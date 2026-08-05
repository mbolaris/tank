import { useEffect, useRef, useState } from 'react';
import type { EntityData, SoccerMatchState } from '../types/simulation';
import { sidesAreSwapped } from '../renderers/soccer/sideAssignment';
import {
    EMPTY_CHAIN_COUNTS,
    possessionChains,
    roleForMeanX,
    teamShapeFrom,
    type PlayerPositionSummary,
    type PositionalRole,
    type PossessionChainCounts,
    type TeamShape,
} from '../components/soccerFormation';

/** Matches the trail window (§4.1, "last ~90 frames") so both read the same span of play. */
export const FORMATION_WINDOW_FRAMES = 90;

/** Owner history is only ever reduced to chain counts; this caps it regardless of match length. */
const MAX_OWNER_HISTORY = 512;

export interface FormationMetrics {
    /** Positional role per `participant_id`, derived from mean position. */
    roles: Record<string, PositionalRole>;
    summaries: PlayerPositionSummary[];
    left: TeamShape;
    right: TeamShape;
    chains: PossessionChainCounts;
    /** Match frames contributing to the current window. */
    sampledFrames: number;
}

export const EMPTY_FORMATION_METRICS: FormationMetrics = {
    roles: {},
    summaries: [],
    left: { areaM2: 0, meanX: 0, widthM: 0 },
    right: { areaM2: 0, meanX: 0, widthM: 0 },
    chains: EMPTY_CHAIN_COUNTS,
    sampledFrames: 0,
};

interface PlayerHistory {
    side: 'left' | 'right';
    xs: number[];
    ys: number[];
}

interface Accumulator {
    matchId: string | null;
    lastFrame: number | null;
    players: Map<string, PlayerHistory>;
    owners: { participantId: string; side: 'left' | 'right' }[];
}

function emptyAccumulator(): Accumulator {
    return { matchId: null, lastFrame: null, players: new Map(), owners: [] };
}

function summarise(accumulator: Accumulator, fieldLength: number, sidesSwapped: boolean): FormationMetrics {
    const summaries: PlayerPositionSummary[] = [];
    for (const [participantId, history] of accumulator.players) {
        if (!history.xs.length) continue;
        summaries.push({
            participantId,
            side: history.side,
            meanX: history.xs.reduce((total, value) => total + value, 0) / history.xs.length,
            meanY: history.ys.reduce((total, value) => total + value, 0) / history.ys.length,
            samples: history.xs.length,
        });
    }
    summaries.sort((left, right) => left.participantId.localeCompare(right.participantId));

    const roles: Record<string, PositionalRole> = {};
    for (const summary of summaries) {
        roles[summary.participantId] = roleForMeanX(summary.meanX, summary.side, fieldLength, sidesSwapped);
    }

    return {
        roles,
        summaries,
        left: teamShapeFrom(summaries.filter((summary) => summary.side === 'left')),
        right: teamShapeFrom(summaries.filter((summary) => summary.side === 'right')),
        chains: possessionChains(accumulator.owners),
        sampledFrames: summaries.reduce((most, summary) => Math.max(most, summary.samples), 0),
    };
}

interface SoccerEntityHint {
    participant_id?: string;
    team?: 'left' | 'right';
}

function participantIdOf(entity: EntityData): string | undefined {
    const hint = entity.render_hint as SoccerEntityHint | undefined;
    return (entity as EntityData & { participant_id?: string }).participant_id ?? hint?.participant_id;
}

/**
 * Canonical y for a payload coordinate.
 *
 * `legacy_render` payloads already carry canvas handedness (+y down), so their
 * y is the negation of canonical. x is identical in both spaces.
 */
function canonicalY(y: number, coordSpace: SoccerMatchState['coord_space']): number {
    return coordSpace === 'canonical' ? y : -y;
}

/**
 * Rolling formation and spacing metrics over the last `FORMATION_WINDOW_FRAMES`
 * match frames.
 *
 * This keeps its own position history rather than reading the renderer's trail
 * buffer: the trail is a *path* drawn on a canvas and the metrics are
 * *statistics* consumed by React, and an imperative channel from renderer back
 * into component state would couple them for no gain. Both are bounded to the
 * same window, so they describe the same span of play.
 *
 * `enabled` is false in Broadcast, where nothing consumes these - the history
 * is dropped so a viewer who never opens Tactical pays nothing.
 */
export function useFormationMetrics(match: SoccerMatchState | null, enabled: boolean): FormationMetrics {
    const accumulatorRef = useRef<Accumulator>(emptyAccumulator());
    const [metrics, setMetrics] = useState<FormationMetrics>(EMPTY_FORMATION_METRICS);

    const matchId = match?.match_id ?? null;
    const frame = match?.frame ?? null;
    const fieldLength = match?.geometry?.length ?? match?.field?.length ?? 105;
    // One definition of the swap for the whole render path, including the
    // `half === 2` fallback for payloads that predate `sides_swapped`.
    const sidesSwapped = sidesAreSwapped(match);

    useEffect(() => {
        if (!enabled) {
            accumulatorRef.current = emptyAccumulator();
            setMetrics(EMPTY_FORMATION_METRICS);
        }
    }, [enabled]);

    useEffect(() => {
        if (!enabled || !match || frame === null) return;
        const accumulator = accumulatorRef.current;

        // A new match, or a rewound clock, shares no history with what came before.
        if (accumulator.matchId !== matchId || (accumulator.lastFrame !== null && frame < accumulator.lastFrame)) {
            accumulatorRef.current = emptyAccumulator();
            accumulatorRef.current.matchId = matchId;
        }
        const current = accumulatorRef.current;
        // Interpolated rAF ticks repeat a frame; sampling them would shrink the
        // window to a fraction of a second of real play.
        if (current.lastFrame === frame) return;
        current.lastFrame = frame;

        const sides = new Map((match.participants ?? []).map((participant) => [participant.participant_id, participant.side]));
        const live = new Set<string>();
        for (const entity of match.entities ?? []) {
            if (entity.type !== 'player') continue;
            const participantId = participantIdOf(entity);
            if (!participantId) continue;
            const hint = entity.render_hint as SoccerEntityHint | undefined;
            const side = sides.get(participantId) ?? entity.team ?? hint?.team;
            if (side !== 'left' && side !== 'right') continue;
            live.add(participantId);
            const history = current.players.get(participantId) ?? { side, xs: [], ys: [] };
            history.side = side;
            history.xs.push(entity.x);
            history.ys.push(canonicalY(entity.y, match.coord_space));
            if (history.xs.length > FORMATION_WINDOW_FRAMES) {
                history.xs.splice(0, history.xs.length - FORMATION_WINDOW_FRAMES);
                history.ys.splice(0, history.ys.length - FORMATION_WINDOW_FRAMES);
            }
            current.players.set(participantId, history);
        }
        for (const key of [...current.players.keys()]) {
            if (!live.has(key)) current.players.delete(key);
        }

        const owner = match.ball_owner;
        if (owner) {
            const side = sides.get(owner);
            if (side === 'left' || side === 'right') {
                const last = current.owners.at(-1);
                if (!last || last.participantId !== owner) {
                    current.owners.push({ participantId: owner, side });
                    if (current.owners.length > MAX_OWNER_HISTORY) {
                        current.owners.splice(0, current.owners.length - MAX_OWNER_HISTORY);
                    }
                }
            }
        }

        // Summarising here rather than during render keeps the accumulator a
        // true ref: nothing reads it while React is rendering.
        setMetrics(summarise(current, fieldLength, sidesSwapped));
    }, [enabled, match, matchId, frame, fieldLength, sidesSwapped]);

    return metrics;
}
