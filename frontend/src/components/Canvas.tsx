/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect, useState, useCallback, type CSSProperties } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import type { Renderer, ViewMode } from '../rendering/types';
import { rendererRegistry } from '../rendering/registry';
import { initRenderers } from '../renderers/init';
import { clearAllPlantCaches } from '../utils/plant';
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

// Selectable entity types (excludes food, nectar, ball, goal zones)
const SELECTABLE_TYPES = new Set(['fish', 'plant', 'crab']);

export function Canvas({ state, width = 800, height = 600, onEntityClick, selectedEntityId, showEffects = true, showSoccer = true, style, viewMode = "side", worldType: worldTypeProp }: CanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const rendererRef = useRef<Renderer | null>(null);
    const [imagesLoaded, setImagesLoaded] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [hoveredEntityId, setHoveredEntityId] = useState<number | null>(null);
    const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

    // Use ref to track if error has been set to avoid repeated setState calls
    const errorSetRef = useRef(false);

    // Stable error setter that only sets once
    const setErrorOnce = useCallback((message: string) => {
        if (!errorSetRef.current) {
            errorSetRef.current = true;
            setError(message);
        }
    }, []);

    // Convert mouse event to world coordinates
    const toWorldCoords = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return null;
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const canvasX = (event.clientX - rect.left) * scaleX;
        const canvasY = (event.clientY - rect.top) * scaleY;
        return {
            worldX: canvasX * (WORLD_WIDTH / width),
            worldY: canvasY * (WORLD_HEIGHT / height),
            clientX: event.clientX,
            clientY: event.clientY,
        };
    }, [width, height]);

    // Hit-test: find the selectable entity at world coordinates
    const hitTest = useCallback((worldX: number, worldY: number) => {
        if (!state) return null;
        const entities = state.snapshot?.entities ?? state.entities ?? [];
        for (let i = entities.length - 1; i >= 0; i--) {
            const entity = entities[i];
            if (!SELECTABLE_TYPES.has(entity.type)) continue;
            const left = entity.x - entity.width / 2;
            const right = entity.x + entity.width / 2;
            const top = entity.y - entity.height / 2;
            const bottom = entity.y + entity.height / 2;
            if (worldX >= left && worldX <= right && worldY >= top && worldY <= bottom) {
                return entity;
            }
        }
        return null;
    }, [state]);

    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!state || !onEntityClick || error) return;
        const coords = toWorldCoords(event);
        if (!coords) return;
        const entity = hitTest(coords.worldX, coords.worldY);
        if (entity) {
            onEntityClick(entity.id, entity.type);
        }
    };

    const handleCanvasMouseMove = useCallback((event: React.MouseEvent<HTMLCanvasElement>) => {
        if (!state || error) return;
        const coords = toWorldCoords(event);
        if (!coords) return;
        const entity = hitTest(coords.worldX, coords.worldY);
        if (entity) {
            setHoveredEntityId(entity.id);
            const label = entity.type.charAt(0).toUpperCase() + entity.type.slice(1);
            setTooltip({ x: coords.clientX, y: coords.clientY, text: `${label} #${entity.id}` });
        } else {
            setHoveredEntityId(null);
            setTooltip(null);
        }
    }, [state, error, toWorldCoords, hitTest]);

    const handleCanvasMouseLeave = useCallback(() => {
        setHoveredEntityId(null);
        setTooltip(null);
    }, []);

    // Refs to hold latest state for the animation loop
    const stateRef = useRef(state);
    const imagesLoadedRef = useRef(imagesLoaded);
    const selectedEntityIdRef = useRef(selectedEntityId);
    const hoveredEntityIdRef = useRef(hoveredEntityId);
    const showEffectsRef = useRef(showEffects);
    const showSoccerRef = useRef(showSoccer);
    const viewModeRef = useRef(viewMode);
    const worldTypePropRef = useRef(worldTypeProp);

    useEffect(() => {
        stateRef.current = state;
        imagesLoadedRef.current = imagesLoaded;
        selectedEntityIdRef.current = selectedEntityId;
        hoveredEntityIdRef.current = hoveredEntityId;
        showEffectsRef.current = showEffects;
        showSoccerRef.current = showSoccer;
        viewModeRef.current = viewMode;
        worldTypePropRef.current = worldTypeProp;
    }, [state, imagesLoaded, selectedEntityId, hoveredEntityId, showEffects, showSoccer, viewMode, worldTypeProp]);

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

        // Initial renderer setup - will be updated in render loop based on state
        const initialWorldType = 'tank'; // Default until state arrives
        const effectiveViewMode = viewMode || 'side';

        const renderer = rendererRegistry.getRenderer(initialWorldType, effectiveViewMode);
        rendererRef.current = renderer;

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
                    const renderer = rendererRegistry.getRenderer(worldType, effectiveViewMode);
                    rendererRef.current = renderer;

                    renderer.render({
                        worldType,
                        viewMode: effectiveViewMode,
                        snapshot: currentState,
                        options: {
                            showEffects: showEffectsRef.current,
                            showSoccer: showSoccerRef.current,
                            selectedEntityId: selectedEntityIdRef.current,
                            hoveredEntityId: hoveredEntityIdRef.current,
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
            if (rendererRef.current) {
                if (import.meta.env.DEV) {
                    console.debug('[Canvas] Disposing Renderer');
                }
                rendererRef.current.dispose();
                rendererRef.current = null;
            }
        };
    }, [width, height, setErrorOnce, error, viewMode]); // Stable dependencies only


    // Periodic memory cleanup to prevent unbounded memory growth during long viewing sessions.
    // This clears plant texture caches and path caches every 30 seconds.
    // Caches will be regenerated on demand - plants may briefly flicker but memory stays bounded.
    useEffect(() => {
        const CLEANUP_INTERVAL_MS = 30_000; // 30 seconds

        const interval = setInterval(() => {
            try {
                // Clear all plant texture and geometry caches
                clearAllPlantCaches();

                // Clear the renderer's path cache
                rendererRef.current?.clearPathCache?.();

                if (import.meta.env.DEV) {
                    console.debug('[Memory Cleanup] Cleared plant caches and path cache');
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
        <div style={{ position: 'relative', display: 'inline-block' }}>
            <canvas
                ref={canvasRef}
                width={width}
                height={height}
                className="tank-canvas"
                onClick={handleCanvasClick}
                onMouseMove={handleCanvasMouseMove}
                onMouseLeave={handleCanvasMouseLeave}
                style={{
                    cursor: hoveredEntityId !== null ? 'pointer' : 'default',
                    ...style,
                }}
            />
            {tooltip && (
                <div
                    style={{
                        position: 'fixed',
                        left: tooltip.x + 12,
                        top: tooltip.y - 28,
                        padding: '4px 10px',
                        background: 'rgba(0, 0, 0, 0.8)',
                        backdropFilter: 'blur(4px)',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: 6,
                        color: '#f1f5f9',
                        fontSize: 12,
                        fontWeight: 600,
                        fontFamily: 'var(--font-main)',
                        pointerEvents: 'none',
                        zIndex: 60,
                        whiteSpace: 'nowrap',
                    }}
                >
                    {tooltip.text}
                </div>
            )}
        </div>
    );
}
