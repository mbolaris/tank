import { useState, useCallback } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { Canvas } from './Canvas';
import { ControlPanel } from './ControlPanel';
import { PhylogeneticTree } from './PhylogeneticTree';
import { PokerGame } from './PokerGame';
import { PokerLeaderboard } from './PokerLeaderboard';
import PokerEvents from './PokerEvents';
import { AutoEvaluateDisplay } from './AutoEvaluateDisplay';
import { EvolutionBenchmarkDisplay } from './EvolutionBenchmarkDisplay';
import { TransferDialog } from './TransferDialog';
import { EcosystemStats } from './EcosystemStats';
import { PokerScoreDisplay } from './PokerScoreDisplay';
import { ViewModeToggle } from './ViewModeToggle';
import { useViewMode } from '../hooks/useViewMode';
import { initRenderers } from '../renderers/init';
import { CollapsibleSection, Button } from './ui';

import type { PokerGameState } from '../types/simulation';

interface TankViewProps {
    tankId?: string;
}

export function TankView({ tankId }: TankViewProps) {
    const { state, isConnected, sendCommand, sendCommandWithResponse } = useWebSocket(tankId);
    const [pokerGameState, setPokerGameState] = useState<PokerGameState | null>(null);
    const [showPokerGame, setShowPokerGame] = useState(false);
    const [pokerLoading, setPokerLoading] = useState(false);
    const [showEffects, setShowEffects] = useState(true); // Toggle for energy bars and poker effects

    // Plant energy input control
    const [plantEnergyInput, setPlantEnergyInput] = useState(0.15); // Default from PLANT_MIN_ENERGY_GAIN

    const handlePlantEnergyChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const rate = parseFloat(e.target.value);
        setPlantEnergyInput(rate);
        sendCommand({ command: 'set_plant_energy_input', data: { rate } });
    }, [sendCommand]);

    // Entity transfer state
    const [selectedEntityId, setSelectedEntityId] = useState<number | null>(null);
    const [selectedEntityType, setSelectedEntityType] = useState<string | null>(null);
    const [showTransferDialog, setShowTransferDialog] = useState(false);
    const [transferMessage, setTransferMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    // Error handling state
    const [pokerError, setPokerError] = useState<string | null>(null);

    const { effectiveViewMode, setOverrideViewMode, petriMode, setPetriMode } = useViewMode(state?.view_mode as any);

    // Effective world type for rendering - when petriMode is enabled, use 'petri' renderer
    const effectiveWorldType = petriMode ? 'petri' : 'tank';

    // Ensure renderers are initialized
    initRenderers();


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
                    fastForwardEnabled={state?.stats?.fast_forward}
                    showEffects={showEffects}
                    onToggleEffects={() => setShowEffects(!showEffects)}
                />

                <ViewModeToggle
                    viewMode={effectiveViewMode}
                    onChange={setOverrideViewMode}
                    petriMode={petriMode}
                    onPetriModeChange={setPetriMode}
                />

                {/* Plant Energy Input Control */}
                <div className="glass-panel" style={{
                    padding: '8px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                }}>
                    <span style={{
                        color: 'var(--color-text-dim)',
                        fontSize: '11px',
                        fontWeight: 600,
                        letterSpacing: '0.05em',
                        whiteSpace: 'nowrap'
                    }}>
                        🌱 PLANT ENERGY
                    </span>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={plantEnergyInput}
                        onChange={handlePlantEnergyChange}
                        disabled={!isConnected}
                        style={{
                            width: '80px',
                            accentColor: '#4ade80',
                            cursor: isConnected ? 'pointer' : 'not-allowed',
                        }}
                    />
                    <span style={{
                        color: 'var(--color-text-main)',
                        fontFamily: 'var(--font-mono)',
                        fontSize: '12px',
                        minWidth: '40px',
                    }}>
                        {plantEnergyInput.toFixed(2)}
                    </span>
                </div>
            </div>

            {/* Simulation Stats Panel - Moved Above Tank */}
            <div style={{ marginBottom: '20px', width: '100%', maxWidth: '1140px', marginLeft: 'auto', marginRight: 'auto' }}>
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

                    {effectiveWorldType !== 'tank' && (
                        <>
                            <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{
                                    fontSize: '10px',
                                    fontWeight: 600,
                                    letterSpacing: '0.05em',
                                    backgroundColor: 'rgba(139, 92, 246, 0.2)',
                                    color: '#a78bfa',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                    textTransform: 'uppercase'
                                }}>
                                    {effectiveWorldType}
                                </span>
                            </div>
                        </>
                    )}

                    {/* Mode/View Debug Badge */}
                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />
                    <span style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        letterSpacing: '0.05em',
                        backgroundColor: 'rgba(59, 130, 246, 0.2)',
                        color: '#60a5fa',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontFamily: 'var(--font-mono)',
                    }}>
                        Mode: {state?.mode_id ?? 'tank'} | View: {effectiveViewMode}
                    </span>

                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>FRAME</span>
                        <span style={{ color: 'var(--color-text-main)', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500 }}>
                            {state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'}
                        </span>
                    </div>

                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />

                    {state?.stats?.fps !== undefined && (
                        <>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <span style={{ color: 'var(--color-text-dim)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>FPS</span>
                                <span style={{ color: 'var(--color-text-main)', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500 }}>
                                    {state.stats.fps.toFixed(1)}
                                </span>
                            </div>
                            <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />
                        </>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>POPULATION</span>
                        <span style={{ color: 'var(--color-text-main)', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500 }}>
                            {state?.stats?.fish_count ? state.stats.fish_count.toLocaleString() : '0'}
                        </span>
                    </div>

                    <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--color-text-dim)', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>MAX GEN</span>
                        <span style={{ color: 'var(--color-text-main)', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 500 }}>
                            {state?.stats ? (state.stats.max_generation ?? state.stats.generation ?? 0) : '0'}
                        </span>
                    </div>

                    {/* Poker Score - inline display for consistency with Network Dashboard */}
                    {(state?.stats?.poker_elo !== undefined || state?.stats?.poker_score !== undefined) && (
                        <>
                            <div style={{ width: '1px', height: '16px', background: 'rgba(255,255,255,0.1)' }} />
                            <PokerScoreDisplay
                                score={state.stats.poker_score}
                                elo={state.stats.poker_elo}
                                history={state.stats.poker_elo && state.stats.poker_elo_history && state.stats.poker_elo_history.length > 0
                                    ? state.stats.poker_elo_history
                                    : (state.stats.poker_score_history || [])}
                                compact={true}
                            />
                        </>
                    )}
                </div>
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
                        viewMode={effectiveViewMode}
                        worldType={effectiveWorldType}
                    />
                    <div className="canvas-glow" aria-hidden />
                </div>
            </div>

            {/* Poker Game - Collapsible Panel */}
            <div className="glass-panel" style={{ marginTop: '20px', width: '100%', maxWidth: '1140px', marginLeft: 'auto', marginRight: 'auto', padding: '16px', boxSizing: 'border-box' }}>
                <CollapsibleSection
                    title={
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                            <span style={{ fontSize: '16px', fontWeight: 600, color: '#a78bfa' }}>Poker Table</span>
                            {showPokerGame && (
                                <span style={{
                                    fontSize: '11px',
                                    backgroundColor: 'rgba(167, 139, 250, 0.2)',
                                    color: '#a78bfa',
                                    padding: '2px 8px',
                                    borderRadius: '4px'
                                }}>
                                    Active Game
                                </span>
                            )}
                        </div>
                    }
                    defaultExpanded={showPokerGame}
                >
                    <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'center' }}>
                        {!showPokerGame ? (
                            <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                                <div style={{ fontSize: '48px' }}>🎰</div>
                                <div style={{ color: 'var(--color-text-secondary)', marginBottom: '8px' }}>
                                    Ready to play a hand against the population?
                                </div>
                                <Button
                                    onClick={handleStartPoker}
                                    disabled={!isConnected || pokerLoading}
                                    variant="poker"
                                    style={{ padding: '12px 32px', fontSize: '16px' }}
                                >
                                    {pokerLoading ? 'Loading...' : '🃏 Sit Down & Play'}
                                </Button>
                            </div>
                        ) : (
                            <PokerGame
                                onClose={handleClosePoker}
                                onAction={handlePokerAction}
                                onNewRound={handleNewRound}
                                onGetAutopilotAction={handleGetAutopilotAction}
                                gameState={pokerGameState}
                                loading={pokerLoading}
                            />
                        )}
                    </div>
                </CollapsibleSection>
            </div>



            {/* Poker Skill Benchmark (bb/100) */}
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px', marginLeft: 'auto', marginRight: 'auto' }}>
                <EvolutionBenchmarkDisplay tankId={tankId} />
            </div>

            {/* Ecosystem Stats */}
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px', marginLeft: 'auto', marginRight: 'auto' }}>
                <EcosystemStats stats={state?.stats ?? null} />

            </div>

            {/* Evolution Progress */}
            {
                state?.auto_evaluation && (
                    <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px', marginLeft: 'auto', marginRight: 'auto' }}>
                        <AutoEvaluateDisplay stats={state.auto_evaluation} loading={false} />
                    </div>
                )
            }


            {/* Poker Dashboard - Leaderboard & Activity */}
            {state && (
                <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px', marginLeft: 'auto', marginRight: 'auto' }}>
                    <div className="glass-panel" style={{ padding: '16px' }}>
                        <CollapsibleSection
                            title={
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                                    <span style={{ fontSize: '16px', fontWeight: 600, color: '#93c5fd' }}>Poker Dashboard</span>
                                </div>
                            }
                            defaultExpanded={false}
                        >
                            <div style={{ marginTop: '16px' }}>
                                {/* Key Metrics Row */}
                                <div style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'repeat(5, 1fr)',
                                    gap: '12px',
                                    marginBottom: '16px'
                                }}>
                                    <div style={{
                                        backgroundColor: '#0f172a',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        border: '1px solid #334155',
                                        textAlign: 'center'
                                    }}>
                                        <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>Total Games</div>
                                        <div style={{ color: '#f1f5f9', fontSize: '18px', fontWeight: 700 }}>
                                            {state.stats?.poker_stats?.total_games?.toLocaleString() ?? 0}
                                        </div>
                                    </div>
                                    <div style={{
                                        backgroundColor: '#0f172a',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        border: '1px solid #334155',
                                        textAlign: 'center'
                                    }}>
                                        <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>Economy Volume</div>
                                        <div style={{ color: '#f1f5f9', fontSize: '18px', fontWeight: 700 }}>
                                            {Math.round(state.stats?.poker_stats?.total_energy_won ?? 0).toLocaleString()}⚡
                                        </div>
                                    </div>
                                    <div style={{
                                        backgroundColor: '#0f172a',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        border: '1px solid #334155',
                                        textAlign: 'center'
                                    }}>
                                        <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>Avg Win Rate</div>
                                        <div style={{ color: '#f1f5f9', fontSize: '18px', fontWeight: 700 }}>
                                            {state.stats?.poker_stats?.win_rate_pct ?? "0%"}
                                        </div>
                                    </div>
                                    <div style={{
                                        backgroundColor: '#0f172a',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        border: '1px solid #334155',
                                        textAlign: 'center'
                                    }}>
                                        <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>🌱 Plant Win Rate</div>
                                        <div style={{ color: '#4ade80', fontSize: '18px', fontWeight: 700 }}>
                                            {state.stats?.poker_stats?.plant_win_rate_pct ?? "0.0%"}
                                        </div>
                                        <div style={{ color: '#64748b', fontSize: '10px', marginTop: '2px' }}>
                                            {state.stats?.poker_stats?.plant_poker_wins ?? 0}W / {state.stats?.poker_stats?.fish_poker_wins ?? 0}L
                                        </div>
                                    </div>
                                    <div style={{
                                        backgroundColor: '#0f172a',
                                        borderRadius: '8px',
                                        padding: '12px',
                                        border: '1px solid #334155',
                                        textAlign: 'center'
                                    }}>
                                        <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '4px' }}>Plant Games</div>
                                        <div style={{ color: '#f1f5f9', fontSize: '18px', fontWeight: 700 }}>
                                            {state.stats?.poker_stats?.total_plant_games?.toLocaleString() ?? 0}
                                        </div>
                                    </div>
                                </div>
                                {/* Leaderboard and Activity */}
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
                                        <PokerLeaderboard leaderboard={state.poker_leaderboard ?? []} />
                                    </div>
                                    <div style={{
                                        backgroundColor: '#0f172a',
                                        borderRadius: '12px',
                                        padding: '16px',
                                        border: '1px solid #334155'
                                    }}>
                                        <PokerEvents events={state.poker_events ?? []} currentFrame={state.snapshot?.frame ?? state.frame ?? 0} />
                                    </div>
                                </div>
                            </div>
                        </CollapsibleSection>
                    </div>
                </div>
            )}

            {/* Phylogenetic Tree */}
            <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                <div className="glass-panel" style={{ padding: '16px' }}>
                    <CollapsibleSection
                        title={
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', width: '100%' }}>
                                <span style={{ fontSize: '16px', fontWeight: 600, color: '#4ade80' }}>Phylogenetic Tree</span>
                            </div>
                        }
                        defaultExpanded={false}
                    >
                        <div style={{ marginTop: '16px', height: '600px', display: 'flex', flexDirection: 'column' }}>
                            <PhylogeneticTree tankId={tankId || state?.tank_id} />
                        </div>
                    </CollapsibleSection>
                </div>
            </div>

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
