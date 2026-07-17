export const WORLD_WIDTH = 1088;
export const WORLD_HEIGHT = 612;
export const MAX_RENDER_DPR = 2;
export const MAX_RENDER_PIXELS = 12_000_000;

export function fitWorldToContainer(containerWidth: number, containerHeight: number) {
    const scale = Math.min(containerWidth / WORLD_WIDTH, containerHeight / WORLD_HEIGHT);
    return {
        cssWidth: WORLD_WIDTH * scale,
        cssHeight: WORLD_HEIGHT * scale,
    };
}

export function getRenderDpr(cssWidth: number, cssHeight: number, devicePixelRatio: number) {
    const requestedDpr = Math.min(devicePixelRatio || 1, MAX_RENDER_DPR);
    const pixelBudgetDpr = Math.sqrt(MAX_RENDER_PIXELS / (cssWidth * cssHeight));
    return Math.min(requestedDpr, pixelBudgetDpr);
}

export function screenPointToWorld(
    clientX: number,
    clientY: number,
    rect: { left: number; top: number; width: number; height: number },
    bufferWidth: number,
    bufferHeight: number,
) {
    const canvasX = (clientX - rect.left) * (bufferWidth / rect.width);
    const canvasY = (clientY - rect.top) * (bufferHeight / rect.height);
    return {
        worldX: canvasX * (WORLD_WIDTH / bufferWidth),
        worldY: canvasY * (WORLD_HEIGHT / bufferHeight),
    };
}
