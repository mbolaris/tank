export function formatSimulationClock(frame: number | undefined, framesPerSecond = 10): string {
    if (frame === undefined || !Number.isFinite(frame) || frame < 0 || !Number.isFinite(framesPerSecond) || framesPerSecond <= 0) {
        return '--:--';
    }
    const totalSeconds = Math.floor(frame / framesPerSecond);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `SIM ${minutes}:${seconds.toString().padStart(2, '0')}`;
}
