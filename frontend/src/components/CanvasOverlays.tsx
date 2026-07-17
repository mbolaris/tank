import type { ConnectionStatus } from '../hooks/useWebSocket';
import type { MetricsHistory } from '../types/simulation';
import { CONNECTION_STATUS_DISPLAY } from '../utils/connectionStatusDisplay';
import { EvolutionHealthReadout } from './EvolutionHealthReadout';
import { LivingWorldToasts } from './LivingWorldToasts';
import { ModeSwitch, type UiMode } from './ModeSwitch';

interface CanvasOverlaysProps {
    connectionStatus: ConnectionStatus;
    watchMode: boolean;
    uiMode: UiMode | null;
    onSelectMode: (mode: UiMode) => void;
    worldId: string | undefined;
    onOpenBoard: () => void;
    metricsHistory: MetricsHistory | null;
    onOpenTrends: () => void;
    livePopulation: number | null;
}

/**
 * Everything that floats over the canvas: connection status, the unified
 * Watch/Build/Analyze mode switch, ambient Living World toasts, and (in
 * Watch Mode) the compact evolution-health badge. Kept out of TankView so
 * canvas-overlay features don't keep growing an already-large component.
 */
export function CanvasOverlays({
    connectionStatus,
    watchMode,
    uiMode,
    onSelectMode,
    worldId,
    onOpenBoard,
    metricsHistory,
    onOpenTrends,
    livePopulation,
}: CanvasOverlaysProps) {
    return (
        <>
            <div className="canvas-glow" aria-hidden />
            <div className="canvas-hud">
                <div className="hud-group">
                    <div className="hud-item">
                        <span
                            className={`status-dot ${connectionStatus}${connectionStatus !== 'live' ? ' animate-pulse' : ''}`}
                            style={{
                                width: 6,
                                height: 6,
                                borderRadius: '50%',
                                background: CONNECTION_STATUS_DISPLAY[connectionStatus].color,
                            }}
                        />
                        {CONNECTION_STATUS_DISPLAY[connectionStatus].label}
                    </div>
                </div>
                <div className="hud-group">
                    <ModeSwitch mode={uiMode} onSelect={onSelectMode} />
                </div>
            </div>
            <LivingWorldToasts worldId={worldId} onOpenBoard={onOpenBoard} />
            {watchMode && (
                <EvolutionHealthReadout compact history={metricsHistory} onOpenTrends={onOpenTrends} livePopulation={livePopulation} />
            )}
        </>
    );
}
