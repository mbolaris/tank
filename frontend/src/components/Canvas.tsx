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

    // Find clicked entity (check in reverse order to prioritize entities rendered on top)
    for (let i = state.entities.length - 1; i >= 0; i--) {
      const entity = state.entities[i];

      // Skip food items (only allow transferring fish and plants)
      if (entity.type === 'food' || entity.type === 'nectar') continue;

      // Check if click is within entity bounds
      const left = entity.x - entity.width / 2;
      const right = entity.x + entity.width / 2;
      const top = entity.y - entity.height / 2;
      const bottom = entity.y + entity.height / 2;

      if (clickX >= left && clickX <= right && clickY >= top && clickY <= bottom) {
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

    // Prevent orientation cache from growing without bound when entities churn
    renderer.pruneEntityFacingCache(state.entities.map((entity) => entity.id));

    // Clear canvas with time-of-day effects
    renderer.clear(width, height, state.stats?.time);

    // Render all entities
    state.entities.forEach((entity) => {
      renderer.renderEntity(entity, state.elapsed_time || 0);

      // Highlight selected entity
      if (selectedEntityId === entity.id) {
        renderer.ctx.strokeStyle = '#3b82f6';
        renderer.ctx.lineWidth = 3;
        renderer.ctx.setLineDash([5, 5]);
        renderer.ctx.strokeRect(
          entity.x - entity.width / 2 - 5,
          entity.y - entity.height / 2 - 5,
          entity.width + 10,
          entity.height + 10
        );
        renderer.ctx.setLineDash([]);
      }
    });
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
