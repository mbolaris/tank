/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect, useState, useCallback, type CSSProperties } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import type { PursuitOverlayData, TargetMemoryOverlayData, Renderer, ViewMode } from '../rendering/types';
import { rendererRegistry } from '../rendering/registry';
import { initRenderers } from '../renderers/init';
import { ImageLoader } from '../utils/ImageLoader';
import { FOLLOW_ZOOM, getFollowViewport } from './followViewport';

interface CanvasProps {
    state: SimulationUpdate | null;
    width?: number;
    height?: number;
    onEntityClick?: (entityId: number, entityType: string) => void;
    selectedEntityId?: number | null;
    /** Selected fish's pursuit-module vectors, drawn for it only. */
    pursuitOverlay?: PursuitOverlayData | null;
    /** Selected fish's target memory vectors/details, drawn for it only. */
    targetMemoryOverlay?: TargetMemoryOverlayData | null;
    /** Opt-in camera target. The renderer still receives the full world state. */
    followEntityId?: number | null;
    showEffects?: boolean;
    showSoccer?: boolean;
    style?: CSSProperties;
    viewMode?: ViewMode;
    worldType?: string;  // Optional override for renderer selection (e.g., 'petri' for circular dish)
    buildMode?: boolean;
    buildPlacementActive?: boolean;
    onBuildPlace?: (x: number, y: number) => void;
    onBuildPointerMove?: (x: number, y: number) => void;
    onBuildDragStart?: (objectId: number) => void;
    onBuildDragEnd?: (objectId: number, x: number, y: number) => void;
    buildGhost?: { kind: string; x: number; y: number; width: number; height: number } | null;
}

