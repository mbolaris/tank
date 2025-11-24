/**
 * NetworkDashboard - Tank World Net overview page
 *
 * Shows all tanks in the network and allows management
 */

import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { config, type TankStatus, type TanksListResponse } from '../config';
import { TankThumbnail } from '../components/TankThumbnail';
import { TransferHistory } from '../components/TransferHistory';

export function NetworkDashboard() {
    const [tanks, setTanks] = useState<TankStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [defaultTankId, setDefaultTankId] = useState<string | null>(null);

    // Create tank form state
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [newTankName, setNewTankName] = useState('');
    const [newTankDescription, setNewTankDescription] = useState('');
    const [creating, setCreating] = useState(false);

    // Transfer history state
    const [showHistory, setShowHistory] = useState(false);

    const fetchTanks = useCallback(async () => {
        try {
            setError(null);
            const response = await fetch(`${config.tanksApiUrl}?include_private=true`);
            if (!response.ok) {
                throw new Error(`Failed to fetch tanks: ${response.status}`);
            }
            const data: TanksListResponse = await response.json();
            setTanks(data.tanks);
            setDefaultTankId(data.default_tank_id);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load tanks');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchTanks();
        // Refresh every 5 seconds
        const interval = setInterval(fetchTanks, 5000);
        return () => clearInterval(interval);
    }, [fetchTanks]);

    const handleCreateTank = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTankName.trim()) return;

        setCreating(true);
        try {
            const params = new URLSearchParams({
                name: newTankName.trim(),
                description: newTankDescription.trim(),
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
            await fetchTanks();
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
            const response = await fetch(`${config.tanksApiUrl}/${tankId}`, {
                method: 'DELETE',
            });
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || `Failed to delete tank: ${response.status}`);
            }
            await fetchTanks();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete tank');
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
                maxWidth: '1200px',
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
                            {tanks.length} tank{tanks.length !== 1 ? 's' : ''} in network
                            {' '}&bull;{' '}
                            Server: {config.serverDisplay}
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
                            onClick={() => setShowCreateForm(true)}
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
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button
                                    type="submit"
                                    disabled={creating || !newTankName.trim()}
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
                {loading && tanks.length === 0 && (
                    <div style={{
                        textAlign: 'center',
                        padding: '48px',
                        color: '#94a3b8',
                    }}>
                        Loading tanks...
                    </div>
                )}

                {/* Tank Grid */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
                    gap: '20px',
                }}>
                    {tanks.map((tankStatus) => (
                        <TankCard
                            key={tankStatus.tank.tank_id}
                            tankStatus={tankStatus}
                            isDefault={tankStatus.tank.tank_id === defaultTankId}
                            onDelete={() => handleDeleteTank(tankStatus.tank.tank_id, tankStatus.tank.name)}
                            onRefresh={fetchTanks}
                        />
                    ))}
                </div>

                {/* Empty State */}
                {!loading && tanks.length === 0 && !error && (
                    <div style={{
                        textAlign: 'center',
                        padding: '48px',
                        color: '#94a3b8',
                    }}>
                        <p style={{ fontSize: '18px', margin: '0 0 16px 0' }}>No tanks found</p>
                        <p style={{ fontSize: '14px', margin: 0 }}>Create your first tank to get started</p>
                    </div>
                )}
            </div>
        </div>
    );
}

interface TankCardProps {
    tankStatus: TankStatus;
    isDefault: boolean;
    onDelete: () => void;
    onRefresh: () => void;
}

