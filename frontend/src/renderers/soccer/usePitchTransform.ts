export interface PitchGeometryDimensions {
    length: number;
    width: number;
}

export interface PitchViewport {
    width: number;
    height: number;
}

export interface PitchTransform {
    scale: number;
    originX: number;
    originY: number;
    toScreen(x: number, y: number): [number, number];
    toField(px: number, py: number): [number, number];
}

/** Build the one uniform metres-to-pixels transform used by the soccer renderer. */
export function usePitchTransform(
    geometry: PitchGeometryDimensions,
    viewport: PitchViewport,
    margin = 20,
): PitchTransform {
    const length = Math.max(geometry.length, Number.EPSILON);
    const width = Math.max(geometry.width, Number.EPSILON);
    const availableWidth = Math.max(viewport.width - margin * 2, 1);
    const availableHeight = Math.max(viewport.height - margin * 2, 1);
    const scale = Math.min(availableWidth / length, availableHeight / width);
    const originX = viewport.width / 2;
    const originY = viewport.height / 2;

    return {
        scale,
        originX,
        originY,
        toScreen: (x, y) => [originX + x * scale, originY + y * scale],
        toField: (px, py) => [(px - originX) / scale, (py - originY) / scale],
    };
}
