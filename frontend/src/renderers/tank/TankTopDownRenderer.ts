
import { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import { buildTankScene, TankScene, TankEntity } from './tankScene';

export class TankTopDownRenderer implements Renderer {
    id = "tank-topdown";

    dispose() {
        // No heavy resources to dispose
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        const scene = buildTankScene(frame.snapshot);

        // Clear and fill background
        ctx.fillStyle = "#1a1a2e"; // Dark blue-ish gray
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Calculate scale to fit world
        // Add some padding
        const padding = 20;
        const availWidth = canvas.width - padding * 2;
        const availHeight = canvas.height - padding * 2;

        const scaleX = availWidth / scene.width;
        const scaleY = availHeight / scene.height;
        const scale = Math.min(scaleX, scaleY);

        const offsetX = (canvas.width - scene.width * scale) / 2;
        const offsetY = (canvas.height - scene.height * scale) / 2;

        ctx.save();
        ctx.translate(offsetX, offsetY);
        ctx.scale(scale, scale);

        // Draw World Bounds
        ctx.strokeStyle = "#444";
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, scene.width, scene.height);

        // Draw grid
        ctx.strokeStyle = "#2a2a3e";
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let x = 0; x <= scene.width; x += 100) {
            ctx.moveTo(x, 0);
            ctx.lineTo(x, scene.height);
        }
        for (let y = 0; y <= scene.height; y += 100) {
            ctx.moveTo(0, y);
            ctx.lineTo(scene.width, y);
        }
        ctx.stroke();

        // Draw Entities
        scene.entities.forEach(entity => {
            this.drawEntity(ctx, entity);
        });

        ctx.restore();

        // Draw debug overlay
        ctx.fillStyle = "#fff";
        ctx.font = "12px monospace";
        ctx.fillText(`Top-Down View | Entities: ${scene.entities.length}`, 10, 20);
    }

    private drawEntity(ctx: CanvasRenderingContext2D, entity: TankEntity) {
        ctx.save();
        ctx.translate(entity.x, entity.y);

        // Color based on type
        let color = "#fff";
        switch (entity.kind) {
            case 'fish':
                color = entity.colorHue !== undefined ? `hsl(${entity.colorHue * 360}, 70%, 60%)` : "#3498db";
                break;
            case 'food':
                color = "#2ecc71";
                break;
            case 'plant':
            case 'plant_nectar':
                color = "#27ae60";
                break;
            case 'crab':
                color = "#e74c3c";
                break;
            case 'castle':
                color = "#95a5a6";
                break;
            default:
                color = this.hashColor(entity.kind);
        }

        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(0, 0, entity.radius, 0, Math.PI * 2);
        ctx.fill();

        // Draw heading if available
        if (entity.headingRad !== undefined) {
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(Math.cos(entity.headingRad) * entity.radius, Math.sin(entity.headingRad) * entity.radius);
            ctx.stroke();
        }

        // Selected/Debug ring (optional, maybe check specific ID?)
        // For debugging, print small ID
        if (entity.kind === 'fish') {
            ctx.fillStyle = "#fff";
            ctx.font = `${Math.max(8, entity.radius)}px monospace`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            // ctx.fillText(entity.id.toString().slice(-2), 0, 0); 
        }

        ctx.restore();
    }

    private hashColor(str: string): string {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
        return "#" + "00000".substring(0, 6 - c.length) + c;
    }
}
