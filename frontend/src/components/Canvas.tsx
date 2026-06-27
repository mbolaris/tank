/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect, useState, useCallback, type CSSProperties } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import type { Renderer, ViewMode } from '../rendering/types';
import { rendererRegistry } from '../rendering/registry';
import { initRenderers } from '../renderers/init';
import { ImageLoader } from '../utils/ImageLoader';

interface CanvasProps {
    state: SimulationUpdate | null;
    width?: number;
    height?: number;
    onEntityClick?: (entityId: number, entityType: string) => void;
    selectedEntityId?: number | null;
    showEffects?: boolean;
    showSoccer?: boolean;
    style?: CSSProperties;
    viewMode?: ViewMode;
    worldType?: string;  // Optional override for renderer selection (e.g., 'petri' for circular dish)
}

// Tank world dimensions (from core/constants.py)
const WORLD_WIDTH = 1088;
const WORLD_HEIGHT = 612;

export function Canvas({ state, width = 800, height = 600, onEntityClick, selectedEntityId, showEffects = true, showSoccer = true, style, viewMode = "side", worldType: worldTypeProp }: CanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<Renderer | null>(null);
    const [imagesLoaded, setImagesLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Use ref to track if error has been set to avoid repeated setState calls
    const errorSetRef = useRef(false);

    // Stable error setter that only sets once
    const setErrorOnce = useCallback((message: string) => {
        if (!errorSetRef.current) {
            errorSetRef.current = true;
            setError(message);
        }
    }, []);

    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!state || !onEntityClick || error) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        // Get click coordinates relative to canvas
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const clickX = (event.clientX - rect.left) * scaleX;
        const clickY = (event.clientY - rect.top) * scaleY;

        // Account for world-to-canvas scaling
        const worldScaleX = WORLD_WIDTH / width;
        const worldScaleY = WORLD_HEIGHT / height;
        const worldX = clickX * worldScaleX;
        const worldY = clickY * worldScaleY;

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

    // Refs to hold latest state for the animation loop
    const stateRef = useRef(state);
    const imagesLoadedRef = useRef(imagesLoaded);
    const selectedEntityIdRef = useRef(selectedEntityId);
    const showEffectsRef = useRef(showEffects);
    const showSoccerRef = useRef(showSoccer);
    const viewModeRef = useRef(viewMode);
    const worldTypePropRef = useRef(worldTypeProp);

    useEffect(() => {
        stateRef.current = state;
        imagesLoadedRef.current = imagesLoaded;
        selectedEntityIdRef.current = selectedEntityId;
        showEffectsRef.current = showEffects;
        showSoccerRef.current = showSoccer;
        viewModeRef.current = viewMode;
        worldTypePropRef.current = worldTypeProp;
    }, [state, imagesLoaded, selectedEntityId, showEffects, showSoccer, viewMode, worldTypeProp]);

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
            const currentState = stateRef.current;

            if (currentState && !error) {
                try {
                    // Get fresh renderer for the current mode (use ref to avoid stale closure)
                    // ALWAYS use the prop if provided - never fall back to server world_type
                    // This ensures the frontend toggle controls the renderer, not the server state
                    const worldType = worldTypePropRef.current || 'tank';

                    // Determine effective view mode:
                    // - Tank mode: ALWAYS use 'side' view (fish in rectangular tank)
                    // - Petri mode: ALWAYS use 'topdown' view (microbes in circular dish)
                    // This prevents the confusing case of microbes in a rectangle.
                    let effectiveViewMode: 'side' | 'topdown';
                    if (worldType === 'tank') {
                        // Tank mode = side view only (fish in rectangle)
                        effectiveViewMode = 'side';
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

                    currentRenderer.render({
                        worldType,
                        viewMode: effectiveViewMode,
                        snapshot: currentState,
                        options: {
                            showEffects: showEffectsRef.current,
                            showSoccer: showSoccerRef.current,
                            selectedEntityId: selectedEntityIdRef.current,
                        },
                    }, {
                        canvas,
                        ctx,
                        dpr: window.devicePixelRatio || 1,
                        nowMs: performance.now()
                    });
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
            style={{
                cursor: onEntityClick ? 'pointer' : 'default',
                ...style,
            }}
        />
    );
}
