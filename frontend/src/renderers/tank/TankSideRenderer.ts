
import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import { Renderer as LegacyRenderer } from '../../utils/renderer';
import type { EntityData } from '../../types/simulation';

export class TankSideRenderer implements Renderer {
    id = "tank-side";
    private legacyRenderer: LegacyRenderer | null = null;
    private currentCtx: CanvasRenderingContext2D | null = null;

    // Tank world dimensions (from core/constants.py & Canvas.tsx)
    private readonly WORLD_WIDTH = 1088;
    private readonly WORLD_HEIGHT = 612;

    dispose() {
        if (this.legacyRenderer) {
            this.legacyRenderer.dispose();
            this.legacyRenderer = null;
        }
        this.currentCtx = null;
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        const state = frame.snapshot;

        // Initialize or re-initialize legacy renderer if context changes
        if (!this.legacyRenderer || this.currentCtx !== ctx) {
            if (this.legacyRenderer) {
                this.legacyRenderer.dispose();
            }
            this.legacyRenderer = new LegacyRenderer(ctx);
            this.currentCtx = ctx;
        }

        const r = this.legacyRenderer;

        // Calculate scale to fit world in canvas
        // This logic matches Canvas.tsx
        const scaleX = canvas.width / this.WORLD_WIDTH;
        const scaleY = canvas.height / this.WORLD_HEIGHT;

        // Collect active poker effect IDs for cleanup
        // Matches Canvas.tsx logic
        const pokerActiveIds = new Set<number>();
        if (state.entities) {
            state.entities.forEach((e: EntityData) => {
                if (e.poker_effect_state && (e.poker_effect_state.status === 'lost' || e.poker_effect_state.status === 'won')) {
                    pokerActiveIds.add(e.id);
                }
            });
        }


        // Prune caches
        if (state.entities) {
            r.pruneEntityFacingCache(state.entities.map((e: EntityData) => e.id), pokerActiveIds);
            r.prunePlantCaches(
                state.entities
                    .filter((e: EntityData) => e.type === 'plant')
                    .map((e: EntityData) => e.id)
            );
        }

        ctx.save();
        try {
            ctx.scale(scaleX, scaleY);

            // Clear background & draw environment
            r.clear(this.WORLD_WIDTH, this.WORLD_HEIGHT, state.stats?.time);

            // Render entities
            if (state.entities) {
                // Read showEffects from frame options (defaults to true if not specified)
                const showEffects = frame.options?.showEffects ?? true;

                state.entities.forEach((entity: EntityData) => {
                    r.renderEntity(entity, state.elapsed_time || 0, state.entities, showEffects);
                });
            }

        } finally {
            ctx.restore();
        }
    }
}
