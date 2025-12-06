export interface EnergyFlowData {
    foodAdded: number;
    plantNectar: number;
    fishMetabolism: number;
    fishDeaths: number;
    pokerTotalPot: number;
    pokerHouseCut: number;
}

interface EnergySankeyProps {
    data: EnergyFlowData;
    title?: string;
    subtitle?: string;
}

function formatValue(value: number): string {
    if (!Number.isFinite(value) || value === 0) return '0';
    return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

interface FlowBarProps {
    label: string;
    value: number;
    color: string;
    icon: string;
    isOutflow?: boolean;
}

function FlowBar({ label, value, color, icon, isOutflow = false }: FlowBarProps) {
    if (value <= 0) return null;
    
    return (
        <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            padding: '6px 8px',
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '6px',
            borderLeft: `3px solid ${color}`
        }}>
            <span style={{ fontSize: '14px' }}>{icon}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '10px', color: 'var(--color-text-dim)', textTransform: 'uppercase' }}>
                    {label}
                </div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: color }}>
                    {isOutflow ? '-' : '+'}{formatValue(value)}⚡
                </div>
            </div>
        </div>
    );
}

export function EnergySankey({ data, title = 'Energy Flux', subtitle }: EnergySankeyProps) {
    const totalInflow = data.foodAdded + data.plantNectar;
    const totalOutflow = data.fishMetabolism + data.fishDeaths;
    const pokerNetReturn = data.pokerTotalPot - data.pokerHouseCut;

    return (
        <div style={{ background: 'rgba(15,23,42,0.7)', borderRadius: 12, padding: '12px', height: '100%' }}>
            <div style={{ marginBottom: 8 }}>
                <div style={{ color: 'var(--color-text-muted)', fontSize: 12, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                    ⚡ {title}
                </div>
                {subtitle && <div style={{ color: 'var(--color-text-dim)', fontSize: 11, marginTop: 2 }}>{subtitle}</div>}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {/* Energy Sources (Inflows) */}
                <div>
                    <div style={{ fontSize: '10px', color: 'var(--color-success)', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase' }}>
                        Sources (+{formatValue(totalInflow)}⚡)
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <FlowBar label="User Food" value={data.foodAdded} color="#fbbf24" icon="🥕" />
                        <FlowBar label="Plant Nectar" value={data.plantNectar} color="#22c55e" icon="🌿" />
                    </div>
                </div>

                {/* Poker Economy (Circular Flow) */}
                {data.pokerTotalPot > 0 && (
                    <div>
                        <div style={{ fontSize: '10px', color: '#a855f7', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase' }}>
                            Poker Economy ({pokerNetReturn >= 0 ? '+' : ''}{formatValue(pokerNetReturn)}⚡ net)
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
                            <div style={{ 
                                padding: '6px 8px',
                                background: 'rgba(168, 85, 247, 0.1)',
                                borderRadius: '6px',
                                border: '1px solid rgba(168, 85, 247, 0.3)',
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '10px', color: 'var(--color-text-dim)' }}>Pot</div>
                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#a855f7' }}>
                                    {formatValue(data.pokerTotalPot)}⚡
                                </div>
                            </div>
                            <div style={{ 
                                padding: '6px 8px',
                                background: 'rgba(148, 163, 184, 0.1)',
                                borderRadius: '6px',
                                border: '1px solid rgba(148, 163, 184, 0.3)',
                                textAlign: 'center'
                            }}>
                                <div style={{ fontSize: '10px', color: 'var(--color-text-dim)' }}>House</div>
                                <div style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8' }}>
                                    {formatValue(data.pokerHouseCut)}⚡
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Energy Sinks (Outflows) */}
                <div>
                    <div style={{ fontSize: '10px', color: 'var(--color-danger)', fontWeight: 600, marginBottom: '4px', textTransform: 'uppercase' }}>
                        Sinks (-{formatValue(totalOutflow)}⚡)
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <FlowBar label="Metabolism" value={data.fishMetabolism} color="#fb7185" icon="🔥" isOutflow />
                        <FlowBar label="Deaths" value={data.fishDeaths} color="#ef4444" icon="☠️" isOutflow />
                    </div>
                </div>
            </div>
        </div>
    );
}

export default EnergySankey;
