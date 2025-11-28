/**
 * NetworkDashboard - Tank World Net overview page
 *
 * Shows all servers and their tanks in the network
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { config, type TankStatus, type ServerWithTanks } from '../config';
import { TankThumbnail } from '../components/TankThumbnail';
import { TransferHistory } from '../components/TransferHistory';
import { TankNetworkMap } from '../components/TankNetworkMap';
import type { SimulationUpdate } from '../types/simulation';

interface ServersResponse {
    servers: ServerWithTanks[];
}

export function NetworkDashboard() {
    const [servers, setServers] = useState<ServerWithTanks[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Create tank form state
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [newTankName, setNewTankName] = useState('');
    const [newTankDescription, setNewTankDescription] = useState('');
    const [selectedServerId, setSelectedServerId] = useState<string>('');
    const [creating, setCreating] = useState(false);

    // Transfer history state
    const [showHistory, setShowHistory] = useState(false);

    const totalTanks = servers.reduce((sum, s) => sum + s.tanks.length, 0);

    const fetchServers = useCallback(async () => {
        try {
            setError(null);
            const response = await fetch(config.serversApiUrl);
            if (!response.ok) {
                throw new Error(`Failed to fetch servers: ${response.status}`);
            }
            const data: ServersResponse = await response.json();
            setServers(data.servers);

            // Set default server for create form if not set
            if (!selectedServerId && data.servers.length > 0) {
                setSelectedServerId(data.servers[0].server.server_id);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load servers');
        } finally {
            setLoading(false);
        }
    }, [selectedServerId]);

    useEffect(() => {
        fetchServers();
        // Refresh every 1 second
        const interval = setInterval(fetchServers, 1000);
        return () => clearInterval(interval);
    }, [fetchServers]);

    const handleCreateTank = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedServerId) return;

        setCreating(true);
        try {
            const name = newTankName.trim() || `Tank ${totalTanks + 1}`;
            const params = new URLSearchParams({
                name,
                description: newTankDescription.trim(),
                server_id: selectedServerId,
            });
            const response = await fetch(`${config.tanksApiUrl}?${params}`, {
                method: 'POST',
            });
            if (!response.ok) {
                throw new Error(`Failed to create tank: ${response.status}`);
            }
            // Reset form and refresh
            setNewTankName('');
            setNewTankDescription('');
            setShowCreateForm(false);
            await fetchServers();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to create tank');
        } finally {
            setCreating(false);
        }
    };

    const handleDeleteTank = async (tankId: string, tankName: string) => {
        if (!confirm(`Are you sure you want to delete "${tankName}"? This cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`${config.apiBaseUrl}/api/tanks/${tankId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.error || `Failed to delete tank: ${response.status}`);
            }
            await fetchServers();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete tank');
        }
    };

    const handleOpenCreateForm = () => {
        setShowCreateForm(true);
        if (!newTankName.trim()) {
            setNewTankName(`Tank ${totalTanks + 1}`);
        }
        if (!selectedServerId && servers[0]) {
            setSelectedServerId(servers[0].server.server_id);
        }
    };

    return (
        <div style={{
            minHeight: '100vh',
            backgroundColor: '#0a0f1a',
            color: '#e2e8f0',
            padding: '24px',
        }}>
            <div style={{
                maxWidth: '1400px',
                margin: '0 auto',
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '32px',
                }}>
                    <div>
                        <h1 style={{
                            fontSize: '28px',
                            fontWeight: 700,
                            color: '#3b82f6',
                            margin: 0,
                        }}>
                            Tank World Net
                        </h1>
                        <p style={{
                            color: '#94a3b8',
                            margin: '8px 0 0 0',
                            fontSize: '14px',
                        }}>
                            {servers.length} server{servers.length !== 1 ? 's' : ''}
                            {' '}&bull;{' '}
                            {totalTanks} tank{totalTanks !== 1 ? 's' : ''}
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '12px' }}>
                        <button
                            onClick={() => setShowHistory(true)}
                            style={{
                                padding: '10px 20px',
                                backgroundColor: '#475569',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                fontSize: '14px',
                            }}
                        >
                            📋 History
                        </button>
                        <button
                            onClick={handleOpenCreateForm}
                            style={{
                                padding: '10px 20px',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                fontSize: '14px',
                            }}
                        >
                            + New Tank
                        </button>
                    </div>
                </div>

                {/* Create Tank Form */}
                {showCreateForm && (
                    <div style={{
                        backgroundColor: '#1e293b',
                        borderRadius: '12px',
                        padding: '24px',
                        marginBottom: '24px',
                        border: '1px solid #334155',
                    }}>
                        <h3 style={{ margin: '0 0 16px 0', color: '#f1f5f9' }}>Create New Tank</h3>
                        <form onSubmit={handleCreateTank}>
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '6px', color: '#94a3b8', fontSize: '14px' }}>
                                    Tank Name
                                </label>
                                <input
                                    type="text"
                                    value={newTankName}
                                    onChange={(e) => setNewTankName(e.target.value)}
                                    placeholder="My Tank"
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        backgroundColor: '#0f172a',
                                        border: '1px solid #475569',
                                        borderRadius: '6px',
                                        color: '#e2e8f0',
                                        fontSize: '14px',
                                        boxSizing: 'border-box',
                                    }}
                                    autoFocus
                                />
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '6px', color: '#94a3b8', fontSize: '14px' }}>
                                    Description (optional)
                                </label>
                                <input
                                    type="text"
                                    value={newTankDescription}
                                    onChange={(e) => setNewTankDescription(e.target.value)}
                                    placeholder="A brief description"
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        backgroundColor: '#0f172a',
                                        border: '1px solid #475569',
                                        borderRadius: '6px',
                                        color: '#e2e8f0',
                                        fontSize: '14px',
                                        boxSizing: 'border-box',
                                    }}
                                />
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                                <label style={{ display: 'block', marginBottom: '6px', color: '#94a3b8', fontSize: '14px' }}>
                                    Server
                                </label>
                                <select
                                    value={selectedServerId}
                                    onChange={(e) => setSelectedServerId(e.target.value)}
                                    style={{
                                        width: '100%',
                                        padding: '10px 12px',
                                        backgroundColor: '#0f172a',
                                        border: '1px solid #475569',
                                        borderRadius: '6px',
                                        color: '#e2e8f0',
                                        fontSize: '14px',
                                        boxSizing: 'border-box',
                                    }}
                                >
                                    {servers.map((serverWithTanks) => (
                                        <option key={serverWithTanks.server.server_id} value={serverWithTanks.server.server_id}>
                                            {serverWithTanks.server.hostname} ({serverWithTanks.server.status})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button
                                    type="submit"
                                    disabled={creating || !selectedServerId}
                                    style={{
                                        padding: '10px 20px',
                                        backgroundColor: creating ? '#475569' : '#22c55e',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        cursor: creating ? 'not-allowed' : 'pointer',
                                        fontWeight: 600,
                                        fontSize: '14px',
                                    }}
                                >
                                    {creating ? 'Creating...' : 'Create Tank'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowCreateForm(false)}
                                    style={{
                                        padding: '10px 20px',
                                        backgroundColor: 'transparent',
                                        color: '#94a3b8',
                                        border: '1px solid #475569',
                                        borderRadius: '6px',
                                        cursor: 'pointer',
                                        fontSize: '14px',
                                    }}
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div style={{
                        backgroundColor: '#7f1d1d',
                        color: '#fecaca',
                        padding: '16px',
                        borderRadius: '8px',
                        marginBottom: '24px',
                    }}>
                        {error}
                    </div>
                )}

                {/* Loading State */}
                {loading && servers.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        padding: '48px',
                        color: '#94a3b8',
                    }}>
                        Loading servers...
                    </div>
                )}

                {/* Server Cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                    {servers.map((serverWithTanks) => (
                        <ServerCard
                            key={serverWithTanks.server.server_id}
                            serverWithTanks={serverWithTanks}
                            onDeleteTank={handleDeleteTank}
                            onRefresh={fetchServers}
                        />
                    ))}
                </div>

                {/* Tube Network Map - directly follows thumbnails when servers exist */}
                {servers.length > 0 && (
                    <div style={{ marginTop: '24px' }}>
                        <TankNetworkMap servers={servers} />
                    </div>
                )}

                {/* Empty State */}
                {!loading && servers.length === 0 && !error && (
                    <div style={{
                        textAlign: 'center',
                        padding: '48px',
                        color: '#94a3b8',
                    }}>
                        <p style={{ fontSize: '18px', margin: '0 0 16px 0' }}>No servers found</p>
                        <p style={{ fontSize: '14px', margin: 0 }}>Unable to connect to Tank World Network</p>
                    </div>
                )}

                {/* Transfer History Dialog */}
                {showHistory && (
                    <TransferHistory onClose={() => setShowHistory(false)} />
                )}
            </div>
        </div>
    );
}

