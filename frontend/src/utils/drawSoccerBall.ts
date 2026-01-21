/**
 * Shared utility for drawing a realistic soccer ball.
 */

export function drawSoccerBall(
    ctx: CanvasRenderingContext2D,
    x: number,
    y: number,
    radius: number,
    rotationAngle: number = 0
) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(rotationAngle);

    // 1. Drop Shadow (for depth perception)
    ctx.shadowColor = "rgba(0,0,0,0.3)";
    ctx.shadowBlur = radius * 0.4;
    ctx.shadowOffsetX = radius * 0.1;
    ctx.shadowOffsetY = radius * 0.1;

    // 2. White Base (The ball itself)
    const gradient = ctx.createRadialGradient(
        -radius * 0.2, -radius * 0.3, radius * 0.2, // Highlight source
        0, 0, radius // Edge
    );
    gradient.addColorStop(0, "#ffffff");      // Bright highlight
    gradient.addColorStop(0.8, "#eeeeee");    // Base white
    gradient.addColorStop(1, "#cccccc");      // Shadowed edge

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.fill();

    // Reset shadow for internal patterns to avoid double-shadowing
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    // 3. Black Pentagons (The classic pattern)
    // We draw a central pentagon and parts of surrounding hexagons/pentagons
    // warped slightly to simulate spherical surface.

    ctx.fillStyle = "#222222"; // Dark gray/black

    // Central Pentagon
    const sideLength = radius * 0.35; // Reduced from 0.5
    drawPoly(ctx, 0, 0, sideLength, 5);

    // Surrounding patches (simulating 3D wrap)
    // We draw 5 surrounding shapes at the edges
    for (let i = 0; i < 5; i++) {
        const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2; // Start from top
        const dist = radius * 0.85;
        const px = Math.cos(angle) * dist;
        const py = Math.sin(angle) * dist;

        // Draw slightly distorted patches at the perimeter
        ctx.beginPath();
        ctx.arc(px, py, radius * 0.25, 0, Math.PI * 2); // Reduced from 0.35
        ctx.fill();
    }

    // 4. Subtle Specular Highlight (Glossy finish)
    ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
    ctx.beginPath();
    ctx.ellipse(
        -radius * 0.3, -radius * 0.3,
        radius * 0.4, radius * 0.25,
        Math.PI / 4, 0, Math.PI * 2
    );
    ctx.fill();

    // 5. Crisp Outline
    ctx.strokeStyle = "rgba(0,0,0,0.15)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.stroke();

    ctx.restore();
}

/**
 * Helper to draw a regular polygon
 */
function drawPoly(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, sides: number) {
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
        const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
        const px = x + Math.cos(angle) * radius;
        const py = y + Math.sin(angle) * radius;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
}
