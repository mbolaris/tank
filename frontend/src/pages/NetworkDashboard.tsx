/**
 * NetworkDashboard - Tank World Net overview page
 *
 * Shows all servers and their tanks in the network
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { config, type WorldStatus, type ServerWithTanks } from '../config';
import { TankThumbnail } from '../components/TankThumbnail';
import { TransferHistory } from '../components/TransferHistory';
import { TankNetworkMap } from '../components/TankNetworkMap';
import type { SimulationUpdate, PokerPerformanceSnapshot } from '../types/simulation';
import { PokerScoreDisplay } from '../components/PokerScoreDisplay';

/** Player data from poker performance snapshots */
type SnapshotPlayer = PokerPerformanceSnapshot['players'][number];

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
        // Refresh every 5 seconds to avoid overwhelming the browser
        const interval = setInterval(fetchServers, 5000);
        return () => clearInterval(interval);
    }, [fetchServers]);

    const handleCreateTank = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedServerId) return;

        setCreating(true);
        try {
            const name = newTankName.trim() || `Tank ${totalTanks + 1}`;
            const response = await fetch(config.worldsApiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    world_type: 'tank',
                    name,
                    description: newTankDescription.trim(),
                }),
            });
            if (!response.ok) {
                throw new Error(`Failed to create world: ${response.status}`);
            }
            // Reset form and refresh
            setNewTankName('');
            setNewTankDescription('');
            setShowCreateForm(false);
            await fetchServers();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to create world');
        } finally {
            setCreating(false);
        }
    };

    const handleDeleteTank = async (tankId: string, tankName: string) => {
        if (!confirm(`Are you sure you want to delete "${tankName}"? This cannot be undone.`)) {
            return;
        }

        try {
            const response = await fetch(`${config.apiBaseUrl}/api/worlds/${tankId}`, {
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
                        {[...tanks].sort((a, b) => (b.frame_count ?? 0) - (a.frame_count ?? 0)).map((tankStatus) => (
                            <TankCard
                                key={tankStatus.world_id}
                                tankStatus={tankStatus}
                                onDelete={() => onDeleteTank(tankStatus.world_id, tankStatus.name)}
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
    tankStatus: WorldStatus;
    onDelete: () => void;
    onRefresh: () => void;
}

/**
 * Mini performance chart for network dashboard
 */
function MiniPerformanceChart({ history }: { history: PokerPerformanceSnapshot[] }) {
    if (!history || history.length === 0) {
        return null;
    }

    const sortedHistory = [...history].sort((a, b) => a.hand - b.hand);
    const width = 280;
    const height = 50;
    const padding = { top: 5, right: 5, bottom: 5, left: 25 };
    const maxHand = Math.max(...sortedHistory.map((h) => h.hand), 1);
    const minHand = Math.min(...sortedHistory.map((h) => h.hand));
    const handRange = maxHand - minHand || 1;

    // Calculate fish average and standard values for each hand
    const chartData = sortedHistory.map((snapshot) => {
        const fishPlayers = snapshot.players.filter((p: SnapshotPlayer) => !p.is_standard && p.species !== 'plant');
        const plantPlayers = snapshot.players.filter((p: SnapshotPlayer) => !p.is_standard && p.species === 'plant');
        const standardPlayer = snapshot.players.find((p: SnapshotPlayer) => p.is_standard);

        const fishAvg = fishPlayers.length > 0
            ? fishPlayers.reduce((sum: number, p: SnapshotPlayer) => sum + p.net_energy, 0) / fishPlayers.length
            : 0;
        const plantAvg = plantPlayers.length > 0
            ? plantPlayers.reduce((sum: number, p: SnapshotPlayer) => sum + p.net_energy, 0) / plantPlayers.length
            : null;

        return {
            hand: snapshot.hand,
            fishAvg,
            plantAvg,
            standard: standardPlayer ? standardPlayer.net_energy : 0,
        };
    });

    const values = chartData.flatMap((d) => [d.fishAvg, d.standard, d.plantAvg].filter((v): v is number => v !== null));
    const minValue = Math.min(0, ...values);
    const maxValue = Math.max(0, ...values);
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

    const hasPlantLine = chartData.some((point) => point.plantAvg !== null);
    const plantPath = hasPlantLine
        ? chartData
            .map((point, i) => {
                const plantValue = point.plantAvg ?? 0;
                const x = scaleX(point.hand);
                const y = scaleY(plantValue);
                return `${i === 0 ? 'M' : 'L'}${x},${y}`;
            })
            .join(' ')
        : '';

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

            {/* Plant average line */}
            {hasPlantLine && (
                <path
                    d={plantPath}
                    fill="none"
                    stroke="#22c55e"
                    strokeWidth="1.5"
                    strokeDasharray="3,3"
                />
            )}
        </svg>
    );
}




function TankCard({ tankStatus, onDelete, onRefresh }: TankCardProps) {
    const { world_id, name, frame_count, paused } = tankStatus;
    // Adapt old fields to new WorldStatus
    const description = tankStatus.description || '';
    const descriptionText = description && description.length > 0 ? description : 'No description provided';
    const running = true; // Worlds in the list are active

    // Stats are part of snapshot, not WorldStatus. 
    // We'll fetch snapshot logic below.
    const [actionLoading, setActionLoading] = useState(false);
    const [fullState, setFullState] = useState<SimulationUpdate | null>(null);

    // Derived stats from fullState
    const stats = fullState?.stats;
    const fps = (stats as any)?.fps ?? 0;
    const fast_forward = (stats as any)?.fast_forward ?? false;
    const frame = fullState?.frame ?? frame_count;

    // Fetch full state periodically
    useEffect(() => {
        let mounted = true;

        const fetchFullState = async () => {
            try {
                const response = await fetch(`${config.apiBaseUrl}/api/worlds/${world_id}/snapshot`);
                if (!response.ok) return;
                if (mounted) {
                    const data = await response.json();
                    if (data && (data.entities || data.snapshot)) {
                        setFullState(data);
                    }
                }
            } catch {
                // Silent fail
            }
        };

        fetchFullState();
        const interval = setInterval(fetchFullState, 3000);

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, [world_id]);

    const sendTankCommand = async (action: 'pause' | 'resume') => {
        setActionLoading(true);
        try {
            const response = await fetch(`${config.apiBaseUrl}/api/worlds/${world_id}/${action}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || `Failed to ${action} world`);
            }

            await onRefresh();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'World command failed');
        } finally {
            setActionLoading(false);
        }
    };

    const toggleFastForward = async () => {
        setActionLoading(true);
        try {
            // Note: We need current fast_forward state. 
            // Since WorldStatus doesn't have it, we rely on implicit toggle or fullState
            const newEnabled = !fast_forward;
            const response = await fetch(
                `${config.apiBaseUrl}/api/worlds/${world_id}/fast_forward?enabled=${newEnabled}`,
                { method: 'POST' }
            );

            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || 'Failed to toggle fast forward');
            }

            // fetchFullState will update UI eventually
            await onRefresh();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Fast forward toggle failed');
        } finally {
            setActionLoading(false);
        }
    };

    const statusText = running ? (paused ? 'Paused' : 'Running') : 'Stopped';
    const statusColor = running ? (paused ? '#f59e0b' : '#22c55e') : '#ef4444';

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
                        {name}
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
            <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <TankThumbnail
                    tankId={world_id}
                    status={running ? (paused ? 'paused' : 'running') : 'stopped'}
                />

                {/* Core Stats - Single Row */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    background: '#1e293b',
                    borderRadius: '6px',
                    padding: '8px 12px',
                }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>Fish</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{stats?.fish_count ?? 0}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>Gen</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{stats?.max_generation ?? 0}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>Frame</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{frame?.toLocaleString() ?? 0}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>FPS</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{typeof fps === 'number' ? fps.toFixed(0) : '—'}</div>
                    </div>
                </div>

                {/* Energy Row */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-around',
                    background: '#1e293b',
                    borderRadius: '6px',
                    padding: '8px 12px',
                }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>🐟 Energy</div>
                        <div style={{ fontSize: '14px', color: '#3b82f6', fontWeight: 700 }}>{stats?.fish_energy?.toFixed(0) ?? 0}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>🌱 Energy</div>
                        <div style={{ fontSize: '14px', color: '#10b981', fontWeight: 700 }}>{stats?.plant_energy?.toFixed(0) ?? 0}</div>
                    </div>
                    {stats?.poker_stats && stats.poker_stats.total_games > 0 && (
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '9px', color: '#94a3b8' }}>🃏 Games</div>
                            <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{(stats.poker_stats.total_games / 1000).toFixed(0)}k</div>
                        </div>
                    )}
                </div>

                {/* Poker Score Row */}
                <PokerScoreDisplay
                    score={stats?.poker_score}
                    elo={stats?.poker_elo}
                    history={stats?.poker_elo && stats?.poker_elo_history && stats?.poker_elo_history.length > 0
                        ? stats.poker_elo_history
                        : (stats?.poker_score_history || [])}
                    isLoading={stats?.poker_score === undefined && stats?.poker_elo === undefined}
                />

                {/* Auto-Evaluation Summary */}
                {fullState?.auto_evaluation && fullState.auto_evaluation.players && fullState.auto_evaluation.players.length > 0 && (() => {
                    const autoEval = fullState.auto_evaluation!;
                    const history = autoEval.performance_history || [];
                    const latestSnapshot = history.length > 0 ? history[history.length - 1] : null;
                    const players = latestSnapshot?.players || autoEval.players;

                    const fishPlayers = players.filter((p) => !p.is_standard && p.species !== 'plant');
                    const plantPlayers = players.filter((p) => !p.is_standard && p.species === 'plant');
                    const standardPlayer = players.find((p) => p.is_standard);

                    if (!fishPlayers.length || !standardPlayer) return null;

                    const fishAvg = fishPlayers.reduce((sum, p) => sum + p.net_energy, 0) / fishPlayers.length;
                    const plantAvg = plantPlayers.length > 0
                        ? plantPlayers.reduce((sum, p) => sum + p.net_energy, 0) / plantPlayers.length
                        : null;
                    const baseline = standardPlayer.net_energy;
                    const hasPlants = plantAvg !== null;

                    // Compact inline scoreboard
                    const formatProfit = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(0)}`;

                    return (
                        <div style={{
                            background: '#0f172a',
                            borderRadius: '6px',
                            padding: '8px 10px',
                        }}>
                            {/* Compact single-line scoreboard */}
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                gap: '8px',
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                    <span style={{
                                        fontSize: '12px',
                                        fontWeight: 700,
                                        color: fishAvg >= 0 ? '#22c55e' : '#ef4444'
                                    }}>
                                        🐟 {formatProfit(fishAvg)}
                                    </span>
                                    {hasPlants && (
                                        <span style={{
                                            fontSize: '12px',
                                            fontWeight: 700,
                                            color: plantAvg! >= 0 ? '#22c55e' : '#ef4444'
                                        }}>
                                            🌱 {formatProfit(plantAvg!)}
                                        </span>
                                    )}
                                    <span style={{
                                        fontSize: '12px',
                                        fontWeight: 700,
                                        color: baseline >= 0 ? '#22c55e' : '#ef4444'
                                    }}>
                                        📊 {formatProfit(baseline)}
                                    </span>
                                </div>
                                <span style={{ fontSize: '9px', color: '#64748b' }}>
                                    {autoEval.hands_played}h
                                </span>
                            </div>

                            {/* Mini Chart - more compact */}
                            {history.length > 1 && (
                                <div style={{ marginTop: '6px' }}>
                                    <MiniPerformanceChart history={history} />
                                </div>
                            )}
                        </div>
                    );
                })()}

                {/* Actions */}
                <div style={{
                    display: 'flex',
                    gap: '6px',
                }}>
                    <button
                        onClick={() => sendTankCommand(paused ? 'resume' : 'pause')}
                        disabled={actionLoading || !running}
                        style={{
                            padding: '6px 10px',
                            backgroundColor: paused ? '#3b82f6' : '#f59e0b',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: (!running || actionLoading) ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '11px',
                        }}
                    >
                        {paused ? '▶' : '⏸'}
                    </button>
                    <button
                        onClick={toggleFastForward}
                        disabled={actionLoading || !running}
                        style={{
                            padding: '6px 10px',
                            backgroundColor: fast_forward ? '#a855f7' : '#475569',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: (!running || actionLoading) ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '11px',
                        }}
                        title={fast_forward ? 'Normal Speed' : 'Fast Forward'}
                    >
                        {fast_forward ? '⏩' : '⏩'}
                    </button>
                    <Link
                        to={`/tank/${world_id}`}
                        style={{
                            flex: 1,
                            padding: '6px',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            textDecoration: 'none',
                            borderRadius: '4px',
                            textAlign: 'center',
                            fontWeight: 600,
                            fontSize: '11px',
                        }}
                    >
                        View
                    </Link>
                    <button
                        onClick={onDelete}
                        style={{
                            padding: '6px 10px',
                            backgroundColor: 'transparent',
                            color: '#ef4444',
                            border: '1px solid #ef4444',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '11px',
                        }}
                    >
                        ✕
                    </button>
                </div>
            </div>
        </div>
    );
}
