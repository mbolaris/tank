import { SizeSummaryGraph, CollapsibleSection } from './ui';
/**
 * Ecosystem statistics component
 * Displays comprehensive energy flow and fish health statistics below the tank simulation
 */

import EnergyEconomyPanel from './EnergyEconomyPanel';
// import SizeHistogram from './ui/SizeHistogram'; // Removed unused import
import type { GeneDistributionEntry, StatsData } from '../types/simulation';

interface EcosystemStatsProps {
    stats: StatsData | null;
}

function normalizeBins(bins: number[] | undefined): number[] {
    if (!bins || bins.length === 0) return [];
    const total = bins.reduce((a, b) => a + b, 0);
    if (total === 0) return bins.map(() => 0);
    return bins.map(b => (b / total) * 100);
}

function legacyPhysicalGeneDistributions(stats: Partial<StatsData>): GeneDistributionEntry[] {
    // Back-compat: build a small set of physical distributions from legacy flat fields
    const mk = (
        key: string,
        label: string,
        bins?: number[],
        bin_edges?: number[],
        min?: number,
        median?: number,
        max?: number,
        allowedMin?: number,
        allowedMax?: number,
        discrete: boolean = false
    ): GeneDistributionEntry => ({
        key,
        label,
        category: 'physical',
        discrete,
        allowed_min: allowedMin ?? 0,
        allowed_max: allowedMax ?? 0,
        min: min ?? 0,
        median: median ?? 0,
        max: max ?? 0,
        bins: bins ?? [],
        bin_edges: bin_edges ?? [],
        meta: {
            mut_rate_mean: (stats as any)[`${key}_mut_rate_mean`] ?? 0,
            mut_rate_std: (stats as any)[`${key}_mut_rate_std`] ?? 0,
            mut_strength_mean: (stats as any)[`${key}_mut_strength_mean`] ?? 0,
            mut_strength_std: (stats as any)[`${key}_mut_strength_std`] ?? 0,
            hgt_prob_mean: (stats as any)[`${key}_hgt_prob_mean`] ?? 0,
            hgt_prob_std: (stats as any)[`${key}_hgt_prob_std`] ?? 0,
        }
    });

    return [
        mk(
            'adult_size',
            'Adult Size',
            stats.adult_size_bins,
            stats.adult_size_bin_edges,
            stats.adult_size_min,
            stats.adult_size_median,
            stats.adult_size_max,
            stats.allowed_adult_size_min,
            stats.allowed_adult_size_max,
        ),
        mk('eye_size', 'Eye Size', stats.eye_size_bins, stats.eye_size_bin_edges, stats.eye_size_min, stats.eye_size_median, stats.eye_size_max, stats.allowed_eye_size_min, stats.allowed_eye_size_max),
        mk('fin_size', 'Fin Size', stats.fin_size_bins, stats.fin_size_bin_edges, stats.fin_size_min, stats.fin_size_median, stats.fin_size_max, stats.allowed_fin_size_min, stats.allowed_fin_size_max),
        mk('tail_size', 'Tail Size', (stats as any).tail_size_bins, (stats as any).tail_size_bin_edges, (stats as any).tail_size_min, (stats as any).tail_size_median, (stats as any).tail_size_max, (stats as any).allowed_tail_size_min, (stats as any).allowed_tail_size_max),
        mk('body_aspect', 'Body Aspect', (stats as any).body_aspect_bins, (stats as any).body_aspect_bin_edges, (stats as any).body_aspect_min, (stats as any).body_aspect_median, (stats as any).body_aspect_max, (stats as any).allowed_body_aspect_min, (stats as any).allowed_body_aspect_max),
        mk('template_id', 'Template', (stats as any).template_id_bins, (stats as any).template_id_bin_edges, (stats as any).template_id_min, (stats as any).template_id_median, (stats as any).template_id_max, (stats as any).allowed_template_id_min, (stats as any).allowed_template_id_max, true),
        mk('pattern_type', 'Pattern', (stats as any).pattern_type_bins, (stats as any).pattern_type_bin_edges, (stats as any).pattern_type_min, (stats as any).pattern_type_median, (stats as any).pattern_type_max, (stats as any).allowed_pattern_type_min, (stats as any).allowed_pattern_type_max, true),
        mk('pattern_intensity', 'Pattern Intensity', (stats as any).pattern_intensity_bins, (stats as any).pattern_intensity_bin_edges, (stats as any).pattern_intensity_min, (stats as any).pattern_intensity_median, (stats as any).pattern_intensity_max, (stats as any).allowed_pattern_intensity_min, (stats as any).allowed_pattern_intensity_max),
        mk('lifespan_modifier', 'Lifespan Mod', (stats as any).lifespan_modifier_bins, (stats as any).lifespan_modifier_bin_edges, (stats as any).lifespan_modifier_min, (stats as any).lifespan_modifier_median, (stats as any).lifespan_modifier_max, (stats as any).allowed_lifespan_modifier_min, (stats as any).allowed_lifespan_modifier_max),
    ];
}

