/**
 * TankView component - displays a single tank simulation with controls
 */

import { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { Canvas } from './Canvas';
import { ControlPanel } from './ControlPanel';
import { PhylogeneticTree } from './PhylogeneticTree';
import { PokerGame } from './PokerGame';
import { PokerLeaderboard } from './PokerLeaderboard';
import PokerEvents from './PokerEvents';
import { AutoEvaluateDisplay } from './AutoEvaluateDisplay';
import { TransferDialog } from './TransferDialog';
import type { PokerGameState } from '../types/simulation';

interface TankViewProps {
    tankId?: string;
}

export function TankView({ tankId }: TankViewProps) {
    const { state, isConnected, sendCommand, sendCommandWithResponse } = useWebSocket(tankId);
    const [pokerGameState, setPokerGameState] = useState<PokerGameState | null>(null);
    const [showPokerGame, setShowPokerGame] = useState(false);
    const [pokerLoading, setPokerLoading] = useState(false);
    const [showTree, setShowTree] = useState(false);
    const [showLeaderboard, setShowLeaderboard] = useState(false);

    // Entity transfer state
    const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null);
    const [selectedEntityType, setSelectedEntityType] = useState<string | null>(null);
    const [showTransferDialog, setShowTransferDialog] = useState(false);
    const [transferMessage, setTransferMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    const maxGeneration = state?.stats
        ? state.stats.max_generation ?? state.stats.generation ?? 0
        : 0;

    const handleStartPoker = async () => {
        try {
            setPokerLoading(true);
            setShowPokerGame(true);
            const response = await sendCommandWithResponse({
                command: 'start_poker',
                data: { energy: 500 },
            });
            if (response.success === false) {
                alert(response.error || 'Failed to start poker game');
                setShowPokerGame(false);
            } else if (response.state) {
                setPokerGameState(response.state);
            }
        } catch {
            alert('Failed to start poker game. Please try again.');
            setShowPokerGame(false);
        } finally {
            setPokerLoading(false);
        }
    };

    const handlePokerAction = async (action: string, amount?: number) => {
        try {
            setPokerLoading(true);
            const response = await sendCommandWithResponse({
                command: 'poker_action',
                data: { action, amount: amount || 0 },
            });
            if (response.success === false) {
                alert(response.error || 'Invalid action');
            } else if (response.state) {
                setPokerGameState(response.state);
            }
        } catch {
            alert('Failed to send action. Please try again.');
        } finally {
            setPokerLoading(false);
        }
    };

    const handleClosePoker = () => {
        setShowPokerGame(false);
        setPokerGameState(null);
    };

    const handleNewRound = async () => {
        try {
            setPokerLoading(true);
            const response = await sendCommandWithResponse({
                command: 'poker_new_round',
                data: {},
            });
            if (response.success === false) {
                alert(response.error || 'Failed to start new round');
            } else if (response.state) {
                setPokerGameState(response.state);
            }
        } catch {
            alert('Failed to start new round. Please try again.');
        } finally {
            setPokerLoading(false);
        }
    };

    const handleGetAutopilotAction = async () => {
        const response = await sendCommandWithResponse({
            command: 'poker_autopilot_action',
            data: {},
        });
        return response as { success: boolean; action: string; amount: number };
    };

    const handleEntityClick = (entityId: number, entityType: string) => {
        setSelectedEntityId(entityId);
        setSelectedEntityType(entityType);
        setShowTransferDialog(true);
    };

    const handleTransferComplete = (success: boolean, message: string) => {
        setTransferMessage({ type: success ? 'success' : 'error', text: message });
        setSelectedEntityId(null);
        setSelectedEntityType(null);

        // Clear message after 5 seconds
        setTimeout(() => setTransferMessage(null), 5000);
    };

    const handleCloseTransferDialog = () => {
        setShowTransferDialog(false);
        setSelectedEntityId(null);
        setSelectedEntityType(null);
    };

    const pokerStats = state?.stats?.poker_stats;

    return (
        <>
            {/* Single row of compact controls */}
            <div style={{
                display: 'flex',
                gap: '16px',
                alignItems: 'center',
                marginBottom: '20px',
                width: '100%',
                maxWidth: '1140px',
                marginLeft: 'auto',
                marginRight: 'auto'
            }}>
                <ControlPanel
                    onCommand={sendCommand}
                    isConnected={isConnected}
                    onPlayPoker={handleStartPoker}
                    showTree={showTree}
                    onToggleTree={() => setShowTree(!showTree)}
                />
            </div>

            {/* Tank simulation */}
            <div className="top-section">
                <div className="canvas-wrapper">
                    <div className="canvas-meta-compact">
                        <span className={`status-badge ${isConnected ? 'online' : 'offline'}`}>
                            {isConnected ? 'Connected' : 'Waiting'}
                        </span>
                        <span className="meta-item">
                            <span className="meta-label">Sim</span>
                            <span className="meta-value-wide">{state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'}</span>
                            <span>frames</span>
                            {state?.stats?.fps !== undefined && (
                                <span style={{ marginLeft: '8px', color: '#94a3b8', fontSize: '12px' }}>
                                    ({state.stats.fps.toFixed(1)} FPS)
                                </span>
                            )}
                        </span>
                        <span className="meta-item">
                            <span className="meta-label">Pop</span>
                            <span className="meta-value">{state?.stats?.fish_count ?? 0}</span>
                            <span>fish</span>
                            <span className="meta-sub">Gen {maxGeneration}</span>
                        </span>
                        <span className="meta-item" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                            <span className="meta-label">Energy</span>
                            <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                    <span style={{ fontSize: 10 }}>🐟</span>
                                    <span style={{ color: '#3b82f6' }}>{state?.stats?.fish_energy ? Math.round(state.stats.fish_energy).toLocaleString() : '0'}</span>
                                </span>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                    <span style={{ fontSize: 10 }}>🌱</span>
                                    <span style={{ color: '#4ade80' }}>{state?.stats?.plant_energy ? Math.round(state.stats.plant_energy).toLocaleString() : '0'}</span>
                                </span>
                            </span>
                            {state?.stats?.poker_stats && (state.stats.poker_stats.total_plant_games ?? 0) > 0 && (() => {
                                const energyTransfer = state.stats.poker_stats.total_plant_energy_transferred || 0;
                                const isPositive = energyTransfer > 0;
                                const color = isPositive ? '#4ade80' : (energyTransfer < 0 ? '#f87171' : '#94a3b8');
                                const prefix = isPositive ? '+' : '';
                                return (
                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, marginLeft: 8 }}>
                                        <span style={{ fontSize: 12 }}>🌱⚡→🐟</span>
                                        <span style={{ color, fontWeight: 600 }}>{prefix}{energyTransfer.toFixed(0)}</span>
                                    </span>
                                );
                            })()}
                        </span>
                        {pokerStats && (
                            (() => {
                                const fishGames = state?.stats?.poker_stats?.total_fish_games ?? (state?.poker_events || []).filter((e: any) => !e.is_plant).length;
                                const plantGames = state?.stats?.poker_stats?.total_plant_games ?? (state?.poker_events || []).filter((e: any) => e.is_plant).length;

                                return (
                                    <span className="meta-item" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <span className="meta-label">Poker</span>
                                        <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                                <span style={{ fontSize: 10 }}>🐟</span>
                                                <span style={{ color: '#3b82f6' }}>{fishGames}</span>
                                            </span>
                                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                                                <span style={{ fontSize: 10 }}>🌱</span>
                                                <span style={{ color: '#4ade80' }}>{plantGames}</span>
                                            </span>
                                        </span>
                                    </span>
                                );
                            })()
                        )}
                        <span className="meta-item">
                            <span className="meta-label">Time</span>
                            <span>{state?.stats?.time ?? '—'}</span>
                        </span>
                    </div>
                    <Canvas
                        state={state}
                        width={1088}
                        height={612}
                        onEntityClick={handleEntityClick}
                        selectedEntityId={selectedEntityId}
                    />
                    <div className="canvas-glow" aria-hidden />
                </div>
            </div>

            {/* Poker Game - Below Tank */}
            {showPokerGame && (
                <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                    <PokerGame
                        onClose={handleClosePoker}
                        onAction={handlePokerAction}
                        onNewRound={handleNewRound}
                        onGetAutopilotAction={handleGetAutopilotAction}
                        gameState={pokerGameState}
                        loading={pokerLoading}
                    />
                </div>
            )}

            {/* Evolution Progress */}
            {state?.auto_evaluation && (
                <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                    <AutoEvaluateDisplay stats={state.auto_evaluation} loading={false} />
                </div>
            )}

            {/* Poker Dashboard - Leaderboard & Activity */}
            {state?.poker_leaderboard && state?.poker_events && (
                <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '12px'
                    }}>
                        <h3 style={{ color: '#3b82f6', fontSize: '18px', margin: 0 }}>
                            Poker Dashboard
                        </h3>
                        {showLeaderboard && (
                            <button
                                onClick={() => setShowLeaderboard(false)}
                                style={{
                                    padding: '6px 12px',
                                    backgroundColor: '#1e293b',
                                    color: '#94a3b8',
                                    border: '1px solid #475569',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                }}
                            >
                                Collapse
                            </button>
                        )}
                    </div>

                    {/* Leaderboard & Activity Grid */}
                    {showLeaderboard && state?.poker_leaderboard && state?.poker_events && (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: '1fr 1fr',
                            gap: '16px'
                        }}>
                            <div style={{
                                backgroundColor: '#0f172a',
                                borderRadius: '12px',
                                padding: '16px',
                                border: '1px solid #334155'
                            }}>
                                <PokerLeaderboard leaderboard={state.poker_leaderboard} />
                            </div>
                            <div style={{
                                backgroundColor: '#0f172a',
                                borderRadius: '12px',
                                padding: '16px',
                                border: '1px solid #334155'
                            }}>
                                <PokerEvents events={state.poker_events} currentFrame={state.frame} />
                            </div>
                        </div>
                    )}

                    {/* Expand button when collapsed */}
                    {!showLeaderboard && state?.poker_leaderboard && (
                        <button
                            onClick={() => setShowLeaderboard(true)}
                            style={{
                                marginTop: '12px',
                                padding: '8px 16px',
                                backgroundColor: '#1e293b',
                                color: '#3b82f6',
                                border: '1px solid #475569',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600,
                                fontSize: '13px'
                            }}
                        >
                            Show Leaderboard & Activity
                        </button>
                    )}
                </div>
            )}

            {/* Phylogenetic Tree - Full Screen Overlay */}
            {showTree && (
                <div className="tree-overlay">
                    <div className="tree-content">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h2 style={{ color: '#00ff00', fontSize: '24px', margin: 0 }}>Phylogenetic Tree</h2>
                            <button
                                onClick={() => setShowTree(false)}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#94a3b8',
                                    fontSize: '24px',
                                    cursor: 'pointer'
                                }}
                            >
                                ✕
                            </button>
                        </div>
                        <PhylogeneticTree tankId={tankId} />
                    </div>
                </div>
            )}

            {/* Transfer Dialog */}
            {showTransferDialog && selectedEntityId !== null && selectedEntityType !== null && state?.tank_id && (
                <TransferDialog
                    entityId={selectedEntityId}
                    entityType={selectedEntityType}
                    sourceTankId={state.tank_id}
                    sourceTankName={state.tank_id}
                    onClose={handleCloseTransferDialog}
                    onTransferComplete={handleTransferComplete}
                />
            )}

            {/* Transfer Notification */}
            {transferMessage && (
                <div
                    style={{
                        position: 'fixed',
                        bottom: '20px',
                        right: '20px',
                        padding: '16px 20px',
                        borderRadius: '8px',
                        backgroundColor: transferMessage.type === 'success' ? '#166534' : '#7f1d1d',
                        color: transferMessage.type === 'success' ? '#bbf7d0' : '#fecaca',
                        border: `1px solid ${transferMessage.type === 'success' ? '#22c55e' : '#ef4444'}`,
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                        zIndex: 1001,
                        maxWidth: '400px',
                        fontWeight: 500,
                    }}
                >
                    {transferMessage.text}
                </div>
            )}
        </>
    );
}
