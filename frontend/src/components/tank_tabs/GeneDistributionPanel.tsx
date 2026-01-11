
import { SizeSummaryGraph, CollapsibleSection } from '../ui';
import type { GeneDistributionEntry } from '../../types/simulation';

// Helper function
function normalizeBins(bins: number[] | undefined): number[] {
    if (!bins || bins.length === 0) return [];
    const total = bins.reduce((a, b) => a + b, 0);
    if (total === 0) return bins.map(() => 0);
    return bins.map(b => (b / total) * 100);
}

interface GeneDistributionPanelProps {
    title: string;
    items: GeneDistributionEntry[];
    chartWidth: number;
    defaultExpanded?: boolean;
}

export function GeneDistributionPanel({
    title,
    items,
    chartWidth,
    defaultExpanded,
}: GeneDistributionPanelProps) {
    const templateLabels = ['Round', 'Torpedo', 'Flat', 'Angular', 'Chubby', 'Eel'];
    const patternLabels = ['Stripe', 'Spots', 'Solid', 'Grad', 'Chevron', 'Scale'];

    // Composable Behavior Labels
    const threatLabels = ['Panic', 'Stealth', 'Freeze', 'Erratic'];
    const foodLabels = ['Direct', 'Predict', 'Circle', 'Ambush', 'Zigzag', 'Patrol'];
    const energyLabels = ['Conserv', 'Burst', 'Balance'];
    const socialLabels = ['Solo', 'Loose', 'Tight', 'Follow'];
    const pokerLabels = ['Avoid', 'Passive', 'Opport', 'Aggro'];

    return (
        <div className="glass-panel" style={{ padding: '16px', gridColumn: '1 / -1' }}>
            <CollapsibleSection
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                        <span>{title}</span>
                    </div>
                }
                defaultExpanded={defaultExpanded ?? true}
            >
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                    gap: '16px',
                    marginTop: '8px'
                }}>
                    {items.map((g) => {
                        const integerValues = g.discrete === true;
                        let labels: string[] | undefined;

                        if (g.key === 'template_id') labels = templateLabels;
                        else if (g.key === 'pattern_type') labels = patternLabels;
                        else if (g.key === 'threat_response') labels = threatLabels;
                        else if (g.key === 'food_approach') labels = foodLabels;
                        else if (g.key === 'energy_style') labels = energyLabels;
                        else if (g.key === 'social_mode') labels = socialLabels;
                        else if (g.key === 'poker_engagement') labels = pokerLabels;

                        const meta = g.meta;
                        return (
                            <div key={g.key} className="gene-graph-card" style={{
                                background: 'rgba(0,0,0,0.25)',
                                borderRadius: '8px',
                                padding: '12px',
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center'
                            }}>
                                <SizeSummaryGraph
                                    bins={normalizeBins(g.bins)}
                                    binEdges={g.bin_edges || []}
                                    min={g.min}
                                    median={g.median}
                                    max={g.max}
                                    allowedMin={g.allowed_min}
                                    allowedMax={g.allowed_max}
                                    width={chartWidth}
                                    height={140}
                                    xLabel={g.label}
                                    yLabel="Pop %"
                                    integerValues={integerValues}
                                    labels={labels}
                                    mutationRateMean={meta?.mut_rate_mean}
                                    mutationRateStd={meta?.mut_rate_std}
                                    mutationStrengthMean={meta?.mut_strength_mean}
                                    mutationStrengthStd={meta?.mut_strength_std}
                                    hgtProbMean={meta?.hgt_prob_mean}
                                    hgtProbStd={meta?.hgt_prob_std}
                                />
                            </div>
                        );
                    })}
                </div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
                    <div style={{
                        fontSize: '11px',
                        color: 'rgba(255, 255, 255, 0.6)',
                        fontWeight: 500,
                        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                        background: 'rgba(0,0,0,0.2)',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        border: '1px solid rgba(255,255,255,0.05)'
                    }}>
                        MR: Mutation Rate · MS: Mutation Strength · HP: Horizontal Gene Transfer Prob · Meta-Data Mut Rate: 1%
                    </div>
                </div>
            </CollapsibleSection>
        </div>
    );
}
