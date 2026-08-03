import { formatSimulationClock } from './formatSimulationClock';

export function MatchClock({ frame, framesPerSecond = 10 }: { frame?: number; framesPerSecond?: number }) {
    const label = formatSimulationClock(frame, framesPerSecond);
    return (
        <time dateTime={frame === undefined ? undefined : `PT${Math.floor(frame / framesPerSecond)}S`} title={frame === undefined ? 'Simulation frame unavailable' : `Simulation frame ${frame}`}>
            {label}
        </time>
    );
}
