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

    useEffect(() => {
        let isMounted = true;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
            setErrorOnce('Failed to get canvas 2D context');
            return;
        }

        // Initialize renderer immediately so we can draw background
        rendererRef.current = new Renderer(ctx);

        // Preload images
        const loadImages = async () => {
            try {
                await ImageLoader.preloadGameImages();
                if (isMounted) {
                    setImagesLoaded(true);
                }
            } catch (err) {
                // Log for debugging but don't break the app - images may load later
                if (isMounted) {
                    setErrorOnce(`Failed to load images: ${err instanceof Error ? err.message : String(err)}`);
                }
            }
        };

        loadImages();

        return () => {
            // Dispose renderer resources on unmount to avoid leaking canvas/context
            isMounted = false;
            if (rendererRef.current) {
                try {
                    rendererRef.current.dispose();
                } catch (e) {
                    // swallow
                }
                rendererRef.current = null;
            }
        };
    }, [setErrorOnce]);

    useEffect(() => {
        if (!state || !rendererRef.current || error) return;

        const renderer = rendererRef.current;
        const ctx = renderer.ctx;

        // Calculate scale to fit the entire world into the canvas
        const scaleX = width / WORLD_WIDTH;
        const scaleY = height / WORLD_HEIGHT;

        // Prevent orientation cache from growing without bound when entities churn
        renderer.pruneEntityFacingCache(state.entities.map((entity) => entity.id));
        // Keep fractal plant caches bounded as plants spawn and despawn
        renderer.prunePlantCaches(
            state.entities
                .filter((entity) => entity.type === 'plant')
                .map((entity) => entity.id)
        );

        // Save context state
        ctx.save();

        try {
            // Apply scale transformation to fit world into canvas
            ctx.scale(scaleX, scaleY);

            // Clear canvas with time-of-day effects (using world dimensions)
            // We can do this even if images aren't loaded yet
            renderer.clear(WORLD_WIDTH, WORLD_HEIGHT, state.stats?.time);

            // Render all entities only if images are loaded
            if (imagesLoaded) {
                state.entities.forEach((entity) => {
                    renderer.renderEntity(entity, state.elapsed_time || 0, state.entities, showEffects);

                    // Highlight selected entity
                    if (selectedEntityId === entity.id) {
                        ctx.strokeStyle = '#3b82f6';
                        ctx.lineWidth = 3;
                        ctx.setLineDash([5, 5]);
                        ctx.strokeRect(
                            entity.x - entity.width / 2 - 5,
                            entity.y - entity.height / 2 - 5,
                            entity.width + 10,
                            entity.height + 10
                        );
                        ctx.setLineDash([]);
                    }
                });
            }
        } catch (err) {
            // Only set error state for persistent issues, not transient rendering glitches
            const message = err instanceof Error ? err.message : String(err);
            setErrorOnce(`Rendering error: ${message}`);
        } finally {
            // Restore context state
            ctx.restore();
        }
    }, [state, width, height, imagesLoaded, selectedEntityId, showEffects, error, setErrorOnce]);

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
                    // eslint-disable-next-line no-console
                    console.debug('[Memory Cleanup] Cleared plant caches and path cache');
                }
            } catch (e) {
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
