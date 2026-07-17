const WORLD_WIDTH = 1088;
const WORLD_HEIGHT = 612;

export const FOLLOW_ZOOM = 1.75;

export interface FollowViewport {
    sourceX: number;
    sourceY: number;
    sourceWidth: number;
    sourceHeight: number;
}

/** Keep a follow target centred where possible while clamping at world edges. */
export function getFollowViewport(
    target: { x: number; y: number; width: number; height: number },
    canvasWidth: number,
    canvasHeight: number,
    zoom: number = FOLLOW_ZOOM
): FollowViewport {
    const sourceWidth = canvasWidth / zoom;
    const sourceHeight = canvasHeight / zoom;
    const targetX = (target.x + target.width / 2) * (canvasWidth / WORLD_WIDTH);
    const targetY = (target.y + target.height / 2) * (canvasHeight / WORLD_HEIGHT);
    return {
        sourceX: Math.max(0, Math.min(canvasWidth - sourceWidth, targetX - sourceWidth / 2)),
        sourceY: Math.max(0, Math.min(canvasHeight - sourceHeight, targetY - sourceHeight / 2)),
        sourceWidth,
        sourceHeight,
    };
}
