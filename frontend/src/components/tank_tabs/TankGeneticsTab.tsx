import { PhylogeneticTree } from '../PhylogeneticTree';
import styles from './TankGeneticsTab.module.css';

interface TankGeneticsTabProps {
    worldId: string | undefined;
}

export function TankGeneticsTab({ worldId }: TankGeneticsTabProps) {
    return (
        <div className={styles.geneticsTab}>
            {/* Phylogenetic Tree */}
            <div className="glass-panel" style={{ padding: '16px' }}>
                <h2 className={styles.sectionTitle}>
                    <span className={styles.sectionIcon}>🧬</span>
                    Phylogenetic Tree
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
