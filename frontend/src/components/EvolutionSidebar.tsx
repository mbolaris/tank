import { memo } from 'react';
import type { MetricsHistory } from '../types/simulation';
import { EvolutionHealthReadout } from './EvolutionHealthReadout';
import { SkillProgressPanel } from './SkillProgressPanel';
import styles from './EvolutionSidebar.module.css';

interface EvolutionSidebarProps {
    history: MetricsHistory | null;
    onOpenTrends: () => void;
    livePopulation: number | null;
    worldId?: string;
}

/**
 * The column beside the aquarium: how the ecosystem is doing, then whether the
 * things living in it are getting better at anything.
 *
 * They belong together because they answer adjacent questions and are read in
 * the same glance - health says the tank is alive, progress says whether that
 * life is going anywhere.
 */
// Memoized: its props change only on user action, a new metrics sample or a
// fish-count change, while TankView re-renders on every WebSocket payload.
export const EvolutionSidebar = memo(function EvolutionSidebar({
    history,
    onOpenTrends,
    livePopulation,
    worldId,
}: EvolutionSidebarProps) {
    return (
        <div className={styles.sidebar}>
            <EvolutionHealthReadout
                history={history}
                onOpenTrends={onOpenTrends}
                livePopulation={livePopulation}
            />
            <SkillProgressPanel worldId={worldId} />
        </div>
    );
});
