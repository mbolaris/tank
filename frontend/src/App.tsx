/**
 * Main App component
 */

import { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { Canvas } from './components/Canvas';
import { ControlPanel } from './components/ControlPanel';
import { PhylogeneticTree } from './components/PhylogeneticTree';
import { PokerGame } from './components/PokerGame';
import { PokerLeaderboard } from './components/PokerLeaderboard';
import PokerEvents from './components/PokerEvents';
import { AutoEvaluateDisplay } from './components/AutoEvaluateDisplay';
import type { PokerGameState } from './types/simulation';
import { getEnergyColor } from './utils/energy';
import './App.css';

function App() {
    const { state, isConnected, sendCommand, sendCommandWithResponse } = useWebSocket();
    const [pokerGameState, setPokerGameState] = useState<PokerGameState | null>(null);
    const [showPokerGame, setShowPokerGame] = useState(false);
    const [pokerLoading, setPokerLoading] = useState(false);
    const [showTree, setShowTree] = useState(false);
    const [showLeaderboard, setShowLeaderboard] = useState(true);

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

    const pokerStats = state?.stats?.poker_stats;
    const minutesElapsed = state ? state.frame / 30 / 60 : 0;
    const gamesPerMinute = minutesElapsed > 0 && pokerStats
        ? (pokerStats.total_games / minutesElapsed).toFixed(1)
        : "0.0";

    return (
        <div className="app">
            <main className="main">
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
                                {state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'} frames
                            </span>
                            <span className="meta-item">
                                <span className="meta-label">Pop</span>
                                {state?.stats?.fish_count ?? 0} fish
                                <span className="meta-sub">Gen {maxGeneration}</span>
                            </span>
                            <span className="meta-item" style={{ color: getEnergyColor(state?.stats?.total_energy ?? 0) }}>
                                <span className="meta-label">Energy</span>
                                {state?.stats?.total_energy ? Math.round(state.stats.total_energy).toLocaleString() : '—'}
                            </span>
                            <span className="meta-item">
                                <span className="meta-label">Time</span>
                                {state?.stats?.time ?? '—'}
                            </span>
                        </div>
                        <Canvas state={state} width={1088} height={612} />
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

                {/* Poker Stats */}
                {pokerStats && (
                    <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                        <div style={{
                            backgroundColor: '#0f172a',
                            borderRadius: '12px',
                            padding: '20px',
                            border: '1px solid #334155'
                        }}>
                            <h3 style={{ color: '#3b82f6', marginBottom: '16px', fontSize: '18px' }}>
                                🎰 Poker Statistics
                            </h3>
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                gap: '16px'
                            }}>
                                <div style={{
                                    padding: '12px',
                                    backgroundColor: '#1e293b',
                                    borderRadius: '8px',
                                    border: '1px solid #334155'
                                }}>
                                    <p style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>Activity Rate</p>
                                    <p style={{ color: '#3b82f6', fontSize: '24px', fontWeight: 'bold' }}>{gamesPerMinute}</p>
                                    <p style={{ color: '#64748b', fontSize: '11px' }}>Games / Minute</p>
                                </div>
                                <div style={{
                                    padding: '12px',
                                    backgroundColor: '#1e293b',
                                    borderRadius: '8px',
                                    border: '1px solid #334155'
                                }}>
                                    <p style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>Total Games</p>
                                    <p style={{ color: '#e2e8f0', fontSize: '24px', fontWeight: 'bold' }}>
                                        {pokerStats.total_games.toLocaleString()}
                                    </p>
                                    <p style={{ color: '#64748b', fontSize: '11px' }}>Lifetime Hands Dealt</p>
                                </div>
                                <div style={{
                                    padding: '12px',
                                    backgroundColor: '#1e293b',
                                    borderRadius: '8px',
                                    border: '1px solid #334155'
                                }}>
                                    <p style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>Economy Volume</p>
                                    <p style={{ color: '#e2e8f0', fontSize: '24px', fontWeight: 'bold' }}>
                                        {Math.round(pokerStats.total_energy_won).toLocaleString()}⚡
                                    </p>
                                    <p style={{ color: '#64748b', fontSize: '11px' }}>Total Energy Exchanged</p>
                                </div>
                                <div style={{
                                    padding: '12px',
                                    backgroundColor: '#1e293b',
                                    borderRadius: '8px',
                                    border: '1px solid #334155'
                                }}>
                                    <p style={{ color: '#94a3b8', fontSize: '12px', marginBottom: '4px' }}>Avg Win Rate</p>
                                    <p style={{ color: '#e2e8f0', fontSize: '24px', fontWeight: 'bold' }}>
                                        {pokerStats.win_rate_pct ?? "0%"}
                                    </p>
                                    <p style={{ color: '#64748b', fontSize: '11px' }}>Population Skill Level</p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Leaderboard & Activity - Side by side (optional) */}
                {showLeaderboard && state?.poker_leaderboard && state?.poker_events && (
                    <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '12px'
                        }}>
                            <h3 style={{ color: '#3b82f6', fontSize: '18px' }}>
                                🏆 Leaderboard & Activity
                            </h3>
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
                                Hide
                            </button>
                        </div>
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
                    </div>
                )}

                {!showLeaderboard && state?.poker_leaderboard && (
                    <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                        <button
                            onClick={() => setShowLeaderboard(true)}
                            style={{
                                padding: '8px 16px',
                                backgroundColor: '#1e293b',
                                color: '#3b82f6',
                                border: '1px solid #475569',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: 600
                            }}
                        >
                            Show Leaderboard & Activity
                        </button>
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
                            <PhylogeneticTree />
                        </div>
                    </div>
                )}
            </main>
            <footer className="footer">
                <p>Built with React + FastAPI + WebSocket | Running at ~30 FPS</p>
            </footer>
        </div>
    );
}

export default App;