function GeneDistributionPanel({
    title,
    items,
    chartWidth,
    defaultExpanded,
}: {
    title: string;
    items: GeneDistributionEntry[];
    chartWidth: number;
    defaultExpanded?: boolean;
}) {
    const templateLabels = ['Round', 'Torpedo', 'Flat', 'Angular', 'Chubby', 'Eel'];
    const patternLabels = ['Stripe', 'Spots', 'Solid', 'Grad', 'Chevron', 'Scale'];

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
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
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
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                    gap: '16px',
                    marginTop: '8px'
                }}>
                    {items.map((g) => {
                        const integerValues = g.discrete === true;
                        const labels = g.key === 'template_id'
                            ? templateLabels
                            : g.key === 'pattern_type'
                                ? patternLabels
                                : undefined;

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
            </CollapsibleSection>
        </div>
    );
}

export function EcosystemStats({ stats }: EcosystemStatsProps) {
    // Use default values if stats is null
    const safeStats = stats ?? ({} as Partial<StatsData>);
    const deathCauseEntries = Object.entries(safeStats.death_causes ?? {});
    // Recent Energy Inflows - use windowed data for Fish Energy Economy panel
    // This tracks energy CONSUMED BY FISH in the recent time window, not energy spawned into tank
    const energySourcesRecent = safeStats.energy_sources_recent ?? {};
    const energyFromNectar = Math.round(energySourcesRecent.nectar ?? 0);
    const energyFromLiveFood = Math.round(energySourcesRecent.live_food ?? 0);
    const energyFromFallingFood = Math.round(energySourcesRecent.falling_food ?? 0);
    const energyFromAutoEval = Math.round(energySourcesRecent.auto_eval ?? 0);

    // Energy Sinks Breakdown
    const energyBurnRecent = safeStats.energy_burn_recent ?? {};
    const burnExistence = energyBurnRecent.existence ?? 0;
    const burnMetabolism = energyBurnRecent.metabolism ?? 0;
    const burnTraits = energyBurnRecent.trait_maintenance ?? 0;
    const burnMovement = energyBurnRecent.movement ?? 0;
    // Note: Predation energy is now tracked as death_predation, included in fishDeathEnergyLoss

    // Combine base metabolism and existence cost for total life support cost
    const baseLifeSupport = burnMetabolism + burnExistence;

    // Poker Outflows
    const burnPokerHouseCut = energyBurnRecent.poker_house_cut ?? 0;
    const burnPokerPlantLoss = energyBurnRecent.poker_plant_loss ?? 0;

    // New energy flows
    const burnTurning = energyBurnRecent.turning ?? 0;
    const burnMigration = energyBurnRecent.migration ?? 0;

    // Reproduction costs and birth energy (now visible to help users understand energy flow)
    const burnReproduction = energyBurnRecent.reproduction_cost ?? 0;
    const sourceBirth = energySourcesRecent.birth ?? 0;

    // FIX: Don't fall back to cumulative energySources - only use windowed values
    // energySources contains lifetime totals, which would cause value to spike when
    // there's no recent activity in the windowed period
    const sourceSoupSpawn = Math.round(energySourcesRecent.soup_spawn ?? safeStats.energy_from_soup_spawn ?? 0);
    const sourceMigrationIn = Math.round(
        energySourcesRecent.migration_in ?? safeStats.energy_from_migration_in ?? 0
    );

    // Energy delta (true change in fish population energy over window)
    const energyDelta = safeStats.energy_delta;

    // Poker stats - use windowed data for consistency with other energy flows
    // Poker losses tracked in burns, poker wins tracked in sources
    const pokerLossRecent = energyBurnRecent.poker_loss ?? 0;
    const pokerWinRecent = energySourcesRecent.poker_fish ?? 0;
    // Poker loop volume = total energy that flowed through poker (won + lost)
    const pokerLoopVolume = pokerWinRecent + pokerLossRecent;

    // Plant poker net (positive = fish won from plants, negative = fish lost to plants)
    const plantPokerWin = energySourcesRecent.poker_plant ?? 0;
    const plantPokerNetRecent = plantPokerWin - burnPokerPlantLoss;

    const fishDeathEnergyLoss = Math.max(0,
        (energyBurnRecent.death_starvation ?? 0) +
        (energyBurnRecent.death_old_age ?? 0) +
        (energyBurnRecent.death_predation ?? 0) +
        (energyBurnRecent.death_migration ?? 0) +
        (energyBurnRecent.death_unknown ?? 0)
    );

    // Overflow energy that was converted to food drops
    const burnOverflowFood = energyBurnRecent.overflow_food ?? 0;
    // Overflow energy that triggered asexual reproduction (this energy is "consumed")
    const burnOverflowReproduction = energyBurnRecent.overflow_reproduction ?? 0;

    // Fish health distribution
    const fishHealthCritical = safeStats.fish_health_critical ?? 0;
    const fishHealthLow = safeStats.fish_health_low ?? 0;
    const fishHealthHealthy = safeStats.fish_health_healthy ?? 0;
    const fishHealthFull = safeStats.fish_health_full ?? 0;
    const fishCount = safeStats.fish_count || 1; // Prevent division by zero

    // Calculate percentages for health bar
    const criticalPct = (fishHealthCritical / fishCount) * 100;
    const lowPct = (fishHealthLow / fishCount) * 100;
    const healthyPct = (fishHealthHealthy / fishCount) * 100;
    const fullPct = (fishHealthFull / fishCount) * 100;

    // Early return after hooks and calculations
    if (!stats) return null;

    const chartWidth = 280;

    const geneDistributions = safeStats.gene_distributions;
    const physicalGenes = geneDistributions?.physical ?? legacyPhysicalGeneDistributions(safeStats);
    const behavioralGenes = geneDistributions?.behavioral ?? [];

    // Energy source percentages
    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {/* Fish Energy Status Card */}
            <div className="glass-panel" style={{ padding: '12px' }}>
                <h3 style={{
                    margin: '0 0 10px 0',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--color-text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                }}>
                    <span>🐟</span> Fish Energy Status
                </h3>

                {/* Fish Health Distribution Bar */}
                <div style={{ marginBottom: '10px' }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '6px'
                    }}>
                        <span style={{
                            fontSize: '18px',
                            fontWeight: '700',
                            color: 'var(--color-text-main)',
                            letterSpacing: '-0.02em'
                        }}>
                            {stats.fish_count}
                            <span style={{
                                fontSize: '11px',
                                fontWeight: '500',
                                color: 'var(--color-text-muted)',
                                marginLeft: '4px',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em'
                            }}>Fish</span>
                        </span>
                        <span style={{ fontSize: '10px', color: 'var(--color-text-dim)' }}>Health Distribution</span>
                    </div>
                    <div style={{
                        display: 'flex',
                        height: '12px',
                        borderRadius: '6px',
                        overflow: 'hidden',
                        background: 'rgba(0,0,0,0.3)'
                    }}>
                        {criticalPct > 0 && (
                            <div style={{ width: `${criticalPct}%`, background: '#ef4444', transition: 'width 0.3s' }} title={`Critical: ${fishHealthCritical}`} />
                        )}
                        {lowPct > 0 && (
                            <div style={{ width: `${lowPct}%`, background: '#f97316', transition: 'width 0.3s' }} title={`Low: ${fishHealthLow}`} />
                        )}
                        {healthyPct > 0 && (
                            <div style={{ width: `${healthyPct}%`, background: '#22c55e', transition: 'width 0.3s' }} title={`Healthy: ${fishHealthHealthy}`} />
                        )}
                        {fullPct > 0 && (
                            <div style={{ width: `${fullPct}%`, background: '#3b82f6', transition: 'width 0.3s' }} title={`Full: ${fishHealthFull}`} />
                        )}
                    </div>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '9px',
                        marginTop: '4px',
                        gap: '4px'
                    }}>
                        <HealthLegend color="#ef4444" label="Critical" count={fishHealthCritical} />
                        <HealthLegend color="#f97316" label="Low" count={fishHealthLow} />
                        <HealthLegend color="#22c55e" label="Healthy" count={fishHealthHealthy} />
                        <HealthLegend color="#3b82f6" label="Full" count={fishHealthFull} />
                    </div>
                </div>

                {/* Energy Stats */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <MiniStat label="Total Energy" value={`${Math.round(stats.fish_energy).toLocaleString()}⚡`} />
                    <MiniStat label="Avg/Fish" value={`${Math.round(stats.avg_fish_energy ?? 0)}⚡`} />
                    <MiniStat
                        label="Energy Range"
                        value={`${Math.round(stats.min_fish_energy ?? 0)}-${Math.round(stats.max_fish_energy ?? 0)}`}
                    />
                    <div style={{
                        gridColumn: 'span 2',
                        background: 'rgba(0,0,0,0.2)',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '9px', color: 'var(--color-text-dim)', marginBottom: '2px' }}>Max Energy Capacity (Genetics)</div>
                        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-main)' }}>
                            Range: {Math.round(stats.min_max_energy_capacity ?? 0)}-{Math.round(stats.max_max_energy_capacity ?? 0)} <span style={{ color: 'var(--color-text-dim)', fontWeight: 400 }}>|</span> Median: {Math.round(stats.median_max_energy_capacity ?? 0)}
                        </div>
                    </div>
                    <div style={{
                        background: 'rgba(0,0,0,0.2)',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        textAlign: 'center',
                        display: 'none' // Hidden as moved to Economy Panel
                    }}>
                    </div>
                </div>
            </div>

            {/* Energy Economy Panel (New) */}
            <div style={{ gridRow: 'span 2' }}>
                <EnergyEconomyPanel
                    className=""
                    data={{
                        fallingFood: Math.max(0, energyFromFallingFood),
                        liveFood: Math.max(0, energyFromLiveFood),
                        plantNectar: Math.max(0, energyFromNectar),
                        baseMetabolism: Math.max(0, baseLifeSupport),
                        traitMaintenance: Math.max(0, burnTraits),
                        movementCost: Math.max(0, burnMovement),
                        turningCost: Math.max(0, burnTurning),
                        fishDeaths: fishDeathEnergyLoss,
                        migrationOut: Math.max(0, burnMigration),
                        overflowFood: Math.max(0, burnOverflowFood),
                        overflowReproduction: Math.max(0, burnOverflowReproduction),

                        pokerTotalPot: Math.max(0, pokerLoopVolume),
                        pokerHouseCut: Math.max(0, burnPokerHouseCut),
                        plantPokerNet: plantPokerNetRecent,
                        soupSpawn: Math.max(0, sourceSoupSpawn),
                        migrationIn: Math.max(0, sourceMigrationIn),
                        autoEval: Math.max(0, energyFromAutoEval),

                        // Reproduction (internal transfer, but visible for understanding)
                        reproductionCost: Math.max(0, burnReproduction),
                        birthEnergy: Math.max(0, sourceBirth),

                        // True energy delta
                        energyDelta: energyDelta?.energy_delta ?? 0,
                    }}
                />
            </div>

            {/* Ecosystem Overview Card */}
            <div className="glass-panel" style={{ padding: '12px' }}>
                <h3 style={{
                    margin: '0 0 10px 0',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--color-text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                }}>
                    <span>🌿</span> Ecosystem
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <StatItem label="PLANTS" value={stats.plant_count} subValue={`${Math.round(stats.plant_energy).toLocaleString()}⚡`} color="var(--color-success)" />
                    <StatItem label="FOOD" value={stats.food_count} subValue={`${Math.round(stats.food_energy ?? 0)}⚡`} />
                    <StatItem label="LIVE FOOD" value={stats.live_food_count} subValue={`${Math.round(stats.live_food_energy ?? 0)}⚡`} color="#fbbf24" />
                </div>
            </div>

            {/* Population Card */}
            <div className="glass-panel" style={{ padding: '12px' }}>
                <h3 style={{
                    margin: '0 0 10px 0',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--color-text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                }}>
                    <span>👥</span> Population
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <RowItem label="Generation" value={stats.max_generation ?? stats.generation ?? 0} />
                    <RowItem
                        label="Total Births"
                        value={stats.births}
                        valueColor="var(--color-success)"
                        subValue={`S: ${stats.total_sexual_births ?? 0} / A: ${stats.total_asexual_births ?? 0} / Soup: ${Math.max(0, stats.births - (stats.total_sexual_births ?? 0) - (stats.total_asexual_births ?? 0))}`}
                    />
                    <RowItem label="Total Deaths" value={stats.deaths} valueColor="var(--color-danger)" />
                </div>
            </div>

            {/* Death Causes Card - next to Population */}
            {deathCauseEntries.length > 0 && (
                <div className="glass-panel" style={{ padding: '12px' }}>
                    <h3 style={{
                        margin: '0 0 10px 0',
                        fontSize: '12px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        color: 'var(--color-text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                    }}>
                        <span>💀</span> Mortality
                    </h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {deathCauseEntries.map(([cause, count]) => (
                            <div key={cause} style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                border: '1px solid rgba(239, 68, 68, 0.25)',
                                padding: '4px 10px',
                                borderRadius: 'var(--radius-full)',
                                fontSize: '11px'
                            }}>
                                <span style={{ color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>{cause.replace('_', ' ')}</span>
                                <span style={{ color: '#fca5a5', fontWeight: 700 }}>{count.toLocaleString()}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

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
                defaultExpanded={false}
            />
        </div>
    );
}

function HealthLegend({ color, label, count }: { color: string, label: string, count: number }) {
    if (count === 0) return null;
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: color }} />
            <span style={{ color: 'var(--color-text-dim)' }}>{label}</span>
            <span style={{ color: color, fontWeight: 600 }}>{count}</span>
        </div>
    );
}

function MiniStat({ label, value }: { label: string, value: string }) {
    return (
        <div style={{
            background: 'rgba(0,0,0,0.2)',
            padding: '6px 8px',
            borderRadius: '4px',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '9px', color: 'var(--color-text-dim)', marginBottom: '2px' }}>{label}</div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-main)' }}>{value}</div>
        </div>
    );
}

function StatItem({ label, value, subValue, color = 'var(--color-text-main)' }: { label: string, value: string | number, subValue?: string, color?: string }) {
    return (
        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '8px 10px', borderRadius: '6px', width: '100%' }}>
            <div style={{ fontSize: '10px', color: 'var(--color-text-dim)', marginBottom: '2px', textTransform: 'uppercase' }}>{label}</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: color, display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                {value}
                {subValue && <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontWeight: 400 }}>({subValue})</span>}
            </div>
        </div>
    );
}

function RowItem({ label, value, subValue, valueColor = 'var(--color-text-main)' }: { label: string, value: string | number, subValue?: string, valueColor?: string }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>{label}</span>
            <div style={{ textAlign: 'right' }}>
                <span style={{ color: valueColor, fontWeight: 600, fontSize: '14px' }}>{value}</span>
                {subValue && <div style={{ fontSize: '10px', color: 'var(--color-text-dim)' }}>{subValue}</div>}
            </div>
        </div>
    );
}
