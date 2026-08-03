import { lazy, Suspense } from 'react';
import type { SoccerEventData, SoccerLeagueLiveState } from '../types/simulation';
import { Panel, PanelLoading } from './TankPanel';

const TankSoccerTab = lazy(() => import('./tank_tabs/TankSoccerTab').then((module) => ({ default: module.TankSoccerTab })));

interface TankSoccerPanelProps {
    liveState: SoccerLeagueLiveState | null;
    events: SoccerEventData[];
    currentFrame: number;
    worldId?: string;
    onClose: () => void;
    onOpenArena?: () => void;
}

export function TankSoccerPanel({ liveState, events, currentFrame, worldId, onClose, onOpenArena }: TankSoccerPanelProps) {
    return (
        <Panel title="Soccer League" icon="⚽" onClose={onClose}>
            <Suspense fallback={<PanelLoading />}>
                <TankSoccerTab liveState={liveState} events={events} currentFrame={currentFrame} worldId={worldId} onOpenArena={onOpenArena} />
            </Suspense>
        </Panel>
    );
}
