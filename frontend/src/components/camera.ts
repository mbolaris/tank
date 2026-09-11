/** The tank camera: what part of the world the canvas is currently showing.
 *
 * The renderer always draws the whole world into a buffer the size of the
 * visible canvas. A camera is therefore just a source rectangle handed to
 * `drawImage`, and "no camera" is the rectangle covering the whole buffer.
 *
 * Following a fish and freely exploring are the same operation with a
 * different centre and zoom, so both produce a `Camera` and share one
 * viewport function. That matters for correctness as much as tidiness: hit
 * testing has to invert exactly the transform the render loop applied, and
 * the two drifting apart is how a click starts selecting the wrong fish.
 */

import { WORLD_HEIGHT, WORLD_WIDTH } from './canvasGeometry';

export const MIN_ZOOM = 1;
/** Capped to MAX_SUPERSAMPLE in Canvas.tsx: past the point where the world can
 *  be re-rendered at zoom resolution, zooming only enlarges pixels, so the
 *  range stops where the image stops being honest. */
export const MAX_ZOOM = 4;

/** Zoom applied when following a fish. */
export const FOLLOW_ZOOM = 1.75;

export interface Camera {
    zoom: number;
    /** Centre of the visible region, in world units. */
    centerX: number;
    centerY: number;
}

export interface CameraViewport {
    sourceX: number;
    sourceY: number;
    sourceWidth: number;
    sourceHeight: number;
}

export const DEFAULT_CAMERA: Camera = {
    zoom: MIN_ZOOM,
    centerX: WORLD_WIDTH / 2,
    centerY: WORLD_HEIGHT / 2,
};

function clamp(value: number, low: number, high: number): number {
    // low > high when the world is narrower than the view; centre it instead
    // of returning a NaN-ish inversion.
    if (high < low) return (low + high) / 2;
    return Math.min(high, Math.max(low, value));
}

/** Constrain zoom to range, then keep the view inside the world. */
export function clampCamera(camera: Camera): Camera {
    const zoom = clamp(camera.zoom, MIN_ZOOM, MAX_ZOOM);
    const halfWidth = WORLD_WIDTH / (2 * zoom);
    const halfHeight = WORLD_HEIGHT / (2 * zoom);
    return {
        zoom,
        centerX: clamp(camera.centerX, halfWidth, WORLD_WIDTH - halfWidth),
        centerY: clamp(camera.centerY, halfHeight, WORLD_HEIGHT - halfHeight),
    };
}

/** True when the camera shows the whole world, so no blit is needed. */
export function isDefaultCamera(camera: Camera): boolean {
    return (
        Math.abs(camera.zoom - DEFAULT_CAMERA.zoom) < 1e-9 &&
        Math.abs(camera.centerX - DEFAULT_CAMERA.centerX) < 1e-9 &&
        Math.abs(camera.centerY - DEFAULT_CAMERA.centerY) < 1e-9
    );
}

/** Centre on an entity at the follow zoom, clamped to the world. */
export function cameraForTarget(
    target: { x: number; y: number; width: number; height: number },
    zoom: number = FOLLOW_ZOOM,
): Camera {
    return clampCamera({
        zoom,
        centerX: target.x + target.width / 2,
        centerY: target.y + target.height / 2,
    });
}

/** The source rectangle, in buffer pixels, this camera reads from. */
export function getCameraViewport(
    camera: Camera,
    bufferWidth: number,
    bufferHeight: number,
): CameraViewport {
    const safe = clampCamera(camera);
    const sourceWidth = bufferWidth / safe.zoom;
    const sourceHeight = bufferHeight / safe.zoom;
    const scaleX = bufferWidth / WORLD_WIDTH;
    const scaleY = bufferHeight / WORLD_HEIGHT;
    return {
        sourceX: (safe.centerX - WORLD_WIDTH / (2 * safe.zoom)) * scaleX,
        sourceY: (safe.centerY - WORLD_HEIGHT / (2 * safe.zoom)) * scaleY,
        sourceWidth,
        sourceHeight,
    };
}

/** World point at a fractional position across the view (0..1, left/top origin). */
export function viewFractionToWorld(
    camera: Camera,
    fractionX: number,
    fractionY: number,
): { worldX: number; worldY: number } {
    const safe = clampCamera(camera);
    const visibleWidth = WORLD_WIDTH / safe.zoom;
    const visibleHeight = WORLD_HEIGHT / safe.zoom;
    return {
        worldX: safe.centerX - visibleWidth / 2 + fractionX * visibleWidth,
        worldY: safe.centerY - visibleHeight / 2 + fractionY * visibleHeight,
    };
}

/** World point under a screen coordinate, inverting exactly what was drawn. */
export function cameraScreenToWorld(
    camera: Camera,
    clientX: number,
    clientY: number,
    rect: { left: number; top: number; width: number; height: number },
): { worldX: number; worldY: number } {
    return viewFractionToWorld(
        camera,
        (clientX - rect.left) / rect.width,
        (clientY - rect.top) / rect.height,
    );
}

/** Zoom while keeping the world point under the cursor under the cursor.
 *
 * At the world edges the centre clamp wins and the anchor drifts, which is
 * correct: there is nothing outside the tank to pull into view.
 */
export function zoomAtFraction(
    camera: Camera,
    nextZoom: number,
    fractionX: number,
    fractionY: number,
): Camera {
    const zoom = clamp(nextZoom, MIN_ZOOM, MAX_ZOOM);
    const anchor = viewFractionToWorld(camera, fractionX, fractionY);
    return clampCamera({
        zoom,
        centerX: anchor.worldX + (0.5 - fractionX) * (WORLD_WIDTH / zoom),
        centerY: anchor.worldY + (0.5 - fractionY) * (WORLD_HEIGHT / zoom),
    });
}

/** Drag the world with the pointer: content follows the cursor. */
export function panByScreenDelta(
    camera: Camera,
    deltaX: number,
    deltaY: number,
    rectWidth: number,
    rectHeight: number,
): Camera {
    if (rectWidth <= 0 || rectHeight <= 0) return clampCamera(camera);
    const safe = clampCamera(camera);
    const worldPerPixelX = WORLD_WIDTH / safe.zoom / rectWidth;
    const worldPerPixelY = WORLD_HEIGHT / safe.zoom / rectHeight;
    return clampCamera({
        zoom: safe.zoom,
        centerX: safe.centerX - deltaX * worldPerPixelX,
        centerY: safe.centerY - deltaY * worldPerPixelY,
    });
}

/** Multiply zoom about the view centre, for buttons and keyboard. */
export function zoomByStep(camera: Camera, factor: number): Camera {
    return zoomAtFraction(camera, camera.zoom * factor, 0.5, 0.5);
}
