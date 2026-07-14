import type { TargetMemoryOverlayData } from '../rendering/types';

export function drawTargetMemoryOverlay(
    ctx: CanvasRenderingContext2D,
    fishX: number,
    fishY: number,
    overlay: TargetMemoryOverlayData,
    nowMs: number
) {
    const { domain, lastSeenPosition, predictedPosition, confidence, isSwitching } = overlay;
    
    // Determine base color based on domain
    // Food = Minty green, Ball = Soccer golden orange
    const baseColor = domain.toLowerCase() === 'food' ? '#4ade80' : '#ffa726';
    
    // Alpha fades with confidence (min alpha of 0.15 so it doesn't completely disappear when confidence is 0 but still active)
    const alpha = Math.max(0.15, confidence);
    ctx.save();
    
    // 1. Draw last-seen target position (a small dashed circle)
    const [lsX, lsY] = lastSeenPosition;
    ctx.strokeStyle = `rgba(154, 160, 166, ${alpha * 0.7})`; // Soft gray
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.arc(lsX, lsY, 8, 0, Math.PI * 2);
    ctx.stroke();
    
    // Small inner dot for last seen
    ctx.fillStyle = `rgba(154, 160, 166, ${alpha * 0.5})`;
    ctx.beginPath();
    ctx.arc(lsX, lsY, 2, 0, Math.PI * 2);
    ctx.fill();

    // 2. Draw dead-reckoned target position (crosshair / ring at predicted position)
    const [predX, predY] = predictedPosition;
    
    // Draw connecting line between last-seen and predicted position (dead reckoning path)
    ctx.strokeStyle = `rgba(154, 160, 166, ${alpha * 0.3})`;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(lsX, lsY);
    ctx.lineTo(predX, predY);
    ctx.stroke();

    // Draw predicted position crosshair
    ctx.strokeStyle = hexToRgba(baseColor, alpha * 0.8);
    ctx.lineWidth = 2;
    ctx.setLineDash([]);
    
    // Circle at predicted position
    ctx.beginPath();
    ctx.arc(predX, predY, 6, 0, Math.PI * 2);
    ctx.stroke();
    
    // Crosshair ticks
    ctx.beginPath();
    // Horizontal tick
    ctx.moveTo(predX - 10, predY);
    ctx.lineTo(predX + 10, predY);
    // Vertical tick
    ctx.moveTo(predX, predY - 10);
    ctx.lineTo(predX, predY + 10);
    ctx.stroke();

    // 3. Draw current search vector (line/arrow from fish to predicted position)
    const dx = predX - fishX;
    const dy = predY - fishY;
    const dist = Math.hypot(dx, dy);
    
    if (dist > 5) {
        ctx.strokeStyle = hexToRgba(baseColor, alpha * 0.5);
        ctx.lineWidth = 1.5;
        // Dotted/dashed line representing search path
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(fishX, fishY);
        ctx.lineTo(predX, predY);
        ctx.stroke();
        
        // Draw directional arrow along the search line
        const angle = Math.atan2(dy, dx);
        const arrowX = fishX + Math.cos(angle) * (dist * 0.6);
        const arrowY = fishY + Math.sin(angle) * (dist * 0.6);
        
        ctx.save();
        ctx.translate(arrowX, arrowY);
        ctx.rotate(angle);
        ctx.fillStyle = hexToRgba(baseColor, alpha * 0.6);
        ctx.beginPath();
        ctx.moveTo(5, 0);
        ctx.lineTo(-5, -4);
        ctx.lineTo(-5, 4);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    // 4. Draw flash if switching targets
    if (isSwitching) {
        // Expand ripple from predicted/target position
        const speed = 0.005; // speed of animation
        const t = (nowMs * speed) % 1.0; // loops 0 to 1
        const maxRadius = 30;
        const rippleRadius = 5 + t * maxRadius;
        const rippleAlpha = (1.0 - t) * 0.8;
        
        ctx.strokeStyle = `rgba(255, 255, 255, ${rippleAlpha})`;
        ctx.lineWidth = 3;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.arc(predX, predY, rippleRadius, 0, Math.PI * 2);
        ctx.stroke();
        
        // Add a second ripple
        const t2 = ((nowMs * speed) + 0.5) % 1.0;
        const rippleRadius2 = 5 + t2 * maxRadius;
        const rippleAlpha2 = (1.0 - t2) * 0.8;
        ctx.strokeStyle = hexToRgba(baseColor, rippleAlpha2);
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(predX, predY, rippleRadius2, 0, Math.PI * 2);
        ctx.stroke();
    }
    
    ctx.restore();
}

function hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
