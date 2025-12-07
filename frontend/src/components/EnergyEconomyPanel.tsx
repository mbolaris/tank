


interface EnergyFlowData {
    // Sources (In)
    fallingFood: number;
    liveFood: number;
    plantNectar: number;
    birthEnergy: number; // Energy babies are created with (from reproduction)
    soupSpawn: number; // Energy from spontaneous/system fish spawns
    migrationIn: number; // Energy entering tank via fish migration

    // Sinks (Out)
    baseMetabolism: number;
    traitMaintenance: number; // Eyes, fins, etc.
    movementCost: number;
    turningCost: number; // Energy spent on direction changes
    reproductionCost: number; // Energy parents spend creating babies
    fishDeaths: number;
    migrationOut: number; // Energy leaving tank via fish migration

    // Poker Economy (only external flows)
    pokerTotalPot: number;
    pokerHouseCut: number; // Energy lost to house cut
    plantPokerNet: number; // Net fish↔plant transfer (positive = fish won)
}

interface EnergyEconomyPanelProps {
    data: EnergyFlowData;
    className?: string;
}

export function EnergyEconomyPanel({ data, className }: EnergyEconomyPanelProps) {

    // Calculate Totals
    // Treated as Net Flows
    const plantGain = Math.max(0, data.plantPokerNet);
    const plantLoss = Math.max(0, -data.plantPokerNet);

    const totalIn = data.fallingFood + data.liveFood + data.plantNectar + plantGain + data.birthEnergy + data.soupSpawn + data.migrationIn;
    const totalOut = data.baseMetabolism + data.traitMaintenance + data.movementCost + data.turningCost + data.reproductionCost + data.fishDeaths + data.migrationOut + data.pokerHouseCut + plantLoss;
    const netChange = totalIn - totalOut;

    const formatVal = (val: number) => Math.round(val).toLocaleString();

    // Helper for flow bars
    const FlowBar = ({ label, value, color, icon, total, isOut = false }: { label: string, value: number, color: string, icon: string, total: number, isOut?: boolean }) => {
        if (value <= 0) return null;
        const width = Math.min(100, (value / (total || 1)) * 100);

        return (
            <div style={{ marginBottom: '8px', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px', color: 'var(--color-text-dim)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span>{icon}</span> {label}
                    </span>
                    <span style={{ color: isOut ? 'var(--color-danger)' : color, fontWeight: 600, fontSize: '11px' }}>
                        {isOut ? '-' : '+'}{formatVal(value)}⚡
                    </span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{
                        width: `${width}%`,
                        height: '100%',
                        background: color,
                        borderRadius: '3px',
                        transition: 'width 0.5s ease-out',
                        boxShadow: `0 0 8px ${color}40`
                    }} />
                </div>
            </div>
        );
    };

    return (
        <div className={`glass-panel ${className}`} style={{ padding: '16px', position: 'relative', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ margin: 0, fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>🔋</span> Energy Economy
                </h3>
                <div style={{
                    fontSize: '12px',
                    fontWeight: 700,
                    color: netChange >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                    background: netChange >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    padding: '2px 8px',
                    borderRadius: '4px'
                }}>
                    {netChange > 0 ? '+' : ''}{formatVal(netChange)}⚡ Net
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1px 1fr', gap: '16px' }}>

                {/* INFLOWS */}
                <div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '10px', textAlign: 'center' }}>
                        Inflows (+{formatVal(totalIn)})
                    </div>

                    <FlowBar label="Live Food Eaten" value={data.liveFood} color="#22c55e" icon="🦐" total={totalIn} />
                    <FlowBar label="Plant Nectar" value={data.plantNectar} color="#10b981" icon="🌿" total={totalIn} />
                    <FlowBar label="Baby Energy" value={data.birthEnergy} color="#4ade80" icon="👶" total={totalIn} />
                    <FlowBar label="Soup Spawns" value={data.soupSpawn} color="#a3e635" icon="🥣" total={totalIn} />
                    <FlowBar label="Plant Net (Won)" value={plantGain} color="#059669" icon="🎋" total={totalIn} />
                    <FlowBar label="Migration In" value={data.migrationIn} color="#86efac" icon="🛬" total={totalIn} />

                    {/* Empty State */}
                    {totalIn === 0 && <div style={{ fontSize: '11px', color: 'var(--color-text-dim)', textAlign: 'center', padding: '10px' }}>No energy input</div>}
                </div>

                {/* Divider Line */}
                <div style={{ background: 'rgba(255,255,255,0.1)', height: '100%' }} />

                {/* OUTFLOWS */}
                <div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: '10px', textAlign: 'center' }}>
                        Outflows (-{formatVal(totalOut)})
                    </div>

                    <FlowBar label="Base Life Support" value={data.baseMetabolism} color="#60a5fa" icon="❤️" total={totalOut} isOut />
                    <FlowBar label="Trait Upkeep" value={data.traitMaintenance} color="#f472b6" icon="🧬" total={totalOut} isOut />
                    <FlowBar label="Movement" value={data.movementCost} color="#fb7185" icon="💨" total={totalOut} isOut />
                    <FlowBar label="Turning" value={data.turningCost} color="#f97316" icon="🔄" total={totalOut} isOut />
                    <FlowBar label="Reproduction" value={data.reproductionCost} color="#d946ef" icon="🥚" total={totalOut} isOut />
                    <FlowBar label="Deaths" value={data.fishDeaths} color="#ef4444" icon="💀" total={totalOut} isOut />
                    <FlowBar label="Poker House Cut" value={data.pokerHouseCut} color="#94a3b8" icon="🏛️" total={totalOut} isOut />
                    <FlowBar label="Plant Net (Lost)" value={plantLoss} color="#be185d" icon="🥀" total={totalOut} isOut />
                    <FlowBar label="Migration" value={data.migrationOut} color="#8b5cf6" icon="✈️" total={totalOut} isOut />
                </div>
            </div>

            {/* Poker Economy Highlight */}
            {(data.pokerTotalPot > 0) && (
                <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--color-text-dim)' }}>
                        <span>Poker Economy Loop</span>
                        <span>Pot Volume: {formatVal(data.pokerTotalPot)}⚡</span>
                    </div>
                </div>
            )}
        </div>
    );
}

export default EnergyEconomyPanel;
