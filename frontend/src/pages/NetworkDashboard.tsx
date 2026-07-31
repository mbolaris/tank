/**
 * NetworkDashboard - Tank World Net overview page
 *
 * Shows all servers and their tanks in the network.
 *
 * This file is the page shell: it owns server fetching, the create/delete
 * actions, and the top-level states (loading, error, empty). The pieces it
 * composes live in ./network/ — one server's card, one tank's card, the
 * create form, and the poker mini-chart.
 */

import { useState, useEffect, useCallback } from 'react';
import { config, type ServerWithWorlds } from '../config';
import { TransferHistory } from '../components/TransferHistory';
import { TankNetworkMap } from '../components/TankNetworkMap';
import { ServerCard } from './network/ServerCard';
import { CreateTankForm } from './network/CreateTankForm';
import styles from './NetworkDashboard.module.css';

interface ServersResponse {
    servers: ServerWithWorlds[];
}

export function NetworkDashboard() {
    const [servers, setServers] = useState<ServerWithWorlds[]>([]);
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

    const totalWorlds = servers.reduce((sum, s) => sum + s.worlds.length, 0);

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
            const name = newTankName.trim() || `World ${totalWorlds + 1}`;
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
            setNewTankName(`World ${totalWorlds + 1}`);
        }
        if (!selectedServerId && servers[0]) {
            setSelectedServerId(servers[0].server.server_id);
        }
    };

    return (
        <div className={styles.page} style={{
            minHeight: '100vh',
            backgroundColor: '#0a0f1a',
            color: '#e2e8f0',
            padding: '24px',
        }}>
            <div className={styles.content} style={{
                maxWidth: '1400px',
                margin: '0 auto',
            }}>
                {/* Header */}
                <div className={styles.dashboardHeader} style={{
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
                            {totalWorlds} world{totalWorlds !== 1 ? 's' : ''}
                        </p>
                    </div>
                    <div className={styles.headerActions} style={{ display: 'flex', gap: '12px' }}>
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
                    <CreateTankForm
                        servers={servers}
                        name={newTankName}
                        onNameChange={setNewTankName}
                        description={newTankDescription}
                        onDescriptionChange={setNewTankDescription}
                        selectedServerId={selectedServerId}
                        onServerChange={setSelectedServerId}
                        creating={creating}
                        onSubmit={handleCreateTank}
                        onCancel={() => setShowCreateForm(false)}
                    />
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
                    {servers.map((serverWithWorlds) => (
                        <ServerCard
                            key={serverWithWorlds.server.server_id}
                            serverWithWorlds={serverWithWorlds}
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
