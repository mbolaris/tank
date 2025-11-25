import { useCallback, useEffect, useMemo, useState } from 'react';
import { config, type ServerWithTanks } from '../config';

interface TankNode {
    id: string;
    name: string;
    serverName: string;
    allowTransfers: boolean;
    x: number;
    y: number;
}

export interface TankConnection {
    id: string;
    sourceId: string;
    destinationId: string;
    probability: number; // 0-100
}

interface TankNetworkMapProps {
    servers: ServerWithTanks[];
}

interface TransferRecord {
    transfer_id: string;
    entity_type: string;
    source_tank_id: string;
    destination_tank_id: string;
    source_tank_name: string;
    destination_tank_name: string;
}

const STORAGE_KEY = 'tank-network-connections';

const loadConnections = (): TankConnection[] => {
    if (typeof window === 'undefined') return [];
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
            return parsed;
        }
    } catch (err) {
        console.warn('Failed to parse saved connections', err);
    }
    return [];
};

const persistConnections = (connections: TankConnection[]) => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(connections));
};

const getRingPosition = (index: number, total: number, radiusX: number, radiusY: number, centerX: number, centerY: number) => {
    if (total === 0) return { x: centerX, y: centerY };
    const angle = (2 * Math.PI * index) / total - Math.PI / 2;
    return {
        x: centerX + radiusX * Math.cos(angle),
        y: centerY + radiusY * Math.sin(angle),
    };
};

