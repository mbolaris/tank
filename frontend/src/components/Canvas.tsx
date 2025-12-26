/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect, useState, useCallback, type CSSProperties } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import { Renderer } from '../utils/renderer';
import { clearAllPlantCaches } from '../utils/plant';
import { ImageLoader } from '../utils/ImageLoader';

interface CanvasProps {
    state: SimulationUpdate | null;
    width?: number;
    height?: number;
    onEntityClick?: (entityId: number, entityType: string) => void;
    selectedEntityId?: number | null;
    showEffects?: boolean;
    style?: CSSProperties;
}

// Tank world dimensions (from core/constants.py)
const WORLD_WIDTH = 1088;
const WORLD_HEIGHT = 612;

export function Canvas({ state, width = 800, height = 600, onEntityClick, selectedEntityId, showEffects = true, style }: CanvasProps) {
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
        for (let i = state.entities.length - 1; i >= 0; i--) {
            const entity = state.entities[i];

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

    useEffect(() => {
        stateRef.current = state;
        imagesLoadedRef.current = imagesLoaded;
        selectedEntityIdRef.current = selectedEntityId;
        showEffectsRef.current = showEffects;
    }, [state, imagesLoaded, selectedEntityId, showEffects]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            setErrorOnce('Failed to get canvas 2D context');
            return;
        }

        // Initialize renderer
        if (import.meta.env.DEV) {
            console.debug('[Canvas] Creating new Renderer instance');
        }
        const renderer = new Renderer(ctx);
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
            const currentImagesLoaded = imagesLoadedRef.current;
            const currentSelectedEntityId = selectedEntityIdRef.current;
            const currentShowEffects = showEffectsRef.current;

            if (currentState && !error && rendererRef.current) {
                const r = rendererRef.current;

                // Calculate scale
                const scaleX = width / WORLD_WIDTH;
                const scaleY = height / WORLD_HEIGHT;

                // Prune caches
                r.pruneEntityFacingCache(currentState.entities.map(e => e.id));
                r.prunePlantCaches(
                    currentState.entities
                        .filter(e => e.type === 'plant')
                        .map(e => e.id)
                );

                r.ctx.save();
                try {
                    r.ctx.scale(scaleX, scaleY);
                    r.clear(WORLD_WIDTH, WORLD_HEIGHT, currentState.stats?.time);

                    if (currentImagesLoaded) {
                        currentState.entities.forEach(entity => {
                            r.renderEntity(entity, currentState.elapsed_time || 0, currentState.entities, currentShowEffects);

                            // Highlight selection
                            if (currentSelectedEntityId === entity.id) {
                                r.ctx.strokeStyle = '#3b82f6';
                                r.ctx.lineWidth = 3;
                                r.ctx.setLineDash([5, 5]);
                                r.ctx.strokeRect(
                                    entity.x - entity.width / 2 - 5,
                                    entity.y - entity.height / 2 - 5,
                                    entity.width + 10,
                                    entity.height + 10
                                );
                                r.ctx.setLineDash([]);
                            }
                        });
                    }
                } catch (err) {
                    console.error("Render loop error:", err);
                } finally {
                    r.ctx.restore();
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
    }, [width, height, setErrorOnce, error]); // Stable dependencies only


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
                if (rendererRef.current) {
                    rendererRef.current.clearPathCache();
                }

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
