import type { ResolvedSoccerFieldGeometry } from './fieldGeometry';
import type { PitchTransform } from './usePitchTransform';

const FIELD_GREEN = '#1f7a45';
const FIELD_GREEN_DARK = '#155c38';
const STADIUM_EDGE = '#071c22';
const LINE_COLOR = 'rgba(241, 248, 244, 0.88)';
const GOAL_FILL = 'rgba(241, 248, 244, 0.96)';

/** Draws the non-animated pitch surface in metres using the supplied profile. */
export class StaticFieldLayer {
    private cacheCanvas: HTMLCanvasElement | null = null;
    private cacheKey = '';

    draw(
        ctx: CanvasRenderingContext2D,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
    ): void {
        const { canvas } = ctx;
        const key = this.makeCacheKey(canvas, geometry, transform);
        if (!this.cacheCanvas || this.cacheKey !== key) {
            const cacheCanvas = this.getCacheCanvas(canvas);
            cacheCanvas.width = canvas.width;
            cacheCanvas.height = canvas.height;
            const cacheContext = cacheCanvas.getContext('2d');
            if (!cacheContext) return;
            this.drawStaticGeometry(cacheContext, geometry, transform);
            this.cacheCanvas = cacheCanvas;
            this.cacheKey = key;
        }

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(this.cacheCanvas, 0, 0);
    }

    private getCacheCanvas(canvas: HTMLCanvasElement): HTMLCanvasElement {
        if (this.cacheCanvas) return this.cacheCanvas;
        const cacheCanvas = canvas.ownerDocument.createElement('canvas');
        cacheCanvas.setAttribute('aria-hidden', 'true');
        return cacheCanvas;
    }

    private makeCacheKey(
        canvas: HTMLCanvasElement,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
    ): string {
        return [
            canvas.width,
            canvas.height,
            transform.scale,
            transform.originX,
            transform.originY,
            geometry.profile_id,
            geometry.length,
            geometry.width,
            geometry.goal_width,
            geometry.goal_depth,
            geometry.centre_circle_radius,
            geometry.penalty_area_depth,
            geometry.penalty_area_width,
            geometry.goal_area_depth,
            geometry.goal_area_width,
            geometry.penalty_spot_distance,
            geometry.corner_arc_radius,
        ].join('|');
    }

    private drawStaticGeometry(
        ctx: CanvasRenderingContext2D,
        geometry: ResolvedSoccerFieldGeometry,
        transform: PitchTransform,
    ): void {
        const { canvas } = ctx;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = STADIUM_EDGE;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.save();
        ctx.translate(transform.originX, transform.originY);
        ctx.scale(transform.scale, transform.scale);

        const halfLength = geometry.length / 2;
        const halfWidth = geometry.width / 2;
        const goalPadding = Math.max(geometry.goal_depth * 1.5, 1);

        ctx.fillStyle = '#0d3b31';
        ctx.fillRect(
            -halfLength - goalPadding,
            -halfWidth - goalPadding,
            geometry.length + goalPadding * 2,
            geometry.width + goalPadding * 2,
        );

        const grassGradient = ctx.createLinearGradient(-halfLength, -halfWidth, halfLength, halfWidth);
        grassGradient.addColorStop(0, FIELD_GREEN_DARK);
        grassGradient.addColorStop(0.5, FIELD_GREEN);
        grassGradient.addColorStop(1, FIELD_GREEN_DARK);
        ctx.fillStyle = grassGradient;
        ctx.fillRect(-halfLength, -halfWidth, geometry.length, geometry.width);

        ctx.save();
        ctx.beginPath();
        ctx.rect(-halfLength, -halfWidth, geometry.length, geometry.width);
        ctx.clip();
        const stripeWidth = Math.max(geometry.length / 12, 1);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.035)';
        for (let x = -halfLength; x < halfLength; x += stripeWidth * 2) {
            ctx.fillRect(x, -halfWidth, stripeWidth, geometry.width);
        }
        ctx.restore();

        ctx.strokeStyle = LINE_COLOR;
        ctx.lineWidth = Math.max(0.08, 1.5 / transform.scale);
        ctx.strokeRect(-halfLength, -halfWidth, geometry.length, geometry.width);

