/**
 * Formation and spacing maths for Tactical mode (§4.1).
 *
 * Pure functions over canonical field metres (ADR-017): `+x` toward the right
 * team's goal, `+y` north. Nothing here knows about pixels, canvas size, or
 * DPR - the same numbers must hold whatever the pitch is rendered at.
 */

export type PositionalRole = 'D' | 'M' | 'F';

export interface FieldPoint {
    x: number;
    y: number;
}

export interface PlayerPositionSummary {
    participantId: string;
    side: 'left' | 'right';
    /** Mean canonical x over the sampled window. */
    meanX: number;
    meanY: number;
    samples: number;
}

export interface TeamShape {
    /** Convex hull area of the team's mean positions, in m². */
    areaM2: number;
    /** Mean of the team's mean x positions, in canonical metres. */
    meanX: number;
    /** Spread: max minus min mean-x across the team, in metres. */
    widthM: number;
}

/**
 * True when the given side is defending the `-x` goal.
 *
 * `side` is a fixed team label for the whole match, **not** the half a team
 * currently stands in. At half time the engine inverts every position
 * (`SoccerMatch._handle_half_time` maps `x -> -x`) and sets `swapped_sides`,
 * while participant ids and `side` values stay put - its own comment says "If
 * sides swapped, Right Team is on Left Side". So the end a side defends is the
 * exclusive-or of its label and the swap.
 */
export function defendsNegativeX(side: 'left' | 'right', sidesSwapped: boolean): boolean {
    return (side === 'left') !== sidesSwapped;
}

/**
 * The positional role a mean x-position implies, for a player on `side`.
 *
 * **Derived, not assigned.** The soccer engine has no role concept and no
 * goalkeeper (`build_default_formation` places a symmetric line and nothing
 * else), so `GK` is deliberately absent: labelling a player a keeper the
 * simulation does not have would be an invention, not a readout.
 *
 * Thirds are measured from the team's *own* goal, so `F` always means "far
 * forward" for both sides and in both halves, rather than "toward +x".
 */
export function roleForMeanX(
    meanX: number,
    side: 'left' | 'right',
    fieldLength: number,
    sidesSwapped = false,
): PositionalRole {
    if (fieldLength <= 0) return 'M';
    const halfLength = fieldLength / 2;
    // Distance from own goal line, normalised to 0..1 up the pitch.
    const fromOwnGoal = defendsNegativeX(side, sidesSwapped) ? meanX + halfLength : halfLength - meanX;
    const progress = Math.min(1, Math.max(0, fromOwnGoal / fieldLength));
    if (progress < 1 / 3) return 'D';
    if (progress < 2 / 3) return 'M';
    return 'F';
}

export const ROLE_LABELS: Record<PositionalRole, string> = {
    D: 'Defensive third',
    M: 'Middle third',
    F: 'Attacking third',
};

/** Convex hull by monotone chain, returned counter-clockwise in canonical space. */
export function convexHull(points: readonly FieldPoint[]): FieldPoint[] {
    const unique = dedupePoints(points);
    if (unique.length < 3) return unique;
    const sorted = [...unique].sort((left, right) => left.x - right.x || left.y - right.y);

    const build = (source: readonly FieldPoint[]): FieldPoint[] => {
        const chain: FieldPoint[] = [];
        for (const point of source) {
            while (chain.length >= 2 && cross(chain[chain.length - 2], chain[chain.length - 1], point) <= 0) {
                chain.pop();
            }
            chain.push(point);
        }
        chain.pop();
        return chain;
    };

    return [...build(sorted), ...build([...sorted].reverse())];
}

function dedupePoints(points: readonly FieldPoint[]): FieldPoint[] {
    const seen = new Set<string>();
    const unique: FieldPoint[] = [];
    for (const point of points) {
        const key = `${point.x}:${point.y}`;
        if (seen.has(key)) continue;
        seen.add(key);
        unique.push(point);
    }
    return unique;
}

function cross(origin: FieldPoint, a: FieldPoint, b: FieldPoint): number {
    return (a.x - origin.x) * (b.y - origin.y) - (a.y - origin.y) * (b.x - origin.x);
}

/** Shoelace area of a polygon, always non-negative. */
export function polygonArea(polygon: readonly FieldPoint[]): number {
    if (polygon.length < 3) return 0;
    let total = 0;
    for (let index = 0; index < polygon.length; index += 1) {
        const current = polygon[index];
        const next = polygon[(index + 1) % polygon.length];
        total += current.x * next.y - next.x * current.y;
    }
    return Math.abs(total) / 2;
}

/**
 * Team shape from the per-player mean positions.
 *
 * Two players cannot enclose an area, so a 2-a-side team reports 0 m² rather
 * than a degenerate sliver - which is correct, not a gap.
 */
export function teamShapeFrom(summaries: readonly PlayerPositionSummary[]): TeamShape {
    if (!summaries.length) return { areaM2: 0, meanX: 0, widthM: 0 };
    const points = summaries.map((summary) => ({ x: summary.meanX, y: summary.meanY }));
    const xs = summaries.map((summary) => summary.meanX);
    return {
        areaM2: polygonArea(convexHull(points)),
        meanX: xs.reduce((total, value) => total + value, 0) / xs.length,
        widthM: Math.max(...xs) - Math.min(...xs),
    };
}

export interface PossessionChainCounts {
    left: number;
    right: number;
    longestLeft: number;
    longestRight: number;
}

export const EMPTY_CHAIN_COUNTS: PossessionChainCounts = {
    left: 0,
    right: 0,
    longestLeft: 0,
    longestRight: 0,
};

/**
 * Possession chains from an ordered sequence of ball owners.
 *
 * A **chain** is a maximal run of consecutive distinct owners on one side; a
 * chain of length n contains n-1 completed passes, so only runs of 2 or more
 * are counted. Repeats of the same owner are collapsed first: a player keeping
 * the ball for forty cycles is one touch, not forty passes to themselves.
 */
export function possessionChains(
    owners: readonly { participantId: string; side: 'left' | 'right' }[],
): PossessionChainCounts {
    const counts = { ...EMPTY_CHAIN_COUNTS };
    let runSide: 'left' | 'right' | null = null;
    let runLength = 0;
    let previousParticipant: string | null = null;

    const closeRun = () => {
        if (runSide && runLength >= 2) {
            counts[runSide] += 1;
            const longestKey = runSide === 'left' ? 'longestLeft' : 'longestRight';
            counts[longestKey] = Math.max(counts[longestKey], runLength);
        }
        runLength = 0;
    };

    for (const owner of owners) {
        if (owner.participantId === previousParticipant) continue;
        previousParticipant = owner.participantId;
        if (owner.side !== runSide) {
            closeRun();
            runSide = owner.side;
        }
        runLength += 1;
    }
    closeRun();
    return counts;
}
