import { formatSimulationClock } from './formatSimulationClock';

/**
 * The match clock.
 *
 * While disconnected the frame is simply the last one received, so the value
 * already freezes. `stopped` makes that freeze *visible* and says so in the
 * tooltip - a clock that silently stops reads as a live clock at a standstill.
 */
export function MatchClock({ frame, framesPerSecond = 10, stopped = false }: { frame?: number; framesPerSecond?: number; stopped?: boolean }) {
    const label = formatSimulationClock(frame, framesPerSecond);
    const title = frame === undefined
        ? 'Simulation frame unavailable'
        : stopped
            ? `Clock stopped · last received simulation frame ${frame}`
            : `Simulation frame ${frame}`;
    return (
        <time
            dateTime={frame === undefined ? undefined : `PT${Math.floor(frame / framesPerSecond)}S`}
            title={title}
            data-stopped={stopped ? 'true' : undefined}
        >
            {label}
        </time>
    );
}
