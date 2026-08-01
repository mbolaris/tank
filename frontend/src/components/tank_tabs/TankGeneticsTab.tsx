import { PhylogeneticTree } from '../PhylogeneticTree';
import { StandingPopulationPanel } from '../StandingPopulationPanel';
import type { StatsData } from '../../types/simulation';
import styles from './TankGeneticsTab.module.css';

interface TankGeneticsTabProps {
    worldId: string | undefined;
    stats?: StatsData | null;
}

export function TankGeneticsTab({ worldId, stats = null }: TankGeneticsTabProps) {
    return (
        <div className={styles.geneticsTab}>
            {/* Living Trait Distributions & Standing Population Panel */}
            <StandingPopulationPanel stats={stats} />

            {/* Phylogenetic Tree */}
            <div className="glass-panel" style={{ padding: '16px', marginTop: '16px' }}>
                <h2 className={styles.sectionTitle}>
                    <span className={styles.sectionIcon}>🧬</span>
                    Phylogenetic Lineage Tree
                </h2>
                <p className={styles.sectionDesc}>
                    Visualize the evolutionary lineage of fish in your tank. The tree shows
                    parent-child relationships and tracks how the population has evolved over time.
                </p>
                <div className={styles.treeContainer}>
                    <PhylogeneticTree worldId={worldId} />
                </div>
            </div>
        </div>
    );
}

