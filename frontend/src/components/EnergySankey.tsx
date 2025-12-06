import { ResponsiveContainer, Sankey, Tooltip, Layer, Rectangle } from 'recharts';

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

const nodeColors = {
    food: '#fbbf24',
    nectar: '#22c55e',
    fish: '#60a5fa',
    poker: '#a855f7',
    metabolism: '#fb7185',
    death: '#ef4444',
    house: '#94a3b8',
};

const nodeLabels = [
    { name: '🥕 User Food', color: nodeColors.food },
    { name: '🌿 Plant Nectar', color: nodeColors.nectar },
    { name: '🐟 Fish Population', color: nodeColors.fish },
    { name: '🎴 Poker Economy', color: nodeColors.poker },
    { name: '🔥 Metabolism', color: nodeColors.metabolism },
    { name: '☠️ Death', color: nodeColors.death },
    { name: '🏛️ House Cut', color: nodeColors.house },
];

function formatValue(value: number): string {
    if (!Number.isFinite(value)) return '0';
    return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

export function EnergySankey({ data, title = 'Energy Flux', subtitle }: EnergySankeyProps) {
    const pokerNetReturn = Math.max(0, data.pokerTotalPot - data.pokerHouseCut);

    const links = [
        { source: 0, target: 2, value: Math.max(0, data.foodAdded), color: nodeColors.food },
        { source: 1, target: 2, value: Math.max(0, data.plantNectar), color: nodeColors.nectar },
        { source: 2, target: 3, value: Math.max(0, data.pokerTotalPot), color: nodeColors.poker },
        { source: 3, target: 2, value: pokerNetReturn, color: nodeColors.poker },
        { source: 2, target: 4, value: Math.max(0, data.fishMetabolism), color: nodeColors.metabolism },
        { source: 2, target: 5, value: Math.max(0, data.fishDeaths), color: nodeColors.death },
        { source: 3, target: 6, value: Math.max(0, data.pokerHouseCut), color: nodeColors.house },
    ];

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const { source, target, value } = payload[0].payload;
            return (
                <div
                    style={{
                        backgroundColor: 'rgba(15,23,42,0.95)',
                        padding: '10px 12px',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '10px',
                        color: '#e2e8f0',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                    }}
                >
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: 12 }}>
                        <span style={{ color: source.color }}>{source.name}</span>
                        <span style={{ opacity: 0.6 }}>→</span>
                        <span style={{ color: target.color }}>{target.name}</span>
                    </div>
                    <div style={{ fontWeight: 700, marginTop: 6 }}>{formatValue(value)}⚡</div>
                </div>
            );
        }
        return null;
    };

    const renderNode = (props: any) => {
        const { x, y, width, height, index, payload } = props;
        const centerY = y + height / 2;
        const centerX = x + width / 2;

        return (
            <Layer key={`node-${index}`}>
                <Rectangle
                    x={x}
                    y={y}
                    width={width}
                    height={height}
                    fill={payload.color}
                    radius={4}
                    stroke="rgba(15,23,42,0.6)"
                />
                <text
                    x={centerX}
                    y={centerY}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#0b1221"
                    fontSize={11}
                    fontWeight={700}
                >
                    {payload.name}
                </text>
            </Layer>
        );
    };

    return (
        <div style={{ background: 'rgba(15,23,42,0.7)', borderRadius: 12, padding: '12px', height: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
                <div>
                    <div style={{ color: 'var(--color-text-muted)', fontSize: 12, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                        ⚡ {title}
                    </div>
                    {subtitle && <div style={{ color: 'var(--color-text-dim)', fontSize: 11 }}>{subtitle}</div>}
                </div>
            </div>
            <div style={{ height: 260 }}>
                <ResponsiveContainer>
                    <Sankey
                        data={{ nodes: nodeLabels, links }}
                        node={renderNode}
                        nodePadding={22}
                        iterations={32}
                        margin={{ top: 10, bottom: 10, left: 10, right: 10 }}
                        link={{ strokeOpacity: 0.25 }}
                    >
                        <Tooltip content={<CustomTooltip />} />
                    </Sankey>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

export default EnergySankey;
