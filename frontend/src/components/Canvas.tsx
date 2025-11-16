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
}

export function Canvas({ state, width = 800, height = 600 }: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);
  const [imagesLoaded, setImagesLoaded] = useState(false);

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

    // Clear canvas
    renderer.clear(width, height);

    // Render all entities
    state.entities.forEach((entity) => {
      renderer.renderEntity(entity, state.elapsed_time || 0);
    });
  }, [state, width, height, imagesLoaded]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        border: '2px solid #333',
        borderRadius: '8px',
        backgroundColor: '#1a4d6d',
      }}
    />
  );
}
