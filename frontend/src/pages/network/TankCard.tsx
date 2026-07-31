import { useState, useEffect } from 'react';
import { config, type WorldStatus } from '../../config';
import { TankThumbnail } from '../../components/TankThumbnail';
import type { SimulationUpdate } from '../../types/simulation';
import { PokerScoreDisplay } from '../../components/PokerScoreDisplay';
import { NetworkTankActions } from '../../components/NetworkTankActions';
import { MiniPerformanceChart } from './MiniPerformanceChart';
import type { AutoEvalPlayer } from './types';
import styles from '../NetworkDashboard.module.css';

interface TankCardProps {
    tankStatus: WorldStatus;
    onDelete: () => void;
    onRefresh: () => void;
}

export function TankCard({ tankStatus, onDelete, onRefresh }: TankCardProps) {
    const { world_id, name, frame_count, paused } = tankStatus;
    // Adapt old fields to new WorldStatus
    const description = tankStatus.description || '';
    const descriptionText = description && description.length > 0 ? description : 'No description provided';
    const running = true; // Worlds in the list are active

    // Stats are part of snapshot, not WorldStatus.
    // We'll fetch snapshot logic below.
    const [actionLoading, setActionLoading] = useState(false);
    const [fullState, setFullState] = useState<SimulationUpdate | null>(null);

    // Derived stats from fullState - stats are nested inside snapshot
    const stats = fullState?.snapshot?.stats ?? fullState?.stats;
    const detailsReady = fullState !== null;
    const fps = stats?.fps ?? 0;
    const fast_forward = stats?.fast_forward ?? false;
    const frame = fullState?.snapshot?.frame ?? fullState?.frame ?? frame_count;


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
            <div className={styles.tankCardHeader} style={{
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
                <div className={styles.tankStatus} style={{
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
            <div style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '10px' }} aria-busy={!detailsReady}>
                <TankThumbnail
                    tankId={world_id}
                    status={running ? (paused ? 'paused' : 'running') : 'stopped'}
                />

                {/* Core Stats - Single Row */}
                {!detailsReady && <div className={styles.snapshotLoading} role="status">Loading live snapshot…</div>}

                <div className={styles.tankStatsRow} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    background: '#1e293b',
                    borderRadius: '6px',
                    padding: '8px 12px',
                }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>Fish</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{detailsReady ? (stats?.fish_count ?? '—') : '—'}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>Gen</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{detailsReady ? (stats?.max_generation ?? '—') : '—'}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>Frame</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{detailsReady ? (frame?.toLocaleString() ?? '—') : '—'}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>FPS</div>
                        <div style={{ fontSize: '14px', color: '#e2e8f0', fontWeight: 700 }}>{detailsReady && typeof fps === 'number' ? fps.toFixed(0) : '—'}</div>
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
                        <div style={{ fontSize: '14px', color: '#3b82f6', fontWeight: 700 }}>{detailsReady ? (stats?.fish_energy?.toFixed(0) ?? '—') : '—'}</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '9px', color: '#94a3b8' }}>🌱 Energy</div>
                        <div style={{ fontSize: '14px', color: '#10b981', fontWeight: 700 }}>{detailsReady ? (stats?.plant_energy?.toFixed(0) ?? '—') : '—'}</div>
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
                {(fullState?.snapshot?.auto_evaluation ?? fullState?.auto_evaluation) &&
                    (() => {
                        const autoEval = fullState?.snapshot?.auto_evaluation ?? fullState?.auto_evaluation;
                        if (!autoEval || autoEval.players.length === 0) {
                            return null;
                        }

                        const history = autoEval.performance_history ?? [];
                        const latestSnapshot = history.length > 0 ? history[history.length - 1] : null;
                        const players = (latestSnapshot?.players ?? autoEval.players) as AutoEvalPlayer[];

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

                <div className={styles.tankActions}>
                    <NetworkTankActions
                        worldId={world_id}
                        name={name}
                        paused={paused}
                        fastForward={fast_forward}
                        disabled={actionLoading || !running}
                        onPause={() => sendTankCommand(paused ? 'resume' : 'pause')}
                        onFastForward={toggleFastForward}
                        onDelete={onDelete}
                    />
                </div>
            </div>
        </div>
    );
}
