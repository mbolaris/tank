
import type { SimulationUpdate, SoccerMatchState } from '../types/simulation';

export type WorldType = string;
export type ViewMode = "side" | "topdown";
export type RenderSnapshot = SimulationUpdate | SoccerMatchState;

export interface RenderContext {
    canvas: HTMLCanvasElement;
    ctx: CanvasRenderingContext2D;
    dpr: number;
    nowMs: number;
}

export interface RenderOptions {
    showEffects?: boolean;
    showSoccer?: boolean;
    selectedEntityId?: number | null;
    viewMode?: ViewMode;
}

export interface RenderFrame {
    worldType: WorldType;
    viewMode: ViewMode;
    snapshot: RenderSnapshot;
    options?: RenderOptions;
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

    /**
     * Optional cache eviction hook for long-running sessions.
     */
    clearPathCache?: () => void;
}
