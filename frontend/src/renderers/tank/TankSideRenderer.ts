
import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import { EntityPositionInterpolator } from '../../rendering/entityPositionInterpolator';
import { Renderer as TankRenderer } from '../../utils/renderer';
import type { EntityData, SimulationUpdate } from '../../types/simulation';

const PLANT_LAYER_FRAME_MS = 1000 / 15;

export class TankSideRenderer implements Renderer {
    id = "tank-side";
    private tankRenderer: TankRenderer | null = null;
    private plantLayerRenderer: TankRenderer | null = null;
    private plantLayerCanvas: HTMLCanvasElement | null = null;
    private plantLayerCtx: CanvasRenderingContext2D | null = null;
    private lastPlantLayerRenderMs = -Infinity;
    private currentCtx: CanvasRenderingContext2D | null = null;
    private lastPrunedEntities: EntityData[] | null = null;
    private positionInterpolator = new EntityPositionInterpolator();

    // Tank world dimensions (from core/constants.py & Canvas.tsx)
    private readonly WORLD_WIDTH = 1088;
    private readonly WORLD_HEIGHT = 612;

    dispose() {
        if (this.tankRenderer) {
            this.tankRenderer.dispose();
            this.tankRenderer = null;
        }
        if (this.plantLayerRenderer) {
            this.plantLayerRenderer.dispose();
            this.plantLayerRenderer = null;
        }
        if (this.plantLayerCanvas) {
            this.plantLayerCanvas.width = 0;
            this.plantLayerCanvas.height = 0;
            this.plantLayerCanvas = null;
        }
        this.plantLayerCtx = null;
        this.lastPlantLayerRenderMs = -Infinity;
        this.currentCtx = null;
        this.lastPrunedEntities = null;
        this.positionInterpolator.reset();
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        const state = frame.snapshot as SimulationUpdate;

        // V1 Schema: Extract data from the required snapshot structure
        const snapshot = state?.snapshot;
        if (!snapshot) {
            return; // No data to render
        }

        const entities: EntityData[] = snapshot.entities ?? [];
        const stats = snapshot.stats;
        const elapsedTime = snapshot.elapsed_time ?? 0;

        // Initialize or re-initialize tank renderer if context changes
        if (!this.tankRenderer || this.currentCtx !== ctx) {
            if (this.tankRenderer) {
                this.tankRenderer.dispose();
            }
            this.tankRenderer = new TankRenderer(ctx);
            this.currentCtx = ctx;
        }

        const r = this.tankRenderer;
        const renderedEntities = this.positionInterpolator.interpolate(entities, rc.nowMs);
        const plantLayer = this.updatePlantLayer(
            renderedEntities,
            elapsedTime,
            frame.options?.showEffects ?? true,
            rc.nowMs
        );

        // Calculate scale to fit world in canvas
        // This logic matches Canvas.tsx
        const scaleX = canvas.width / this.WORLD_WIDTH;
        const scaleY = canvas.height / this.WORLD_HEIGHT;

        // Cache maintenance only needs to run when a new entity snapshot arrives,
        // not on every requestAnimationFrame that redraws the same snapshot.
        if (entities !== this.lastPrunedEntities) {
            const activeEntityIds = new Set<number>();
            const activePlantIds = new Set<number>();
            const pokerActiveIds = new Set<number>();

            entities.forEach((e: EntityData) => {
                activeEntityIds.add(e.id);
                if (e.type === 'plant') {
                    activePlantIds.add(e.id);
                }
                if (e.poker_effect_state && (e.poker_effect_state.status === 'lost' || e.poker_effect_state.status === 'won')) {
                    pokerActiveIds.add(e.id);
                }
            });

            r.pruneEntityFacingCache(activeEntityIds, pokerActiveIds);
            r.prunePlantCaches(activePlantIds);
            this.lastPrunedEntities = entities;
        }

        ctx.save();
        try {
            ctx.scale(scaleX, scaleY);

            // Clear background & draw environment
            // Pass showEffects to control decorative features like light rays
            const showEffects = frame.options?.showEffects ?? true;
            r.clear(this.WORLD_WIDTH, this.WORLD_HEIGHT, stats?.time, showEffects);

            // Render entities
            let plantLayerDrawn = false;
            renderedEntities.forEach((entity: EntityData) => {
                if (entity.type === 'plant' && plantLayer) {
                    if (!plantLayerDrawn) {
                        ctx.drawImage(plantLayer, 0, 0, this.WORLD_WIDTH, this.WORLD_HEIGHT);
                        plantLayerDrawn = true;
                    }
                    return;
                }
                r.renderEntity(entity, elapsedTime, renderedEntities, showEffects);
                this.drawSoccerEffect(ctx, entity);
            });

        } finally {
            ctx.restore();
        }
    }

