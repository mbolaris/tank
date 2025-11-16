/**
 * Canvas component for rendering the simulation
 */

import { useRef, useEffect } from 'react';
import type { SimulationUpdate } from '../types/simulation';
import { Renderer } from '../utils/renderer';

interface CanvasProps {
  state: SimulationUpdate | null;
  width?: number;
  height?: number;
}

export function Canvas({ state, width = 800, height = 600 }: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<Renderer | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Initialize renderer
    rendererRef.current = new Renderer(ctx);
  }, []);

  useEffect(() => {
    if (!state || !rendererRef.current) return;

    const renderer = rendererRef.current;

    // Clear canvas
    renderer.clear(width, height);

    // Render all entities
    state.entities.forEach((entity) => {
      renderer.renderEntity(entity);
    });
  }, [state, width, height]);

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