function TankCard({ tankStatus, isDefault, onDelete, onRefresh }: TankCardProps) {
    const { tank, running, client_count, frame, paused } = tankStatus;
    const stats = tankStatus.stats ?? {
        fish_count: 0,
        generation: 0,
        max_generation: 0,
        total_energy: 0,
        fish_energy: 0,
        plant_energy: 0,
    };

    const [actionLoading, setActionLoading] = useState(false);

    const sendTankCommand = async (action: 'pause' | 'resume' | 'start' | 'stop') => {
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

    return (
        <div style={{
            backgroundColor: '#1e293b',
            borderRadius: '12px',
            border: isDefault ? '2px solid #3b82f6' : '1px solid #334155',
            overflow: 'hidden',
        }}>
            {/* Card Header */}
            <div style={{
                padding: '16px 20px',
                borderBottom: '1px solid #334155',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <div>
                    <h3 style={{
                        margin: 0,
                        fontSize: '18px',
                        fontWeight: 600,
                        color: '#f1f5f9',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                    }}>
                        {tank.name}
                        {isDefault && (
                            <span style={{
                                fontSize: '10px',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                fontWeight: 500,
                            }}>
                                DEFAULT
                            </span>
                        )}
                    </h3>
                    {tank.description && (
                        <p style={{
                            margin: '4px 0 0 0',
                            fontSize: '13px',
                            color: '#94a3b8',
                        }}>
                            {tank.description}
                        </p>
                    )}
                </div>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                }}>
                    <span style={{
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        backgroundColor: statusColor,
                    }} />
                    <span style={{
                        fontSize: '12px',
                        color: statusColor,
                        fontWeight: 500,
                    }}>
                        {statusText}
                    </span>
                </div>
            </div>

            {/* Card Body */}
            <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <TankThumbnail
                    tankId={tank.tank_id}
                    status={running ? (paused ? 'paused' : 'running') : 'stopped'}
                />

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '12px',
                }}>
                    <div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '2px' }}>Frame</div>
                        <div style={{ fontSize: '16px', fontWeight: 600, color: '#e2e8f0' }}>
                            {frame.toLocaleString()}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '2px' }}>Connections</div>
                        <div style={{ fontSize: '16px', fontWeight: 600, color: '#e2e8f0' }}>
                            {client_count}
                        </div>
                    </div>
                    <div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginBottom: '2px' }}>Owner</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0' }}>
                            {tank.owner || 'System'}
                        </div>
                    </div>
                </div>

                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '12px',
                }}>
                    <div style={{ background: '#0f172a', borderRadius: '8px', padding: '12px', border: '1px solid #1f2937' }}>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: 4 }}>Fish</div>
                        <div style={{ fontSize: '18px', color: '#e2e8f0', fontWeight: 700 }}>
                            {stats.fish_count.toLocaleString()}
                        </div>
                    </div>
                    <div style={{ background: '#0f172a', borderRadius: '8px', padding: '12px', border: '1px solid #1f2937' }}>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: 4 }}>Max Generation</div>
                        <div style={{ fontSize: '18px', color: '#e2e8f0', fontWeight: 700 }}>
                            {stats.max_generation.toLocaleString()}
                        </div>
                        <div style={{ fontSize: '11px', color: '#64748b', marginTop: 4 }}>
                            {stats.total_extinctions ?? 0} extinction{(stats.total_extinctions ?? 0) !== 1 ? 's' : ''}
                        </div>
                    </div>
                    <div style={{ background: '#0f172a', borderRadius: '8px', padding: '12px', border: '1px solid #1f2937' }}>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginBottom: 4 }}>Energy</div>
                        <div style={{ fontSize: '16px', color: '#e2e8f0', fontWeight: 700 }}>
                            {Math.round(stats.total_energy).toLocaleString()} total
                        </div>
                        <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: 4, display: 'flex', gap: 8 }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ fontSize: 12 }}>🐟</span>
                                <span>{Math.round(stats.fish_energy).toLocaleString()}</span>
                            </span>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                <span style={{ fontSize: 12 }}>🌱</span>
                                <span>{Math.round(stats.plant_energy).toLocaleString()}</span>
                            </span>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div style={{
                    display: 'flex',
                    gap: '8px',
                    flexWrap: 'wrap',
                    alignItems: 'stretch',
                }}>
                    <button
                        onClick={() => sendTankCommand('start')}
                        disabled={actionLoading || running}
                        style={{
                            padding: '10px 12px',
                            backgroundColor: running ? '#1f2937' : (actionLoading ? '#166534' : '#22c55e'),
                            color: running ? '#94a3b8' : 'white',
                            border: '1px solid #22c55e',
                            borderRadius: '6px',
                            cursor: (actionLoading || running) ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '14px',
                            flex: '0 0 auto',
                            opacity: actionLoading ? 0.7 : 1,
                        }}
                    >
                        {actionLoading ? 'Starting...' : 'Start'}
                    </button>
                    <button
                        onClick={() => sendTankCommand(paused ? 'resume' : 'pause')}
                        disabled={actionLoading || !running}
                        title={paused ? 'Resume simulation from current state' : 'Pause simulation (keeps state)'}
                        style={{
                            padding: '10px 12px',
                            backgroundColor: paused ? (actionLoading ? '#1e3a8a' : '#3b82f6') : (actionLoading ? '#92400e' : '#f59e0b'),
                            color: 'white',
                            border: '1px solid #334155',
                            borderRadius: '6px',
                            cursor: (!running || actionLoading) ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '14px',
                            flex: '0 0 auto',
                            opacity: actionLoading ? 0.7 : 1,
                        }}
                    >
                        {actionLoading ? (paused ? 'Resuming...' : 'Pausing...') : (paused ? 'Resume' : 'Pause')}
                    </button>
                    <button
                        onClick={() => sendTankCommand('stop')}
                        disabled={actionLoading || !running}
                        title="Stop simulation completely (resets state)"
                        style={{
                            padding: '10px 12px',
                            backgroundColor: actionLoading ? '#7f1d1d' : '#ef4444',
                            color: 'white',
                            border: '1px solid #ef4444',
                            borderRadius: '6px',
                            cursor: (!running || actionLoading) ? 'not-allowed' : 'pointer',
                            fontWeight: 600,
                            fontSize: '14px',
                            flex: '0 0 auto',
                            opacity: actionLoading ? 0.7 : 1,
                        }}
                    >
                        {actionLoading ? 'Stopping...' : 'Stop'}
                    </button>
                    <Link
                        to={`/tank/${tank.tank_id}`}
                        style={{
                            flex: 1,
                            padding: '10px',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            textDecoration: 'none',
                            borderRadius: '6px',
                            textAlign: 'center',
                            fontWeight: 600,
                            fontSize: '14px',
                            minWidth: '120px',
                        }}
                    >
                        View Tank
                    </Link>
                    {!isDefault && (
                        <button
                            onClick={onDelete}
                            style={{
                                padding: '10px 16px',
                                backgroundColor: 'transparent',
                                color: '#ef4444',
                                border: '1px solid #ef4444',
                                borderRadius: '6px',
                                cursor: 'pointer',
                                fontSize: '14px',
                                minWidth: '120px',
                            }}
                        >
                            Delete
                        </button>
                    )}
                </div>
            </div>

            {/* Transfer History Dialog */}
            {showHistory && (
                <TransferHistory onClose={() => setShowHistory(false)} />
            )}
        </div>
    );
}
