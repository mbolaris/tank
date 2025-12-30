
export type WorldType = string;
export type ViewMode = "side" | "topdown";

export interface RenderContext {
    canvas: HTMLCanvasElement;
    ctx: CanvasRenderingContext2D;
    dpr: number;
    nowMs: number;
}

export interface RenderFrame {
    worldType: WorldType;
    viewMode: ViewMode;
    // Using any for snapshot to avoid circular dependency or tight coupling for now.
    // In strict mode this might be SimulationUpdate.
    snapshot: any;
}

export interface Renderer {
    id: string;
    /**
     * Release resources (WebGL context, event listeners, cached images)
     */
    dispose(): void;

    /**
     * Draw a single frame
     */
    render(frame: RenderFrame, rc: RenderContext): void;
}
