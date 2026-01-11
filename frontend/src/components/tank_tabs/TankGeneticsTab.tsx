import { PhylogeneticTree } from '../PhylogeneticTree';
import { GeneDistributionPanel } from './GeneDistributionPanel';
import type { StatsData } from '../../types/simulation';
import styles from './TankGeneticsTab.module.css';

interface TankGeneticsTabProps {
    worldId: string | undefined;
    stats: StatsData | null;
}

export function TankGeneticsTab({ worldId, stats }: TankGeneticsTabProps) {
    const geneDistributions = stats?.gene_distributions;
    const physicalGenes = geneDistributions?.physical ?? [];
    const behavioralGenes = geneDistributions?.behavioral ?? [];
    const chartWidth = 280;

    return (
        <div className={styles.geneticsTab}>
            {/* Gene Distributions */}
            <div style={{ display: 'grid', gap: '16px', marginBottom: '16px' }}>
                <GeneDistributionPanel
                    title="Physical Gene Distribution"
                    items={physicalGenes}
                    chartWidth={chartWidth}
                    defaultExpanded={true}
                />

                <GeneDistributionPanel
                    title="Behavioral Gene Distribution"
                    items={behavioralGenes}
                    chartWidth={chartWidth}
                    defaultExpanded={true}
                />
            </div>

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
