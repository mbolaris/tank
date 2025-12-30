
import { Renderer, ViewMode, WorldType, RenderFrame, RenderContext } from './types';

// Fallback renderer for unsupported views
class FallbackRenderer implements Renderer {
    id = "fallback";

    dispose() { }

    render(_frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        ctx.fillStyle = "#111";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = "#f55";
        ctx.font = "20px monospace";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`No renderer for ${_frame.worldType} / ${_frame.viewMode}`, canvas.width / 2, canvas.height / 2);
    }
}

type RendererFactory = () => Renderer;

class RendererRegistry {
    private factories: Map<string, RendererFactory> = new Map();
    // Cache instantiated renderers: key = "worldType:viewMode"
    private instances: Map<string, Renderer> = new Map();

    register(worldType: WorldType, viewMode: ViewMode, factory: RendererFactory) {
        const key = this.getKey(worldType, viewMode);
        this.factories.set(key, factory);
    }

    getRenderer(worldType: WorldType, viewMode: ViewMode): Renderer {
        const key = this.getKey(worldType, viewMode);

        if (!this.instances.has(key)) {
            const factory = this.factories.get(key);
            if (factory) {
                this.instances.set(key, factory());
            } else {
                return new FallbackRenderer();
            }
        }

        return this.instances.get(key)!;
    }

    // Helper to clear instances if we need to full reset (e.g. hmr)
    reset() {
        this.instances.forEach(r => r.dispose());
        this.instances.clear();
    }

    private getKey(worldType: WorldType, viewMode: ViewMode): string {
        return `${worldType}:${viewMode}`;
    }
}

export const rendererRegistry = new RendererRegistry();
