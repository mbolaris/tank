/**
 * Ecosystem statistics component
 * Displays comprehensive energy flow and fish health statistics below the tank simulation
 */

import EnergyEconomyPanel from './EnergyEconomyPanel';
import type { StatsData } from '../types/simulation';

interface EcosystemStatsProps {
    stats: StatsData | null;
}

export function EcosystemStats({ stats }: EcosystemStatsProps) {
    // Use default values if stats is null
    const safeStats = stats ?? ({} as Partial<StatsData>);
    const deathCauseEntries = Object.entries(safeStats.death_causes ?? {});
    const energySources = safeStats.energy_sources ?? {};
    const energyFromNectar = Math.round(safeStats.energy_from_nectar ?? energySources.nectar ?? 0);
    const energyFromLiveFood = Math.round(safeStats.energy_from_live_food ?? energySources.live_food ?? 0);
    const energyFromFallingFood = Math.round(safeStats.energy_from_falling_food ?? energySources.falling_food ?? 0);

    // Energy Sinks Breakdown
    const energyBurnRecent = safeStats.energy_burn_recent ?? {};
    const burnExistence = energyBurnRecent.existence ?? 0;
    const burnMetabolism = energyBurnRecent.metabolism ?? 0;
    const burnTraits = energyBurnRecent.trait_maintenance ?? 0;
    const burnMovement = energyBurnRecent.movement ?? 0;
    // Note: Predation energy is now tracked as death_predation, included in fishDeathEnergyLoss

    // Poker Outflows
    const burnPokerHouseCut = energyBurnRecent.poker_house_cut ?? 0;
    const burnPokerPlantLoss = energyBurnRecent.poker_plant_loss ?? 0;

    // Recent Energy Inflows (New logic to fix discrepancy)
    // We prefer energy_sources_recent (windowed) over energy_sources (lifetime cumulative)
    // to match energyBurnRecent (windowed).
    const energySourcesRecent = safeStats.energy_sources_recent ?? {};

    // New energy flows
    const burnTurning = energyBurnRecent.turning ?? 0;
    const burnMigration = energyBurnRecent.migration ?? 0;

    // Note: burnReproduction and sourceBirth are intentionally not tracked here
    // because reproduction is an internal transfer (parent→baby), not an external flow
    // FIX: Don't fall back to cumulative energySources - only use windowed values
    // energySources contains lifetime totals, which would cause value to spike when
    // there's no recent activity in the windowed period
    const sourceSoupSpawn = Math.round(energySourcesRecent.soup_spawn ?? safeStats.energy_from_soup_spawn ?? 0);
    const sourceMigrationIn = Math.round(
        energySourcesRecent.migration_in ?? safeStats.energy_from_migration_in ?? 0
    );


    // Combined Base Metabolism (Existence + Base Rate)
    const baseLifeSupport = burnExistence + burnMetabolism;

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

                        pokerTotalPot: Math.max(0, pokerLoopVolume),
                        pokerHouseCut: Math.max(0, burnPokerHouseCut),
                        plantPokerNet: plantPokerNetRecent,
                        soupSpawn: Math.max(0, sourceSoupSpawn),
                        migrationIn: Math.max(0, sourceMigrationIn),
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

            {/* Death Causes Card */}
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
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {deathCauseEntries.map(([cause, count]) => (
                            <div key={cause} style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-full)',
                                fontSize: '11px'
                            }}>
                                <span style={{ color: 'var(--color-text-muted)', textTransform: 'capitalize' }}>{cause.replace('_', ' ')}</span>
                                <span style={{ color: '#fca5a5', fontWeight: 600 }}>{count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
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
