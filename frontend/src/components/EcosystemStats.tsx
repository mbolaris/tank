/**
 * Ecosystem statistics component
 * Displays non-poker stats below the tank simulation
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

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {/* Ecosystem Card */}
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
                    <StatItem label="FISH" value={stats.fish_count} subValue={`${Math.round(stats.fish_energy).toLocaleString()}⚡`} color="var(--color-primary)" />
                    <StatItem label="PLANTS" value={stats.plant_count} subValue={`${Math.round(stats.plant_energy).toLocaleString()}⚡`} color="var(--color-success)" />
                    <StatItem label="FOOD" value={stats.food_count} subValue={`${Math.round(stats.food_energy ?? 0)}⚡`} />
                    <StatItem label="LIVE FOOD" value={stats.live_food_count} subValue={`${Math.round(stats.live_food_energy ?? 0)}⚡`} color="#fbbf24" />
                    <div style={{ gridColumn: 'span 2' }}>
                        <StatItem
                            label="🌿 → 🐟 TRANSFER"
                            value={`${pokerTransfer > 0 ? '+' : ''}${Math.round(pokerTransfer).toLocaleString()}⚡`}
                            subValue={`🐟 Hands: ${stats.poker_stats?.total_fish_games ?? 0} • 🌿 Hands: ${stats.poker_stats?.total_plant_games ?? 0}`}
                            color={pokerTransfer >= 0 ? 'var(--color-success)' : 'var(--color-danger)'}
                        />
                    </div>
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

            {/* Energy Origins Card */}
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
                    <span>⚡</span> Fish Energy Sources (Last 10s)
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
                    <StatItem label="Nectar" value={energyFromNectar.toLocaleString()} subValue="🌸" color="#ec4899" />
                    <StatItem label="Live Food" value={energyFromLiveFood.toLocaleString()} subValue="🦐" color="#fbbf24" />
                    <StatItem label="Falling Food" value={energyFromFallingFood.toLocaleString()} subValue="🍽️" color="var(--color-success)" />
                    <StatItem label="Fish Poker" value={energyFromPoker.toLocaleString()} subValue="🐟🃏" color="var(--color-primary)" />
                    <StatItem label="Plant Poker" value={energyFromPokerPlant.toLocaleString()} subValue="🌿🃏" color="#8b5cf6" />
                    <StatItem label="Auto Eval" value={energyFromAutoEval.toLocaleString()} subValue="🏆" color="#8b5cf6" />
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
