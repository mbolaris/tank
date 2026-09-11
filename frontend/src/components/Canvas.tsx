/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect, useState, useCallback, type CSSProperties } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import type { PursuitOverlayData, TargetMemoryOverlayData, Renderer, ViewMode } from '../rendering/types';
import { rendererRegistry } from '../rendering/registry';
import { initRenderers } from '../renderers/init';
import { ImageLoader } from '../utils/ImageLoader';
import {
    DEFAULT_CAMERA,
    MAX_ZOOM,
    MIN_ZOOM,
    cameraForTarget,
    cameraScreenToWorld,
    getCameraViewport,
    isDefaultCamera,
    panByScreenDelta,
    zoomAtFraction,
    zoomByStep,
    type Camera,
} from './camera';
import { findEntityAtPoint } from './canvasEntityHitTest';
import { fitWorldToContainer, getRenderDpr } from './canvasGeometry';

/** Pointer travel before a press counts as a pan rather than a click. */
const PAN_THRESHOLD_PX = 4;
/** Wheel delta -> zoom factor, via exp() so trackpads and mice both feel linear. */
const WHEEL_ZOOM_SENSITIVITY = 0.0015;
/** Upper bound on how much larger the offscreen buffer may get when zoomed.
 *  Without supersampling, zooming magnifies a canvas-sized bitmap and just
 *  shows bigger pixels; rendering the world into a proportionally larger
 *  buffer is what turns zoom into actual detail.
 *
 *  Held at 2 because the cost is quadratic and measured: a 4x buffer is 16x
 *  the pixels and took the render loop from 37fps to 8fps. A 2x buffer is 4x
 *  the pixels, keeps the range people actually linger in (~1.5-2.5x, close
 *  enough to watch one fish) genuinely sharp, and still beats no
 *  supersampling at the top of the range. */
const MAX_SUPERSAMPLE = 2;
/** Matches canvasGeometry's budget: keep the zoom buffer from exploding. */
const MAX_BUFFER_PIXELS = 12_000_000;

