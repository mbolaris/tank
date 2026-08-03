export type SoccerCoordinateSpace = 'canonical' | 'legacy_render' | string | undefined;

export interface RenderCoordinate {
    x: number;
    y: number;
}

/** Convert canonical (+y north) match coordinates to canvas (+y down) coordinates. */
export function renderFromCanonical(
    coordinate: RenderCoordinate,
    coordSpace: SoccerCoordinateSpace,
): RenderCoordinate {
    if (coordSpace === 'canonical') {
        return { x: coordinate.x, y: -coordinate.y };
    }

    // PR 0 payloads marked legacy_render already use canvas handedness. Unknown
    // values stay on the compatibility path until a newer adapter is shipped.
    return { ...coordinate };
}
