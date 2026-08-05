import { describe, expect, it } from 'vitest';
import {
    convexHull,
    defendsNegativeX,
    polygonArea,
    possessionChains,
    roleForMeanX,
    teamShapeFrom,
    type PlayerPositionSummary,
} from './soccerFormation';

const FIELD_LENGTH = 105;

describe('roleForMeanX', () => {
    it('measures thirds from each side\'s own goal, not from +x', () => {
        // The left team defends -x, the right team defends +x, so the same
        // canonical x is a defender for one side and a forward for the other.
        expect(roleForMeanX(-45, 'left', FIELD_LENGTH)).toBe('D');
        expect(roleForMeanX(-45, 'right', FIELD_LENGTH)).toBe('F');
        expect(roleForMeanX(45, 'left', FIELD_LENGTH)).toBe('F');
        expect(roleForMeanX(45, 'right', FIELD_LENGTH)).toBe('D');
    });

    it('calls the centre circle the middle third for both sides', () => {
        expect(roleForMeanX(0, 'left', FIELD_LENGTH)).toBe('M');
        expect(roleForMeanX(0, 'right', FIELD_LENGTH)).toBe('M');
    });

    it('clamps a player who has strayed past a goal line', () => {
        expect(roleForMeanX(-200, 'left', FIELD_LENGTH)).toBe('D');
        expect(roleForMeanX(200, 'left', FIELD_LENGTH)).toBe('F');
    });

    it('degrades to the middle third rather than dividing by a zero-length field', () => {
        expect(roleForMeanX(0, 'left', 0)).toBe('M');
    });

    it('survives the half swap, when the same position becomes the other end', () => {
        // `SoccerMatch._handle_half_time` inverts every position (x -> -x) and
        // sets `swapped_sides`, but participant ids and `side` values stay put -
        // "If sides swapped, Right Team is on Left Side". A defender who has not
        // moved relative to their own goal must still read as a defender.
        expect(roleForMeanX(-45, 'left', FIELD_LENGTH, false)).toBe('D');
        expect(roleForMeanX(45, 'left', FIELD_LENGTH, true)).toBe('D');
        expect(roleForMeanX(45, 'right', FIELD_LENGTH, false)).toBe('D');
        expect(roleForMeanX(-45, 'right', FIELD_LENGTH, true)).toBe('D');
    });
});

describe('defendsNegativeX', () => {
    it('is the exclusive-or of the side label and the swap', () => {
        expect(defendsNegativeX('left', false)).toBe(true);
        expect(defendsNegativeX('right', false)).toBe(false);
        expect(defendsNegativeX('left', true)).toBe(false);
        expect(defendsNegativeX('right', true)).toBe(true);
    });
});

describe('convexHull / polygonArea', () => {
    it('measures a square, ignoring an interior point', () => {
        const square = [
            { x: 0, y: 0 },
            { x: 10, y: 0 },
            { x: 10, y: 10 },
            { x: 0, y: 10 },
            { x: 5, y: 5 },
        ];
        expect(polygonArea(convexHull(square))).toBeCloseTo(100);
    });

    it('reports no area for fewer than three distinct points', () => {
        expect(polygonArea(convexHull([{ x: 0, y: 0 }, { x: 5, y: 5 }]))).toBe(0);
        expect(polygonArea(convexHull([{ x: 1, y: 1 }, { x: 1, y: 1 }, { x: 1, y: 1 }]))).toBe(0);
    });

    it('reports no area for collinear players', () => {
        const line = [{ x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }];
        expect(polygonArea(convexHull(line))).toBeCloseTo(0);
    });
});

describe('teamShapeFrom', () => {
    const summary = (participantId: string, meanX: number, meanY: number): PlayerPositionSummary => ({
        participantId,
        side: 'left',
        meanX,
        meanY,
        samples: 10,
    });

    it('reports area, mean x and depth together', () => {
        const shape = teamShapeFrom([
            summary('left_1', -30, -10),
            summary('left_2', -10, 0),
            summary('left_3', -20, 10),
        ]);
        expect(shape.areaM2).toBeGreaterThan(0);
        expect(shape.meanX).toBeCloseTo(-20);
        expect(shape.widthM).toBeCloseTo(20);
    });

    it('is empty for an empty team rather than NaN', () => {
        expect(teamShapeFrom([])).toEqual({ areaM2: 0, meanX: 0, widthM: 0 });
    });
});

describe('possessionChains', () => {
    const owner = (participantId: string, side: 'left' | 'right') => ({ participantId, side });

    it('counts a run of same-side owners as one chain', () => {
        const counts = possessionChains([
            owner('left_1', 'left'),
            owner('left_2', 'left'),
            owner('left_3', 'left'),
        ]);
        expect(counts.left).toBe(1);
        expect(counts.longestLeft).toBe(3);
        expect(counts.right).toBe(0);
    });

    it('does not count a single touch as a chain', () => {
        const counts = possessionChains([owner('left_1', 'left'), owner('right_1', 'right')]);
        expect(counts).toEqual({ left: 0, right: 0, longestLeft: 0, longestRight: 0 });
    });

    it('collapses a player holding the ball instead of counting self-passes', () => {
        const counts = possessionChains([
            owner('left_1', 'left'),
            owner('left_1', 'left'),
            owner('left_1', 'left'),
        ]);
        expect(counts.left).toBe(0);
    });

    it('splits a chain at a turnover and counts both sides', () => {
        const counts = possessionChains([
            owner('left_1', 'left'),
            owner('left_2', 'left'),
            owner('right_1', 'right'),
            owner('right_2', 'right'),
            owner('right_3', 'right'),
        ]);
        expect(counts.left).toBe(1);
        expect(counts.right).toBe(1);
        expect(counts.longestRight).toBe(3);
    });
});