interface ServerCardProps {
    serverWithTanks: ServerWithTanks;
    onDeleteTank: (tankId: string, tankName: string) => void;
    onRefresh: () => void;
}

function ServerCard({ serverWithTanks, onDeleteTank, onRefresh }: ServerCardProps) {
    const { server, tanks } = serverWithTanks;

    const statusColor = server.status === 'online' ? '#22c55e' :
        server.status === 'degraded' ? '#f59e0b' : '#ef4444';

    const formatUptime = (seconds: number): string => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        }
        return `${minutes}m`;
    };

    const platformMeta = [
        server.platform,
        server.architecture,
        server.hardware_model,
        server.logical_cpus ? `${server.logical_cpus} logical CPUs` : null,
    ].filter(Boolean) as string[];

    return (
        <div style={{
            backgroundColor: '#1e293b',
            borderRadius: '12px',
            border: '2px solid #334155',
            overflow: 'hidden',
        }}>
            {/* Server Header */}
            <div style={{
                padding: '20px 24px',
                borderBottom: '1px solid #334155',
                backgroundColor: '#0f172a',
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                            <h2 style={{
                                margin: 0,
                                fontSize: '20px',
                                fontWeight: 600,
                                color: '#f1f5f9',
                            }}>
                                🖥️ {server.hostname}
                            </h2>
                            <span style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '12px',
                                color: statusColor,
                                fontWeight: 500,
                            }}>
                                <span style={{
                                    width: '8px',
                                    height: '8px',
                                    borderRadius: '50%',
                                    backgroundColor: statusColor,
                                }} />
                                {server.status.toUpperCase()}
                            </span>
                            <span style={{
                                fontSize: '11px',
                                backgroundColor: '#334155',
                                color: '#94a3b8',
                                padding: '2px 8px',
                                borderRadius: '4px',
                                fontWeight: 500,
                            }}>
                                v{server.version}
                            </span>
                        </div>
                        <div style={{ fontSize: '13px', color: '#94a3b8', display: 'flex', gap: '16px' }}>
                            <span>{server.host}:{server.port}</span>
                            <span>&bull;</span>
                            <span>Uptime: {formatUptime(server.uptime_seconds)}</span>
                            {server.cpu_percent != null && (
                                <>
                                    <span>&bull;</span>
                                    <span>CPU: {server.cpu_percent.toFixed(1)}%</span>
                                </>
                            )}
                            {server.memory_mb != null && (
                                <>
                                    <span>&bull;</span>
                                    <span>Memory: {server.memory_mb.toFixed(0)} MB</span>
                                </>
                            )}
                        </div>
                        {platformMeta.length > 0 && (
                            <div style={{
                                marginTop: '8px',
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '8px',
                                fontSize: '12px',
                                color: '#cbd5e1',
                            }}>
                                {platformMeta.map((detail) => (
                                    <span key={detail} style={{
                                        backgroundColor: '#0b1728',
                                        border: '1px solid #334155',
                                        padding: '4px 8px',
                                        borderRadius: '6px',
                                    }}>
                                        {detail}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                    <div style={{
                        textAlign: 'right',
                    }}>
                        <div style={{ fontSize: '28px', fontWeight: 700, color: '#3b82f6' }}>
                            {tanks.length}
                        </div>
                        <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                            tank{tanks.length !== 1 ? 's' : ''}
                        </div>
                    </div>
                </div>
            </div>

            {/* Tanks Grid */}
            <div style={{ padding: '20px' }}>
                {tanks.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '32px',
                        color: '#64748b',
                        fontSize: '14px',
                    }}>
                        No tanks running on this server
                    </div>
                ) : (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                        gap: '16px',
                    }}>
                        {tanks.map((tankStatus) => (
                            <TankCard
                                key={tankStatus.tank.tank_id}
                                tankStatus={tankStatus}
                                onDelete={() => onDeleteTank(tankStatus.tank.tank_id, tankStatus.tank.name)}
                                onRefresh={onRefresh}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

interface TankCardProps {
    tankStatus: TankStatus;
    onDelete: () => void;
    onRefresh: () => void;
}

/**
 * Mini performance chart for network dashboard
 */
function MiniPerformanceChart({ history }: { history: any[] }) {
    if (!history || history.length === 0) {
        return null;
    }

    const sortedHistory = [...history].sort((a, b) => a.hand - b.hand);
    const width = 300;
    const height = 80;
    const padding = { top: 10, right: 10, bottom: 20, left: 35 };
    const maxHand = Math.max(...sortedHistory.map((h) => h.hand), 1);
    const minHand = Math.min(...sortedHistory.map((h) => h.hand));
    const handRange = maxHand - minHand || 1;

    // Calculate fish average and standard values for each hand
    const chartData = sortedHistory.map((snapshot) => {
        const fishPlayers = snapshot.players.filter((p: any) => !p.is_standard && p.species !== 'plant');
        const standardPlayer = snapshot.players.find((p: any) => p.is_standard);

        const fishAvg = fishPlayers.length > 0
            ? fishPlayers.reduce((sum: number, p: any) => sum + p.net_energy, 0) / fishPlayers.length
            : 0;

        return {
            hand: snapshot.hand,
            fishAvg,
            standard: standardPlayer ? standardPlayer.net_energy : 0,
        };
    });

    const allValues = chartData.flatMap((d) => [d.fishAvg, d.standard]);
    const minValue = Math.min(0, ...allValues);
    const maxValue = Math.max(0, ...allValues);
    const range = maxValue - minValue || 1;

    const scaleX = (hand: number) =>
        padding.left + ((hand - minHand) / handRange) * (width - padding.left - padding.right);
    const scaleY = (value: number) =>
        height - padding.bottom - ((value - minValue) / range) * (height - padding.top - padding.bottom);

    // Generate paths for fish average and standard
    const fishPath = chartData
        .map((point, i) => {
            const x = scaleX(point.hand);
            const y = scaleY(point.fishAvg);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        })
        .join(' ');

    const standardPath = chartData
        .map((point, i) => {
            const x = scaleX(point.hand);
            const y = scaleY(point.standard);
            return `${i === 0 ? 'M' : 'L'}${x},${y}`;
        })
        .join(' ');

    const zeroY = scaleY(0);

    return (
        <svg width={width} height={height} style={{ display: 'block', margin: '0 auto' }}>
            {/* Zero line */}
            <line
                x1={padding.left}
                y1={zeroY}
                x2={width - padding.right}
                y2={zeroY}
                stroke="#475569"
                strokeWidth="1"
                strokeDasharray="2,2"
            />

            {/* Standard line (baseline) */}
            <path
                d={standardPath}
                fill="none"
                stroke="#ef4444"
                strokeWidth="1.5"
                strokeDasharray="3,3"
            />

            {/* Fish average line */}
            <path
                d={fishPath}
                fill="none"
                stroke="#a855f7"
                strokeWidth="2"
            />

            {/* X-axis label */}
            <text
                x={width / 2}
                y={height - 2}
                fontSize="9"
                fill="#64748b"
                textAnchor="middle"
            >
                Hands
            </text>

            {/* Y-axis label */}
            <text
                x={5}
                y={height / 2}
                fontSize="9"
                fill="#64748b"
                textAnchor="start"
            >
                Net
            </text>
        </svg>
    );
}

function TankCard({ tankStatus, onDelete, onRefresh }: TankCardProps) {
    const { tank, running, client_count, frame, paused, fps } = tankStatus;
    const stats = tankStatus.stats ?? {
        fish_count: 0,
        generation: 0,
        max_generation: 0,
        total_energy: 0,
        fish_energy: 0,
        plant_energy: 0,
        poker_stats: undefined,
    };

    const [actionLoading, setActionLoading] = useState(false);
    const [fullState, setFullState] = useState<SimulationUpdate | null>(null);

    // Fetch full state periodically to get auto_evaluation data
    useEffect(() => {
        let mounted = true;

        const fetchFullState = async () => {
            try {
                const response = await fetch(`${config.apiBaseUrl}/api/tanks/${tank.tank_id}/snapshot`);
                if (!response.ok) return;
                if (mounted) {
                    const data = await response.json();
                    if (data && data.entities && Array.isArray(data.entities)) {
                        setFullState(data);
                    }
                }
            } catch (err) {
                // Silent fail - we have basic stats from tankStatus anyway
            }
        };

        fetchFullState();
        const interval = setInterval(fetchFullState, 1000); // Refresh every second

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, [tank.tank_id]);

    const sendTankCommand = async (action: 'pause' | 'resume') => {
        setActionLoading(true);
        try {
            const response = await fetch(`${config.apiBaseUrl}/api/tanks/${tank.tank_id}/${action}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || `Failed to ${action} tank`);
            }

            await onRefresh();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Tank command failed');
        } finally {
            setActionLoading(false);
        }
    };

    const statusText = running ? (paused ? 'Paused' : 'Running') : 'Stopped';
    const statusColor = running ? (paused ? '#f59e0b' : '#22c55e') : '#ef4444';

    const description = tank.description?.trim();
    const descriptionText = description && description.length > 0 ? description : 'No description provided';

    return (
        <div style={{
            backgroundColor: '#0f172a',
            borderRadius: '10px',
            border: '1px solid #1e293b',
            overflow: 'hidden',
        }}>
            {/* Card Header */}
            <div style={{
                padding: '14px 16px',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <div>
                    <h3 style={{
                        margin: 0,
                        fontSize: '16px',
                        fontWeight: 600,
                        color: '#f1f5f9',
                    }}>
                        {tank.name}
                    </h3>
                    <p style={{
                        margin: '4px 0 0 0',
                        fontSize: '12px',
                        color: '#94a3b8',
                    }}>
                        {descriptionText}
                    </p>
                </div>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                }}>
                    <span style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        backgroundColor: statusColor,
                    }} />
                    <span style={{
                        fontSize: '11px',
                        color: statusColor,
                        fontWeight: 500,
                    }}>
                        {statusText}
                    </span>
                </div>
            </div>

            {/* Card Body */}
            <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <TankThumbnail
                    tankId={tank.tank_id}
                    status={running ? (paused ? 'paused' : 'running') : 'stopped'}
                />

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: '10px',
                }}>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Fish</div>
                        <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                            {stats.fish_count?.toLocaleString() ?? '0'}
                        </div>
                    </div>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Gen</div>
                        <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                            {stats.max_generation?.toLocaleString() ?? '0'}
                        </div>
                    </div>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Frame</div>
                        <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                            {frame?.toLocaleString() ?? '0'}
                        </div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: 2 }}>
                            {fps != null ? `${fps.toFixed(1)} FPS` : 'FPS —'}
                        </div>
                    </div>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Clients</div>
                        <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                            {client_count}
                        </div>
                    </div>
                </div>

                {/* Energy Stats */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '10px',
                }}>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Total Energy</div>
                        <div style={{ fontSize: '16px', color: '#22c55e', fontWeight: 700 }}>
                            {stats.total_energy?.toFixed(0) ?? '0'}
                        </div>
                    </div>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Fish Energy</div>
                        <div style={{ fontSize: '16px', color: '#3b82f6', fontWeight: 700 }}>
                            {stats.fish_energy?.toFixed(0) ?? '0'}
                        </div>
                    </div>
                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                        <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Plant Energy</div>
                        <div style={{ fontSize: '16px', color: '#10b981', fontWeight: 700 }}>
                            {stats.plant_energy?.toFixed(0) ?? '0'}
                        </div>
                    </div>
                </div>

                {/* Poker Stats */}
                {stats.poker_stats && stats.poker_stats.total_games > 0 && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(3, 1fr)',
                        gap: '10px',
                    }}>
                        <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                            <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Poker Games</div>
                            <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                                {stats.poker_stats.total_games.toLocaleString()}
                            </div>
                        </div>
                        <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                            <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Win Rate</div>
                            <div style={{ fontSize: '16px', color: stats.poker_stats.win_rate && stats.poker_stats.win_rate > 50 ? '#22c55e' : '#e2e8f0', fontWeight: 700 }}>
                                {stats.poker_stats.win_rate != null ? `${stats.poker_stats.win_rate.toFixed(1)}%` : '—'}
                            </div>
                        </div>
                        <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                            <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Net Energy</div>
                            <div style={{ fontSize: '16px', color: stats.poker_stats.net_energy > 0 ? '#22c55e' : stats.poker_stats.net_energy < 0 ? '#ef4444' : '#e2e8f0', fontWeight: 700 }}>
                                {stats.poker_stats.net_energy > 0 ? '+' : ''}{stats.poker_stats.net_energy.toFixed(0)}
                            </div>
                        </div>
                    </div>
                )}

                {/* Additional Stats Row - Plant Transfer & Time */}
                {fullState?.stats && (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '10px',
                    }}>
                        {/* Plant-to-Fish Energy Transfer */}
                        {fullState.stats.poker_stats && (fullState.stats.poker_stats.total_plant_games ?? 0) > 0 && (() => {
                            const energyTransfer = fullState.stats.poker_stats.total_plant_energy_transferred || 0;
                            const isPositive = energyTransfer > 0;
                            const color = isPositive ? '#4ade80' : (energyTransfer < 0 ? '#f87171' : '#94a3b8');
                            return (
                                <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                                    <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>🌱→🐟 Transfer</div>
                                    <div style={{ fontSize: '16px', color, fontWeight: 700 }}>
                                        {isPositive ? '+' : ''}{energyTransfer.toFixed(0)}
                                    </div>
                                </div>
                            );
                        })()}
                        {/* Time of Day */}
                        <div style={{ background: '#1e293b', borderRadius: '6px', padding: '10px', border: '1px solid #334155' }}>
                            <div style={{ fontSize: '10px', color: '#94a3b8', marginBottom: 3 }}>Time</div>
                            <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                                {fullState.stats.time ?? '—'}
                            </div>
                        </div>
                    </div>
                )}

                {/* Auto-Evaluation Summary */}
                {fullState?.auto_evaluation && fullState.auto_evaluation.players && fullState.auto_evaluation.players.length > 0 && (() => {
                    const autoEval = fullState.auto_evaluation;
                    const fishPlayers = autoEval.players.filter((p: any) => !p.is_standard && p.species !== 'plant');
                    const standardPlayer = autoEval.players.find((p: any) => p.is_standard);

                    if (!fishPlayers.length || !standardPlayer) return null;

                    const fishAvgEnergy = fishPlayers.reduce((sum: number, p: any) => sum + p.net_energy, 0) / fishPlayers.length;
                    const standardEnergy = standardPlayer.net_energy;
                    const fishAvgWinRate = fishPlayers.reduce((sum: number, p: any) => sum + (p.win_rate || 0), 0) / fishPlayers.length;
                    const standardWinRate = standardPlayer.win_rate || 0;

                    const outperforming = fishAvgEnergy > standardEnergy;
                    const progress = autoEval.game_over ? '✓ Complete' : `${autoEval.hands_played}/${autoEval.hands_played + autoEval.hands_remaining} hands`;

                    return (
                        <div style={{
                            background: '#1e293b',
                            borderRadius: '8px',
                            padding: '12px',
                            border: '1px solid #334155',
                        }}>
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '8px'
                            }}>
                                <div style={{ fontSize: '11px', color: '#94a3b8', fontWeight: 600 }}>
                                    Poker Benchmark
                                </div>
                                <div style={{ fontSize: '10px', color: '#64748b' }}>
                                    {progress}
                                </div>
                            </div>

                            {/* Performance Stats */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: '1fr 1fr',
                                gap: '8px',
                                marginBottom: '10px'
                            }}>
                                <div style={{ background: '#0f172a', borderRadius: '4px', padding: '6px' }}>
                                    <div style={{ fontSize: '9px', color: '#94a3b8', marginBottom: 2 }}>Fish Avg vs Baseline</div>
                                    <div style={{
                                        fontSize: '14px',
                                        color: outperforming ? '#22c55e' : '#ef4444',
                                        fontWeight: 700
                                    }}>
                                        {fishAvgEnergy > 0 ? '+' : ''}{fishAvgEnergy.toFixed(0)} vs {standardEnergy > 0 ? '+' : ''}{standardEnergy.toFixed(0)}
                                    </div>
                                </div>
                                <div style={{ background: '#0f172a', borderRadius: '4px', padding: '6px' }}>
                                    <div style={{ fontSize: '9px', color: '#94a3b8', marginBottom: 2 }}>Win Rate</div>
                                    <div style={{
                                        fontSize: '14px',
                                        color: fishAvgWinRate > standardWinRate ? '#22c55e' : '#e2e8f0',
                                        fontWeight: 700
                                    }}>
                                        {fishAvgWinRate.toFixed(1)}% vs {standardWinRate.toFixed(1)}%
                                    </div>
                                </div>
                            </div>

                            {/* Mini Chart */}
                            {autoEval.performance_history && autoEval.performance_history.length > 0 && (
                                <MiniPerformanceChart history={autoEval.performance_history} />
                            )}
                        </div>
                    );
                })()}

                {/* Actions */}
                <div style={{
                    display: 'flex',
                    gap: '6px',
                    flexWrap: 'wrap',
                }}>
                    <button
                        onClick={() => sendTankCommand(paused ? 'resume' : 'pause')}
                        disabled={actionLoading || !running}
                        style={{
                            padding: '8px 10px',
                            backgroundColor: paused ? '#3b82f6' : '#f59e0b',
                            color: 'white',
                            border: 'none',
                            borderRadius: '5px',
                            cursor: (!running || actionLoading) ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '12px',
                            flex: '0 0 auto',
                        }}
                    >
                        {paused ? 'Resume' : 'Pause'}
                    </button>
                    <Link
                        to={`/tank/${tank.tank_id}`}
                        style={{
                            flex: 1,
                            padding: '8px',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            textDecoration: 'none',
                            borderRadius: '5px',
                            textAlign: 'center',
                            fontWeight: 600,
                            fontSize: '12px',
                            minWidth: '80px',
                        }}
                    >
                        View
                    </Link>
                    <button
                        onClick={onDelete}
                        style={{
                            padding: '8px 12px',
                            backgroundColor: 'transparent',
                            color: '#ef4444',
                            border: '1px solid #ef4444',
                            borderRadius: '5px',
                            cursor: 'pointer',
                            fontSize: '12px',
                        }}
                    >
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
}
