
import { describe, it, expect, beforeEach } from 'vitest';
import { rendererRegistry } from './registry';
import { Renderer, RenderFrame, RenderContext } from './types';

class MockRenderer implements Renderer {
    id = "mock";
    dispose() { }
    render() { }
}

describe('RendererRegistry', () => {
    beforeEach(() => {
        rendererRegistry.reset();
    });

    it('should register and retrieve a renderer', () => {
        rendererRegistry.register('tank', 'side', () => new MockRenderer());
        const renderer = rendererRegistry.getRenderer('tank', 'side');
        expect(renderer).toBeDefined();
        expect(renderer.id).toBe('mock');
    });

    it('should return fallback renderer when no match found', () => {
        const renderer = rendererRegistry.getRenderer('unknown', 'side');
        expect(renderer).toBeDefined();
        expect(renderer.id).toBe('fallback');
    });

    it('should cache renderer instances', () => {
        rendererRegistry.register('tank', 'side', () => new MockRenderer());
        const r1 = rendererRegistry.getRenderer('tank', 'side');
        const r2 = rendererRegistry.getRenderer('tank', 'side');
        expect(r1).toBe(r2);
    });
});
