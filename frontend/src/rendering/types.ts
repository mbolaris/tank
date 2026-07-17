
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

/** The selected fish's shared Target Pursuit Module vectors, for the overlay. */
export interface PursuitOverlayData {
    targetVector: [number, number] | null;
    aimVector: [number, number] | null;
}

/** The selected fish's Target Memory details, for the overlay. */
export interface TargetMemoryOverlayRecentEvent {
    domain: string;
    action: string;
    ageFrames: number;
}

export interface TargetMemoryOverlayData {
    domain: string;
    action: string;
    lastSeenPosition: [number, number];
    predictedPosition: [number, number];
    searchVector: [number, number];
    confidence: number;
    recentEvent: TargetMemoryOverlayRecentEvent | null;
}

export interface RenderOptions {
    showEffects?: boolean;
    showSoccer?: boolean;
    selectedEntityId?: number | null;
    viewMode?: ViewMode;
    pursuitOverlay?: PursuitOverlayData | null;
    targetMemoryOverlay?: TargetMemoryOverlayData | null;
    buildGhost?: { kind: string; x: number; y: number; width: number; height: number } | null;
    /** Build mode exposes ecosystem interaction geometry; Observe mode stays clean. */
    buildMode?: boolean;
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