export function TankNetworkMap({ servers }: TankNetworkMapProps) {
    const tanks = useMemo(() => {
        return servers.flatMap((server) =>
            server.tanks.map((tankStatus) => ({
                id: tankStatus.tank.tank_id,
                name: tankStatus.tank.name,
                allowTransfers: tankStatus.tank.allow_transfers,
                serverName: server.server.hostname,
            })),
        );
    }, [servers]);

    const [connections, setConnections] = useState<TankConnection[]>(() => loadConnections());
    const [sourceId, setSourceId] = useState('');
    const [destinationId, setDestinationId] = useState('');
    const [probability, setProbability] = useState(25);
    const [latestTransferId, setLatestTransferId] = useState<string | null>(null);
    const [activeConnection, setActiveConnection] = useState<{ connectionId: string; entity: string; label: string } | null>(null);
    const activeConnectionMeta = useMemo(
        () => (activeConnection ? connections.find((c) => c.id === activeConnection.connectionId) : null),
        [activeConnection, connections],
    );

    // Keep form selections in sync with available tanks
    useEffect(() => {
        if (!sourceId && tanks.length > 0) {
            setSourceId(tanks[0].id);
        }
        if (!destinationId && tanks.length > 1) {
            setDestinationId(tanks[1].id);
        }
    }, [tanks, sourceId, destinationId]);

    // Remove connections that reference missing tanks
    useEffect(() => {
        const validIds = new Set(tanks.map((t) => t.id));
        setConnections((prev) => prev.filter((c) => validIds.has(c.sourceId) && validIds.has(c.destinationId)));
    }, [tanks]);

    // Persist connections to localStorage
    useEffect(() => {
        persistConnections(connections);
    }, [connections]);

    const nodes: TankNode[] = useMemo(() => {
        const radiusX = 420;
        const radiusY = 190;
        const centerX = 500;
        const centerY = 240;

        return tanks.map((tank, index) => {
            const position = getRingPosition(index, tanks.length, radiusX, radiusY, centerX, centerY);
            return {
                ...tank,
                x: position.x,
                y: position.y,
            } as TankNode;
        });
    }, [tanks]);

    const nodeLookup = useMemo(() => {
        const map = new Map<string, TankNode>();
        nodes.forEach((node) => map.set(node.id, node));
        return map;
    }, [nodes]);

    const handleAddConnection = (e: React.FormEvent) => {
        e.preventDefault();
        if (!sourceId || !destinationId || sourceId === destinationId) return;

        setConnections((prev) => {
            const existing = prev.find((c) => c.sourceId === sourceId && c.destinationId === destinationId);
            if (existing) {
                return prev.map((c) => (c.id === existing.id ? { ...c, probability } : c));
            }
            const id = `${sourceId}->${destinationId}`;
            return [...prev, { id, sourceId, destinationId, probability }];
        });
    };

    const handleDeleteConnection = (id: string) => {
        setConnections((prev) => prev.filter((c) => c.id !== id));
    };

    const maxProbability = connections.reduce((max, c) => Math.max(max, c.probability), 0);

    const pollTransfers = useCallback(async () => {
        try {
            const response = await fetch(`${config.apiBaseUrl}/api/transfers?limit=1&success_only=true`);
            if (!response.ok) return;
            const data = await response.json();
            const latest: TransferRecord | undefined = data.transfers?.[0];
            if (!latest || latest.transfer_id === latestTransferId) return;

            setLatestTransferId(latest.transfer_id);

            const matching = connections.find(
                (c) => c.sourceId === latest.source_tank_id && c.destinationId === latest.destination_tank_id,
            );

            if (matching) {
                setActiveConnection({
                    connectionId: matching.id,
                    entity: latest.entity_type,
                    label: `${latest.source_tank_name} → ${latest.destination_tank_name}`,
                });
            }
        } catch (err) {
            console.error('Failed to poll transfers for network map', err);
        }
    }, [connections, latestTransferId]);

    useEffect(() => {
        pollTransfers();
        const interval = setInterval(pollTransfers, 4000);
        return () => clearInterval(interval);
    }, [pollTransfers]);

    useEffect(() => {
        if (!activeConnection) return;
        const timeout = setTimeout(() => setActiveConnection(null), 2600);
        return () => clearTimeout(timeout);
    }, [activeConnection]);

    const probabilityWidth = (value: number) => {
        const base = 3;
        const maxExtra = 14;
        return base + (maxProbability === 0 ? 0 : (value / 100) * maxExtra);
    };

    return (
        <div
            style={{
                background: 'radial-gradient(circle at 20% 20%, rgba(37,99,235,0.18), rgba(15,23,42,0.9))',
                border: '1px solid #1e293b',
                borderRadius: '16px',
                padding: '20px',
                marginBottom: '24px',
                boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                    <h2 style={{ margin: 0, color: '#f8fafc', fontSize: 20 }}>Tank Migration Tubes</h2>
                    <p style={{ margin: '6px 0 0 0', color: '#94a3b8', fontSize: 13 }}>
                        Connect tanks to allow fish and plants to drift between them. Tube width reflects migration probability.
                    </p>
                </div>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: 10,
                    padding: '8px 12px',
                }}>
                    <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#22c55e' }} />
                    <div style={{ fontSize: 12, color: '#cbd5e1' }}>Transfers allowed</div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, alignItems: 'center' }}>
                <div style={{ position: 'relative', backgroundColor: '#0b1220', borderRadius: 14, border: '1px solid #1f2937' }}>
                    <svg viewBox="0 0 1000 480" style={{ width: '100%', height: '100%' }}>
                        <defs>
                            <linearGradient id="tubeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.25" />
                                <stop offset="50%" stopColor="#60a5fa" stopOpacity="0.4" />
                                <stop offset="100%" stopColor="#a78bfa" stopOpacity="0.25" />
                            </linearGradient>
                        </defs>

                        {connections.map((connection) => {
                            const source = nodeLookup.get(connection.sourceId);
                            const dest = nodeLookup.get(connection.destinationId);
                            if (!source || !dest) return null;

                            const isActive = activeConnection?.connectionId === connection.id;
                            const thickness = probabilityWidth(connection.probability);

                            return (
                                <g key={connection.id}>
                                    <path
                                        d={`M ${source.x} ${source.y} Q ${(source.x + dest.x) / 2} ${
                                            (source.y + dest.y) / 2 - 60
                                        } ${dest.x} ${dest.y}`}
                                        stroke="url(#tubeGradient)"
                                        strokeWidth={thickness}
                                        fill="none"
                                        opacity={0.9}
                                        className={isActive ? 'tube-flow' : undefined}
                                        strokeLinecap="round"
                                    />
                                    {isActive && (
                                        <circle
                                            cx={(source.x * 2 + dest.x) / 3}
                                            cy={(source.y * 2 + dest.y) / 3}
                                            r={Math.max(10, thickness + 4)}
                                            fill="rgba(59,130,246,0.25)"
                                            stroke="#22d3ee"
                                            strokeWidth={2}
                                            className="tube-pulse"
                                        />
                                    )}
                                    <text
                                        x={(source.x + dest.x) / 2}
                                        y={(source.y + dest.y) / 2 - 16}
                                        fill="#cbd5e1"
                                        fontSize="12"
                                        textAnchor="middle"
                                        style={{ userSelect: 'none' }}
                                    >
                                        {connection.probability}%
                                    </text>
                                </g>
                            );
                        })}

                        {nodes.map((node) => {
                            const isActive = activeConnectionMeta
                                ? activeConnectionMeta.sourceId === node.id || activeConnectionMeta.destinationId === node.id
                                : false;
                            return (
                                <g key={node.id}>
                                    <circle
                                        cx={node.x}
                                        cy={node.y}
                                        r={32}
                                        fill={node.allowTransfers ? '#0ea5e9' : '#1f2937'}
                                        stroke={node.allowTransfers ? '#38bdf8' : '#334155'}
                                        strokeWidth={node.allowTransfers ? 3 : 2}
                                        opacity={node.allowTransfers ? 0.95 : 0.7}
                                        className={isActive ? 'tube-pulse' : undefined}
                                    />
                                    <text
                                        x={node.x}
                                        y={node.y - 6}
                                        fill="#f8fafc"
                                        fontSize="12"
                                        textAnchor="middle"
                                        fontWeight="700"
                                        style={{ userSelect: 'none' }}
                                    >
                                        {node.name}
                                    </text>
                                    <text
                                        x={node.x}
                                        y={node.y + 12}
                                        fill="#cbd5e1"
                                        fontSize="11"
                                        textAnchor="middle"
                                        style={{ userSelect: 'none' }}
                                    >
                                        {node.serverName}
                                    </text>
                                    {!node.allowTransfers && (
                                        <text
                                            x={node.x}
                                            y={node.y + 28}
                                            fill="#f87171"
                                            fontSize="10"
                                            textAnchor="middle"
                                            style={{ userSelect: 'none' }}
                                        >
                                            Transfers blocked
                                        </text>
                                    )}
                                </g>
                            );
                        })}
                    </svg>

                    {activeConnection && (
                        <div
                            style={{
                                position: 'absolute',
                                left: 16,
                                bottom: 16,
                                backgroundColor: 'rgba(15,23,42,0.9)',
                                border: '1px solid #334155',
                                padding: '10px 14px',
                                borderRadius: 10,
                                color: '#e2e8f0',
                                boxShadow: '0 10px 30px rgba(0,0,0,0.35)',
                            }}
                        >
                            <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>Live transfer</div>
                            <div style={{ fontWeight: 700, fontSize: 14 }}>
                                {activeConnection.entity === 'fish' ? '🐟' : '🌿'} {activeConnection.label}
                            </div>
                            <div style={{ fontSize: 12, color: '#38bdf8', marginTop: 2 }}>Tube opens to pull entity across</div>
                        </div>
                    )}
                </div>

                <div
                    style={{
                        backgroundColor: '#0f172a',
                        border: '1px solid #1f2937',
                        borderRadius: 12,
                        padding: 14,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 12,
                    }}
                >
                    <h3 style={{ margin: 0, fontSize: 16, color: '#e2e8f0' }}>Configure migration</h3>
                    <p style={{ margin: 0, color: '#94a3b8', fontSize: 12 }}>
                        Choose a source and destination tank, then set the probability for fish and plant drift.
                    </p>

                    <form onSubmit={handleAddConnection} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <label style={{ fontSize: 12, color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 6 }}>
                            Source tank
                            <select
                                value={sourceId}
                                onChange={(e) => setSourceId(e.target.value)}
                                style={{
                                    padding: '10px',
                                    backgroundColor: '#0b1220',
                                    color: '#e2e8f0',
                                    borderRadius: 8,
                                    border: '1px solid #334155',
                                }}
                            >
                                {tanks.map((tank) => (
                                    <option key={tank.id} value={tank.id}>
                                        {tank.name} ({tank.serverName})
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label style={{ fontSize: 12, color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 6 }}>
                            Destination tank
                            <select
                                value={destinationId}
                                onChange={(e) => setDestinationId(e.target.value)}
                                style={{
                                    padding: '10px',
                                    backgroundColor: '#0b1220',
                                    color: '#e2e8f0',
                                    borderRadius: 8,
                                    border: '1px solid #334155',
                                }}
                            >
                                {tanks.map((tank) => (
                                    <option key={tank.id} value={tank.id} disabled={tank.id === sourceId}>
                                        {tank.name} ({tank.serverName})
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label style={{ fontSize: 12, color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 6 }}>
                            Migration probability
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                <input
                                    type="range"
                                    min={5}
                                    max={100}
                                    step={5}
                                    value={probability}
                                    onChange={(e) => setProbability(Number(e.target.value))}
                                    style={{ flex: 1 }}
                                />
                                <span style={{ width: 40, textAlign: 'right', fontWeight: 700, color: '#38bdf8' }}>
                                    {probability}%
                                </span>
                            </div>
                        </label>
                        <button
                            type="submit"
                            disabled={!sourceId || !destinationId || sourceId === destinationId || tanks.length < 2}
                            style={{
                                padding: '10px 12px',
                                background: 'linear-gradient(90deg, #2563eb, #22c55e)',
                                color: '#fff',
                                border: 'none',
                                borderRadius: 8,
                                fontWeight: 700,
                                cursor: 'pointer',
                                boxShadow: '0 10px 25px rgba(34,197,94,0.2)',
                            }}
                        >
                            Save connection
                        </button>
                    </form>

                    <div style={{ marginTop: 4 }}>
                        <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6 }}>Active tubes</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {connections.length === 0 ? (
                                <div
                                    style={{
                                        padding: '12px',
                                        borderRadius: 8,
                                        backgroundColor: '#0b1220',
                                        border: '1px dashed #334155',
                                        color: '#94a3b8',
                                        fontSize: 12,
                                    }}
                                >
                                    No tubes yet. Link tanks to start migrations.
                                </div>
                            ) : (
                                connections.map((connection) => {
                                    const source = nodeLookup.get(connection.sourceId);
                                    const dest = nodeLookup.get(connection.destinationId);
                                    if (!source || !dest) return null;
                                    return (
                                        <div
                                            key={connection.id}
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                padding: '10px 12px',
                                                backgroundColor: '#0b1220',
                                                borderRadius: 8,
                                                border: '1px solid #1f2937',
                                                gap: 8,
                                            }}
                                        >
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                                <div style={{ fontWeight: 700, fontSize: 13, color: '#e2e8f0' }}>
                                                    {source.name}
                                                    <span style={{ margin: '0 6px', color: '#38bdf8' }}>→</span>
                                                    {dest.name}
                                                </div>
                                                <div style={{ fontSize: 12, color: '#94a3b8' }}>
                                                    {source.serverName} to {dest.serverName} &bull; {connection.probability}%
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => handleDeleteConnection(connection.id)}
                                                style={{
                                                    background: 'transparent',
                                                    border: '1px solid #ef4444',
                                                    color: '#ef4444',
                                                    padding: '6px 10px',
                                                    borderRadius: 6,
                                                    cursor: 'pointer',
                                                    fontSize: 12,
                                                }}
                                            >
                                                Remove
                                            </button>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