        ctx.beginPath();
        ctx.moveTo(0, -halfWidth);
        ctx.lineTo(0, halfWidth);
        ctx.stroke();

        if (geometry.centre_circle_radius > 0) {
            ctx.beginPath();
            ctx.arc(0, 0, geometry.centre_circle_radius, 0, Math.PI * 2);
            ctx.stroke();
            this.drawSpot(ctx, 0, 0, transform);
        }

        this.drawPenaltyArea(ctx, geometry, -1, transform);
        this.drawPenaltyArea(ctx, geometry, 1, transform);
        this.drawGoal(ctx, geometry, -1);
        this.drawGoal(ctx, geometry, 1);

        if (geometry.corner_arc_radius > 0) {
            const r = geometry.corner_arc_radius;
            for (const [x, y, start, end] of [
                [-halfLength, -halfWidth, 0, Math.PI / 2],
                [halfLength, -halfWidth, Math.PI / 2, Math.PI],
                [halfLength, halfWidth, Math.PI, Math.PI * 1.5],
                [-halfLength, halfWidth, Math.PI * 1.5, Math.PI * 2],
            ] as const) {
                ctx.beginPath();
                ctx.arc(x, y, r, start, end);
                ctx.stroke();
            }
        }

        ctx.restore();

        const vignette = ctx.createRadialGradient(
            canvas.width / 2,
            canvas.height / 2,
            Math.min(canvas.width, canvas.height) * 0.25,
            canvas.width / 2,
            canvas.height / 2,
            Math.max(canvas.width, canvas.height) * 0.72,
        );
        vignette.addColorStop(0, 'rgba(0, 0, 0, 0)');
        vignette.addColorStop(1, 'rgba(0, 0, 0, 0.28)');
        ctx.fillStyle = vignette;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    private drawPenaltyArea(
        ctx: CanvasRenderingContext2D,
        geometry: ResolvedSoccerFieldGeometry,
        side: -1 | 1,
        transform: PitchTransform,
    ): void {
        const halfLength = geometry.length / 2;
        const x = side < 0 ? -halfLength : halfLength - geometry.penalty_area_depth;
        const y = -geometry.penalty_area_width / 2;
        if (geometry.penalty_area_depth > 0 && geometry.penalty_area_width > 0) {
            ctx.strokeRect(x, y, geometry.penalty_area_depth, geometry.penalty_area_width);
        }
        const goalX = side < 0 ? -halfLength + geometry.penalty_spot_distance : halfLength - geometry.penalty_spot_distance;
        if (geometry.penalty_spot_distance > 0) this.drawSpot(ctx, goalX, 0, transform);
        if (geometry.goal_area_depth > 0 && geometry.goal_area_width > 0) {
            const goalAreaX = side < 0 ? -halfLength : halfLength - geometry.goal_area_depth;
            ctx.strokeRect(goalAreaX, -geometry.goal_area_width / 2, geometry.goal_area_depth, geometry.goal_area_width);
        }
    }

    private drawSpot(ctx: CanvasRenderingContext2D, x: number, y: number, transform: PitchTransform): void {
        ctx.fillStyle = LINE_COLOR;
        ctx.beginPath();
        ctx.arc(x, y, Math.max(0.12, 2.5 / transform.scale), 0, Math.PI * 2);
        ctx.fill();
    }

    private drawGoal(ctx: CanvasRenderingContext2D, geometry: ResolvedSoccerFieldGeometry, side: -1 | 1): void {
        const x = side < 0 ? -geometry.length / 2 - geometry.goal_depth : geometry.length / 2;
        ctx.fillStyle = GOAL_FILL;
        ctx.strokeStyle = LINE_COLOR;
        ctx.lineWidth = Math.max(0.08, 1.5 / Math.max(ctx.getTransform().a, 1));
        ctx.fillRect(x, -geometry.goal_width / 2, geometry.goal_depth, geometry.goal_width);
        ctx.strokeRect(x, -geometry.goal_width / 2, geometry.goal_depth, geometry.goal_width);
    }
}
