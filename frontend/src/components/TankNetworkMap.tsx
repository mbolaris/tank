import { useCallback, useEffect, useMemo, useState, useRef, memo } from 'react';
import { config, type ServerWithTanks } from '../config';
import { useErrorNotification } from '../hooks/useErrorNotification';
import { ErrorNotification } from './ErrorNotification';

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
    direction: 'left' | 'right';
}

interface TankNetworkMapProps {
    servers: ServerWithTanks[];
}

interface TransferRecord {
    transfer_id: string;
    timestamp: string;
    entity_type: string;
    entity_old_id: number;
    entity_new_id: number | null;
    source_tank_id: string;
    destination_tank_id: string;
    source_tank_name: string;
    destination_tank_name: string;
    success: boolean;
}

const TankNetworkMapInternal = function TankNetworkMap({ servers }: TankNetworkMapProps) {
    const { errors, addError, clearError } = useErrorNotification();

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

    const [connections, setConnections] = useState<TankConnection[]>([]);
    const [sourceId, setSourceId] = useState('');
    const [destinationId, setDestinationId] = useState('');
    const [probability, setProbability] = useState(25);
    const [latestTransferId, setLatestTransferId] = useState<string | null>(null);
    const [transfers, setTransfers] = useState<TransferRecord[]>([]);
    const [activeConnection, setActiveConnection] = useState<{ connectionId: string; entity: string; label: string } | null>(null);

    const activeConnectionMeta = useMemo(
        () => (activeConnection ? connections.find((c) => c.id === activeConnection.connectionId) : null),
        [activeConnection, connections],
    );

    // Keep form selections in sync with available tanks - initialize once
    const initializedRef = useRef(false);
    useEffect(() => {
        if (initializedRef.current) return;
        if (tanks.length > 0) {
            if (!sourceId) setSourceId(tanks[0].id);
            if (!destinationId && tanks.length > 1) setDestinationId(tanks[1].id);
            initializedRef.current = true;
        }
    }, [tanks, sourceId, destinationId]);

    // Remove connections that reference missing tanks
    useEffect(() => {
        const validIds = new Set(tanks.map((t) => t.id));
        setConnections((prev) => prev.filter((c) => validIds.has(c.sourceId) && validIds.has(c.destinationId)));
    }, [tanks]);

    // Load connections from backend
    useEffect(() => {
        fetch(`${config.apiBaseUrl}/api/connections`)
            .then((res) => res.json())
            .then((data) => {
                if (data.connections) {
                    setConnections(data.connections);
                }
            })
            .catch((err) => addError(err, 'Failed to load connections'));
    }, [addError]);

    const fetchTransfers = useCallback(async () => {
        try {
            const response = await fetch(`${config.apiBaseUrl}/api/transfers?limit=100&success_only=true`);
            if (!response.ok) return;
            const data = await response.json();
            if (Array.isArray(data.transfers)) {
                setTransfers(data.transfers);
            }
        } catch (err) {
            addError(err, 'Failed to load transfers for network map');
        }
    }, [addError]);

    useEffect(() => {
        fetchTransfers();
        const interval = setInterval(fetchTransfers, 2000);
        return () => clearInterval(interval);
    }, [fetchTransfers]);

    const nodes: TankNode[] = useMemo(() => {
        const radiusX = 420;
        const radiusY = 190;
        const centerX = 500;
        const centerY = 240;

        const getRingPosition = (index: number, total: number, radiusX: number, radiusY: number, centerX: number, centerY: number) => {
            if (total === 0) return { x: centerX, y: centerY };
            const angle = (2 * Math.PI * index) / total - Math.PI / 2;
            return {
                x: centerX + radiusX * Math.cos(angle),
                y: centerY + radiusY * Math.sin(angle),
            };
        };

        // With only two tanks the default ring layout stacks them vertically, which hides
        // the connecting tube in the middle. Give the pair a clear left/right layout so
        // their connection line is always visible.
        if (tanks.length === 2) {
            return [
                {
                    ...tanks[0],
                    x: centerX - radiusX / 2,
                    y: centerY,
                },
                {
                    ...tanks[1],
                    x: centerX + radiusX / 2,
                    y: centerY,
                },
            ];
        }

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

    const handleAddConnection = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!sourceId || !destinationId || sourceId === destinationId) return;

        const sourceNode = nodeLookup.get(sourceId);
        const destNode = nodeLookup.get(destinationId);

        const direction = (sourceNode && destNode && destNode.x > sourceNode.x) ? 'right' : 'left';

        const newConnection = {
            id: `${sourceId}->${destinationId}`,
            sourceId,
            destinationId,
            probability,
            direction
        };

        try {
            const res = await fetch(`${config.apiBaseUrl}/api/connections`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConnection),
            });

            if (res.ok) {
                const savedConnection = await res.json();
                setConnections((prev) => {
                    const existing = prev.find((c) => c.id === savedConnection.id);
                    if (existing) {
                        return prev.map((c) => (c.id === existing.id ? savedConnection : c));
                    }
                    return [...prev, savedConnection];
                });
            }
        } catch (err) {
            addError(err, 'Failed to save connection');
        }
    };

    const handleDeleteConnection = async (id: string) => {
        try {
            const res = await fetch(`${config.apiBaseUrl}/api/connections/${id}`, {
                method: 'DELETE',
            });

            if (res.ok) {
                setConnections((prev) => prev.filter((c) => c.id !== id));
            }
        } catch (err) {
            addError(err, 'Failed to delete connection');
        }
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
            fetchTransfers();

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
            addError(err, 'Failed to poll transfers for network map');
        }
    }, [connections, fetchTransfers, latestTransferId, addError]);

    useEffect(() => {
        pollTransfers();
        const interval = setInterval(pollTransfers, 3000); // Poll every 3 seconds to avoid browser resource exhaustion
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

    const connectionMigrationCounts = useMemo(() => {
        const counts = new Map<string, number>();
        transfers.forEach((transfer) => {
            const id = `${transfer.source_tank_id}->${transfer.destination_tank_id}`;
            counts.set(id, (counts.get(id) ?? 0) + 1);
        });
        return counts;
    }, [transfers]);

    const formatTimestamp = (timestamp: string) => {
        try {
            return new Date(timestamp).toLocaleString();
        } catch {
            return timestamp;
        }
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
            <ErrorNotification errors={errors} onDismiss={clearError} />
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
                            {/* Arrow marker for tube direction */}
                            <marker
                                id="tubeArrow"
                                viewBox="0 0 10 10"
                                refX="5"
                                refY="5"
                                markerWidth="4"
                                markerHeight="4"
                                orient="auto-start-reverse"
                            >
                                <path d="M 0 0 L 10 5 L 0 10 z" fill="#60a5fa" opacity="0.8" />
                            </marker>
                            <marker
                                id="tubeArrowActive"
                                viewBox="0 0 10 10"
                                refX="5"
                                refY="5"
                                markerWidth="5"
                                markerHeight="5"
                                orient="auto-start-reverse"
                            >
                                <path d="M 0 0 L 10 5 L 0 10 z" fill="#22d3ee" />
                            </marker>
                        </defs>

                        {connections.map((connection) => {
                            const source = nodeLookup.get(connection.sourceId);
                            const dest = nodeLookup.get(connection.destinationId);
                            if (!source || !dest) return null;

                            const isActive = activeConnection?.connectionId === connection.id;
                            const thickness = probabilityWidth(connection.probability);
                            const migrations = connectionMigrationCounts.get(connection.id) ?? 0;

                            // Calculate control point for Bezier curve
                            // For vertical connections, add horizontal offset to make them visible
                            const dx = dest.x - source.x;
                            const dy = dest.y - source.y;
                            const isVertical = Math.abs(dx) < Math.abs(dy);

                            const controlX = (source.x + dest.x) / 2 + (isVertical ? 80 : 0);
                            const controlY = (source.y + dest.y) / 2 - (isVertical ? 0 : 60);

                            // Calculate points along the curve for direction arrows
                            // Quadratic Bezier: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
                            const getPointOnCurve = (t: number) => {
                                const mt = 1 - t;
                                return {
                                    x: mt * mt * source.x + 2 * mt * t * controlX + t * t * dest.x,
                                    y: mt * mt * source.y + 2 * mt * t * controlY + t * t * dest.y,
                                };
                            };

                            // Get tangent direction at point t
                            const getTangent = (t: number) => {
                                const mt = 1 - t;
                                // Derivative: B'(t) = 2(1-t)(P1-P0) + 2t(P2-P1)
                                const tx = 2 * mt * (controlX - source.x) + 2 * t * (dest.x - controlX);
                                const ty = 2 * mt * (controlY - source.y) + 2 * t * (dest.y - controlY);
                                const len = Math.sqrt(tx * tx + ty * ty);
                                return { x: tx / len, y: ty / len };
                            };

                            // Place arrows at 33% and 66% along the curve
                            const arrowPositions = [0.35, 0.65];

                            return (
                                <g key={connection.id}>
                                    <path
                                        d={`M ${source.x} ${source.y} Q ${controlX} ${controlY} ${dest.x} ${dest.y}`}
                                        stroke="url(#tubeGradient)"
                                        strokeWidth={thickness}
                                        fill="none"
                                        opacity={0.9}
                                        className={isActive ? 'tube-flow' : undefined}
                                        strokeLinecap="round"
                                    />
                                    {/* Direction arrows along the tube */}
                                    {arrowPositions.map((t, idx) => {
                                        const point = getPointOnCurve(t);
                                        const tangent = getTangent(t);
                                        const angle = Math.atan2(tangent.y, tangent.x) * (180 / Math.PI);
                                        const arrowSize = Math.max(8, thickness * 0.8);
                                        return (
                                            <g key={idx} transform={`translate(${point.x}, ${point.y}) rotate(${angle})`}>
                                                <polygon
                                                    points={`${arrowSize},0 ${-arrowSize * 0.6},${arrowSize * 0.6} ${-arrowSize * 0.6},${-arrowSize * 0.6}`}
                                                    fill={isActive ? '#22d3ee' : '#60a5fa'}
                                                    opacity={isActive ? 1 : 0.7}
                                                    className={isActive ? 'tube-pulse' : undefined}
                                                />
                                            </g>
                                        );
                                    })}
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
                                        x={controlX}
                                        y={controlY - 4}
                                        fill="#cbd5e1"
                                        fontSize="12"
                                        textAnchor="middle"
                                        style={{ userSelect: 'none' }}
                                    >
                                        {connection.probability}%
                                    </text>
                                    <text
                                        x={controlX}
                                        y={controlY + 10}
                                        fill="#94a3b8"
                                        fontSize="11"
                                        textAnchor="middle"
                                        style={{ userSelect: 'none' }}
                                    >
                                        {migrations} migration{migrations === 1 ? '' : 's'}
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
                                                    {source.serverName} to {dest.serverName} &bull; {connection.probability}% &bull;{' '}
                                                    {connectionMigrationCounts.get(connection.id) ?? 0} migrations
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

                    <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6 }}>Recent migrations</div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {transfers.length === 0 ? (
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
                                    No migrations recorded yet.
                                </div>
                            ) : (
                                transfers.slice(0, 6).map((transfer) => (
                                    <div
                                        key={transfer.transfer_id}
                                        style={{
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: 4,
                                            padding: '10px 12px',
                                            backgroundColor: '#0b1220',
                                            borderRadius: 8,
                                            border: '1px solid #1f2937',
                                        }}
                                    >
                                        <div style={{ fontWeight: 700, fontSize: 13, color: '#e2e8f0' }}>
                                            {transfer.entity_type === 'fish' ? '🐟' : '🌿'} {transfer.source_tank_name}
                                            <span style={{ margin: '0 6px', color: '#38bdf8' }}>→</span>
                                            {transfer.destination_tank_name}
                                        </div>
                                        <div style={{ fontSize: 12, color: '#94a3b8' }}>
                                            {formatTimestamp(transfer.timestamp)}
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export const TankNetworkMap = memo(TankNetworkMapInternal);
