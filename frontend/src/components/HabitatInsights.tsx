/**
 * HabitatInsights component
 * Explains where fish are clustering and how they are fueling survival & reproduction.
 */

import { useEffect, useRef } from 'react';
import type { EntityData, SimulationUpdate } from '../types/simulation';

const WORLD_WIDTH = 1088;
const WORLD_HEIGHT = 612;

interface HabitatInsightsProps {
    state: SimulationUpdate | null;
}

function averageEnergy(entities: EntityData[]) {
    if (entities.length === 0) return 0;
    const total = entities.reduce((sum, entity) => sum + Math.max(entity.energy ?? 0, 0), 0);
    return total / entities.length;
}

function totalEnergy(entities: EntityData[]) {
    return entities.reduce((sum, entity) => sum + Math.max(entity.energy ?? 0, 0), 0);
}

function formatPercent(value: number) {
    return `${value.toFixed(0)}%`;
}

function formatEnergy(value: number) {
    return `${Math.round(value).toLocaleString()}⚡`;
}

export function HabitatInsights({ state }: HabitatInsightsProps) {
    if (!state || !state.stats) return null;

    const { stats, entities } = state;

    const isHotZone = (entity: EntityData) => entity.x > WORLD_WIDTH * 0.6 && entity.y < WORLD_HEIGHT * 0.4;

    const fish = entities.filter((entity) => entity.type === 'fish');
    const fishInHotZone = fish.filter(isHotZone);
    const fishOutsideHotZone = fish.filter((entity) => !isHotZone(entity));

    const plants = entities.filter((entity) => entity.type === 'plant' || entity.type === 'fractal_plant');
    const nectar = entities.filter((entity) => entity.type === 'plant_nectar');
    const pellets = entities.filter((entity) => entity.type === 'food');
    const liveFood = entities.filter((entity) => entity.type === 'live_food');

    const hotspotPlantCount = plants.filter(isHotZone).length;
    const hotspotNectarCount = nectar.filter(isHotZone).length;
    const hotspotFoodCount = pellets.filter(isHotZone).length + liveFood.filter(isHotZone).length;

    const hotspotEnergy = averageEnergy(fishInHotZone);
    const elsewhereEnergy = averageEnergy(fishOutsideHotZone);
    const hotspotTotalEnergy = totalEnergy(fishInHotZone);

    const prevSnapshot = useRef<{
        frame: number;
        totalEnergy: number;
        hotspotEnergy: number;
        hotspotTotalEnergy: number;
    } | null>(null);

    const totalEnergyInLastWindow =
        (stats.energy_from_nectar ?? 0) +
        (stats.energy_from_live_food ?? 0) +
        (stats.energy_from_falling_food ?? 0) +
        (stats.energy_from_poker ?? 0) +
        (stats.energy_from_poker_plant ?? 0) +
        (stats.energy_from_auto_eval ?? 0);

    const energyPerFish = stats.fish_count > 0 ? totalEnergyInLastWindow / stats.fish_count : 0;
    const birthsVsDeathsDelta = stats.births - stats.deaths;

    const growthSignal = birthsVsDeathsDelta > 0 ? 'population growing' : birthsVsDeathsDelta === 0 ? 'holding steady' : 'declining';

    const totalEnergyDelta =
        prevSnapshot.current && stats.total_energy !== undefined
            ? stats.total_energy - prevSnapshot.current.totalEnergy
            : null;

    const hotspotEnergyDelta =
        prevSnapshot.current && !Number.isNaN(hotspotEnergy)
            ? hotspotEnergy - prevSnapshot.current.hotspotEnergy
            : null;

    const hotspotTotalEnergyDelta =
        prevSnapshot.current && !Number.isNaN(hotspotTotalEnergy)
            ? hotspotTotalEnergy - prevSnapshot.current.hotspotTotalEnergy
            : null;

    const impliedBurn = totalEnergyDelta !== null ? totalEnergyInLastWindow - totalEnergyDelta : null;
    const energyBurnRecent = stats.energy_burn_recent ?? {};
    const movementBurn = energyBurnRecent.movement ?? 0;
    const existenceBurn = energyBurnRecent.existence ?? 0;
    const metabolismBurn = energyBurnRecent.metabolism ?? 0;
    const turningBurn = energyBurnRecent.turning ?? 0;
    const trackedBurnTotal =
        stats.energy_burn_total ??
        Object.entries(energyBurnRecent).reduce(
            (sum, [key, value]) => (key === 'total' ? sum : sum + (value ?? 0)),
            0,
        );
    const unaccountedBurn = impliedBurn !== null ? impliedBurn - trackedBurnTotal : null;

    useEffect(() => {
        prevSnapshot.current = {
            frame: stats.frame,
            totalEnergy: stats.total_energy ?? 0,
            hotspotEnergy,
            hotspotTotalEnergy,
        };
    }, [stats.frame, stats.total_energy, hotspotEnergy, hotspotTotalEnergy]);

    return (
        <div className="glass-panel" style={{ padding: '12px 16px', marginTop: '12px' }}>
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '12px',
                }}
            >
                <h3
                    style={{
                        margin: 0,
                        fontSize: '14px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--color-text-muted)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                    }}
                >
                    <span>🧭</span> Habitat Insight
                </h3>
                <span style={{ color: 'var(--color-text-dim)', fontSize: '12px' }}>
                    Upper-right hotspot explained
                </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px', alignItems: 'stretch' }}>
                <div
                    style={{
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '8px',
                        padding: '12px',
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                        gap: '10px',
                    }}
                >
                    <HotspotChip
                        label="Fish in hotspot"
                        value={`${fishInHotZone.length}/${fish.length || 1}`}
                        detail={formatPercent(fish.length ? (fishInHotZone.length / fish.length) * 100 : 0)}
                    />
                    <HotspotChip
                        label="Avg energy in hotspot"
                        value={formatEnergy(hotspotEnergy)}
                        detail={`per fish • ${formatEnergy(elsewhereEnergy || 0)} elsewhere`}
                    />
                    <HotspotChip
                        label="Total energy in hotspot"
                        value={formatEnergy(hotspotTotalEnergy)}
                        detail={
                            hotspotTotalEnergyDelta !== null
                                ? `${hotspotTotalEnergyDelta >= 0 ? '+' : ''}${Math.round(hotspotTotalEnergyDelta).toLocaleString()}⚡ change`
                                : 'collecting baseline'
                        }
                    />
                    <HotspotChip
                        label="Nearby resources"
                        value={`${hotspotPlantCount} plants`}
                        detail={`${hotspotNectarCount} nectar • ${hotspotFoodCount} food`}
                    />
                    <HotspotChip
                        label="Avg energy change"
                        value={hotspotEnergyDelta !== null ? formatEnergy(hotspotEnergyDelta) : '—'}
                        detail={hotspotEnergyDelta !== null ? 'since last sample' : 'collecting baseline'}
                    />
                </div>

                <div
                    style={{
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '8px',
                        padding: '12px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                    }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Energy intake / fish (last 10s)</span>
                        <span
                            style={{
                                color: energyPerFish >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                                fontWeight: 700,
                            }}
                        >
                            {formatEnergy(energyPerFish)}
                        </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Avg fish reserves</span>
                        <span style={{ color: 'var(--color-text-main)', fontWeight: 700 }}>{formatEnergy(stats.avg_fish_energy ?? 0)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Births vs deaths</span>
                        <span style={{ color: birthsVsDeathsDelta >= 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 700 }}>
                            {stats.births.toLocaleString()} / {stats.deaths.toLocaleString()} ({growthSignal})
                        </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Net tank energy change</span>
                        <span style={{ color: (totalEnergyDelta ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)', fontWeight: 700 }}>
                            {totalEnergyDelta !== null ? `${totalEnergyDelta >= 0 ? '+' : ''}${Math.round(totalEnergyDelta).toLocaleString()}⚡` : '—'}
                        </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Energy burned/transferred</span>
                        <span style={{ color: (impliedBurn ?? 0) >= 0 ? 'var(--color-warning)' : 'var(--color-success)', fontWeight: 700 }}>
                            {impliedBurn !== null
                                ? `${impliedBurn >= 0 ? '' : '-'}${Math.abs(Math.round(impliedBurn)).toLocaleString()}⚡`
                                : '—'}
                        </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Tracked burn (last 10s)</span>
                        <span style={{ color: 'var(--color-text-main)', fontWeight: 700 }}>
                            {formatEnergy(trackedBurnTotal)}
                        </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Breakdown</span>
                        <span style={{ color: 'var(--color-text-muted)', fontSize: '11px', textAlign: 'right', maxWidth: '240px' }}>
                            {`${formatEnergy(existenceBurn)} exist • ${formatEnergy(metabolismBurn + movementBurn)} swim/metab • ${formatEnergy(turningBurn)} turning`}
                        </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>Untracked drain gap</span>
                        <span style={{ color: 'var(--color-warning)', fontWeight: 700 }}>
                            {unaccountedBurn !== null ? `${unaccountedBurn >= 0 ? '' : '-'}${Math.abs(Math.round(unaccountedBurn)).toLocaleString()}⚡` : '—'}
                        </span>
                    </div>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: '12px', margin: '6px 0 0 0' }}>
                        {hotspotPlantCount + hotspotNectarCount + hotspotFoodCount > 0
                            ? 'High nearby nectar/live-food density keeps the hotspot topped up, which supports mating energy thresholds. The "Total energy in hotspot" row shows the sum rising when resources are present, while "Net tank energy" and "Energy burned" confirm the gains come from intake.'
                            : 'The hotspot looks steady because remaining high-energy fish skew the average while lower-energy fish die or leave. With zero nearby resources, the total hotspot energy should drift down (see "Total energy" row) and the burn breakdown shows metabolism + movement are actively draining reserves.'}
                    </p>
                </div>
            </div>
        </div>
    );
}

function HotspotChip({ label, value, detail }: { label: string; value: string; detail: string }) {
    return (
        <div
            style={{
                background: 'rgba(59, 130, 246, 0.08)',
                border: '1px solid rgba(59, 130, 246, 0.2)',
                borderRadius: '8px',
                padding: '10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
                minHeight: '70px',
            }}
        >
            <span style={{ color: 'var(--color-text-dim)', fontSize: '11px' }}>{label}</span>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ color: '#60a5fa', fontWeight: 700, fontSize: '16px' }}>{value}</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '11px' }}>{detail}</span>
            </div>
        </div>
    );
}
