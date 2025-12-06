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
import { EcosystemStats } from './EcosystemStats';
import { HabitatInsights } from './HabitatInsights';
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
    const [showEffects, setShowEffects] = useState(true); // Toggle for energy bars and poker effects

    // Entity transfer state
    const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null);
    const [selectedEntityType, setSelectedEntityType] = useState<string | null>(null);
    const [showTransferDialog, setShowTransferDialog] = useState(false);
    const [transferMessage, setTransferMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    // Error handling state
    const [pokerError, setPokerError] = useState<string | null>(null);

    const handlePokerError = (message: string, error?: unknown) => {
        const errorDetail = error instanceof Error ? error.message : String(error ?? '');
        const fullMessage = errorDetail ? `${message}: ${errorDetail}` : message;
        setPokerError(fullMessage);
        // Auto-clear error after 5 seconds
        setTimeout(() => setPokerError(null), 5000);
    };



    // Process AI turns one at a time with delay for visual feedback
    const processAiTurnsWithDelay = async () => {
        const AI_TURN_DELAY = 1000; // ms to show each AI player's turn before they act

        const processNextAiTurn = async (): Promise<void> => {
            try {
                // Wait BEFORE the AI makes their move so user can see who's about to act
                await new Promise(resolve => setTimeout(resolve, AI_TURN_DELAY));

                const response = await sendCommandWithResponse({
                    command: 'poker_process_ai_turn',
                    data: {},
                });

                if (response.state) {
                    setPokerGameState(response.state);
                }

                // If an action was taken, process next AI turn
                if (response.action_taken) {
                    await processNextAiTurn();
                }
                // If no action taken (human_turn or game_over), we're done
            } catch (error) {
                handlePokerError('Failed to process AI turn', error);
            }
        };

        // Start processing AI turns (delay happens at the beginning of processNextAiTurn)
        await processNextAiTurn();
    };

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
                // Process AI turns if it's not the human's turn first
                if (!response.state.is_your_turn && !response.state.game_over) {
                    processAiTurnsWithDelay();
                }
            }
        } catch (error) {
            handlePokerError('Failed to start poker game', error);
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
                // Start processing AI turns after human action
                processAiTurnsWithDelay();
            }
        } catch (error) {
            handlePokerError('Failed to send poker action', error);
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
                // Process AI turns if it's not the human's turn first
                if (!response.state.is_your_turn && !response.state.game_over) {
                    processAiTurnsWithDelay();
                }
            }
        } catch (error) {
            handlePokerError('Failed to start new poker round', error);
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
                    fastForwardEnabled={state?.stats?.fast_forward}
                    showEffects={showEffects}
                    onToggleEffects={() => setShowEffects(!showEffects)}
                />
            </div>

            {/* Tank simulation */}
            <div className="top-section">
                <div className="canvas-wrapper">
                    <Canvas
                        state={state}
                        width={1088}
                        height={612}
                        onEntityClick={handleEntityClick}
                        selectedEntityId={selectedEntityId}
                        showEffects={showEffects}
                    />
                    <div className="canvas-glow" aria-hidden />
                </div>
            </div>

            {/* Poker Game - Just below Tank */}
            {
                showPokerGame && (
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
                )
            }

            {/* Simulation Stats Panel */}
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                <div className="glass-panel" style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '32px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}
                            style={{
                                width: 8, height: 8, borderRadius: '50%',
                                background: isConnected ? 'var(--color-success)' : 'var(--color-warning)',
                                boxShadow: isConnected ? '0 0 8px var(--color-success)' : 'none'
                            }}
                        />
                        <span style={{ color: 'var(--color-text-muted)', fontSize: '12px', fontWeight: 600, letterSpacing: '0.05em' }}>
                            {isConnected ? 'LIVE' : 'OFFLINE'}
                        </span>
                    </div>

                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>SIMULATION FRAME</span>
                        <span style={{ color: 'var(--color-text-main)', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500 }}>
                            {state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'}
                        </span>
                    </div>

                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />

                    {state?.stats?.fps !== undefined && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--color-text-dim)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>FPS</span>
                            <span style={{ color: 'var(--color-text-main)', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500 }}>
                                {state.stats.fps.toFixed(1)}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Ecosystem Stats */}
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                <EcosystemStats stats={state?.stats ?? null} />
                <HabitatInsights state={state} />
            </div>

            {/* Evolution Progress */}
            {
                state?.auto_evaluation && (
                    <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                        <AutoEvaluateDisplay stats={state.auto_evaluation} loading={false} />
                    </div>
                )
            }

            {/* Poker Dashboard - Leaderboard & Activity */}
            {
                state?.poker_leaderboard && state?.poker_events && (
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
                )
            }

            {/* Phylogenetic Tree - Full Screen Overlay */}
            {
                showTree && (
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
                )
            }

            {/* Transfer Dialog */}
            {
                showTransferDialog && selectedEntityId !== null && selectedEntityType !== null && state?.tank_id && (
                    <TransferDialog
                        entityId={selectedEntityId}
                        entityType={selectedEntityType}
                        sourceTankId={state.tank_id}
                        sourceTankName={state.tank_id}
                        onClose={handleCloseTransferDialog}
                        onTransferComplete={handleTransferComplete}
                    />
                )
            }

            {/* Transfer Notification */}
            {
                transferMessage && (
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
                )
            }

            {/* Poker Error Notification */}
            {
                pokerError && (
                    <div
                        style={{
                            position: 'fixed',
                            bottom: transferMessage ? '90px' : '20px',
                            right: '20px',
                            padding: '16px 20px',
                            borderRadius: '8px',
                            backgroundColor: '#7f1d1d',
                            color: '#fecaca',
                            border: '1px solid #ef4444',
                            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
                            zIndex: 1001,
                            maxWidth: '400px',
                            fontWeight: 500,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                        }}
                    >
                        <span>⚠️</span>
                        <span>{pokerError}</span>
                        <button
                            onClick={() => setPokerError(null)}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: '#fecaca',
                                cursor: 'pointer',
                                padding: '0 4px',
                                fontSize: '16px',
                            }}
                        >
                            ✕
                        </button>
                    </div>
                )
            }
        </>
    );
}
