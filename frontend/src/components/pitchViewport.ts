import type { SoccerFieldGeometry } from '../types/simulation';

export interface PitchViewportSize {
    width: number;
    height: number;
    dpr: number;
}

/**
 * Resolve the pitch's visual cap.
 *
 * `maxWidth` wins when given. Otherwise an explicit `width` is treated as a
 * deliberate fixed size and caps the pitch. With neither, the pitch is
 * responsive and fills whatever the host gives it - which is what the dedicated
 * arena wants, and why it passes neither.
 */
export function resolvePitchMaxWidth(width?: number, maxWidth?: number): number | undefined {
    if (maxWidth !== undefined) return maxWidth;
    return width;
}

export function calculatePitchViewport(
    containerWidth: number,
    geometry: Pick<SoccerFieldGeometry, 'length' | 'width'> | undefined,
    maxWidth: number,
    devicePixelRatio = 1,
): PitchViewportSize {
    const fieldLength = (geometry?.length ?? 0) > 0 ? geometry?.length ?? 105 : 105;
    const fieldWidth = (geometry?.width ?? 0) > 0 ? geometry?.width ?? 68 : 68;
    const width = Math.max(1, Math.min(containerWidth, maxWidth));
    return {
        width,
        height: Math.max(1, width * fieldWidth / fieldLength),
        dpr: Math.max(1, devicePixelRatio),
    };
}
