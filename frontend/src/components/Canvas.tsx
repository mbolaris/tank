/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect, useState } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import { Renderer } from '../utils/renderer';
import { ImageLoader } from '../utils/ImageLoader';

interface CanvasProps {
  state: SimulationUpdate | null;
  width?: number;
  height?: number;
  onEntityClick?: (entityId: number, entityType: string) => void;
  selectedEntityId?: number | null;
}

export function Canvas({ state, width = 800, height = 600, onEntityClick, selectedEntityId }: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const [imagesLoaded, setImagesLoaded] = useState(false);

  // Tank world dimensions (from core/constants.py)
  const WORLD_WIDTH = 1088;
  const WORLD_HEIGHT = 612;

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!state || !onEntityClick) return;

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
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Initialize renderer and preload images
    const initRenderer = async () => {
      await ImageLoader.preloadGameImages();
      rendererRef.current = new Renderer(ctx);
      setImagesLoaded(true);
    };

    initRenderer();
  }, []);

  useEffect(() => {
    if (!state || !rendererRef.current || !imagesLoaded) return;

    const renderer = rendererRef.current;
    const ctx = renderer.ctx;

    // Calculate scale to fit the entire world into the canvas
    const scaleX = width / WORLD_WIDTH;
    const scaleY = height / WORLD_HEIGHT;

    // Prevent orientation cache from growing without bound when entities churn
    renderer.pruneEntityFacingCache(state.entities.map((entity) => entity.id));

    // Save context state
    ctx.save();

    // Apply scale transformation to fit world into canvas
    ctx.scale(scaleX, scaleY);

    // Clear canvas with time-of-day effects (using world dimensions)
    renderer.clear(WORLD_WIDTH, WORLD_HEIGHT, state.stats?.time);

    // Render all entities (they're already in world coordinates)
    state.entities.forEach((entity) => {
      renderer.renderEntity(entity, state.elapsed_time || 0);

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

    // Restore context state
    ctx.restore();
  }, [state, width, height, imagesLoaded, selectedEntityId]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="tank-canvas"
      onClick={handleCanvasClick}
      style={{
        cursor: onEntityClick ? 'pointer' : 'default',
      }}
    />
  );
}
