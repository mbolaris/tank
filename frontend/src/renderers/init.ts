import { rendererRegistry } from '../rendering/registry';
import type { Renderer, RenderContext, RenderFrame } from '../rendering/types';

let initialized = false;

type RendererLoader = () => Promise<Renderer>;

class LazyRenderer implements Renderer {
    id: string;
    private renderer: Renderer | null = null;
    private loadPromise: Promise<Renderer> | null = null;
    private disposed = false;
    private readonly loader: RendererLoader;

    constructor(id: string, loader: RendererLoader) {
        this.id = id;
        this.loader = loader;
    }

    dispose() {
        this.disposed = true;
        if (this.renderer) {
            this.renderer.dispose();
            this.renderer = null;
        }
    }

    clearPathCache() {
        this.renderer?.clearPathCache?.();
    }

    render(frame: RenderFrame, rc: RenderContext) {
        if (this.renderer) {
            this.renderer.render(frame, rc);
            return;
        }

        this.startLoading();
        drawLoadingFrame(rc, this.id);
    }

    private startLoading() {
        if (this.loadPromise) return;

        this.loadPromise = this.loader().then((renderer) => {
            if (this.disposed) {
                renderer.dispose();
                return renderer;
            }
            this.renderer = renderer;
            return renderer;
        });
    }
}

function drawLoadingFrame({ ctx, canvas }: RenderContext, rendererId: string) {
    ctx.fillStyle = '#07111f';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#8aa3b8';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`Loading ${rendererId} renderer...`, canvas.width / 2, canvas.height / 2);
}

export function initRenderers() {
    if (initialized) return;
    initialized = true;

    rendererRegistry.register(
        'tank',
        'side',
        () =>
            new LazyRenderer('tank-side', async () => {
                const module = await import('./tank/TankSideRenderer');
                return new module.TankSideRenderer();
            })
    );
    rendererRegistry.register(
        'tank',
        'topdown',
        () =>
            new LazyRenderer('tank-topdown', async () => {
                const module = await import('./tank/TankTopDownRenderer');
                return new module.TankTopDownRenderer();
            })
    );
    rendererRegistry.register(
        'petri',
        'topdown',
        () =>
            new LazyRenderer('petri-topdown', async () => {
                const module = await import('./petri/PetriTopDownRenderer');
                return new module.PetriTopDownRenderer();
            })
    );
    rendererRegistry.register(
        'soccer',
        'topdown',
        () =>
            new LazyRenderer('soccer-topdown', async () => {
                const module = await import('./soccer/SoccerTopDownRenderer');
                return new module.SoccerTopDownRenderer();
            })
    );

    console.debug('[Renderer] Registered default renderers');
}
