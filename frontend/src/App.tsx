/**
 * Main App component
 */

import { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { Canvas } from './components/Canvas';
import { ControlPanel } from './components/ControlPanel';
import { StatsPanel } from './components/StatsPanel';
import { PhylogeneticTree } from './components/PhylogeneticTree';
import { PokerGame } from './components/PokerGame';
import { PokerDashboard } from './components/PokerDashboard';
import type { PokerGameState } from './types/simulation';
import { getEnergyColor } from './utils/energy';
import './App.css';

function App() {
    const { state, isConnected, sendCommand, sendCommandWithResponse } = useWebSocket();
    const [pokerGameState, setPokerGameState] = useState<PokerGameState | null>(null);
    const [showPokerGame, setShowPokerGame] = useState(false);
    const [pokerLoading, setPokerLoading] = useState(false);

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

    return (
        <div className="app">
            <main className="main">
                <div className="top-section">
                    <div className="canvas-wrapper">
                        <div className="canvas-meta">
                            <div>
                                <p className="canvas-label">Status</p>
                                <p className={`canvas-status ${isConnected ? 'online' : 'offline'}`}>
                                    {isConnected ? 'Connected' : 'Waiting'}
                                </p>
                            </div>
                            <div>
                                <p className="canvas-label">Simulation</p>
                                <p className="canvas-value">
                                    {state?.stats?.frame ? state.stats.frame.toLocaleString() : '—'}{' '}
                                    <span>frames</span>
                                </p>
                            </div>
                            <div>
                                <p className="canvas-label">Population</p>
                                <p className="canvas-value">
                                    {state?.stats?.fish_count ?? 0}
                                    <span> fish</span>
                                    {state?.stats && (
                                        <span className="canvas-subvalue">Max Gen {maxGeneration}</span>
                                    )}
                                </p>
                            </div>
                            <div>
                                <p className="canvas-label">Energy</p>
                                <p
                                    className="canvas-value"
                                    style={{ color: getEnergyColor(state?.stats?.total_energy ?? 0) }}
                                >
                                    {state?.stats?.total_energy ? Math.round(state.stats.total_energy).toLocaleString() : '—'}
                                    <span>total</span>
                                </p>
                            </div>
                            <div>
                                <p className="canvas-label">Time</p>
                                <p className="canvas-value">
                                    {state?.stats?.time ?? '—'}
                                </p>
                            </div>
                        </div>
                        <Canvas state={state} width={1088} height={612} />
                        <div className="canvas-glow" aria-hidden />
                    </div>

                    <div className="controls-compact">
                        <ControlPanel
                            onCommand={sendCommand}
                            isConnected={isConnected}
                            onPlayPoker={handleStartPoker}
                        />
                        <StatsPanel stats={state?.stats ?? null} />
                    </div>
                </div>

                <div className="canvas-section">

                    <PokerDashboard state={state} />

                    <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                        <h2 style={{ color: '#00ff00', marginBottom: '10px', fontSize: '20px' }}>
                            Phylogenetic Tree
                        </h2>
                        <PhylogeneticTree />
                    </div>

                    {/* Poker Game */}
                    {showPokerGame && (
                        <div style={{ marginTop: '20px', width: '100%', maxWidth: '1140px' }}>
                            <PokerGame
                                onClose={handleClosePoker}
                                onAction={handlePokerAction}
                                gameState={pokerGameState}
                                loading={pokerLoading}
                            />
                        </div>
                    )}
                </div>
            </main>

            <footer className="footer">
                <p>
                    Built with React + FastAPI + WebSocket | Running at ~30 FPS
                </p>
            </footer>
        </div>
    );
}

export default App;