    private updatePlantLayer(
        entities: EntityData[],
        elapsedTime: number,
        showEffects: boolean,
        nowMs: number
    ): HTMLCanvasElement | null {
        if (typeof document === 'undefined') return null;

        if (!this.plantLayerCanvas) {
            const canvas = document.createElement('canvas');
            canvas.width = this.WORLD_WIDTH;
            canvas.height = this.WORLD_HEIGHT;
            const ctx = canvas.getContext('2d');
            if (!ctx) return null;
            this.plantLayerCanvas = canvas;
            this.plantLayerCtx = ctx;
            this.plantLayerRenderer = new TankRenderer(ctx);
        }

        if (
            this.plantLayerCtx
            && this.plantLayerRenderer
            && nowMs - this.lastPlantLayerRenderMs >= PLANT_LAYER_FRAME_MS
        ) {
            this.plantLayerCtx.clearRect(0, 0, this.WORLD_WIDTH, this.WORLD_HEIGHT);
            for (const entity of entities) {
                if (entity.type === 'plant') {
                    this.plantLayerRenderer.renderEntity(
                        entity,
                        elapsedTime,
                        entities,
                        showEffects
                    );
                }
            }
            this.lastPlantLayerRenderMs = nowMs;
        }

        return this.plantLayerCanvas;
    }

    private drawSoccerEffect(ctx: CanvasRenderingContext2D, entity: EntityData) {
        const soccerState = entity.soccer_effect_state;
        if (!soccerState) return;

        const { type, amount, timer } = soccerState;

        // Calculate fade based on timer (60 frames max)
        // Keep opaque longer (until last 15 frames)
        const opacity = Math.min(1, timer / 15);
        const radius = entity.radius || 16;
        const yOffset = -(entity.height || radius * 2) / 2 - 20 - (60 - timer) * 0.8;

        ctx.save();
        // Translate to entity position (handled by outer scale)
        ctx.translate(entity.x + (entity.width || 0) / 2, entity.y + (entity.height || 0) / 2);

        // Color based on type
        let color = '#00ff00'; // Green for kicks
        let fontSize = 16;

        if (type === 'goal') {
            color = '#ffdd00'; // Gold for goals
            fontSize = 24; // Much larger for goals
        } else if (type === 'progress') {
            color = '#88ff88'; // Light green for progress
        }

        ctx.globalAlpha = opacity;

        // Draw separate stroke and fill with better contrast settings
        ctx.font = `900 ${fontSize}px "Segoe UI", Roboto, Helvetica, Arial, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        // Use shadow for better visibility against any background
        ctx.shadowColor = 'black';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 1;

        const text = `+${Math.round(amount)}`;

        ctx.fillStyle = color;
        ctx.fillText(text, 0, yOffset);

        // Remove shadow for stroke to keep it crisp
        ctx.shadowColor = 'transparent';
        ctx.strokeStyle = 'black';
        ctx.lineWidth = 1.5; // Thinner distinct stroke
        ctx.strokeText(text, 0, yOffset);

        ctx.restore();
    }
}