interface CanvasProps {
    state: SimulationUpdate | null;
    width?: number;
    height?: number;
    /**
     * When true, the canvas measures its parent container and sizes its
     * backing store to (container size x devicePixelRatio) instead of a
     * fixed width/height, so it stays crisp at any display size. The
     * width/height props still seed the initial render before the first
     * measurement. Off by default so fixed-size callers (e.g. the small
     * TankThumbnail preview) are unaffected.
     */
    responsive?: boolean;
    /**
     * Opaque value to re-measure the container on, in addition to organic
     * resizes. ResizeObserver alone can be slow (or in some environments
     * never fire) for a size change caused by a CSS class toggle rather
     * than the window itself resizing, so callers whose layout can change
     * discontinuously (e.g. entering/exiting a fullscreen mode) should pass
     * something that changes when that happens, such as the mode flag.
     */
    layoutSignal?: unknown;
    onEntityClick?: (entityId: number, entityType: string) => void;
    /** A deliberate shortcut for watch mode: select and follow a fish. */
    onEntityDoubleClick?: (entityId: number, entityType: string) => void;
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
export function Canvas({ state, width = 800, height = 600, responsive = false, layoutSignal, onEntityClick, onEntityDoubleClick, selectedEntityId, pursuitOverlay, targetMemoryOverlay, followEntityId, showEffects = true, showSoccer = true, style, viewMode = "side", worldType: worldTypeProp, buildMode = false, buildPlacementActive = false, onBuildPlace, onBuildPointerMove, onBuildDragStart, onBuildDragEnd, buildGhost = null }: CanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const rendererRef = useRef<Renderer | null>(null);
    const [imagesLoaded, setImagesLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const followCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const draggingObjectIdRef = useRef<number | null>(null);

    // Backing-store (device pixel) size plus the CSS display size. In
    // non-responsive mode these stay equal to the width/height props,
    // matching the previous fixed-size behavior exactly.
    const [renderSize, setRenderSize] = useState({
        bufferWidth: width,
        bufferHeight: height,
        cssWidth: width,
        cssHeight: height,
        dpr: 1,
    });
    const renderSizeRef = useRef(renderSize);

    useEffect(() => {
        renderSizeRef.current = renderSize;
    }, [renderSize]);

    useEffect(() => {
        if (!responsive) {
            setRenderSize({ bufferWidth: width, bufferHeight: height, cssWidth: width, cssHeight: height, dpr: 1 });
            return;
        }
        const container = containerRef.current;
        if (!container) return;

        const recompute = () => {
            const rect = container.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return;
            const { cssWidth, cssHeight } = fitWorldToContainer(rect.width, rect.height);
            const dpr = getRenderDpr(cssWidth, cssHeight, window.devicePixelRatio);
            setRenderSize({
                bufferWidth: Math.round(cssWidth * dpr),
                bufferHeight: Math.round(cssHeight * dpr),
                cssWidth,
                cssHeight,
                dpr,
            });
        };

        recompute();
        const observer = new ResizeObserver(recompute);
        observer.observe(container);
        return () => observer.disconnect();
        // layoutSignal forces a re-measure for layout changes (e.g. a CSS
        // mode toggle) that don't reliably reach ResizeObserver.
    }, [responsive, width, height, layoutSignal]);

    // Use ref to track if error has been set to avoid repeated setState calls
    const errorSetRef = useRef(false);

    // Stable error setter that only sets once
    const setErrorOnce = useCallback((message: string) => {
        if (!errorSetRef.current) {
            errorSetRef.current = true;
            setError(message);
        }
    }, []);

    // While following a fish, that fish owns the camera: free look stands down
    // rather than fighting it, and the controls hide instead of reporting a
    // zoom the view is not using.
    const following = followEntityId !== null && followEntityId !== undefined;

    // Free-look camera. Kept in a ref for the render loop (which must not
    // re-subscribe every frame) and in state for the reset affordance.
    const [camera, setCamera] = useState<Camera>(DEFAULT_CAMERA);
    const cameraRef = useRef(camera);
    const panOriginRef = useRef<{ x: number; y: number } | null>(null);
    // A drag that moved is a pan, not a click; without this, releasing after
    // dragging the view would also select whatever ended up under the cursor.
    const didPanRef = useRef(false);

    const applyCamera = useCallback((next: (prev: Camera) => Camera) => {
        setCamera((prev) => next(prev));
    }, []);

    /** The camera actually on screen: following a fish overrides free look. */
    const resolveCamera = useCallback((): Camera => {
        const followed = followEntityId !== null && followEntityId !== undefined
            ? (state?.snapshot?.entities ?? state?.entities ?? []).find((entity) => entity.id === followEntityId)
            : undefined;
        return followed ? cameraForTarget(followed) : cameraRef.current;
    }, [followEntityId, state]);

    const getWorldPoint = (event: { clientX: number; clientY: number }) => {
        const canvas = canvasRef.current;
        if (!canvas || !state) return null;
        // One inversion of one transform. When the camera is the default this
        // reduces to the old un-zoomed mapping, which camera.test.ts pins.
        return cameraScreenToWorld(resolveCamera(), event.clientX, event.clientY, canvas.getBoundingClientRect());
    };

    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (didPanRef.current) {
            didPanRef.current = false;
            return;
        }
        if (!state || error) return;
        const point = getWorldPoint(event);
        if (!point) return;
        if (buildMode && buildPlacementActive) {
            onBuildPlace?.(point.worldX, point.worldY);
            return;
        }
        if (!onEntityClick) return;
        const { worldX, worldY } = point;

        const entities = state.snapshot?.entities ?? state.entities ?? [];
        const entity = findEntityAtPoint(entities, worldX, worldY, (candidate) => candidate.type !== 'food' && candidate.type !== 'plant_nectar');
        if (entity) onEntityClick(entity.id, entity.type);
    };

    const handleCanvasDoubleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!state || error || buildMode || !onEntityDoubleClick) return;
        const point = getWorldPoint(event);
        if (!point) return;
        const entities = state.snapshot?.entities ?? state.entities ?? [];
        const fish = findEntityAtPoint(entities, point.worldX, point.worldY, (candidate) => candidate.type === 'fish');
        if (fish) onEntityDoubleClick(fish.id, fish.type);
    };

    const handleCanvasMouseDown = (event: React.MouseEvent<HTMLCanvasElement>) => {
        // Build mode owns left-drag for moving objects, so free-look panning
        // only claims the gesture outside it.
        if (!buildMode && !following && event.button === 0) {
            panOriginRef.current = { x: event.clientX, y: event.clientY };
            didPanRef.current = false;
        }
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

    // Panning tracks the window rather than the canvas: a drag that leaves the
    // tank should keep panning until the button comes up, not stick halfway.
    useEffect(() => {
        const onMove = (event: MouseEvent) => {
            const origin = panOriginRef.current;
            const canvas = canvasRef.current;
            if (!origin || !canvas) return;
            const dx = event.clientX - origin.x;
            const dy = event.clientY - origin.y;
            if (!didPanRef.current && Math.hypot(dx, dy) < PAN_THRESHOLD_PX) return;
            didPanRef.current = true;
            panOriginRef.current = { x: event.clientX, y: event.clientY };
            const rect = canvas.getBoundingClientRect();
            applyCamera((prev) => panByScreenDelta(prev, dx, dy, rect.width, rect.height));
        };
        const onUp = () => {
            panOriginRef.current = null;
        };
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onUp);
        return () => {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onUp);
        };
    }, [applyCamera]);

    // Wheel zoom needs a non-passive listener to stop the page scrolling, which
    // React's onWheel cannot guarantee.
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const onWheel = (event: WheelEvent) => {
            if (following) return;
            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return;
            const factor = Math.exp(-event.deltaY * WHEEL_ZOOM_SENSITIVITY);
            applyCamera((prev) =>
                zoomAtFraction(
                    prev,
                    prev.zoom * factor,
                    (event.clientX - rect.left) / rect.width,
                    (event.clientY - rect.top) / rect.height,
                ),
            );
        };
        canvas.addEventListener('wheel', onWheel, { passive: false });
        return () => canvas.removeEventListener('wheel', onWheel);
    }, [applyCamera, following]);

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
        cameraRef.current = camera;
        showEffectsRef.current = showEffects;
        showSoccerRef.current = showSoccer;
        buildGhostRef.current = buildGhost;
        buildModeRef.current = buildMode;
        viewModeRef.current = viewMode;
        worldTypePropRef.current = worldTypeProp;
    }, [state, imagesLoaded, selectedEntityId, pursuitOverlay, targetMemoryOverlay, followEntityId, camera, showEffects, showSoccer, viewMode, worldTypeProp, buildGhost, buildMode]);

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
                    // Following a fish and free look are the same camera; the
                    // whole-world case still draws straight to the visible
                    // canvas so the common path costs no extra blit.
                    const activeCamera = followTarget ? cameraForTarget(followTarget) : cameraRef.current;
                    const needsViewport = !isDefaultCamera(activeCamera);
                    const renderCanvas = needsViewport
                        ? (followCanvasRef.current ?? document.createElement('canvas'))
                        : canvas;
                    if (needsViewport && !followCanvasRef.current) {
                        followCanvasRef.current = renderCanvas;
                    }
                    // Render the world at zoom resolution so magnifying reveals
                    // detail instead of enlarging pixels, within a pixel budget.
                    const budgetScale = Math.sqrt(
                        MAX_BUFFER_PIXELS / Math.max(1, canvas.width * canvas.height)
                    );
                    const superSample = needsViewport
                        ? Math.max(1, Math.min(activeCamera.zoom, MAX_SUPERSAMPLE, budgetScale))
                        : 1;
                    const bufferWidth = Math.round(canvas.width * superSample);
                    const bufferHeight = Math.round(canvas.height * superSample);
                    if (renderCanvas.width !== bufferWidth || renderCanvas.height !== bufferHeight) {
                        renderCanvas.width = bufferWidth;
                        renderCanvas.height = bufferHeight;
                    }
                    const renderCtx = needsViewport ? renderCanvas.getContext('2d') : ctx;
                    if (!renderCtx) {
                        setErrorOnce('Failed to get camera render context');
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
                        dpr: renderSizeRef.current.dpr,
                        nowMs
                    });

                    if (needsViewport) {
                        const viewport = getCameraViewport(activeCamera, renderCanvas.width, renderCanvas.height);
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

    const canvasEl = (
        <canvas
            ref={canvasRef}
            width={renderSize.bufferWidth}
            height={renderSize.bufferHeight}
            className="tank-canvas"
            onClick={handleCanvasClick}
            onDoubleClick={handleCanvasDoubleClick}
            onMouseDown={handleCanvasMouseDown}
            onMouseUp={handleCanvasMouseUp}
            onMouseMove={handleCanvasPointerMove}
            style={{
                cursor: buildMode
                    ? 'crosshair'
                    : !isDefaultCamera(camera)
                        ? 'grab'
                        : onEntityClick ? 'pointer' : 'default',
                ...(responsive ? { width: renderSize.cssWidth, height: renderSize.cssHeight } : {}),
                ...style,
            }}
        />
    );

    if (!responsive) return canvasEl;

    const atFullView = isDefaultCamera(camera);
    const zoomButtonStyle: CSSProperties = {
        width: 26,
        height: 26,
        display: 'grid',
        placeItems: 'center',
        border: '1px solid rgba(148, 163, 184, 0.28)',
        borderRadius: 7,
        background: 'rgba(15, 23, 42, 0.72)',
        color: 'var(--color-text-main, #e2e8f0)',
        font: '600 14px/1 var(--font-mono, monospace)',
        cursor: 'pointer',
    };

    return (
        <div
            ref={containerRef}
            style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
            {canvasEl}
            {!following && <div
                // Sits quietly until the view is actually moved; scroll-to-zoom
                // over a canvas is conventional enough to carry discovery.
                style={{
                    position: 'absolute',
                    right: 12,
                    bottom: 12,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: 5,
                    borderRadius: 10,
                    background: 'rgba(2, 6, 23, 0.45)',
                    opacity: atFullView ? 0.45 : 1,
                    transition: 'opacity 140ms ease',
                }}
                data-testid="camera-controls"
            >
                <button
                    type="button"
                    aria-label="Zoom out"
                    style={zoomButtonStyle}
                    disabled={camera.zoom <= MIN_ZOOM}
                    onClick={() => applyCamera((prev) => zoomByStep(prev, 1 / 1.4))}
                >
                    −
                </button>
                <span
                    aria-live="polite"
                    style={{
                        minWidth: 42,
                        textAlign: 'center',
                        color: 'var(--color-text-dim, #94a3b8)',
                        font: '600 11px/1 var(--font-mono, monospace)',
                    }}
                >
                    {camera.zoom.toFixed(1)}×
                </span>
                <button
                    type="button"
                    aria-label="Zoom in"
                    style={zoomButtonStyle}
                    disabled={camera.zoom >= MAX_ZOOM}
                    onClick={() => applyCamera((prev) => zoomByStep(prev, 1.4))}
                >
                    +
                </button>
                <button
                    type="button"
                    aria-label="Reset view"
                    style={{ ...zoomButtonStyle, width: 'auto', padding: '0 9px', fontSize: 11 }}
                    disabled={atFullView}
                    onClick={() => setCamera(DEFAULT_CAMERA)}
                >
                    Reset
                </button>
            </div>}
        </div>
    );
}
