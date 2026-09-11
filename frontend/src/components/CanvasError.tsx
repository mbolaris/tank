/** What the tank shows when the 2D context or the render loop could not start.
 *
 * Split out of Canvas.tsx, which had grown past the god-file limit: the canvas
 * module is about drawing the world, and this is the one state where there is
 * no world to draw.
 */
export function CanvasError({
    message,
    width,
    height,
}: {
    message: string;
    width?: number | string;
    height?: number | string;
}) {
    return (
        <div
            style={{
                width,
                height,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#1a0000',
                color: '#ff5555',
                flexDirection: 'column',
                padding: 20,
                border: '1px solid #ff5555',
                borderRadius: 8,
                boxSizing: 'border-box',
            }}
        >
            <div style={{ fontWeight: 'bold', marginBottom: 8 }}>Canvas Error</div>
            <div style={{ fontSize: 12, textAlign: 'center', wordBreak: 'break-word' }}>{message}</div>
        </div>
    );
}