// Tank world dimensions (from core/constants.py)
const WORLD_WIDTH = 1088;
const WORLD_HEIGHT = 612;
export function Canvas({ state, width = 800, height = 600, onEntityClick, selectedEntityId, pursuitOverlay, targetMemoryOverlay, followEntityId, showEffects = true, showSoccer = true, style, viewMode = "side", worldType: worldTypeProp, buildMode = false, buildPlacementActive = false, onBuildPlace, onBuildPointerMove, onBuildDragStart, onBuildDragEnd, buildGhost = null }: CanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<Renderer | null>(null);
    const [imagesLoaded, setImagesLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const followCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const draggingObjectIdRef = useRef<number | null>(null);

    // Use ref to track if error has been set to avoid repeated setState calls
    const errorSetRef = useRef(false);

    // Stable error setter that only sets once
    const setErrorOnce = useCallback((message: string) => {
        if (!errorSetRef.current) {
            errorSetRef.current = true;
            setError(message);
        }
    }, []);

    const getWorldPoint = (event: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas || !state) return null;

        // Get click coordinates relative to canvas
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        let clickX = (event.clientX - rect.left) * scaleX;
        let clickY = (event.clientY - rect.top) * scaleY;

        const followed = followEntityId !== null && followEntityId !== undefined
            ? (state.snapshot?.entities ?? state.entities ?? []).find((entity) => entity.id === followEntityId)
            : undefined;
        if (followed) {
            const viewport = getFollowViewport(followed, canvas.width, canvas.height);
            clickX = viewport.sourceX + clickX / FOLLOW_ZOOM;
            clickY = viewport.sourceY + clickY / FOLLOW_ZOOM;
        }

        // Account for world-to-canvas scaling
        const worldScaleX = WORLD_WIDTH / width;
        const worldScaleY = WORLD_HEIGHT / height;
        const worldX = clickX * worldScaleX;
        const worldY = clickY * worldScaleY;

        return { worldX, worldY };
    };

    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!state || error) return;
        const point = getWorldPoint(event);
        if (!point) return;
        if (buildMode && buildPlacementActive) {
            onBuildPlace?.(point.worldX, point.worldY);
            return;
        }
        if (!onEntityClick) return;
        const { worldX, worldY } = point;

        // Find clicked entity (check in reverse order to prioritize entities rendered on top)
        const entities = state.snapshot?.entities ?? state.entities ?? [];
        for (let i = entities.length - 1; i >= 0; i--) {
            const entity = entities[i];

            // Skip food items (only allow transferring fish and plants)
            if (entity.type === 'food' || entity.type === 'plant_nectar') continue;

            // Check if click is within entity bounds
            const left = entity.x - entity.width / 2;
            const right = entity.x + entity.width / 2;
            const top = entity.y - entity.height / 2;
            const bottom = entity.y + entity.height / 2;

            if (worldX >= left && worldX <= right && worldY >= top && worldY <= bottom) {
                onEntityClick(entity.id, entity.type);
                return;
            }
        }
    };

    const handleCanvasMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!buildMode || buildPlacementActive) return;
        const point = getWorldPoint(event);
        if (!point || !state) return;
        const entities = state.snapshot?.entities ?? state.entities ?? [];
        const objectTypes = new Set(['castle', 'algae_reef', 'protein_grotto', 'decorative_rock']);
        for (let i = entities.length - 1; i >= 0; i -= 1) {
            const entity = entities[i];
            if (!objectTypes.has(entity.type)) continue;
            if (point.worldX >= entity.x && point.worldX <= entity.x + entity.width && point.worldY >= entity.y && point.worldY <= entity.y + entity.height) {
                draggingObjectIdRef.current = entity.id;
                onBuildDragStart?.(entity.id);
                return;
            }
        }
    };

    const handleCanvasMouseUp = (event: React.MouseEvent<HTMLCanvasElement>) => {
        const objectId = draggingObjectIdRef.current;
        if (objectId === null) return;
        const point = getWorldPoint(event);
        draggingObjectIdRef.current = null;
        if (point) onBuildDragEnd?.(objectId, point.worldX, point.worldY);
    };

    const handleCanvasPointerMove = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!buildMode || !onBuildPointerMove) return;
        const point = getWorldPoint(event);
        if (point) onBuildPointerMove(point.worldX, point.worldY);
    };

    // Refs to hold latest state for the animation loop
    const stateRef = useRef(state);
    const imagesLoadedRef = useRef(imagesLoaded);
    const selectedEntityIdRef = useRef(selectedEntityId);
    const pursuitOverlayRef = useRef(pursuitOverlay);
    const targetMemoryOverlayRef = useRef(targetMemoryOverlay);
    const followEntityIdRef = useRef(followEntityId);
    const showEffectsRef = useRef(showEffects);
    const showSoccerRef = useRef(showSoccer);
    const buildGhostRef = useRef(buildGhost);
    const buildModeRef = useRef(buildMode);
    const viewModeRef = useRef(viewMode);
    const worldTypePropRef = useRef(worldTypeProp);

    useEffect(() => {
        stateRef.current = state;
        imagesLoadedRef.current = imagesLoaded;
        selectedEntityIdRef.current = selectedEntityId;
        pursuitOverlayRef.current = pursuitOverlay;
        targetMemoryOverlayRef.current = targetMemoryOverlay;
        followEntityIdRef.current = followEntityId;
        showEffectsRef.current = showEffects;
        showSoccerRef.current = showSoccer;
        buildGhostRef.current = buildGhost;
        buildModeRef.current = buildMode;
        viewModeRef.current = viewMode;
        worldTypePropRef.current = worldTypeProp;
    }, [state, imagesLoaded, selectedEntityId, pursuitOverlay, targetMemoryOverlay, followEntityId, showEffects, showSoccer, viewMode, worldTypeProp, buildGhost, buildMode]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            setErrorOnce('Failed to get canvas 2D context');
            return;
        }

        // Initialize renderers (idempotent)
        initRenderers();

        // Local cache of the active renderer to prevent recreating it on every frame in renderLoop
        let currentRenderer: Renderer | null = null;
        let currentWorldType = '';
        let currentViewMode: 'side' | 'topdown' | '' = '';

        // Initial renderer setup - will be updated in render loop based on state
        const initialWorldType = 'tank'; // Default until state arrives
        const initialViewMode = viewMode || 'side';

        currentRenderer = rendererRegistry.getRenderer(initialWorldType, initialViewMode);
        rendererRef.current = currentRenderer;
        currentWorldType = initialWorldType;
        currentViewMode = initialViewMode;

        // Preload images
        const loadImages = async () => {
            try {
                await ImageLoader.preloadGameImages();
                setImagesLoaded(true); // Triggers re-render to update safe ref
            } catch (err) {
                const msg = `Failed to load images: ${err instanceof Error ? err.message : String(err)}`;
                setErrorOnce(msg);
            }
        };
        loadImages();

        let animationFrameId: number;

        const renderLoop = () => {
            const nowMs = performance.now();
            const currentState = stateRef.current;

            if (currentState && !error) {
                try {
                    // Get fresh renderer for the current mode (use ref to avoid stale closure)
                    // ALWAYS use the prop if provided - never fall back to server world_type
                    // This ensures the frontend toggle controls the renderer, not the server state
                    const worldType = worldTypePropRef.current || 'tank';

                    // Determine effective view mode:
                    // - Tank mode: respects the caller's viewMode prop, which defaults to
                    //   'side' (fish in rectangular tank) but is selectable to 'topdown'
                    //   (genome-driven microbe rendering, see docs/EVOLVABILITY.md sec 3.5)
                    //   via the existing side/topdown override - opt-in only, so the
                    //   out-of-box experience is unchanged.
                    // - Petri/Soccer mode: ALWAYS use 'topdown' view (microbes in circular
                    //   dish). This prevents the confusing case of microbes forced into a
                    //   rectangle if a stale 'side' value ever reaches this branch.
                    let effectiveViewMode: 'side' | 'topdown';
                    if (worldType === 'tank') {
                        effectiveViewMode = viewModeRef.current === 'topdown' ? 'topdown' : 'side';
                    } else {
                        // Petri/Soccer = topdown view
                        effectiveViewMode = 'topdown';
                    }

                    // Only retrieve a new renderer when the worldType or viewMode changes
                    if (!currentRenderer || worldType !== currentWorldType || effectiveViewMode !== currentViewMode) {
                        if (currentRenderer) {
                            if (import.meta.env.DEV) {
                                console.debug('[Canvas] Disposing old Renderer due to mode change:', currentWorldType, currentViewMode);
                            }
                            currentRenderer.dispose();
                        }
                        currentRenderer = rendererRegistry.getRenderer(worldType, effectiveViewMode);
                        rendererRef.current = currentRenderer;
                        currentWorldType = worldType;
                        currentViewMode = effectiveViewMode;
                    }

                    const followTargetId = followEntityIdRef.current;
                    const followTarget = followTargetId !== null && followTargetId !== undefined
                        ? (currentState.snapshot?.entities ?? currentState.entities ?? []).find(
                            (entity) => entity.id === followTargetId
                        )
                        : undefined;
                    const renderCanvas = followTarget
                        ? (followCanvasRef.current ?? document.createElement('canvas'))
                        : canvas;
                    if (followTarget && !followCanvasRef.current) {
                        followCanvasRef.current = renderCanvas;
                    }
                    if (renderCanvas.width !== canvas.width || renderCanvas.height !== canvas.height) {
                        renderCanvas.width = canvas.width;
                        renderCanvas.height = canvas.height;
                    }
                    const renderCtx = followTarget ? renderCanvas.getContext('2d') : ctx;
                    if (!renderCtx) {
                        setErrorOnce('Failed to get follow camera context');
                        return;
                    }

                    currentRenderer.render({
                        worldType,
                        viewMode: effectiveViewMode,
                        snapshot: currentState,
                        options: {
                            showEffects: showEffectsRef.current,
                            buildGhost: buildGhostRef.current,
                            buildMode: buildModeRef.current,
                            showSoccer: showSoccerRef.current,
                            selectedEntityId: selectedEntityIdRef.current,
                            pursuitOverlay: pursuitOverlayRef.current,
                            targetMemoryOverlay: targetMemoryOverlayRef.current,
                        },
                    }, {
                        canvas: renderCanvas,
                        ctx: renderCtx,
                        dpr: window.devicePixelRatio || 1,
                        nowMs
                    });

                    if (followTarget) {
                        const viewport = getFollowViewport(followTarget, canvas.width, canvas.height);
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        ctx.drawImage(
                            renderCanvas,
                            viewport.sourceX,
                            viewport.sourceY,
                            viewport.sourceWidth,
                            viewport.sourceHeight,
                            0,
                            0,
                            canvas.width,
                            canvas.height
                        );
                    }
                } catch (err) {
                    console.error("Render loop error:", err);
                }
            }
            animationFrameId = requestAnimationFrame(renderLoop);
        };

        // Start loop
        animationFrameId = requestAnimationFrame(renderLoop);

        return () => {
            cancelAnimationFrame(animationFrameId);
            if (currentRenderer) {
                if (import.meta.env.DEV) {
                    console.debug('[Canvas] Disposing Renderer');
                }
                currentRenderer.dispose();
                currentRenderer = null;
                rendererRef.current = null;
            }
            if (followCanvasRef.current) {
                followCanvasRef.current.width = 0;
                followCanvasRef.current.height = 0;
                followCanvasRef.current = null;
            }
        };
    }, [width, height, setErrorOnce, error, viewMode]); // Stable dependencies only


    // React dev-mode profiling can accumulate performance entries during long sessions.
    // Render caches are pruned by the renderers and should stay warm between frames.
    useEffect(() => {
        const CLEANUP_INTERVAL_MS = 30_000;

        const interval = setInterval(() => {
            try {
                if (typeof performance !== 'undefined') {
                    performance.clearMeasures?.();
                    performance.clearMarks?.();
                    performance.clearResourceTimings?.();
                }
            } catch {
                // Ignore cleanup errors
            }
        }, CLEANUP_INTERVAL_MS);

        return () => clearInterval(interval);
    }, []);

    if (error) {
        return (
            <div style={{
                width,
                height,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#1a0000',
                color: '#ff5555',
                flexDirection: 'column',
                padding: 20,
                border: '1px solid #ff5555',
                borderRadius: 8,
                boxSizing: 'border-box'
            }}>
                <div style={{ fontWeight: 'bold', marginBottom: 8 }}>Canvas Error</div>
                <div style={{ fontSize: 12, textAlign: 'center', wordBreak: 'break-word' }}>{error}</div>
            </div>
        );
    }

    return (
        <canvas
            ref={canvasRef}
            width={width}
            height={height}
            className="tank-canvas"
            onClick={handleCanvasClick}
            onMouseDown={handleCanvasMouseDown}
            onMouseUp={handleCanvasMouseUp}
            onMouseMove={handleCanvasPointerMove}
            style={{
                cursor: buildMode ? 'crosshair' : onEntityClick ? 'pointer' : 'default',
                ...style,
            }}
        />
    );
}
