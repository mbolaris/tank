
import type { Renderer, RenderFrame, RenderContext } from '../../rendering/types';
import { buildTankScene, type TankEntity } from './tankScene';

export class TankTopDownRenderer implements Renderer {
    id = "tank-topdown";

    dispose() {
        // No heavy resources to dispose
    }

    render(frame: RenderFrame, rc: RenderContext) {
        const { ctx, canvas } = rc;
        const scene = buildTankScene(frame.snapshot);
        const options = frame.options ?? {};
        const showEffects = options.showEffects ?? true;

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

            // Draw HUD elements (energy bars) if enabled
            if (showEffects && entity.energy !== undefined && entity.kind === 'fish') {
                const barWidth = Math.max(entity.radius * 2, 20);
                this.drawEnhancedEnergyBar(
                    ctx,
                    entity.x - barWidth / 2,
                    entity.y - entity.radius - 8,
                    barWidth,
                    entity.energy
                );
            }

            // Draw selection ring
            if (options.selectedEntityId === entity.id) {
                ctx.save();
                ctx.strokeStyle = "#fff";
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.arc(entity.x, entity.y, entity.radius + 4, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }

            // Draw poker effects (arrows from loser to winner)
            if (showEffects && entity.poker_effect_state) {
                this.drawPokerEffect(ctx, entity, scene.entities);
            }

            // Draw birth effect
            if (showEffects && entity.birth_effect_timer && entity.birth_effect_timer > 0) {
                this.drawBirthEffect(ctx, entity.x, entity.y, entity.birth_effect_timer);
            }
        });

        ctx.restore();
    }

    private drawPokerEffect(ctx: CanvasRenderingContext2D, entity: TankEntity, allEntities: TankEntity[]) {
        const state = entity.poker_effect_state;
        if (!state) return;

        // Only draw for 'lost' status (Loser draws the arrow pointing to Winner)
        if (state.status === 'lost' && state.target_id !== undefined) {
            const target = allEntities.find(e => e.id === state.target_id);
            if (!target) return;

            // Check distance - if too far, skip rendering
            const dx = target.x - entity.x;
            const dy = target.y - entity.y;
            const distSq = dx * dx + dy * dy;
            if (distSq > 120 * 120) return;

            ctx.save();

            // Draw the main line (solid)
            ctx.beginPath();
            ctx.moveTo(entity.x, entity.y);
            ctx.lineTo(target.x, target.y);

            // Glow effect
            ctx.shadowColor = '#4ade80';
            ctx.shadowBlur = 10;
            ctx.strokeStyle = '#4ade80';
            ctx.lineWidth = 3;
            ctx.stroke();

            // Draw arrow head at Winner (end of arrow)
            const angle = Math.atan2(target.y - entity.y, target.x - entity.x);
            const headLen = 15;

            ctx.setLineDash([]);
            ctx.fillStyle = '#4ade80';
            ctx.beginPath();
            ctx.moveTo(target.x, target.y);
            ctx.lineTo(
                target.x - headLen * Math.cos(angle - Math.PI / 6),
                target.y - headLen * Math.sin(angle - Math.PI / 6)
            );
            ctx.lineTo(
                target.x - headLen * Math.cos(angle + Math.PI / 6),
                target.y - headLen * Math.sin(angle + Math.PI / 6)
            );
            ctx.closePath();
            ctx.fill();

            // Red dot on loser
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#ff0000';
            ctx.beginPath();
            ctx.arc(entity.x, entity.y, 5, 0, Math.PI * 2);
            ctx.fill();

            // Energy amount label
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const midX = (entity.x + target.x) / 2;
            const midY = (entity.y + target.y) / 2;
            ctx.fillText(`${state.amount.toFixed(0)}`, midX, midY - 8);

            ctx.restore();
        } else if (state.status === 'tie') {
            // Draw TIE bubble
            ctx.save();
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
            ctx.beginPath();
            if ((ctx as any).roundRect) {
                (ctx as any).roundRect(entity.x - 25, entity.y - entity.radius - 25, 50, 20, 10);
            } else {
                ctx.rect(entity.x - 25, entity.y - entity.radius - 25, 50, 20);
            }
            ctx.fill();
            ctx.fillStyle = '#fbbf24';
            ctx.font = 'bold 12px Arial';
            ctx.fillText('TIE', entity.x, entity.y - entity.radius - 15);
            ctx.restore();
        }
    }

    private drawBirthEffect(ctx: CanvasRenderingContext2D, x: number, y: number, timerRemaining: number) {
        const maxDuration = 60;
        const progress = 1 - (timerRemaining / maxDuration);

        ctx.save();

        // Particle burst
        if (progress < 0.6) {
            const particleCount = 8;
            const burstProgress = Math.min(1, progress / 0.6);

            for (let i = 0; i < particleCount; i++) {
                const angle = (Math.PI * 2 * i) / particleCount;
                const distance = burstProgress * 25;
                const particleX = x + Math.cos(angle) * distance;
                const particleY = y + Math.sin(angle) * distance;
                const size = 3 * (1 - burstProgress);
                const alpha = (1 - burstProgress) * 0.8;

                const colors = ['#ff69b4', '#ffd700', '#87ceeb', '#98fb98'];
                ctx.globalAlpha = alpha;
                ctx.fillStyle = colors[i % colors.length];
                ctx.beginPath();
                ctx.arc(particleX, particleY, size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        ctx.restore();
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

    private drawEnhancedEnergyBar(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, energy: number) {
        const barHeight = 4;
        const barWidth = width;
        const padding = 1;

        // Background with border
        ctx.save();
        ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        const radius = 2;
        ctx.beginPath();
        if ((ctx as any).roundRect) {
            (ctx as any).roundRect(x, y, barWidth, barHeight, radius);
        } else {
            ctx.rect(x, y, barWidth, barHeight);
        }
        ctx.fill();
        ctx.stroke();

        // Energy bar with gradient
        let colorStart: string, colorEnd: string, glowColor: string;
        if (energy < 30) {
            colorStart = '#ff6b6b';
            colorEnd = '#ef4444';
            glowColor = 'rgba(239, 68, 68, 0.5)';
        } else if (energy < 60) {
            colorStart = '#ffd93d';
            colorEnd = '#fbbf24';
            glowColor = 'rgba(251, 191, 36, 0.5)';
        } else {
            colorStart = '#6bffb8';
            colorEnd = '#4ade80';
            glowColor = 'rgba(74, 222, 128, 0.5)';
        }

        const barFillWidth = Math.max(0, (barWidth - padding * 2) * (energy / 100));

        if (barFillWidth > 0) {
            // Glow effect
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 4;

            // Gradient fill
            const gradient = ctx.createLinearGradient(x, y, x + barFillWidth, y);
            gradient.addColorStop(0, colorStart);
            gradient.addColorStop(1, colorEnd);
            ctx.fillStyle = gradient;

            ctx.beginPath();
            if ((ctx as any).roundRect) {
                (ctx as any).roundRect(x + padding, y + padding, barFillWidth, barHeight - padding * 2, radius - 1);
            } else {
                ctx.rect(x + padding, y + padding, barFillWidth, barHeight - padding * 2);
            }
            ctx.fill();

            // Highlight on top
            ctx.shadowBlur = 0;
            ctx.globalAlpha = 0.4;
            const highlightGradient = ctx.createLinearGradient(x, y, x, y + barHeight / 2);
            highlightGradient.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
            highlightGradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
            ctx.fillStyle = highlightGradient;
            ctx.fillRect(x + padding, y + padding, barFillWidth, barHeight / 3);
        }

        ctx.restore();
    }
}
