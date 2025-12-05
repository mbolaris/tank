/**
 * Ecosystem statistics component
 * Displays comprehensive energy flow and fish health statistics below the tank simulation
 */

import type { StatsData } from '../types/simulation';

interface EcosystemStatsProps {
    stats: StatsData | null;
}

export function EcosystemStats({ stats }: EcosystemStatsProps) {
    if (!stats) return null;

    const deathCauseEntries = Object.entries(stats.death_causes);
    const pokerTransfer = stats.poker_stats?.total_plant_energy_transferred ?? 0;
    const energySources = stats.energy_sources ?? {};
    const energyFromNectar = Math.round(stats.energy_from_nectar ?? energySources.nectar ?? 0);
    const energyFromLiveFood = Math.round(stats.energy_from_live_food ?? energySources.live_food ?? 0);
    const energyFromFallingFood = Math.round(stats.energy_from_falling_food ?? energySources.falling_food ?? 0);
    const energyFromPoker = Math.round(stats.energy_from_poker ?? energySources.poker_fish ?? 0);
    const energyFromPokerPlant = Math.round(stats.energy_from_poker_plant ?? energySources.poker_plant ?? 0);
    const energyFromAutoEval = Math.round(stats.energy_from_auto_eval ?? energySources.auto_eval ?? 0);

    // Calculate totals for energy flow
    const foodSources = energyFromNectar + energyFromLiveFood + energyFromFallingFood;
    const pokerSources = energyFromPoker + energyFromPokerPlant + energyFromAutoEval;
    const netEnergyIn = foodSources + pokerSources;

    // Fish health distribution
    const fishHealthCritical = stats.fish_health_critical ?? 0;
    const fishHealthLow = stats.fish_health_low ?? 0;
    const fishHealthHealthy = stats.fish_health_healthy ?? 0;
    const fishHealthFull = stats.fish_health_full ?? 0;
    const fishCount = stats.fish_count || 1; // Prevent division by zero

    // Calculate percentages for health bar
    const criticalPct = (fishHealthCritical / fishCount) * 100;
    const lowPct = (fishHealthLow / fishCount) * 100;
    const healthyPct = (fishHealthHealthy / fishCount) * 100;
    const fullPct = (fishHealthFull / fishCount) * 100;

    // Energy source percentages
    const totalFood = foodSources || 1;
    const nectarPct = (energyFromNectar / totalFood) * 100;
    const liveFoodPct = (energyFromLiveFood / totalFood) * 100;
    const fallingFoodPct = (energyFromFallingFood / totalFood) * 100;

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
                        fontSize: '10px',
                        color: 'var(--color-text-dim)',
                        marginBottom: '4px'
                    }}>
                        <span>{stats.fish_count} Fish</span>
                        <span>Health Distribution</span>
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
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px' }}>
                    <MiniStat label="Total" value={`${Math.round(stats.fish_energy).toLocaleString()}⚡`} />
                    <MiniStat label="Avg/Fish" value={`${Math.round(stats.avg_fish_energy ?? 0)}⚡`} />
                    <MiniStat
                        label="Range"
                        value={`${Math.round(stats.min_fish_energy ?? 0)}-${Math.round(stats.max_fish_energy ?? 0)}`}
                    />
                </div>
            </div>

            {/* Energy Flow Card (Last 10s) */}
            <div className="glass-panel" style={{ padding: '12px' }}>
                <h3 style={{
                    margin: '0 0 10px 0',
                    fontSize: '12px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    color: 'var(--color-text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>⚡</span> Energy Flow (10s)
                    </span>
                    <span style={{
                        fontSize: '14px',
                        fontWeight: 600,
                        color: netEnergyIn >= 0 ? 'var(--color-success)' : 'var(--color-danger)'
                    }}>
                        {netEnergyIn >= 0 ? '+' : ''}{netEnergyIn.toLocaleString()}⚡
                    </span>
                </h3>

                {/* Food Sources with Visual Bar */}
                <div style={{ marginBottom: '8px' }}>
                    <div style={{
                        fontSize: '10px',
                        color: 'var(--color-text-dim)',
                        marginBottom: '4px',
                        display: 'flex',
                        justifyContent: 'space-between'
                    }}>
                        <span>Food Sources</span>
                        <span style={{ color: 'var(--color-success)' }}>+{foodSources.toLocaleString()}⚡</span>
                    </div>
                    <div style={{
                        display: 'flex',
                        height: '8px',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        background: 'rgba(0,0,0,0.3)',
                        marginBottom: '4px'
                    }}>
                        {nectarPct > 0 && (
                            <div style={{ width: `${nectarPct}%`, background: '#ec4899', transition: 'width 0.3s' }} />
                        )}
                        {liveFoodPct > 0 && (
                            <div style={{ width: `${liveFoodPct}%`, background: '#fbbf24', transition: 'width 0.3s' }} />
                        )}
                        {fallingFoodPct > 0 && (
                            <div style={{ width: `${fallingFoodPct}%`, background: '#22c55e', transition: 'width 0.3s' }} />
                        )}
                    </div>
                    <div style={{ display: 'flex', gap: '8px', fontSize: '9px' }}>
                        <EnergySource icon="🌸" label="Nectar" value={energyFromNectar} color="#ec4899" />
                        <EnergySource icon="🦐" label="Live" value={energyFromLiveFood} color="#fbbf24" />
                        <EnergySource icon="🍽️" label="Pellets" value={energyFromFallingFood} color="#22c55e" />
                    </div>
                </div>

                {/* Poker Sources */}
                <div>
                    <div style={{
                        fontSize: '10px',
                        color: 'var(--color-text-dim)',
                        marginBottom: '4px',
                        display: 'flex',
                        justifyContent: 'space-between'
                    }}>
                        <span>Poker</span>
                        <span style={{ color: pokerSources >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
                            {pokerSources >= 0 ? '+' : ''}{pokerSources.toLocaleString()}⚡
                        </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', fontSize: '9px' }}>
                        <EnergySource icon="🐟🃏" label="vs Fish" value={energyFromPoker} color="var(--color-primary)" signed />
                        <EnergySource icon="🌿🃏" label="vs Plant" value={energyFromPokerPlant} color="#8b5cf6" signed />
                        <EnergySource icon="🏆" label="Auto" value={energyFromAutoEval} color="#8b5cf6" signed />
                    </div>
                </div>
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
                    <StatItem
                        label="🌿→🐟 XFER"
                        value={`${pokerTransfer > 0 ? '+' : ''}${Math.round(pokerTransfer).toLocaleString()}⚡`}
                        subValue={`${stats.poker_stats?.total_plant_games ?? 0} games`}
                        color={pokerTransfer >= 0 ? 'var(--color-success)' : 'var(--color-danger)'}
                    />
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
                        subValue={`S: ${stats.total_sexual_births ?? 0} / A: ${stats.total_asexual_births ?? 0}`}
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

function EnergySource({ icon, label, value, color, signed = false }: {
    icon: string,
    label: string,
    value: number,
    color: string,
    signed?: boolean
}) {
    const displayValue = signed && value > 0 ? `+${value.toLocaleString()}` : value.toLocaleString();
    const displayColor = signed ? (value >= 0 ? 'var(--color-success)' : 'var(--color-danger)') : color;
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span>{icon}</span>
            <span style={{ color: 'var(--color-text-dim)' }}>{label}</span>
            <span style={{ color: displayColor, fontWeight: 600 }}>{displayValue}</span>
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
